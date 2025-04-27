from .definition import *
from .request_builder import *
from .rules import *
from .spec import *


class Endpoint:
    def __init__(self, api: "AbstractAPI", definition: EndpointDefinition, appliers: "ApplierRegistry") -> None:
        self.definition = definition
        self.appliers = appliers
        self.api = api

    def build_request(self, **parameters) -> httpx.Request:
        return RequestBuilder(
            api=self.api,
            endpoint=self.definition,
            appliers=self.appliers
        ).build(
            **parameters
        )



__all__ = [
    "RequestBuilder",
    "EndpointDefinition"
]