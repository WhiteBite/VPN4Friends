#!/usr/bin/env python3
"""Verify Reality key pair consistency."""

import base64
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization


def verify_key_pair(private_key_b64: str, public_key_b64: str) -> bool:
    """
    Verify if private and public keys form a valid X25519 key pair.
    
    Args:
        private_key_b64: Base64 URL-encoded private key (without padding)
        public_key_b64: Base64 URL-encoded public key (without padding)
    
    Returns:
        True if keys match, False otherwise
    """
    try:
        # Decode base64 URL encoding (Xray uses RawURLEncoding - no padding)
        private_key_bytes = base64.urlsafe_b64decode(private_key_b64 + '==')
        expected_public_bytes = base64.urlsafe_b64decode(public_key_b64 + '==')
        
        # Load private key
        private_key = x25519.X25519PrivateKey.from_private_bytes(private_key_bytes)
        
        # Derive public key from private key
        derived_public_key = private_key.public_key()
        derived_public_bytes = derived_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Compare
        match = derived_public_bytes == expected_public_bytes
        
        print(f"Private key (input): {private_key_b64}")
        print(f"Expected public key: {public_key_b64}")
        print(f"Derived public key:  {base64.urlsafe_b64encode(derived_public_bytes).decode().rstrip('=')}")
        print(f"Keys match: {match}")
        
        return match
        
    except Exception as e:
        print(f"Error verifying keys: {e}")
        return False


if __name__ == "__main__":
    # Keys from server config.json
    server_private = "oLSJT4bqE5NlHCBJ_6P5GwN-NCy_RLd5vloC-xRXqWo"
    server_public = "4YJfGgy6y3zkWJfYyNECrlcFp25CYZ6oQAsmwKfDlA4"
    
    print("=== Verifying Server Reality Keys ===\n")
    is_valid = verify_key_pair(server_private, server_public)
    
    if is_valid:
        print("\n✅ Key pair is VALID - private and public keys match!")
    else:
        print("\n❌ Key pair is INVALID - keys do NOT match!")
        print("\nThis means the server configuration is corrupted.")
        print("The private key does not correspond to the public key.")
