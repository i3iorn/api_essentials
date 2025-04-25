from abc import abstractmethod, ABC

import httpx
from httpx import URL

from .auth.flow import validate_auth_class
from .client import APIClient, RequestOptions
from .logging_decorator import log_method_calls
from .utils import validate_url


def requires_client(func):
    """
    Decorator to ensure that the API client is initialized before calling a method.
    """
    def wrapper(self, *args, **kwargs):
        if self.client is None:
            raise RuntimeError("API client is not initialized.")
        return func(self, *args, **kwargs)
    return wrapper


@log_method_calls()
class AbstractAPI(ABC):
    def __init__(self, base_url: str = None, auth_class: httpx.Auth = None):
        self.client = None
        self.base_url = URL(base_url)
        self.auth_class = validate_auth_class(auth_class)

    @abstractmethod
    def endpoints(self):
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
            event_hooks={},
            **kwargs
        )
        print(f"Client initialized with base URL: {self.client.base_url}")

    @requires_client
    async def get(self, path: str, **kwargs) -> httpx.Response:
        request_options = RequestOptions(
            method="get",
            path=path,
            **kwargs
        )
        return await self.client.request(request_options)

    @requires_client
    async def post(self, path: str, json: dict = None, **kwargs) -> httpx.Response:
        request_options = RequestOptions(
            method="post",
            path=path,
            json=json,
            **kwargs
        )
        return await self.client.request(request_options)

    @requires_client
    async def put(self, path: str, json: dict = None, **kwargs) -> httpx.Response:
        request_options = RequestOptions(
            method="put",
            path=path,
            json=json,
            **kwargs
        )
        return await self.client.request(request_options)

    @requires_client
    async def delete(self, path: str, **kwargs) -> httpx.Response:
        request_options = RequestOptions(
            method="delete",
            path=path,
            **kwargs
        )
        return await self.client.request(request_options)

    @requires_client
    async def patch(self, path: str, json: dict = None, **kwargs) -> httpx.Response:
        request_options = RequestOptions(
            method="patch",
            path=path,
            json=json,
            **kwargs
        )
        return await self.client.request(request_options)

    @requires_client
    async def head(self, path: str, **kwargs) -> httpx.Response:
        request_options = RequestOptions(
            method="head",
            path=path,
            **kwargs
        )
        return await self.client.request(request_options)

    @requires_client
    async def options(self, path: str, **kwargs) -> httpx.Response:
        request_options = RequestOptions(
            method="options",
            path=path,
            **kwargs
        )
        return await self.client.request(request_options)

    @requires_client
    async def close(self):
        await self.client.close()
