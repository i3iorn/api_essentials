import inspect
import logging
from typing import List, Dict, Any
from difflib import get_close_matches

from .auth import AbstractCredentials
from .client import APIClient
from .endpoint import Endpoint
from .flags import Flag
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
            close_endpoint = get_close_matches(name, self._endpoints.keys(), n=1, cutoff=0.6)
            if close_endpoint:
                msg = f"Endpoint '{name}' not found. Did you mean '{close_endpoint[0]}'?"
            else:
                msg = f"Endpoint '{name}' not found. Available endpoints: {', '.join(self._endpoints.keys())}"
            logger.warning(msg)
            raise ValueError(msg)
        
        return self._endpoints[name]

    async def close(self):
        await self.client.close()

    def set_endpoints(self, value: Dict[str, Endpoint]) -> None:
        if not isinstance(value, dict):
            raise ValueError("Endpoints must be a dictionary")
        if not all(isinstance(k, str) and isinstance(v, Endpoint) for k, v in value.items()):
            raise ValueError("Endpoints must be a dictionary of string keys and Endpoint values")
        
        self._endpoints = value
        
    async def request(
            self,
            *flags: Flag,
            auth_info: AbstractCredentials,
            endpoint: Endpoint,
            **kwargs: Any
    ) -> Response:
        """
        Make a request to the API.

        Arguments:
            flags: Flags to be passed to the request.
            auth_info: Authentication information.
            endpoint: The endpoint to make the request to.
            **kwargs: Additional keyword arguments for the request.

        Returns:
            Response: The response from the API.

        Raises:
            ValueError: If the endpoint is not found.
        """
        return await self.client.arequest(
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
