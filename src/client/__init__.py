from typing import Union
import logging
from typing import Callable, Dict, List, Optional, Tuple, Mapping
import httpx
from httpx import URL

from src.response import Response
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
        base_url:       URL,
        auth:           httpx.Auth,
        timeout:        float                               = 10.0,
        headers:        Optional[Dict[str, str]]            = None,
        response_hooks: Optional[Dict[str, List[Callable]]] = None,
        request_hooks:  Optional[Dict[str, List[Callable]]] = None,
        error_strategy: Optional[ErrorStrategy]             = None,
        retry_strategy: Optional[RetryStrategy]             = None,
        flags:          Optional[Tuple[Flag]]               = None,
        user_agent:     Optional[str]                       = None,
        **kwargs
    ):
        self.logger          = logging.getLogger(__name__)
        self._flags          = set(flags)
        self._auth           = auth
        self._base_url       = URL(base_url)
        self._timeout        = timeout
        self._error_strategy = error_strategy or ErrorStrategy()
        self._retry_strategy = retry_strategy or NoRetries()
        self._user_agent     = user_agent or "Generic APIClient/1.0"

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
            base_url=self._base_url,
            timeout=self._timeout,
            verify=not (ALLOW_UNSECURE in self._flags),
            headers=headers,
            event_hooks=event_hooks,
            **kwargs
        )

    @property
    def base_url(self) -> URL:
        return self._base_url

    @property
    def user_agent(self) -> str:
        return self._user_agent

    async def request(self, request: httpx.Request) -> Response:
        """
        Make a request using the HTTPX client.
        """
        self.logger.debug(
            "Making request",
            extra={
                "payload": {
                    "method": request.method,
                    "path": request.url.path,
                    "options": request.headers,
                    "body": request.content,
                }
            }
        )

        async def make_request():
            return await self.client.send(request)

        wrapped = self._retry_strategy.apply(make_request)
        response = await wrapped()
        return Response(response)

    async def close(self) -> None:
        """Close the internal connection pool."""
        await self.client.aclose()
