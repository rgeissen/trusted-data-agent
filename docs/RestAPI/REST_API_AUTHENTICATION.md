# REST API Authentication Guide

## Overview

The Trusted Data Agent REST API supports two authentication methods:
1. **Access Tokens** (Recommended for REST API) - Long-lived tokens for programmatic access
2. **JWT Tokens** (For web UI) - Short-lived session tokens

This guide explains both methods.

## Authentication Methods

### Method 1: Access Tokens (Recommended)

**Best for:** REST API clients, automation scripts, external integrations

**Advantages:**
- ✅ Long-lived (configurable expiration or never expires)
- ✅ Easy to rotate and revoke
- ✅ No need to store username/password
- ✅ Track usage per token
- ✅ Multiple tokens per user (e.g., "Production", "Development")

### Method 2: JWT Tokens

**Best for:** Web UI sessions, short-term access

**Advantages:**
- ✅ Automatic expiration (24 hours)
- ✅ Stateless authentication

---

## Quick Start: Access Tokens

### 1. Login to Get JWT Token (One Time)

```bash
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "api_user",
    "email": "user@example.com",
    "password": "secure_password_123"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "User registered successfully",
  "user": {
    "id": "user-uuid-here",
    "username": "api_user",
    "email": "user@example.com"
  }
}
```

### 2. Login to Get JWT Token

```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "api_user",
    "password": "secure_password_123"
  }'
```

**Response:**
```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user-uuid-here",
    "username": "api_user",
    "email": "user@example.com"
  }
}
```

**Save this token!** You'll need it for all subsequent API calls.

### 3. Use Token in API Calls

Include the JWT token in the `Authorization` header:

```bash
curl -X POST http://localhost:5000/v1/prompts/my_prompt/execute \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "arguments": {
      "database": "production"
    }
  }'
```

## REST API Endpoints

### Execute MCP Prompt

Execute an MCP prompt with the configured LLM.

**Endpoint:** `POST /v1/prompts/<prompt_name>/execute`

**Headers:**
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "arguments": {
    "arg1": "value1",
    "arg2": "value2"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "prompt_text": "Rendered prompt with arguments",
  "response": "LLM response text",
  "input_tokens": 123,
  "output_tokens": 456
}
```

**Example:**
```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST http://localhost:5000/v1/prompts/analyze_database/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "arguments": {
      "database": "customers",
      "focus": "performance"
    }
  }'
```

### Execute Raw Prompt

Execute a prompt and return raw MCP response without LLM processing.

**Endpoint:** `POST /v1/prompts/<prompt_name>/execute-raw`

**Headers:**
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "arguments": {
    "arg1": "value1"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "messages": [
    {
      "role": "user",
      "content": {
        "type": "text",
        "text": "Prompt content"
      }
    }
  ]
}
```

### Configure Application

Configure MCP server and LLM settings.

**Endpoint:** `POST /v1/configure`

**Headers:**
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "mcp_config": {
    "server_name": "my-mcp-server",
    "host": "localhost",
    "port": 3000,
    "use_sse": false
  },
  "llm_config": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "credentials": {
      "api_key": "your_api_key_here"
    }
  }
}
```

### Get Stored Credentials

Retrieve stored credentials for LLM providers.

**Endpoint:** `GET /v1/config/stored-credentials`

**Headers:**
```
Authorization: Bearer <your_jwt_token>
```

**Response:**
```json
{
  "status": "success",
  "providers": {
    "anthropic": {
      "has_credentials": true,
      "credential_keys": ["api_key"]
    },
    "aws": {
      "has_credentials": true,
      "credential_keys": ["access_key_id", "secret_access_key", "region"]
    }
  }
}
```

## Token Management

### Token Expiration

JWT tokens expire after **24 hours** by default. When a token expires, you'll receive a `401 Unauthorized` response:

```json
{
  "status": "error",
  "message": "Authentication required. Please login."
}
```

**Solution:** Login again to get a new token.

### Refresh Token

To get a new token without re-entering credentials:

```bash
curl -X POST http://localhost:5000/auth/refresh \
  -H "Authorization: Bearer <your_expired_token>"
