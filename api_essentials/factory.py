from typing import Optional

import httpx
from openapi_core import OpenAPI
from openapi_spec_validator import validate

from api_essentials.client import APIClient
from api_essentials.api import BaseAPI
from api_essentials.endpoint.factory import EndpointFactory
from api_essentials.logging_decorator import log_method_calls


@log_method_calls()
class APIFactory:
    @classmethod
    def from_openapi(
            cls,
            openapi_spec: dict,
            auth: httpx.Auth = None,
            host_prefix: Optional[str] = None,
            **client_options
    ) -> "BaseAPI":
        """
        Create an API instance from an OpenAPI spec.
        :param openapi_spec: OpenAPI spec
        :param auth:
            Authentication object for the API client
        :param host_prefix:
            Optional host prefix to be added to the base URL
        :param flags:
            Optional flags to be passed to the API client
        :return: API instance
        """
        # Validate the OpenAPI spec
        validate(openapi_spec)

        open_api_client = OpenAPI.from_dict(openapi_spec)
        client = APIClient.from_openapi(open_api_client, auth, **client_options)

        if host_prefix:
            # Add host prefix to the base URL
            client.add_host_prefix(host_prefix)

        api = BaseAPI(client)
        api.set_endpoints(
            EndpointFactory.from_openapi(api, openapi_spec)
        )

        return api