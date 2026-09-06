import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const outputPath = resolve(scriptDirectory, '../src/zenoh/generated/types.py');
const initPath = resolve(scriptDirectory, '../src/zenoh/generated/__init__.py');
const appTypesPath = resolve(scriptDirectory, '../../app/src/generated/zenoh.ts');
const source = readFileSync(outputPath, 'utf8');
const marker = '# Bootstrap renewal schemas generated from zenoh_asyncapi.yaml.\n';
const retained = source.split(marker)[0].trimEnd();
const renewalTypes = `

${marker}
class MowerCertificateRenewChallengeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MowerCertificateRenewChallengeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str
    expires_in: int


class MowerCertificateRenewCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str
    csr_pem: str
    tpm_signature: str


class MowerCertificateRenewCompleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certificate_pem: str
    ca_chain_pem: str
    expires_at: datetime
`;
writeFileSync(outputPath, `${retained}${renewalTypes}`);

const initSource = readFileSync(initPath, 'utf8');
const initMarker = '# Bootstrap renewal exports generated from zenoh_asyncapi.yaml.\n';
const retainedInit = initSource.split(initMarker)[0].trimEnd();
const renewalExports = `

${initMarker}from src.zenoh.generated.types import (
    MowerCertificateRenewChallengeRequest,
    MowerCertificateRenewChallengeResponse,
    MowerCertificateRenewCompleteRequest,
    MowerCertificateRenewCompleteResponse,
)

__all__ += [
    "MowerCertificateRenewChallengeRequest",
    "MowerCertificateRenewChallengeResponse",
    "MowerCertificateRenewCompleteRequest",
    "MowerCertificateRenewCompleteResponse",
]
`;
writeFileSync(initPath, `${retainedInit}${renewalExports}`);

const appTypes = readFileSync(appTypesPath, 'utf8');
const appMarker = '// Bootstrap renewal types generated from zenoh_asyncapi.yaml.\n';
const retainedAppTypes = appTypes.split(appMarker)[0].trimEnd();
const renewalAppTypes = `

${appMarker}export type MowerCertificateRenewChallengeRequest = Record<string, never>;

export interface MowerCertificateRenewChallengeResponse {
  nonce: string;
  expires_in: number;
}

export interface MowerCertificateRenewCompleteRequest {
  nonce: string;
  csr_pem: string;
  tpm_signature: string;
}

export interface MowerCertificateRenewCompleteResponse {
  certificate_pem: string;
  ca_chain_pem: string;
  expires_at: string;
}
`;
writeFileSync(appTypesPath, `${retainedAppTypes}${renewalAppTypes}`);
