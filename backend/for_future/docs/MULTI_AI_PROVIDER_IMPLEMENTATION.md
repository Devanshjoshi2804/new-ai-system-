# Multi-AI Provider with Automatic Fallback

## Overview
Implemented a robust multi-provider AI system that automatically falls back to alternative providers when rate limits are hit.

## Provider Priority
1. **Groq** (Primary) - Fastest, but has rate limits
2. **Gemini** (Secondary) - Free tier, reliable, good for fallback
3. **Mistral** (Tertiary) - Backup option

## How It Works

### Automatic Fallback
When a provider hits a rate limit or fails, the system automatically tries the next provider:

```
Groq (rate limited) → Gemini (tries next) → Mistral (last resort)
```

### Rate Limit Detection
The system detects rate limits by checking for:
- HTTP 429 status codes
- Keywords: "rate", "limit", "quota", "exceeded"
- Any provider-specific rate limit errors

### Implementation

#### MultiAIProvider Class
Located in: `backend/src/application/ai/parsers/pdf_parser.py`

```python
class MultiAIProvider:
    """
    Multi-provider AI with automatic fallback on rate limits
    Priority: Groq (fastest) -> Gemini (free) -> Mistral (backup)
    """
    
    async def generate_content(self, prompt: str, temperature: float = 0.1, max_tokens: int = 8192) -> tuple[str, str]:
        """
        Generate content with automatic provider fallback
        
        Returns:
            Tuple of (generated_text, provider_name)
        """
```

## Benefits

1. **No Manual Intervention**: System automatically handles rate limits
2. **High Availability**: If one provider fails, others take over
3. **Cost Optimization**: Uses free/cheaper providers when primary is unavailable
4. **Transparent**: Logs which provider was used for each request
5. **Fast Recovery**: No need to wait for rate limit reset

## Usage

The PDF parser now automatically uses the multi-provider system:

```python
# Automatically tries Groq → Gemini → Mistral
result_text, provider_used = await self.ai_provider.generate_content(
    prompt=full_prompt,
    temperature=0.1,
    max_tokens=8192
)

logger.info(f"✅ Successfully used {provider_used}")
```

## Configuration

Ensure you have API keys configured in your `.env` file:

```bash
# Primary (fastest)
GROQ_API_KEY=your_groq_key

# Secondary (free tier)
GEMINI_API_KEY=your_gemini_key

# Tertiary (backup)
MISTRAL_API_KEY=your_mistral_key
```

## Logs

The system provides clear logging:

```
✅ Groq provider available (fastest)
✅ Gemini provider available (free & reliable)
✅ Mistral provider available (backup)
🤖 Multi-AI Provider initialized with 3 providers: Groq, Gemini, Mistral

🔄 Trying Groq...
⚠️ Groq rate limited: 429 Too Many Requests
🔄 Trying Gemini...
✅ Successfully used Gemini
```

## Error Handling

If all providers fail, the system raises an exception with the last error:

```python
raise Exception(f"All AI providers failed. Last error: {last_error}")
```

## Testing

To test the fallback system:
1. Use Groq until rate limited
2. System automatically switches to Gemini
3. Continue processing without interruption

## Future Enhancements

- [ ] Add provider health monitoring
- [ ] Implement smart provider selection based on task type
- [ ] Add provider-specific retry strategies
- [ ] Cache provider availability status
- [ ] Add metrics for provider usage and success rates

