#!/usr/bin/env bash
# Generate TLS certificates for the AI backend stack.
# Uses FIPS-approved algorithms: ECDSA P-384, SHA-384.
#
# Usage:
#   ./scripts/generate_certs.sh                    # Self-signed CA + server cert
#   ./scripts/generate_certs.sh --cn myhost.local  # Custom CN
#
# Output: certs/ directory with CA and server certificates.

set -euo pipefail

CERT_DIR="$(dirname "$0")/../certs"
CN="${CN:-ai-segment.local}"
DAYS="${DAYS:-365}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cn) CN="$2"; shift 2 ;;
        --days) DAYS="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

mkdir -p "$CERT_DIR"

echo "=== Generating FIPS-compliant TLS certificates ==="
echo "CN: $CN"
echo "Algorithm: ECDSA P-384 + SHA-384"
echo "Validity: $DAYS days"
echo ""

# ── CA certificate ──
if [ ! -f "$CERT_DIR/ca.key" ]; then
    echo "[1/4] Generating CA private key (ECDSA P-384)..."
    openssl ecparam -genkey -name secp384r1 -noout -out "$CERT_DIR/ca.key"

    echo "[2/4] Generating CA certificate..."
    openssl req -new -x509 -sha384 \
        -key "$CERT_DIR/ca.key" \
        -out "$CERT_DIR/ca.crt" \
        -days "$DAYS" \
        -subj "/C=US/O=Neuro DICOM AI/CN=Neuro AI CA"
else
    echo "[skip] CA already exists"
fi

# ── Server certificate ──
echo "[3/4] Generating server private key (ECDSA P-384)..."
openssl ecparam -genkey -name secp384r1 -noout -out "$CERT_DIR/server.key"

echo "[4/4] Generating server certificate..."
cat > "$CERT_DIR/server.ext" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $CN
DNS.2 = localhost
DNS.3 = orthanc
DNS.4 = ai-service
DNS.5 = ollama
DNS.6 = gateway
IP.1 = 127.0.0.1
EOF

openssl req -new -sha384 \
    -key "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.csr" \
    -subj "/C=US/O=Neuro DICOM AI/CN=$CN"

openssl x509 -req -sha384 \
    -in "$CERT_DIR/server.csr" \
    -CA "$CERT_DIR/ca.crt" \
    -CAkey "$CERT_DIR/ca.key" \
    -CAcreateserial \
    -out "$CERT_DIR/server.crt" \
    -days "$DAYS" \
    -extfile "$CERT_DIR/server.ext"

# ── Cleanup CSR and extension file ──
rm -f "$CERT_DIR/server.csr" "$CERT_DIR/server.ext" "$CERT_DIR/ca.srl"

# ── Set permissions ──
chmod 644 "$CERT_DIR"/*.crt
chmod 600 "$CERT_DIR"/*.key

echo ""
echo "=== Certificates generated ==="
echo "  CA cert:     $CERT_DIR/ca.crt"
echo "  Server cert: $CERT_DIR/server.crt"
echo "  Server key:  $CERT_DIR/server.key"
echo ""
echo "Verify:"
openssl x509 -in "$CERT_DIR/server.crt" -noout -text | grep -E "Issuer:|Subject:|Public Key|Signature Algorithm"
