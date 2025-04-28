import logging
from typing import Dict, Any, TYPE_CHECKING

import httpx

from src.auth import AbstractCredentials
from src.endpoint.definition import EndpointDefinition
from src.logging_decorator import log_method_calls
from src.parameter import applier_registry


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
        api: "AbstractAPI"
    ):
        from src.api import AbstractAPI
        if not isinstance(endpoint, EndpointDefinition):
            raise TypeError("endpoint must be an instance of EndpointDefinition")
        if not isinstance(api, AbstractAPI):
            raise TypeError("api must be an instance of AbstractAPI")

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
            if not pd:
                raise ValueError(f"Unexpected parameter '{name}'")
            pd.constraint.validate(pd.name, raw)

    def build(self, auth_info: AbstractCredentials, **data: Any) -> httpx.Request:
        self.validate_input(data)
        # Construct URL with path params
        new_path = f"{self.api.client.base_url.path.rstrip('/')}/{self.endpoint.path.lstrip('/')}"
        url = self.api.client.base_url.copy_with(path=new_path)
        req = httpx.Request(self.endpoint.method, url)

        # Apply each parameter
        for pd in self.endpoint.parameters:
            if pd.name == "Authorization":
                # Skip Authorization header, handled separately by the API client
                continue

            if pd.name in data:
                val = data[pd.name]
                logger.debug(f"Starting with parameter '{pd.name}' with value '{val}'")

                if pd.constraint.validate(pd.name, val):
                    val = pd.constraint.coerce(pd.name, val)

                applier = applier_registry.get(pd.location)
                req = applier.apply(req, pd, val)

                logger.debug(f"Finished with parameter '{pd.name}' with value '{val}'")

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
