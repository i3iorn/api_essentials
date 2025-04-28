from typing import List, Dict, Any

from src.endpoint.definition import EndpointDefinition
from src.logging_decorator import log_method_calls
from src.parameter import OpenApiVisitor


@log_method_calls()
class OpenApiSpecGenerator:
    """
    Generate full OpenAPI spec from a list of EndpointDefinition.
    """
    def __init__(self, title: str, version: str):
        self.title = title
        self.version = version

    def generate(self, endpoints: List[EndpointDefinition]) -> Dict[str, Any]:
        doc: Dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {"title": self.title, "version": self.version},
            "paths": {}
        }
        for ep in endpoints:
            visitor = OpenApiVisitor()
            ep_spec = visitor.visit_endpoint(ep)
            # merge path entry
            for path, method_obj in ep_spec.items():
                doc["paths"].setdefault(path, {}).update(method_obj)
        return doc
