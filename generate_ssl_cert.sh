#!/bin/bash
# Generate self-signed SSL certificate for Reachy project
# For production, replace with proper CA-signed certificates

set -e

CERT_DIR="/etc/ssl/reachy"
DOMAIN="10.0.4.140"
DAYS=365

echo "Creating SSL certificate directory..."
sudo mkdir -p "$CERT_DIR"

echo "Generating self-signed certificate for $DOMAIN..."
sudo openssl req -x509 -nodes -days $DAYS -newkey rsa:4096 \
    -keyout "$CERT_DIR/reachy.key" \
    -out "$CERT_DIR/reachy.crt" \
    -subj "/C=US/ST=State/L=City/O=Reachy/CN=$DOMAIN" \
    -addext "subjectAltName=IP:$DOMAIN,IP:127.0.0.1,DNS:localhost"

echo "Setting permissions..."
sudo chmod 600 "$CERT_DIR/reachy.key"
sudo chmod 644 "$CERT_DIR/reachy.crt"

echo "Certificate generated:"
echo "  Certificate: $CERT_DIR/reachy.crt"
echo "  Private Key: $CERT_DIR/reachy.key"
echo ""
echo "To view certificate details:"
echo "  sudo openssl x509 -in $CERT_DIR/reachy.crt -text -noout"
