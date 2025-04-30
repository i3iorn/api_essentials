import inspect
import logging
from typing import List, Dict

from .auth import AbstractCredentials
from .client import APIClient
from .endpoint import Endpoint
from .logging_decorator import log_method_calls
from .response import Response

logger = logging.getLogger(__name__)

@log_method_calls()
class BaseAPI:
    def __init__(self, client: APIClient):
        self.client = client
        self._endpoints: Dict[str, Endpoint] = {}

    def get_endpoint(self, name: str) -> Endpoint:
        """Return a list of API endpoints."""
        if name not in self._endpoints:
            logger.error(f"Endpoint '{name}' not found in API. Available endpoints are: {list(self._endpoints.keys())}")
            raise KeyError(f"Endpoint '{name}' not found in API.")
        
        return self._endpoints[name]

    async def close(self):
        await self.client.close()

    def set_endpoints(self, value: Dict[str, Endpoint]) -> None:
        if not isinstance(value, dict):
            raise ValueError("Endpoints must be a dictionary")
        if not all(isinstance(k, str) and isinstance(v, Endpoint) for k, v in value.items()):
            raise ValueError("Endpoints must be a dictionary of string keys and Endpoint values")
        
        self._endpoints = value
        
    async def request(self, *flags, auth_info: AbstractCredentials, endpoint: Endpoint, **kwargs) -> Response:
        """
        Make a request to the API.

        :param kwargs: Additional request parameters
        :return: Response object
        """
        return await self.client.request(
            endpoint.build_request(*flags, auth_info=auth_info, **kwargs)
        )



@log_method_calls()
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
        if not issubclass(api_class, BaseAPI):
            raise ValueError("API class must be a subclass of BaseAPI.")
        self.apis[api_class.__name__] = api_class

    def get_api(self, name: str) -> type:
        """
        Get a registered API class by name.
        :param name: Name of the API class
        :return: API class
        """
        return self.apis.get(name)
