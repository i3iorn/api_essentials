import json
import logging
from typing import Dict, Any, TYPE_CHECKING

import httpx

from api_essentials.auth import AbstractCredentials
from api_essentials.constants import AUTHORIZATION_HEADER_NAME
from api_essentials.endpoint.definition import EndpointDefinition
from api_essentials.flags import TRUST_UNDEFINED_PARAMETERS
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

    def build(self, *flags, auth_info: AbstractCredentials, **data: Any) -> httpx.Request:
        logger.debug("Building request", extra={"data": data})

        self.validate_input(data)
        # Construct URL with path params
        new_path = f"{self.api.client.base_url.path.rstrip('/')}/{self.endpoint.path.lstrip('/')}"
        logger.debug(f"New path: {new_path}")

        url = self.api.client.base_url.copy_with(path=new_path)
        logger.debug(f"URL: {url}")

        req = httpx.Request(self.endpoint.method, url)
        logger.debug(f"Request method: {req.method}")

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

                    logger.debug(f"Finished with parameter '{pd.name}' with value '{val}'")

            if TRUST_UNDEFINED_PARAMETERS in flags:
                current = json.loads(req.content.decode("utf-8")) if req.content else {}
                for name, val in data.items():
                    if name not in [p.name for p in self.endpoint.parameters]:
                        logger.debug(f"Starting with parameter '{name}' with value '{val}'")
                        if isinstance(current, dict):
                            current[name] = str(val)
                        else:
                            raise ValueError(f"Cannot add parameter '{name}' to request with content type '{req.headers.get('Content-Type')}'")
                req = httpx.Request(
                    method=req.method,
                    json=current,
                    url=req.url,
                    extensions=req.extensions,
                    headers=req.headers
                )
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
        # Throw an exception if there was data sent but no content
        if len(data) > 0 and not len(req.content):
            raise ValueError(f"Request has no content but data was sent: {json.dumps(data)}")

        return req
