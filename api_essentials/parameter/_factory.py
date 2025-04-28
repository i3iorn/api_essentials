import warnings
from dataclasses import replace
from typing import Dict, Any

from ._constraint import ParameterConstraint
from ._definition import ParameterDefinition
from ._enums import ParameterLocation, ParameterValueType


class ParameterFactoryService:
    """
    DI-friendly factory for ParameterDefinition.
    """
    def __init__(self, default_constraints: Dict[str, Any] = None):
        self.default_constraints = default_constraints or {}

    def _make(self, name, location, **kw) -> ParameterDefinition:
        merged = {**self.default_constraints, **kw}
        constraint = ParameterConstraint(**merged)
        pd = ParameterDefinition(
            name=name,
            location=location,
            required=merged.get("required", True),
            description=merged.get("description"),
            constraint=constraint
        )
        # override warnings/customs:
        if location is ParameterLocation.QUERY and pd.required:
            warnings.warn("Query params typically not required", UserWarning)
        return pd

    def query(self, name: str, **kw):
        return self._make(name, ParameterLocation.QUERY, **kw)

    def header(self, name: str, **kw):
        return self._make(name, ParameterLocation.HEADER, **kw)

    def path(self, name: str, **kw):
        pd = self._make(name, ParameterLocation.PATH, **kw)
        return replace(pd, required=True)

    def body(self, name: str, **kw):
        pd = self._make(name, ParameterLocation.BODY, **kw)
        return pd
