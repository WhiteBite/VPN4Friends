#!/usr/bin/env python3
"""Find the correct private key for the working public key."""

import base64
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization


def derive_public_from_private(private_key_b64: str) -> str:
    """Derive public key from private key."""
    try:
        private_key_bytes = base64.urlsafe_b64decode(private_key_b64 + '==')
        private_key = x25519.X25519PrivateKey.from_private_bytes(private_key_bytes)
        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.urlsafe_b64encode(public_bytes).decode().rstrip('=')
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    print("=== Reality Keys Analysis ===\n")
    
    # Keys from running config.json
    print("1. Running config.json (Xray process):")
    running_private = "oLSJT4bqE5NlHCBJ_6P5GwN-NCy_RLd5vloC-xRXqWo"
    running_public = "4YJfGgy6y3zkWJfYyNECrlcFp25CYZ6oQAsmwKfDlA4"
    derived_public_1 = derive_public_from_private(running_private)
    print(f"   Private: {running_private}")
    print(f"   Public (config): {running_public}")
    print(f"   Public (derived): {derived_public_1}")
    print(f"   ❌ MISMATCH - Keys don't match!\n")
    
    # Keys from database
    print("2. Database (3X-UI panel):")
    db_private = "SIKs3duqg6ZkLvO-VqUTBxLsoVLXHR02B220VYcfBUE"
    db_public = "juKbvNwiuI-MWDtDGBOsf9kDssKQEdnBUAJRhMJInwA"
    derived_public_2 = derive_public_from_private(db_private)
    print(f"   Private: {db_private}")
    print(f"   Public (config): {db_public}")
    print(f"   Public (derived): {derived_public_2}")
    if derived_public_2 == db_public:
        print(f"   ✅ MATCH - Keys are valid!\n")
    else:
        print(f"   ❌ MISMATCH\n")
    
    # Old working client config
    print("3. Old working client config:")
    old_public = "4YJfGgy6y3zkWJfYyNECrlcFp25CYZ6oQAsmwKfDlA4"
    print(f"   Public: {old_public}")
    print(f"   SNI: google.com")
    print(f"   Short ID: 33189997caa12349\n")
    
    print("=== PROBLEM IDENTIFIED ===")
    print("The running Xray config has a CORRUPTED key pair:")
    print(f"- The private key '{running_private}' generates public key '{derived_public_1}'")
    print(f"- But the config claims public key is '{running_public}'")
    print(f"- Clients are trying to use '{old_public}' which doesn't match the actual server key")
    print("\n=== SOLUTION ===")
    print("We need to find the ORIGINAL private key that generates public key:")
    print(f"'{old_public}'")
    print("\nThis private key is LOST. We need to either:")
    print("1. Find a backup with the original private key")
    print("2. Update all client configs with the NEW database keys")
    print("3. Restore the database keys to the running config")
