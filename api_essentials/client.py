import logging
from typing import Optional, Dict

from httpx import Client

from .auth.config import OAuth2Config
from .auth.oauth2 import BaseOAuth2
from api_essentials.models.request.request_id import RequestId
from .models.request import Request
from .models.response import Response
from .strategy.strategies.ratelimit import RateLimit

class RateLimitExceeded(Exception):
    """Raised when the API client rate limit is exceeded."""
    pass

class APIClient:
    """
    Unified API client with OAuth2 authentication and automatic request ID injection.
    """
    def __init__(self, config: OAuth2Config, base_url: Optional[str] = None, *, max_requests: int = 100, time_window: int = 60, **client_kwargs):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.auth = BaseOAuth2(config)
        self.base_url = base_url or (str(config.token_url) if hasattr(config, 'token_url') else None)
        self.client = Client(base_url=self.base_url, auth=self.auth, **client_kwargs)
        self.request_id = RequestId()
        self.ratelimit = RateLimit(max_requests=max_requests, time_window=time_window)

    def _add_request_id(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        if headers is None:
            headers = {}
        # Generate a new request ID for each request
        rid = self.request_id.__get__(self, self.__class__)
        headers["X-Request-ID"] = rid.hex
        return headers

    def _build_request(self, method: str, url: str, **kwargs) -> Request:
        headers = kwargs.pop("headers", {})
        headers = self._add_request_id(headers)
        self.logger.debug("Building request: %s %s headers=%s kwargs=%s", method, url, headers, kwargs)
        return Request(method=method, url=url, headers=headers, **kwargs)

    def _check_rate_limit(self):
        if self.ratelimit.is_rate_limited():
            self.logger.warning("APIClient rate limit exceeded: %d requests in %d seconds", self.ratelimit.max_requests, self.ratelimit.time_window)
            raise RateLimitExceeded(f"Rate limit exceeded: {self.ratelimit.max_requests} requests in {self.ratelimit.time_window} seconds")
        self.ratelimit.add_request()

    def request(self, method: str, url: str, **kwargs) -> Response:
        """
        Make an API request with automatic request ID injection and rate limiting.

        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE).
            url (str): The URL to send the request to.
            **kwargs: Additional keyword arguments for the request.

        Returns:
            Response: The response from the API.
        """
        self._check_rate_limit()
        request = self._build_request(method, url, **kwargs)
        response = self.client.request(request.method, request.url, headers=request.headers)
        return Response(
            status_code=response.status_code,
            headers=response.headers,
            content=response.content,
            json=response.json() if response.headers.get("Content-Type") == "application/json" else None
        )

    def get(self, url: str, **kwargs) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        return self.request("DELETE", url, **kwargs)

    def close(self):
        self.client.close()

