import json
import logging
from typing import Dict, Any, TYPE_CHECKING

import httpx

from api_essentials.auth import AbstractCredentials
from api_essentials.auth.flow import AUTHORIZATION_HEADER_NAME
from api_essentials.endpoint.definition import EndpointDefinition
from api_essentials.logging_decorator import log_method_calls
from api_essentials.parameter import applier_registry


logger = logging.getLogger(__name__)


@log_method_calls()
class RequestBuilder:
    """
    Builds and validates an httpx.Request given an EndpointDefinition
    and concrete input values.
    """
    def __init__(
        self,
        endpoint: EndpointDefinition,
        api: "BaseAPI"
    ):
        from api_essentials.api import BaseAPI
        if not isinstance(endpoint, EndpointDefinition):
            raise TypeError("endpoint must be an instance of EndpointDefinition")
        if not isinstance(api, BaseAPI):
            raise TypeError("api must be an instance of BaseAPI")

        self.endpoint = endpoint
        self.api = api

        self.default_headers = {
            "User-Agent": self.api.client.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def validate_input(self, data: Dict[str, Any]) -> None:
        # Ensure all required parameters present
        # Validate each provided value
        for name, raw in data.items():
            pd = next((p for p in self.endpoint.parameters if p.name == name), None)
            if pd:
                pd.constraint.validate(pd.name, raw)
            elif pd:
                logger.warning(
                    f"{pd.name} is not configured for this endpoint."
                )

    def build(self, auth_info: AbstractCredentials, **data: Any) -> httpx.Request:
        self.validate_input(data)
        # Construct URL with path params
        new_path = f"{self.api.client.base_url.path.rstrip('/')}/{self.endpoint.path.lstrip('/')}"
        url = self.api.client.base_url.copy_with(path=new_path)
        req = httpx.Request(self.endpoint.method, url)


        # Apply each parameter
        if self.endpoint.parameters:
            for pd in self.endpoint.parameters:
                if pd.name == AUTHORIZATION_HEADER_NAME:
                    # Skip Authorization header, handled separately by the API client
                    continue

                if pd.name in data:
                    val = data[pd.name]
                    logger.debug(f"Starting with parameter '{pd.name}' with value '{val}'")

                    if pd.constraint.validate(pd.name, val):
                        val = pd.constraint.coerce(pd.name, val)

                    applier = applier_registry.get(pd.location)
                    req = applier.apply(req, pd, val)
                    print(req.content)

                    logger.debug(f"Finished with parameter '{pd.name}' with value '{val}'")
        else:
            req = httpx.Request(
                method=req.method,
                json=data,
                url=req.url,
                extensions=req.extensions,
                headers=req.headers
            )

        # Apply headers
        for name, value in self.default_headers.items():
            if name not in req.headers:
                req.headers[name] = value

        # Set content length
        if req.content:
            req.headers["Content-Length"] = str(len(req.content))

        # Add auth info to extensions
        req.extensions["auth_info"] = auth_info

        logger.debug(
            "Request built",
            extra={
                "payload": {
                    "method": req.method,
                    "path": req.url.path,
                    "headers": req.headers,
                    "body": req.content,
                }
            }
        )

        return req