```

## Python Client Example

```python
import requests
import json

class TDAClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.token = None
    
    def login(self, username, password):
        """Login and store JWT token"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        data = response.json()
        if data.get("status") == "success":
            self.token = data.get("token")
            return True
        return False
    
    def execute_prompt(self, prompt_name, arguments=None):
        """Execute MCP prompt with LLM"""
        if not self.token:
            raise Exception("Not authenticated. Call login() first.")
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.base_url}/v1/prompts/{prompt_name}/execute",
            headers=headers,
            json={"arguments": arguments or {}}
        )
        
        return response.json()
    
    def configure(self, mcp_config, llm_config):
        """Configure MCP server and LLM"""
        if not self.token:
            raise Exception("Not authenticated. Call login() first.")
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.base_url}/v1/configure",
            headers=headers,
            json={
                "mcp_config": mcp_config,
                "llm_config": llm_config
            }
        )
        
        return response.json()

# Usage
client = TDAClient()

# Login
if client.login("api_user", "secure_password"):
    print("✓ Logged in successfully")
    
    # Execute prompt
    result = client.execute_prompt(
        "analyze_database",
        {"database": "customers"}
    )
    
    print(f"Response: {result['response']}")
    print(f"Tokens: {result['input_tokens']} in, {result['output_tokens']} out")
else:
    print("✗ Login failed")
```

## JavaScript/Node.js Client Example

```javascript
const axios = require('axios');

class TDAClient {
    constructor(baseURL = 'http://localhost:5000') {
        this.baseURL = baseURL;
        this.token = null;
    }
    
    async login(username, password) {
        try {
            const response = await axios.post(
                `${this.baseURL}/auth/login`,
                { username, password }
            );
            
            if (response.data.status === 'success') {
                this.token = response.data.token;
                return true;
            }
            return false;
        } catch (error) {
            console.error('Login failed:', error.message);
            return false;
        }
    }
    
    async executePrompt(promptName, arguments = {}) {
        if (!this.token) {
            throw new Error('Not authenticated. Call login() first.');
        }
        
        const response = await axios.post(
            `${this.baseURL}/v1/prompts/${promptName}/execute`,
            { arguments },
            {
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        
        return response.data;
    }
    
    async configure(mcpConfig, llmConfig) {
        if (!this.token) {
            throw new Error('Not authenticated. Call login() first.');
        }
        
        const response = await axios.post(
            `${this.baseURL}/v1/configure`,
            {
                mcp_config: mcpConfig,
                llm_config: llmConfig
            },
            {
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        
        return response.data;
    }
}

// Usage
(async () => {
    const client = new TDAClient();
    
    // Login
    const loggedIn = await client.login('api_user', 'secure_password');
    if (loggedIn) {
        console.log('✓ Logged in successfully');
        
        // Execute prompt
        const result = await client.executePrompt('analyze_database', {
            database: 'customers'
        });
        
        console.log(`Response: ${result.response}`);
        console.log(`Tokens: ${result.input_tokens} in, ${result.output_tokens} out`);
    } else {
        console.log('✗ Login failed');
    }
})();
```

## Error Handling

### 401 Unauthorized
**Cause:** Missing or invalid JWT token  
**Solution:** Login again to get a new token

```json
{
  "status": "error",
  "message": "Authentication required. Please login."
}
```

### 403 Forbidden
**Cause:** Token valid but user doesn't have permission  
**Solution:** Check user permissions or contact admin

### 400 Bad Request
**Cause:** Missing required parameters or invalid configuration  
**Solution:** Check request body and ensure all required fields are present

## Security Best Practices

### 1. Store Tokens Securely
```python
# ✅ Good - Use environment variables
import os
TOKEN = os.environ.get('TDA_JWT_TOKEN')

# ✅ Good - Use credential manager
import keyring
TOKEN = keyring.get_password('tda', 'jwt_token')

# ❌ Bad - Hardcoded in source
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 2. Use HTTPS in Production
```python
# ✅ Production
client = TDAClient(base_url="https://tda.company.com")

# ⚠️ Development only
client = TDAClient(base_url="http://localhost:5000")
```

### 3. Implement Token Refresh
```python
def execute_with_retry(client, prompt_name, arguments):
    try:
        return client.execute_prompt(prompt_name, arguments)
    except Unauthorized:
        # Token expired - refresh and retry
        client.refresh_token()
        return client.execute_prompt(prompt_name, arguments)
```

### 4. Handle Token Expiration
```python
import time

class TDAClient:
    def __init__(self):
        self.token = None
        self.token_expires_at = 0
    
    def login(self, username, password):
        # ... login logic ...
        self.token_expires_at = time.time() + (24 * 60 * 60)  # 24 hours
    
    def is_token_valid(self):
        return self.token and time.time() < self.token_expires_at
    
    def execute_prompt(self, prompt_name, arguments):
        if not self.is_token_valid():
            raise Exception("Token expired. Please login again.")
        # ... execute logic ...
```

## Migration from Old Header-Based Auth

**Old Method (Deprecated):**
```bash
curl -X POST http://localhost:5000/v1/prompts/my_prompt/execute \
  -H "X-TDA-User-UUID: user-uuid-here" \
  -H "Content-Type: application/json"
```

**New Method (Required):**
```bash
curl -X POST http://localhost:5000/v1/prompts/my_prompt/execute \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json"
```

**Migration Steps:**
1. Register user account via `/auth/register`
2. Login to get JWT token via `/auth/login`
3. Replace `X-TDA-User-UUID` header with `Authorization: Bearer <token>`
4. Update any automated scripts/clients

## Troubleshooting

### "No valid authentication token provided"
- Check that `Authorization` header is present
- Verify header format: `Authorization: Bearer <token>`
- Ensure token hasn't expired (24 hour lifetime)

### "REST API authentication error"
- Token may be malformed or corrupted
- Login again to get a fresh token
- Check server logs for detailed error message

### Token Works in Browser But Not API
- Ensure you're copying the full token from login response
- Check for extra whitespace or newlines in token string
- Verify you're using `Bearer ` prefix (with space after)

## Complete Example: Automated Workflow

```python
#!/usr/bin/env python3
"""
Automated TDA workflow with JWT authentication.
Runs daily analysis and sends results.
"""
import os
import requests
from datetime import datetime

# Configuration
TDA_URL = os.environ.get('TDA_URL', 'http://localhost:5000')
TDA_USERNAME = os.environ['TDA_USERNAME']
TDA_PASSWORD = os.environ['TDA_PASSWORD']

def get_auth_token():
    """Login and get JWT token"""
    response = requests.post(
        f"{TDA_URL}/auth/login",
        json={
            "username": TDA_USERNAME,
            "password": TDA_PASSWORD
        }
    )
    data = response.json()
    
    if data.get("status") != "success":
        raise Exception(f"Login failed: {data.get('message')}")
    
    return data.get("token")

def execute_analysis(token, database):
    """Run daily database analysis"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{TDA_URL}/v1/prompts/daily_analysis/execute",
        headers=headers,
        json={
            "arguments": {
                "database": database,
                "date": datetime.now().isoformat()
            }
        }
    )
    
    return response.json()

def main():
    print("Starting automated analysis...")
    
    # Authenticate
    token = get_auth_token()
    print("✓ Authenticated successfully")
    
    # Run analysis
    result = execute_analysis(token, "production")
    
    if result.get("status") == "success":
        print("✓ Analysis complete")
        print(f"Response: {result['response']}")
        print(f"Tokens used: {result['input_tokens']} + {result['output_tokens']}")
        
        # Process results...
        # Send notifications...
    else:
        print(f"✗ Analysis failed: {result.get('message')}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
```

## Summary

- ✅ **All REST API endpoints require JWT authentication**
- ✅ **Login via `/auth/login` to get token**
- ✅ **Include token in `Authorization: Bearer <token>` header**
- ✅ **Tokens expire after 24 hours**
- ✅ **Use HTTPS in production**
- ✅ **Store tokens securely (not in source code)**

For more information, see:
- [Authentication System Documentation](../AUTH_ONLY_MIGRATION.md)
- [Main README](../../README.md)
