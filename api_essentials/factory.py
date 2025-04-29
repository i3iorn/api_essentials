from typing import Optional

import httpx
from openapi_core import OpenAPI
from openapi_spec_validator import validate

from api_essentials.client import APIClient
from api_essentials.api import AbstractAPI, BaseApi
from api_essentials.endpoint.factory import EndpointFactory


class APIFactory:
    @classmethod
    def from_openapi(
            cls,
            openapi_spec: dict,
            auth: httpx.Auth = None,
            host_prefix: Optional[str] = None,
            **client_options
    ) -> "AbstractAPI":
        """
        Create an API instance from an OpenAPI spec.
        :param openapi_spec: OpenAPI spec
        :param auth:
        :return: API instance
        """
        # Validate the OpenAPI spec
        validate(openapi_spec)

        open_api_client = OpenAPI.from_dict(openapi_spec)
        client = APIClient.from_openapi(open_api_client, auth, **client_options)
        client.add_host_prefix(host_prefix)
        api = BaseApi(client)
        api.set_endpoints(
            EndpointFactory.from_openapi(api, openapi_spec)
        )

        return api