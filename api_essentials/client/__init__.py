import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional
import httpx
from httpx import URL

from api_essentials.client.options import RequestOptions
from api_essentials.strategies import ErrorStrategy, NoRetries, RetryStrategy
from api_essentials.flags import USE_DEFAULT_POST_RESPONSE_HOOK, ALLOW_UNSECURE
from api_essentials.logging_decorator import log_method_calls


@log_method_calls()
class APIClient:
    """
    Fully configurable HTTPX-based async API client with flag support and hook injection.
    """

    def __init__(
        self,
        base_url: URL,
        auth: httpx.Auth,
        *flags,
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
        event_hooks: Optional[Dict[str, List[Callable]]] = None,
        error_strategy: Optional[ErrorStrategy] = None,
        retry_strategy: Optional[RetryStrategy] = None,
        **
    ):
        self.logger = logging.getLogger(__name__)
        self._flags = set(flags)
        self._auth = auth
        self._base_url = URL(base_url)
        self._timeout = timeout
        self._error_strategy = error_strategy or ErrorStrategy()
        self._retry_strategy = retry_strategy or NoRetries()

        # Setup event hooks
        event_hooks = event_hooks or {}
        response_hooks = event_hooks.setdefault("response", [])

        # Add auth hook if auth is provided
        if self._auth:
            response_hooks.append(self._auth.auth_flow)

        if USE_DEFAULT_POST_RESPONSE_HOOK in self._flags:
            response_hooks.append(self._error_strategy.apply)

        self.client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            verify=not (ALLOW_UNSECURE in self._flags),
            headers=headers,
            event_hooks=event_hooks,
        )

    @property
    def base_url(self) -> URL:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        self._base_url = URL(value)
        self.client.base_url = self._base_url

    async def request(self, options: RequestOptions) -> httpx.Response:
        method_func = getattr(self.client, options.method.lower(), None)
        if not method_func:
            raise ValueError(f"Unsupported HTTP method: {options.method}")

        async def make_request():
            self.logger.debug(f"Making {options.method} request to {options.path} with options: {options.as_dict()}")
            return await method_func(self.base_url.join(options.path), **options.as_dict())

        wrapped = self._retry_strategy.apply(make_request)
        return await wrapped()

    async def close(self) -> None:
        """Close the internal connection pool."""
        await self.client.aclose()
