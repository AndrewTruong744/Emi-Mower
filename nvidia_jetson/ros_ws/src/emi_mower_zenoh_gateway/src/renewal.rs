//! TPM-authorized replacement of a short-lived operational Zenoh certificate.

use anyhow::{bail, Context, Result};
use base64::{engine::general_purpose::STANDARD, Engine as _};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::Path;
use std::process::Command;
use zenoh::config::Config;

use crate::generated::zenoh_paths::{
    mower_certificate_renew_challenge_path, mower_certificate_renew_complete_path,
};

const RENEW_WITHIN_SECONDS: u64 = 30 * 24 * 60 * 60;

pub async fn renew_certificate_if_needed(mower_id: &str) -> Result<bool> {
    let certificate_path = Path::new("/etc/mower/certs/mower.crt");
    if certificate_path.exists()
        && certificate_valid_beyond(certificate_path, RENEW_WITHIN_SECONDS)?
    {
        return Ok(false);
    }

    let bootstrap_config = env::var("ZENOH_BOOTSTRAP_CONFIG")
        .context("set ZENOH_BOOTSTRAP_CONFIG for certificate renewal")?;
    let config = Config::from_file(bootstrap_config)
        .map_err(|error| anyhow::anyhow!("load bootstrap Zenoh config: {error}"))?;
    let session = zenoh::open(config)
        .await
        .map_err(|error| anyhow::anyhow!("open bootstrap Zenoh session: {error}"))?;
    let challenge_path = mower_certificate_renew_challenge_path(mower_id);
    let challenge = query_json(&session, &challenge_path, br#"{}"#).await?;
    let nonce = challenge
        .get("nonce")
        .and_then(serde_json::Value::as_str)
        .context("renewal challenge did not contain nonce")?;

    let (csr, new_key_path) = create_operational_csr(mower_id)?;
    let signature = sign_renewal_message(mower_id, nonce, &csr)?;
    let complete_path = mower_certificate_renew_complete_path(mower_id);
    let request = serde_json::json!({
        "nonce": nonce,
        "csr_pem": csr,
        "tpm_signature": signature,
    });
    let response = query_json(&session, &complete_path, request.to_string().as_bytes()).await?;
    let certificate = response
        .get("certificate_pem")
        .and_then(serde_json::Value::as_str)
        .context("renewal response did not contain certificate_pem")?;
    install_credentials(&new_key_path, certificate)?;
    session
        .close()
        .await
        .map_err(|error| anyhow::anyhow!("close bootstrap Zenoh session: {error}"))?;
    Ok(true)
}

fn certificate_valid_beyond(path: &Path, seconds: u64) -> Result<bool> {
    let status = Command::new("openssl")
        .args(["x509", "-checkend", &seconds.to_string(), "-noout", "-in"])
        .arg(path)
        .status()
        .context("run openssl certificate expiry check")?;
    Ok(status.success())
}

fn create_operational_csr(mower_id: &str) -> Result<(String, String)> {
    let key_path = "/tmp/emi-mower-renewal.key";
    let csr_path = "/tmp/emi-mower-renewal.csr";
    let subject = format!("/C=US/O=EmiSamaTechnologies/CN=mower:{mower_id}");
    let status = Command::new("openssl")
        .args([
            "req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout", key_path, "-out", csr_path,
            "-subj", &subject,
        ])
        .status()
        .context("create operational certificate request")?;
    if !status.success() {
        bail!("openssl could not create renewal CSR");
    }
    Ok((fs::read_to_string(csr_path)?, key_path.to_owned()))
}

fn sign_renewal_message(mower_id: &str, nonce: &str, csr: &str) -> Result<String> {
    let digest = Sha256::digest(csr.as_bytes());
    let mut message = b"emi-mower-renew-v1\0".to_vec();
    message.extend_from_slice(mower_id.as_bytes());
    message.push(0);
    message.extend_from_slice(nonce.as_bytes());
    message.push(0);
    message.extend_from_slice(&digest);
    let message_path = "/tmp/emi-mower-renewal-message";
    let signature_path = "/tmp/emi-mower-renewal-signature";
    fs::write(message_path, message)?;
    let handle = env::var("TPM_DEVICE_ROOT_HANDLE").unwrap_or_else(|_| "0x81000001".to_owned());
    let status = Command::new("tpm2_sign")
        .args([
            "-c",
            &handle,
            "-g",
            "sha256",
            "-m",
            message_path,
            "-f",
            "der",
            "-o",
            signature_path,
        ])
        .status()
        .context("ask TPM to sign renewal request")?;
    if !status.success() {
        bail!("TPM could not sign renewal request");
    }
    Ok(STANDARD.encode(fs::read(signature_path)?))
}

fn install_credentials(new_key_path: &str, certificate: &str) -> Result<()> {
    let directory = Path::new("/etc/mower/certs");
    fs::write(directory.join("mower.crt.new"), certificate)?;
    let status = Command::new("openssl")
        .args(["verify", "-CAfile"])
        .arg(directory.join("root_ca.pem"))
        .arg(directory.join("mower.crt.new"))
        .status()
        .context("verify renewed mower certificate against the installed CA")?;
    if !status.success() {
        bail!("renewal response certificate is not signed by the installed CA");
    }
    fs::rename(new_key_path, directory.join("mower.key.new"))?;
    fs::rename(directory.join("mower.key.new"), directory.join("mower.key"))?;
    fs::rename(directory.join("mower.crt.new"), directory.join("mower.crt"))?;
    Ok(())
}

async fn query_json(
    session: &zenoh::Session,
    key: &str,
    payload: &[u8],
) -> Result<serde_json::Value> {
    let replies = session
        .get(key)
        .payload(payload)
        .await
        .map_err(|error| anyhow::anyhow!("query bootstrap route {key}: {error}"))?;
    let reply = replies
        .recv_async()
        .await
        .map_err(|error| anyhow::anyhow!("receive bootstrap reply: {error}"))?;
    let sample = reply
        .result()
        .map_err(|error| anyhow::anyhow!("bootstrap route rejected query: {error}"))?;
    Ok(serde_json::from_slice(
        sample.payload().to_bytes().as_ref(),
    )?)
}
