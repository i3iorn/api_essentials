from abc import ABC, abstractmethod
from typing import Any

from ._definition import ParameterDefinition


class SpecVisitor(ABC):
    @abstractmethod
    def visit_parameter(self, pd: ParameterDefinition) -> Any:
        ...
    @abstractmethod
    def visit_endpoint(self, ed: "EndpointDefinition") -> Any:
        ...


class OpenApiVisitor(SpecVisitor):
    def visit_parameter(self, pd):
        return pd.to_openapi()
    def visit_endpoint(self, ed):
        ps = [self.visit_parameter(p) for p in ed.parameters]
        return { ed.path: { ed.method.lower(): {
            "operationId":  ed.operation_id,
            "summary":      ed.summary,
            "description":  ed.description,
            "parameters":   ps,
        } } }


class JsonSchemaVisitor(SpecVisitor):
    def visit_parameter(self, pd):
        return pd.to_json_schema()
    def visit_endpoint(self, ed):
        props = {}
        reqs = []
        for p in ed.parameters:
            props.update(self.visit_parameter(p))
            if p.required:
                reqs.append(p.name)
        schema = {"type":"object", "properties": props}
        if reqs:
            schema["required"] = reqs
        return {ed.path: schema}
