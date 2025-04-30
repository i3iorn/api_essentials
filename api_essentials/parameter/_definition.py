import warnings
from dataclasses import dataclass
from typing import Optional, Dict, Any, TYPE_CHECKING

from ._enums import ParameterLocation
from ..logging_decorator import log_method_calls

if TYPE_CHECKING:
    from ._constraint import ParameterConstraint


@dataclass(frozen=True)
@log_method_calls()
class ParameterDefinition:
    name:                   str
    location:               ParameterLocation
    required:               bool
    description:            Optional[str]
    constraint:             "ParameterConstraint"
    deprecated:             bool                = False
    deprecated_description: Optional[str]       = None

    def __post_init__(self):
        if self.deprecated and self.deprecated_description:
            warnings.warn(f"Parameter '{self.name}' deprecated: {self.deprecated_description}", DeprecationWarning)
        if self.location is ParameterLocation.PATH and not self.required:
            raise ValueError("Path parameters must be required")

    def to_openapi(self) -> Dict[str, Any]:
        schema = {"type": self.constraint.value_type.name.lower()}
        if self.constraint.default is not None:
            schema["default"] = self.constraint.default
        if self.constraint.enum:
            schema["enum"] = list(self.constraint.enum)
        if self.constraint.example is not None:
            schema["example"] = self.constraint.example
        return {
            "name":        self.name,
            "in":          self.location.value,
            "required":    self.required,
            "description": self.description,
            "schema":      schema
        }

    def to_json_schema(self) -> Dict[str, Any]:
        base = {
            "type": self.constraint.value_type.name.lower(),
            **({"default": self.constraint.default} if self.constraint.default is not None else {})
        }
        if self.constraint.enum:
            base["enum"] = list(self.constraint.enum)
        if self.constraint.example is not None:
            base["example"] = self.constraint.example
        return {self.name: base}
