# Rate Limiting Implementation

## Overview

Rate limiting has been implemented using the `slowapi` library to protect the VibeSDLC API from abuse, brute-force attacks, and DDoS attempts.

## Rate Limits by Endpoint

### Authentication Endpoints (`/auth/*`)

| Endpoint | Rate Limit | Reason |
|----------|-----------|--------|
| `POST /auth/register` | **3 requests/hour** | Prevent account spam and abuse |
| `POST /auth/login` | **5 requests/minute** | Prevent brute-force password attacks |
| `POST /auth/refresh` | **10 requests/minute** | Allow normal token refresh while preventing abuse |
| `POST /auth/logout` | **20 requests/minute** | Generous limit for normal logout operations |

### User Endpoints (`/users/*`)

| Endpoint | Rate Limit | Reason |
|----------|-----------|--------|
| `GET /users/me` | **30 requests/minute** | Frequently accessed, allow normal usage |
| `PUT /users/me` | **10 requests/minute** | Profile updates are less frequent |
| `POST /users/change-password` | **5 requests/hour** | Security-sensitive operation |

### Project Endpoints (`/projects/*`)

| Endpoint | Rate Limit | Reason |
|----------|-----------|--------|
| `POST /projects` | **10 requests/hour** | Prevent project spam |

### Story Endpoints (`/stories/*`)

| Endpoint | Rate Limit | Reason |
|----------|-----------|--------|
| `POST /stories` | **50 requests/hour** | Allow normal workflow while preventing spam |

## Implementation Details

### Technology Stack

- **Library**: `slowapi` (v0.1.9+)
- **Storage**: In-memory (default)
- **Key Function**: `get_remote_address` (uses client IP)

### Setup

1. **main.py** - Global rate limiter setup:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

2. **Individual Routers** - Per-endpoint limits:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...
```

## Rate Limit Response

When a rate limit is exceeded, the API returns:

**Status Code**: `429 Too Many Requests`

**Response Headers**:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Timestamp when the limit resets

**Response Body**:
```json
{
  "detail": "Rate limit exceeded: 5 per 1 minute"
}
```

## Configuration

### Environment-based Limits

For production environments, you may want to adjust limits based on:
- User subscription tier
- API key type (if implemented)
- Known trusted IPs

### Custom Storage Backend

For distributed deployments, consider using Redis as storage backend:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from limits.storage import RedisStorage

storage = RedisStorage("redis://localhost:6379")
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)
```

## Testing Rate Limits

### Manual Testing

```bash
# Test login rate limit (5/minute)
for i in {1..6}; do
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username_or_email":"test","password":"pass"}'
  echo "Request $i"
done

# The 6th request should return 429
```

### Automated Testing

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_login_rate_limit(client: AsyncClient):
    # First 5 requests should succeed (or return auth errors)
    for i in range(5):
        response = await client.post("/auth/login", json={
            "username_or_email": "test",
            "password": "wrong"
        })
        assert response.status_code != 429

    # 6th request should hit rate limit
    response = await client.post("/auth/login", json={
        "username_or_email": "test",
        "password": "wrong"
    })
    assert response.status_code == 429
```

## Best Practices

1. **Monitor Rate Limit Hits**: Track 429 responses to identify legitimate users hitting limits
2. **Communicate Limits**: Document limits in API documentation
3. **Provide Headers**: Always include rate limit headers in responses
4. **Adjust Based on Usage**: Review and adjust limits based on actual usage patterns
5. **Whitelist IPs**: Consider whitelisting trusted IPs (internal services, monitoring)

## Future Enhancements

- [ ] Redis-based storage for distributed deployments
- [ ] User-tier based rate limits (free vs. premium users)
- [ ] API key authentication with different rate limits
- [ ] Rate limit bypass for trusted services
- [ ] Metrics dashboard for rate limit monitoring
- [ ] Automatic IP blocking for persistent violators

## Security Considerations

Rate limiting is a critical security layer that helps prevent:

- **Brute-force attacks**: Login and password reset endpoints
- **Account enumeration**: Registration and login endpoints
- **Resource exhaustion**: All creation endpoints
- **DDoS attacks**: All endpoints

However, rate limiting should be combined with other security measures:
- Strong password policies
- Account lockout after failed attempts
- CAPTCHA for sensitive operations
- IP-based blocking for malicious actors

## Maintenance

### Updating Rate Limits

To update a rate limit:

1. Modify the `@limiter.limit()` decorator in the respective router file
2. Update this documentation
3. Test the new limit
4. Deploy changes

### Monitoring

Monitor these metrics:
- Number of 429 responses per endpoint
- IPs frequently hitting limits
- Time patterns of rate limit violations

## Support

For issues or questions about rate limiting:
- Check the [slowapi documentation](https://slowapi.readthedocs.io/)
- Review server logs for rate limit violations
- Contact the VibeSDLC team
