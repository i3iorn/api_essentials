import logging
from typing import Optional, Any, Dict
import httpx
from .auth.config import OAuth2Config
from .auth.oauth2 import BaseOAuth2
from .request.request_id import RequestId
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
        self.client = httpx.Client(base_url=self.base_url, auth=self.auth, **client_kwargs)
        self.request_id = RequestId()
        self.ratelimit = RateLimit(max_requests=max_requests, time_window=time_window)

    def _add_request_id(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        if headers is None:
            headers = {}
        # Generate a new request ID for each request
        rid = self.request_id.__get__(self, self.__class__)
        headers["X-Request-ID"] = rid.hex
        return headers

    def _check_rate_limit(self):
        if self.ratelimit.is_rate_limited():
            self.logger.warning("APIClient rate limit exceeded: %d requests in %d seconds", self.ratelimit.max_requests, self.ratelimit.time_window)
            raise RateLimitExceeded(f"Rate limit exceeded: {self.ratelimit.max_requests} requests in {self.ratelimit.time_window} seconds")
        self.ratelimit.add_request()

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        self._check_rate_limit()
        headers = kwargs.pop("headers", {})
        headers = self._add_request_id(headers)
        self.logger.debug("APIClient %s %s headers=%s kwargs=%s", method, url, headers, kwargs)
        response = self.client.request(method, url, headers=headers, **kwargs)
        self.logger.debug("APIClient response: %s %s", response.status_code, response.text)
        response.raise_for_status()
        return response

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

    def close(self):
        self.client.close()

