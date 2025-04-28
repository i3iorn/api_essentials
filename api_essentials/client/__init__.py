from typing import Union
import logging
from typing import Callable, Dict, List, Optional, Tuple, Mapping
import httpx
from httpx import URL
from openapi_core import OpenAPI

from api_essentials.response import Response
from api_essentials.client.options import RequestOptions
from api_essentials.strategies import ErrorStrategy, NoRetries, RetryStrategy
from api_essentials.flags import USE_DEFAULT_POST_RESPONSE_HOOK, ALLOW_UNSECURE, Flag
from api_essentials.logging_decorator import log_method_calls


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
        verify:         bool                                = True,
        **kwargs
    ):
        self.logger          = logging.getLogger(__name__)
        self._flags          = set(flags or ())
        self._auth           = auth
        self._verify         = verify
        self._base_url       = URL(base_url)
        self._timeout        = timeout
        self._error_strategy = error_strategy or ErrorStrategy()
        self._retry_strategy = retry_strategy or NoRetries()
        self._user_agent     = user_agent or "Generic APIClient/1.0"

        # Setup event hooks
        response_hooks = response_hooks or []
        request_hooks = request_hooks or []

        if self._flags and USE_DEFAULT_POST_RESPONSE_HOOK in self._flags:
            response_hooks.append(self._error_strategy.apply)

        event_hooks: Mapping[str, List[Callable]] = {
            "response": response_hooks,
            "request": request_hooks,
        }

        self.client = httpx.AsyncClient(
            auth=self._auth,
            base_url=self._base_url,
            timeout=self._timeout,
            verify=self._verify,
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

    async def request(self, request: httpx.Request, **kwargs) -> Response:
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

    @classmethod
    def from_openapi(
        cls,
        openapi_spec: OpenAPI,
        auth:         httpx.Auth,
        verify:     bool = True,
        **kwargs
    ) -> "APIClient":
        """
        Create an API client from an OpenAPI specification.
        Attempts to use the first server URL in the OpenAPI spec.
        """

        # Default to first server's URL if available
        try:
            server = openapi_spec.spec.get("servers", [])[0]
            base_url = server["url"]
        except (IndexError, KeyError, AttributeError) as e:
            raise ValueError("No valid server URL found in OpenAPI spec") from e

        # Pass all remaining arguments to the constructor
        return cls(
            base_url=URL(base_url),
            auth=auth,
            verify=verify,
            **kwargs
        )

