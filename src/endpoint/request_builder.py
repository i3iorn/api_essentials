from typing import Dict, Any, TYPE_CHECKING

import httpx

from src.utils.url import URL
from src.endpoint.definition import EndpointDefinition
from src.parameter import ApplierRegistry

if TYPE_CHECKING:
    from src.api import AbstractAPI


class RequestBuilder:
    """
    Builds and validates an httpx.Request given an EndpointDefinition
    and concrete input values.
    """
    def __init__(
        self,
        endpoint: EndpointDefinition,
        api: "AbstractAPI",
        appliers: ApplierRegistry
    ):
        self.endpoint = endpoint
        self.appliers = appliers
        self.api = api

    def validate_input(self, data: Dict[str, Any]) -> None:
        # Ensure all required parameters present
        for pd in self.endpoint.parameters:
            if pd.required and pd.name not in data:
                raise ValueError(f"Missing required parameter '{pd.name}'")
        # Validate each provided value
        for name, raw in data.items():
            pd = next((p for p in self.endpoint.parameters if p.name == name), None)
            if not pd:
                raise ValueError(f"Unexpected parameter '{name}'")
            pd.constraint.validate(pd.name, raw)

    def build(self, data: Dict[str, Any]) -> httpx.Request:
        self.validate_input(data)
        # Construct URL with path params
        url = self.api.base_url.add_path(self.endpoint.path)
        req = httpx.Request(self.endpoint.method, url)
        # Apply each parameter
        for pd in self.endpoint.parameters:
            if pd.name in data:
                val = pd.constraint.coerce(pd.name, data[pd.name])
                applier = self.appliers.get(pd.location)
                req = applier.apply(req, pd, val)
        # Handle request body if defined
        if self.endpoint.request_body:
            rb = self.endpoint.request_body
            raw = data.get(rb.name, rb.constraint.default)
            val = rb.constraint.coerce(rb.name, raw)
            req = self.appliers.get(rb.location).apply(req, rb, val)
        return req
