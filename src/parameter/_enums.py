from enum import Enum
from functools import lru_cache
from typing import Any, List

from src.strategies import SimpleCoercion, JSONCoercion


class IsValidEnumMixin:
    @classmethod
    def is_valid(cls, value: Any) -> bool:
        if cls is ParameterValueType.NONE:
            return value is None

        return any(
            isinstance(value, m.value)
            for m in cls
            if m.value is not None
        )

    @classmethod
    @lru_cache(1)
    def values(cls) -> List[Any]:
        return [m.value for m in cls]


class ParameterLocation(IsValidEnumMixin, Enum):
    QUERY     = "query"
    HEADER    = "header"
    BODY      = "body"
    PATH      = "path"
    FORM      = "form"
    MULTIPART = "multipart"
    JSON      = "json"


class ParameterValueType(IsValidEnumMixin, Enum):
    JSON    = str
    STRING  = str
    INTEGER = int
    FLOAT   = float
    BOOLEAN = bool
    ARRAY   = list
    OBJECT  = dict
    NONE    = type(None)

    def coerce(self, raw: Any) -> Any:
        if self is ParameterValueType.JSON:
            return JSONCoercion().apply(raw)
        return SimpleCoercion(self.value).apply(raw)
