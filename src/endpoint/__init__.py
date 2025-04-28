from .definition import *
from .request_builder import *
from .rules import *
from .spec import *
from ..parameter import applier_registry
from ..logging_decorator import log_method_calls


@log_method_calls()
class Endpoint:
    def __init__(self, api: "AbstractAPI", definition: EndpointDefinition, appliers: "ApplierRegistry" = None) -> None:
        self.definition = definition
        self.appliers = appliers or applier_registry
        self.api = api
        self.request_builder = RequestBuilder(definition, api, appliers)

    def build_request(self, **parameters) -> httpx.Request:
        return self.request_builder.build(
            **parameters
        )



__all__ = [
    "RequestBuilder",
    "Endpoint"
]
