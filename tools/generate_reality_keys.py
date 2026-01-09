#!/usr/bin/env python3
"""Generate Reality keys using curve25519."""

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
import base64

# Generate private key
private_key = x25519.X25519PrivateKey.generate()
public_key = private_key.public_key()

# Get raw bytes
private_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption()
)

public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)

# Encode to base64
private_b64 = base64.b64encode(private_bytes).decode('utf-8')
public_b64 = base64.b64encode(public_bytes).decode('utf-8')

print(f"Private Key: {private_b64}")
print(f"Public Key: {public_b64}")
