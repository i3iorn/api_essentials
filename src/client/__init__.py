import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Mapping
import httpx

from src.utils.url import URL
from src.client.options import RequestOptions
from src.strategies import ErrorStrategy, NoRetries, RetryStrategy
from src.flags import USE_DEFAULT_POST_RESPONSE_HOOK, ALLOW_UNSECURE, Flag
from src.logging_decorator import log_method_calls


@log_method_calls()
class APIClient:
    """
    Fully configurable HTTPX-based async API client with flag support and hook injection.
    """

    def __init__(
        self,
        base_url: URL,
        auth: httpx.Auth,
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
        response_hooks: Optional[Dict[str, List[Callable]]] = None,
        request_hooks: Optional[Dict[str, List[Callable]]] = None,
        error_strategy: Optional[ErrorStrategy] = None,
        retry_strategy: Optional[RetryStrategy] = None,
        flags: Optional[Tuple[Flag]] = None,
        **kwargs
    ):
        self.logger = logging.getLogger(__name__)
        self._flags = set(flags)
        self._auth = auth
        self._base_url = URL(base_url)
        self._timeout = timeout
        self._error_strategy = error_strategy or ErrorStrategy()
        self._retry_strategy = retry_strategy or NoRetries()

        # Setup event hooks
        response_hooks = response_hooks or []
        request_hooks = request_hooks or []

        if USE_DEFAULT_POST_RESPONSE_HOOK in self._flags:
            response_hooks.append(self._error_strategy.apply)

        event_hooks: Mapping[str, List[Callable]] = {
            "response": response_hooks,
            "request": request_hooks,
        }

        self.client = httpx.AsyncClient(
            auth=self._auth,
            base_url=self._base_url.to_httpx_url(),
            timeout=self._timeout,
            verify=not (ALLOW_UNSECURE in self._flags),
            headers=headers,
            event_hooks=event_hooks,
            **kwargs
        )

    @property
    def base_url(self) -> URL:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        self._base_url = URL(value)
        self.client.base_url = self._base_url

    async def request(self, *args, **kwargs) -> httpx.Response:
        if isinstance(args[0], RequestOptions):
            return await self.request_from_request_options(args[0])
        elif isinstance(args[0], httpx.Request):
            return await self.request_from_httpx_request(args[0])
        else:
            raise ValueError("Unsupported request type. Use RequestOptions or httpx.Request.")

    async def request_from_httpx_request(self, request: httpx.Request) -> httpx.Response:
        """
        Make a request using the HTTPX client.
        """
        self.logger.debug("Making request",
                          extra={"payload": {"method": request.method,
                                             "path": request.url.path,
                                             "options": request.headers}})

        async def make_request():
            return await self.client.send(request)

        wrapped = self._retry_strategy.apply(make_request)
        return await wrapped()

    async def request_from_request_options(self, options: RequestOptions) -> httpx.Response:
        method_func = getattr(self.client, options.method.lower(), None)
        if not method_func:
            raise ValueError(f"Unsupported HTTP method: {options.method}")

        async def make_request():
            self.logger.debug("Making request",
                              extra={"payload": {"method": options.method,
                                          "path": options.path,
                                          "options": options.as_dict()}})

            url = self.base_url.add_path(options.path).to_httpx_url()
            return await method_func(
                url,
                **options.as_dict()
            )

        wrapped = self._retry_strategy.apply(make_request)
        return await wrapped()

    async def close(self) -> None:
        """Close the internal connection pool."""
        await self.client.aclose()
