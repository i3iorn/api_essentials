import httpx

from .definition import *
from .request_builder import RequestBuilder
from .rules import *
from ..logging_decorator import log_method_calls


@log_method_calls()
class Endpoint:
    def __init__(self, api: "AbstractAPI", definition: EndpointDefinition) -> None:
        self.definition = definition
        self.api = api
        self.request_builder = RequestBuilder(definition, api)

    def build_request(self, **parameters) -> httpx.Request:
        return self.request_builder.build(
            **parameters
        )



__all__ = [
    "RequestBuilder",
    "Endpoint",
    "EndpointDefinition"
]
