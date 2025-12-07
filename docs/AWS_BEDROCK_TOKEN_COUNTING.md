# AWS Bedrock Token Counting Implementation

## Overview

Token counting has been implemented for all AWS Bedrock models that provide token usage data in their API responses. This enables accurate consumption tracking, cost calculation, and quota enforcement for Bedrock users.

## Supported Models

### ✅ Models with Token Counting

#### 1. **Anthropic Claude** (All Versions)
- **Format**: `response_body.usage.input_tokens`, `response_body.usage.output_tokens`
- **Models**: 
  - `anthropic.claude-3-sonnet-20240229-v1:0`
  - `anthropic.claude-3-5-sonnet-20240620-v1:0`
  - `anthropic.claude-3-haiku-20240307-v1:0`
  - All other Claude variants
- **Works with**: Direct model IDs and inference profiles

#### 2. **Amazon Titan Text Express** (Legacy Format)
- **Format**: 
  - Input: `response_body.inputTextTokenCount`
  - Output: `response_body.results[0].tokenCount`
- **Models**: 
  - `amazon.titan-text-express-v1`
  - `amazon.titan-text-lite-v1`
- **Works with**: Direct model IDs only

#### 3. **Amazon Titan Text Premier & Amazon Nova** (New Format)
- **Format**: `response_body.usage.inputTokens`, `response_body.usage.outputTokens`
- **Models**:
  - `amazon.titan-text-premier-v1:0`
  - `amazon.nova-micro-v1:0`
  - `amazon.nova-lite-v1:0`
  - `amazon.nova-pro-v1:0`
- **Works with**: Direct model IDs and inference profiles (mandatory for Nova)
- **Additional**: Also includes `totalTokens` field

#### 4. **Meta Llama** (All Versions)
- **Format**: `response_body.prompt_token_count`, `response_body.generation_token_count`
- **Models**:
  - `meta.llama2-13b-chat-v1`
  - `meta.llama2-70b-chat-v1`
  - `meta.llama3-8b-instruct-v1:0`
  - `meta.llama3-70b-instruct-v1:0`
  - All other Llama variants
- **Works with**: Direct model IDs and inference profiles

### ❌ Models Without Token Counting

The following providers do **not** return token usage data in their API responses:

- **Cohere Command** - No token fields in response
- **Mistral AI** - No token fields in response
- **AI21 Labs** - No token fields in response

