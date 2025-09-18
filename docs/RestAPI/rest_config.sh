curl -X POST http://127.0.0.1:5000/configure \
-H "Content-Type: application/json" \
-d '{
    "provider": "<LLMProvider>",
    "model": "<LLMProviderModel>",
    "apiKey": "<AccessKey>",
    "server_name": "<MCPServer Descriptive Name>",
    "host": "<MCPServer Hostname>",
    "port": "<MCPServer Port",
    "path": "/mcp",
    "tts_credentials_json": "<Google Cloud TTS Credentials>"
}'