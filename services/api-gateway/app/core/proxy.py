"""HTTP proxy utilities for API Gateway."""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


class ServiceProxy:
    """HTTP proxy for microservices."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def proxy_request(
        self,
        request: Request,
        target_url: str,
        path: str,
        exclude_headers: Optional[list] = None
    ) -> Response:
        """Proxy HTTP request to target service."""
        exclude_headers = exclude_headers or ["host", "content-length"]

        # Prepare headers
        headers = {
            key: value for key, value in request.headers.items()
            if key.lower() not in exclude_headers
        }

        # Prepare URL
        url = urljoin(target_url.rstrip("/"), path.lstrip("/"))

        # Prepare query parameters
        params = dict(request.query_params)

        try:
            # Read request body
            body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None

            # Make request to target service
            response = await self.client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=params,
                content=body,
            )

            # Prepare response headers
            response_headers = {
                key: value for key, value in response.headers.items()
                if key.lower() not in ["content-length", "transfer-encoding", "connection"]
            }

            # Return streaming response for large responses
            if response.status_code == 200 and "application/json" in response.headers.get("content-type", ""):
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type")
                )
            else:
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers
                )

        except httpx.TimeoutException:
            logger.error(f"Timeout when proxying request to {url}")
            raise HTTPException(status_code=504, detail="Service timeout")
        except httpx.ConnectError:
            logger.error(f"Connection error when proxying request to {url}")
            raise HTTPException(status_code=503, detail="Service unavailable")
        except Exception as e:
            logger.error(f"Error proxying request to {url}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def health_check(self, service_url: str) -> Dict[str, Any]:
        """Check health of a service."""
        try:
            response = await self.client.get(f"{service_url}/health", timeout=5)
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Global proxy instance
service_proxy = ServiceProxy()