#!/bin/bash

# Configuration Filenames
CONFIG_FILE="mower.cnf"
PRIVATE_KEY="mower.key"
CSR_FILE="mower.csr"
CERT_FILE="mower.crt"

# Relative paths to your Master CA (adjust if your folder structure differs)
CA_CERT="../../backend/certs/ca/ca.crt"
CA_KEY="../../backend/certs/ca/ca.key"

# Exit immediately if a command exits with a non-zero status
set -e

echo "=== 2. Generating Mower Private Key (${PRIVATE_KEY}) ==="
openssl genrsa -out ${PRIVATE_KEY} 2048

echo "=== 3. Creating Certificate Signing Request (${CSR_FILE}) ==="
openssl req -new -key ${PRIVATE_KEY} -out ${CSR_FILE} -config ${CONFIG_FILE}

echo "=== 4. Signing Request with Authority to Generate Certificate (${CERT_FILE}) ==="
if [ ! -f "$CA_CERT" ] || [ ! -f "$CA_KEY" ]; then
    echo "ERROR: Master CA files not found at targets!"
    echo "Expected: ${CA_CERT} and ${CA_KEY}"
    exit 1
fi

openssl x509 -req -in ${CSR_FILE} \
  -CA ${CA_CERT} -CAkey ${CA_KEY} -CAcreateserial \
  -out ${CERT_FILE} -days 365 -sha256 \
  -extfile ${CONFIG_FILE} -extensions req_ext

echo "=== 5. Cleaning up intermediate CSR files ==="
rm ${CSR_FILE}

echo "🎉 Success! Mower identities generated securely."
ls -l ${PRIVATE_KEY} ${CERT_FILE}