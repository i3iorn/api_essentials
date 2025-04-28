import inspect
from abc import abstractmethod, ABC
from typing import List

import httpx
from httpx import URL

from .auth import ClientCredentials, AbstractCredentials
from .auth.flow import validate_auth_class
from .client import APIClient, RequestOptions
from .endpoint import Endpoint
from .flags import ALLOW_UNSECURE
from .logging_decorator import log_method_calls
from .response import Response


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
    def __init__(self, client: APIClient):
        self.client = client

    @abstractmethod
    def endpoints(self) -> List[Endpoint]:
        """Return a list of API endpoints."""
        pass

    async def close(self):
        await self.client.close()

    async def request(self, auth_info: AbstractCredentials, endpoint: Endpoint, **kwargs) -> Response:
        """
        Make a request to the API.
        :param method: HTTP method (GET, POST, etc.)
        :param path: API endpoint
        :param kwargs: Additional request parameters
        :return: Response object
        """
        return await self.client.request(
            endpoint.build_request(auth_info=auth_info, **kwargs)
        )


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
