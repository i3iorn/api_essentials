import inspect
from abc import abstractmethod, ABC
from typing import List

import httpx

from .utils.url import URL
from .auth.flow import validate_auth_class
from .client import APIClient, RequestOptions
from .endpoint import Endpoint
from .flags import ALLOW_UNSECURE
from .logging_decorator import log_method_calls


def requires_client(func):
    """
    Decorator to ensure that the API client is initialized before calling a method.
    """
    if inspect.iscoroutinefunction(func):
        async def async_wrapper(self, *args, **kwargs):
            if self.client is None:
                raise RuntimeError("API client is not initialized.")
            return await func(self, *args, **kwargs)

        return async_wrapper
    else:
        def sync_wrapper(self, *args, **kwargs):
            if self.client is None:
                raise RuntimeError("API client is not initialized.")
            return func(self, *args, **kwargs)

        return sync_wrapper


@log_method_calls()
class AbstractAPI(ABC):
    def __init__(self, base_url: str = None, auth_class: httpx.Auth = None):
        self.client = None
        self.base_url = URL(base_url)
        self.auth_class = validate_auth_class(auth_class)

    @abstractmethod
    def endpoints(self) -> List[Endpoint]:
        """Return a list of API endpoints."""
        pass

    @requires_client
    async def set_base_url(self, base_url: str):
        """Set the base URL for the API client."""
        self.client.base_url = base_url

    @requires_client
    async def set_auth(self, auth_class: httpx.Auth):
        """Set the authentication class for the API client."""
        self.client.auth = auth_class

    async def initialize_client(self, **kwargs):
        """Initialize the API client with base URL and authentication class."""
        self.client = APIClient(
            base_url=self.base_url,
            auth=self.auth_class,
            timeout=10.0,
            headers={"Content-Type": "application/json"},
            flags=(ALLOW_UNSECURE,),
        )

    @requires_client
    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self._request(method="get", path=path, **kwargs)

    @requires_client
    async def post(self, path: str, json: dict = None, **kwargs) -> httpx.Response:
        return await self._request(method="post", path=path, json=json, **kwargs)

    @requires_client
    async def put(self, path: str, json: dict = None, **kwargs) -> httpx.Response:
        return await self._request(method="put", path=path, json=json, **kwargs)

    @requires_client
    async def delete(self, path: str, **kwargs) -> httpx.Response:
        return await self._request(method="delete", path=path, **kwargs)

    @requires_client
    async def patch(self, path: str, json: dict = None, **kwargs) -> httpx.Response:
        return await self._request(method="patch", path=path, json=json, **kwargs)

    @requires_client
    async def head(self, path: str, **kwargs) -> httpx.Response:
        return await self._request(method="head", path=path, **kwargs)

    @requires_client
    async def options(self, path: str, **kwargs) -> httpx.Response:
        return await self._request(method="options", path=path, **kwargs)

    @requires_client
    async def close(self):
        await self.client.close()

    @requires_client
    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """
        Make a request to the API.
        :param method: HTTP method (GET, POST, etc.)
        :param path: API endpoint
        :param kwargs: Additional request parameters
        :return: Response object
        """
        request_options = RequestOptions(
            method=method,
            path=path,
            **kwargs
        )

        return await self.client.request(request_options)

    @requires_client
    async def send_request(self, endpoint: Endpoint, **kwargs) -> httpx.Response:
        """
        Build a request for the given endpoint.
        :param endpoint: Endpoint object
        :param kwargs: Additional request parameters
        :return: RequestOptions object
        """
        request_options = RequestOptions(
            method=endpoint.definition.method,
            path=endpoint.definition.path,
            **kwargs
        )

        # Apply endpoint-specific parameters
        for param in endpoint.definition.parameters:
            if param.name in kwargs:
                request_options.extra[param.name] = kwargs[param.name]

        return await self.client.request(request_options)


class APIRegistry:
    """
    Registry for API classes.
    """
    def __init__(self):
        self.apis = {}

    def register(self, api_class: type):
        """
        Register an API class.
        :param api_class: API class to register
        """
        if not issubclass(api_class, AbstractAPI):
            raise ValueError("API class must be a subclass of AbstractAPI.")
        self.apis[api_class.__name__] = api_class

    def get_api(self, name: str) -> type:
        """
        Get a registered API class by name.
        :param name: Name of the API class
        :return: API class
        """
        return self.apis.get(name)
