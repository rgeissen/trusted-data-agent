# REST API Quick Reference

## Authentication

### 1. Register
```bash
POST /auth/register
{
  "username": "api_user",
  "email": "user@example.com", 
  "password": "secure_password"
}
```

### 2. Login (Get Token)
```bash
POST /auth/login
{
  "username": "api_user",
  "password": "secure_password"
}

Response: { "token": "eyJhbGci..." }
```

### 3. Use Token
```bash
Authorization: Bearer eyJhbGci...
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/prompts/<name>/execute` | POST | Execute MCP prompt with LLM |
| `/v1/prompts/<name>/execute-raw` | POST | Execute prompt (raw response) |
| `/v1/configure` | POST | Configure MCP server & LLM |
| `/v1/config/stored-credentials` | GET | List stored credentials |
| `/v1/config/classification` | GET/PUT | Get/set MCP classification |
| `/v1/rag/generate-questions` | POST | Generate RAG questions |

## Quick Example

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"api_user","password":"password"}' \
  | jq -r '.token')

# 2. Execute prompt
curl -X POST http://localhost:5000/v1/prompts/my_prompt/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"key": "value"}}'
```

## Python One-Liner

```python
import requests

# Login
r = requests.post('http://localhost:5000/auth/login', 
                  json={'username':'api_user','password':'pass'})
token = r.json()['token']

# Execute
result = requests.post('http://localhost:5000/v1/prompts/analyze/execute',
                       headers={'Authorization': f'Bearer {token}'},
                       json={'arguments': {'db': 'prod'}}).json()
```

## Common Headers

```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

## Error Codes

- **401** = Not authenticated (login required)
- **403** = Forbidden (insufficient permissions)
- **400** = Bad request (missing parameters)
- **500** = Server error

## Token Info

- **Lifetime:** 24 hours
- **Format:** JWT (JSON Web Token)
- **Header:** `Authorization: Bearer <token>`

See [Full Documentation](REST_API_AUTHENTICATION.md) for details.
