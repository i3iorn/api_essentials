from dataclasses import dataclass
from typing import Any

import httpx

from ._applier import ApplierRegistry
from ._definition import ParameterDefinition
from ..logging_decorator import log_method_calls


@dataclass
@log_method_calls()
class ParameterValue:
    definition: ParameterDefinition
    raw:        Any

    def validate(self) -> None:
        self.definition.constraint.validate(self.definition.name, self.raw)

    def coerce(self) -> Any:
        return self.definition.constraint.coerce(self.definition.name, self.raw)

    def apply_to(self, req: httpx.Request, appliers: "ApplierRegistry") -> httpx.Request:
        val = self.coerce()
        applier = appliers.get(self.definition.location)
        return applier.apply(req, self.definition, val)
