# To Install

## Gcloud CLI

- sudo apt-get update
- sudo apt-get install -y apt-transport-https ca-certificates gnupg curl
- curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
- echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
- sudo apt-get update && sudo apt-get install -y google-cloud-cli
- `gcloud init`
- Set `emi-mower` as the active project:

  ```bash
  gcloud config set project emi-mower
  ```

The Google Cloud CLI account and Application Default Credentials (ADC) are
separate. Log in to the CLI, then create ADC credentials for local tools and
Google client libraries:

```bash
gcloud auth login
gcloud config set project emi-mower
gcloud auth application-default login
```

Terraform uses ADC automatically when it runs locally. The backend's Google
client libraries do the same.

## Terraform CLI

On macOS (Homebrew):

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
terraform version
```

On Ubuntu/Debian:

```bash
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
terraform version
```

Initialize and check this repository's infrastructure after installation:

```bash
cd infrastructure
terraform init
terraform fmt
terraform validate
terraform plan
```

Review the plan before running `terraform apply`.

## Local development service account

Use a dedicated development service account instead of a downloaded JSON key:

```text
emi-mower-backend-dev@emi-mower.iam.gserviceaccount.com
```

Grant the development service account only the roles required by local
development, such as access to the development Cloud Storage bucket. To use
service-account impersonation locally, grant the active Google user the
Service Account Token Creator role on that service account.

Find the active Google user and available service accounts:

```bash
gcloud auth list --filter=status:ACTIVE --format="value(account)"
gcloud iam service-accounts list \
  --project=emi-mower \
  --format="value(email)"
```

Grant impersonation access, replacing the service-account email and user email
with the actual values:

```bash
gcloud iam service-accounts add-iam-policy-binding \
  emi-mower-backend-dev@emi-mower.iam.gserviceaccount.com \
  --project=emi-mower \
  --member="user:YOUR_GOOGLE_EMAIL" \
  --role="roles/iam.serviceAccountTokenCreator"
```

Verify that impersonation works before configuring ADC:

```bash
gcloud auth print-access-token \
  --impersonate-service-account=emi-mower-backend-dev@emi-mower.iam.gserviceaccount.com
```

Configure ADC to impersonate the development service account:

```bash
gcloud auth application-default revoke --quiet
gcloud auth application-default login \
  --impersonate-service-account=emi-mower-backend-dev@emi-mower.iam.gserviceaccount.com
gcloud auth application-default print-access-token
```

The local backend and Terraform now authenticate as the development service
account without storing its private key. Your Google user must have
`roles/iam.serviceAccountTokenCreator` on the development service account.

Production should use a separate service account attached directly to the
production container workload. Do not grant local users access to the
production service account.

## Docker and local ADC

Docker does not automatically see the host's ADC file. Find the Google Cloud
CLI configuration directory:

```bash
gcloud info --format="value(config.paths.global_config_dir)"
```

The ADC file is named `application_default_credentials.json` in that
directory. Add its absolute host path to the uncommitted `backend/.env` file:

```dotenv
GOOGLE_ADC_FILE=/Users/YOUR_USER/.config/gcloud/application_default_credentials.json
GCP_PROJECT_ID=emi-mower
GCS_CUTOUT_BUCKET=emi-mower-cutouts-sandbox
```

Use the committed GCS Compose override; it mounts the file read-only and does
not contain any credentials. Start the local stack with both Compose files:

```bash
docker compose \
  -f local-docker-compose.yml \
  -f local-docker-compose.gcs.yml \
  up -d
```

The ADC file is mounted read-only. Do not copy it into the image or commit it.
Firebase Admin and GCS both use ADC now. `FIREBASE_SERVICE_ACCOUNT_PATH` is an
explicit legacy fallback only; deployed containers should use their attached
production service account instead.

## GCS buckets

`GCS.tf` provisions private `emi-mower-cutouts-sandbox` and
`emi-mower-cutouts-prod` buckets in the single GCP region `us-east1`
(`us-east-1` is AWS notation). Set `GCS_CUTOUT_BUCKET` to the relevant output
per deployment. Grant the backend runtime service account
`roles/storage.objectUser` on both buckets; local impersonated ADC must also
be able to sign V4 URLs through that service account.
