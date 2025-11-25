# TDA Keys Directory

This directory contains security-related keys and certificates for the Trusted Data Agent.

## Files

### `jwt_secret.key` (⚠️ SECURITY CRITICAL)
- **Purpose**: Secret key used to sign JWT authentication tokens
- **Security**: MUST be regenerated for each installation
- **Default**: Ships with a default key for convenience
- **Action Required**: Run `python maintenance/regenerate_jwt_secret.py` after installation

**Why regenerate?**
- Using the default key is a **security risk**
- Each installation should have a unique secret key
- Anyone with the default key can forge authentication tokens

### `license.key`
- **Purpose**: Application license information
- **Distribution**: Safe to distribute with the application
- **Security**: Public license data, not sensitive

### `public_key.pem`
- **Purpose**: Public key for license verification
- **Distribution**: Safe to distribute with the application
- **Security**: Public key, meant to be shared

## Security Best Practices

1. **Always regenerate JWT secret after installation**
2. Keep `jwt_secret.key` private and secure
3. Back up `jwt_secret.key` in a secure location
4. Use appropriate file permissions (600 for jwt_secret.key)
5. Never commit your regenerated `jwt_secret.key` to public repositories

## File Permissions

Recommended permissions:
```bash
chmod 600 tda_keys/jwt_secret.key  # Owner read/write only
chmod 644 tda_keys/license.key      # Owner read/write, others read
chmod 644 tda_keys/public_key.pem   # Owner read/write, others read
```

## Regenerating JWT Secret

To regenerate the JWT secret key:

```bash
python maintenance/regenerate_jwt_secret.py
```

This will:
- Generate a new cryptographically secure random key
- Replace the existing `jwt_secret.key` file
- Set appropriate file permissions
- Invalidate all existing user sessions (users must re-login)