For these models, token counts will be reported as `0`, which may affect:
- Cost calculations (will show $0.00)
- Quota enforcement (won't track usage)
- Analytics (incomplete data)

## Inference Profiles

**Important**: Inference profiles use the **same response format** as their underlying base models.

### Example: Nova Model via Inference Profile
```
Model ARN: arn:aws:bedrock:us-east-1:123456789:inference-profile/us.amazon.nova-lite-v1:0
Response Format: Same as base amazon.nova-lite-v1:0 (new format with usage field)
Token Extraction: response_body.usage.inputTokens, response_body.usage.outputTokens
```

### Example: Claude via Inference Profile
```
Model ID: us.anthropic.claude-3-5-sonnet-20240620-v1:0
Response Format: Same as base claude-3-5-sonnet (usage field)
Token Extraction: response_body.usage.input_tokens, response_body.usage.output_tokens
```

## Implementation Details

### Code Location
- **File**: `src/trusted_data_agent/llm/handler.py`
- **Function**: `call_llm()` - Amazon provider section (lines ~746-780)

### Token Extraction Logic

```python
# Token counts - Extract based on provider response format
input_tokens = 0
output_tokens = 0

if bedrock_provider == 'anthropic':
    # Anthropic Claude: usage.input_tokens, usage.output_tokens
    input_tokens = response_body.get('usage', {}).get('input_tokens', 0)
    output_tokens = response_body.get('usage', {}).get('output_tokens', 0)
    
elif bedrock_provider == 'amazon':
    # Amazon Titan/Nova models have two formats:
    if 'usage' in response_body:
        # New format (Titan Premier, Nova): usage.inputTokens, usage.outputTokens
        input_tokens = response_body.get('usage', {}).get('inputTokens', 0)
        output_tokens = response_body.get('usage', {}).get('outputTokens', 0)
    elif 'inputTextTokenCount' in response_body:
        # Legacy format (Titan Express): inputTextTokenCount, results[0].tokenCount
        input_tokens = response_body.get('inputTextTokenCount', 0)
        if response_body.get('results'):
            output_tokens = response_body['results'][0].get('tokenCount', 0)
            
elif bedrock_provider == 'meta':
    # Meta Llama: prompt_token_count, generation_token_count
    input_tokens = response_body.get('prompt_token_count', 0)
    output_tokens = response_body.get('generation_token_count', 0)
    
# Note: Cohere, Mistral, and AI21 models don't return token counts
# For these providers, tokens will remain 0
```

### Logging

The implementation includes two types of logging:

1. **Debug Log** (when tokens are found):
   ```
   Bedrock token usage - Provider: anthropic, Input: 150, Output: 75
   ```

2. **Warning Log** (when no tokens available):
   ```
   No token usage data available for Bedrock provider: cohere
   ```

## Testing

### Unit Tests
Run the comprehensive test suite:
```bash
python test/test_bedrock_token_counting.py
```

This validates token extraction for:
- Anthropic Claude
- Amazon Titan Express (legacy)
- Amazon Nova (new format)
- Meta Llama
- Cohere (no tokens)
- Inference profiles

### Format Reference Script
View token response formats:
```bash
python test/check_bedrock_token_formats.py
```

## AWS Documentation References

### Official API Documentation
- [InvokeModel API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html)
- [Anthropic Claude Messages](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html)
- [Amazon Titan Text](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-text.html)
- [Amazon Nova](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-nova.html)

### Token Count Examples from AWS Docs

**Titan Text Express:**
```python
response_body = generate_text(model_id, body)
print(f"Input token count: {response_body['inputTextTokenCount']}")
for result in response_body['results']:
    print(f"Token count: {result['tokenCount']}")
```

**Claude Messages:**
```json
{
  "usage": {
    "input_tokens": 10,
    "output_tokens": 25
  }
}
```

## Migration Notes

### Previous Behavior
- ❌ Only Anthropic Claude models had token counting
- ❌ All other Bedrock models showed 0 tokens
- ❌ Cost calculations were incorrect for non-Claude models
- ❌ Quota enforcement didn't work for Titan/Nova/Llama

### Current Behavior
- ✅ Anthropic Claude - Token counts (unchanged)
- ✅ Amazon Titan Express - Token counts (NEW)
- ✅ Amazon Titan Premier - Token counts (NEW)
- ✅ Amazon Nova - Token counts (NEW)
- ✅ Meta Llama - Token counts (NEW)
- ⚠️  Cohere/Mistral/AI21 - Still no token data (documented limitation)

### Impact on Existing Data
- Historical usage data for non-Claude models will still show 0 tokens
- New invocations will track tokens correctly
- No database migration required
- Cost calculations will now be accurate for supported models

## Troubleshooting

### Issue: Tokens showing as 0 for Nova models
**Solution**: Ensure you're using an inference profile ARN, not the direct model ID. Nova models **require** inference profiles.
```
❌ Bad:  amazon.nova-lite-v1:0
✅ Good: arn:aws:bedrock:us-east-1:...:inference-profile/us.amazon.nova-lite-v1:0
```

### Issue: Legacy Titan Express not counting tokens
**Check**: Verify response has `inputTextTokenCount` and `results[0].tokenCount` fields
**Logs**: Look for "Bedrock token usage" debug messages

### Issue: Cohere/Mistral showing 0 tokens
**Expected**: These providers don't return token usage data in their API responses
**Workaround**: Consider using alternative models with token counting if accurate metrics are critical

## Future Enhancements

### Potential Improvements
1. **Estimation for models without token data**: Use tiktoken or similar to estimate tokens for Cohere/Mistral/AI21
2. **Token caching**: Store token counts for repeated identical prompts
3. **Batch token analysis**: Pre-calculate token usage before API calls for quota checking
4. **Provider-specific cost models**: More accurate per-model pricing

### AWS Bedrock Evolution
As AWS adds token usage data to more models:
1. Check for new response fields in API documentation
2. Add extraction logic for new formats
3. Update tests and documentation
4. Announce to users via release notes

## Validation Checklist

Before deploying token counting changes:
- [x] Unit tests pass for all supported formats
- [x] Logs include debug/warning messages
- [x] Error handling for missing fields
- [x] Documentation updated
- [x] Inference profiles tested
- [x] Zero-token providers documented
- [x] Cost calculation integration verified
- [x] Quota enforcement integration verified

---

**Last Updated**: December 7, 2025  
**Version**: 1.0.0  
**Maintainer**: System Architect
