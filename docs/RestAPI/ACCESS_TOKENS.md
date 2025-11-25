# Access Tokens Quick Guide

## What Are Access Tokens?

Access tokens are **long-lived API keys** that allow programmatic access to the REST API without exposing your username and password.

**Format:** `tda_` + 32 random characters (e.g., `tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p`)

---

## Creating an Access Token

### Option 1: Via Web UI (Coming Soon)

1. Login to the web interface
2. Go to **Settings → Advanced → Access Tokens**
3. Click **"Create New Token"**
4. Enter a name (e.g., "Production Server")
5. Optional: Set expiration (e.g., 90 days)
6. Click **"Generate Token"**
7. **Copy the token immediately** - it won't be shown again!

### Option 2: Via REST API

```bash
# Step 1: Login to get JWT token
JWT=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}' \
  | jq -r '.token')

# Step 2: Create access token
curl -X POST http://localhost:5000/api/v1/auth/tokens \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Server",
    "expires_in_days": 90
  }'
```

**Response:**
```json
{
  "status": "success",
  "token": "tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p",
  "token_id": "uuid-here",
  "name": "Production Server",
  "created_at": "2025-11-25T10:00:00Z",
  "expires_at": "2026-02-25T10:00:00Z"
}
```

⚠️ **IMPORTANT:** Copy the `token` value now! It cannot be retrieved later.

---

## Using Access Tokens

### In cURL

```bash
TOKEN="tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p"

curl -X POST http://localhost:5000/v1/prompts/my_prompt/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"database": "prod"}}'
```

### In Python

```python
import requests

TOKEN = "tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p"
BASE_URL = "http://localhost:5000"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

response = requests.post(
    f"{BASE_URL}/v1/prompts/analyze/execute",
    headers=headers,
    json={"arguments": {"database": "production"}}
)

print(response.json())
```

### In JavaScript

```javascript
const TOKEN = 'tda_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p';
const BASE_URL = 'http://localhost:5000';

fetch(`${BASE_URL}/v1/prompts/analyze/execute`, {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${TOKEN}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        arguments: { database: 'production' }
    })
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## Managing Tokens

### List All Tokens

```bash
curl -X GET http://localhost:5000/api/v1/auth/tokens \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "status": "success",
  "tokens": [
    {
      "id": "uuid",
      "name": "Production Server",
      "token_prefix": "tda_1a2b3c...",
      "created_at": "2025-11-25T10:00:00Z",
      "last_used_at": "2025-11-25T14:30:00Z",
      "expires_at": "2026-02-25T10:00:00Z",
      "revoked": false,
      "use_count": 142
    }
  ]
}
```

### Revoke a Token

```bash
TOKEN_ID="uuid-of-token-to-revoke"

curl -X DELETE http://localhost:5000/api/v1/auth/tokens/$TOKEN_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## Best Practices

### ✅ DO

- **Store tokens securely** (environment variables, secret managers)
- **Use descriptive names** ("Production Server", "CI/CD Pipeline")
- **Set expiration dates** for sensitive environments
- **Rotate tokens regularly** (every 90 days)
- **Revoke unused tokens** immediately
- **Use one token per application** for easier tracking

### ❌ DON'T

- **Don't commit tokens to git**
- **Don't share tokens between applications**
- **Don't use expired tokens** (they won't work)
- **Don't store tokens in plain text files**
- **Don't reuse revoked tokens** (create new ones)

---

## Token Security

### Storage Examples

**✅ Good - Environment Variable:**
```bash
export TDA_ACCESS_TOKEN="tda_1a2b3c..."
python my_script.py
```

**✅ Good - Secret Manager:**
```python
from my_secrets import get_secret
TOKEN = get_secret('tda_access_token')
```

**✅ Good - .env File (gitignored):**
```bash
# .env
TDA_ACCESS_TOKEN=tda_1a2b3c...
```

```python
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('TDA_ACCESS_TOKEN')
```

**❌ Bad - Hardcoded:**
```python
TOKEN = "tda_1a2b3c..."  # DON'T DO THIS!
```

---

## Comparison: Access Tokens vs JWT Tokens

| Feature | Access Tokens | JWT Tokens |
|---------|---------------|------------|
| **Lifetime** | Configurable (or never) | 24 hours |
| **Use Case** | REST API, automation | Web UI sessions |
| **Format** | `tda_xxxxx...` | `eyJhbGci...` |
| **Revocation** | Manual (anytime) | Automatic (24h) |
| **Storage** | User manages | Browser manages |
| **Best For** | Scripts, integrations | Interactive sessions |

---

## Troubleshooting

### "Invalid or revoked access token"
- **Cause:** Token was revoked or doesn't exist
- **Solution:** Create a new token

### "Authentication required"
- **Cause:** Missing `Authorization` header
- **Solution:** Add `Authorization: Bearer tda_xxxxx...`

### Token Not Working
1. Check token format starts with `tda_`
2. Verify token hasn't been revoked
3. Check if token has expired
4. Ensure correct header format: `Authorization: Bearer <token>`

### "Token not found"
- **Cause:** Trying to revoke non-existent token
- **Solution:** List tokens to get correct ID

---

## API Reference

### Create Token
- **Endpoint:** `POST /api/v1/auth/tokens`
- **Auth:** Requires JWT or access token
- **Body:** `{"name": "...", "expires_in_days": 90}`
- **Returns:** Full token (shown once only)

### List Tokens
- **Endpoint:** `GET /api/v1/auth/tokens`
- **Auth:** Requires JWT or access token
- **Query:** `?include_revoked=true` (optional)
- **Returns:** Array of token metadata

### Revoke Token
- **Endpoint:** `DELETE /api/v1/auth/tokens/{token_id}`
- **Auth:** Requires JWT or access token
- **Returns:** Success/error message

---

## Examples

### Automation Script

```bash
#!/bin/bash
# daily_analysis.sh

TOKEN="${TDA_ACCESS_TOKEN}"
BASE_URL="http://localhost:5000"

# Run analysis
curl -X POST "$BASE_URL/v1/prompts/daily_analysis/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "arguments": {
      "database": "production",
      "date": "'$(date +%Y-%m-%d)'"
    }
  }' | jq '.response'
```

### Python Client

```python
import os
import requests

class TDAClient:
    def __init__(self):
        self.token = os.getenv('TDA_ACCESS_TOKEN')
        self.base_url = os.getenv('TDA_BASE_URL', 'http://localhost:5000')
        
        if not self.token:
            raise ValueError("TDA_ACCESS_TOKEN not set")
    
    def execute_prompt(self, prompt_name, arguments=None):
        response = requests.post(
            f"{self.base_url}/v1/prompts/{prompt_name}/execute",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            },
            json={"arguments": arguments or {}}
        )
        response.raise_for_status()
        return response.json()

# Usage
client = TDAClient()
result = client.execute_prompt("analyze_database", {"database": "prod"})
print(result['response'])
```

---

## See Also

- [Full REST API Authentication Guide](REST_API_AUTHENTICATION.md)
- [REST API Quick Reference](QUICK_REFERENCE.md)
- [Main README](../../README.md)
