import re
import warnings
from abc import ABC, abstractmethod
from re import Pattern
from typing import Any, Sequence, Union

from ..parameter._enums import ParameterValueType
from ..strategies import JSONCoercion


class Rule(ABC):
    @abstractmethod
    def validate(self, name: str, value: Any) -> None:
        ...


class TypeRule(Rule):
    def __init__(self, value_type: ParameterValueType):
        self.value_type = value_type
    def validate(self, name, value):
        if self.value_type == ParameterValueType.JSON:
            try:
                JSONCoercion().apply(value)
            except (TypeError, ValueError) as e:
                if not isinstance(value, str):
                    raise TypeError(f"Param '{name}': expected JSON, got {value!r}") from e
        elif not self.value_type.is_valid(value):
            raise TypeError(f"Param '{name}': expected {self.value_type.name}, got {type(value).__name__}")


class EnumRule(Rule):
    def __init__(self, choices: Sequence[Any]):
        self.choices = choices
    def validate(self, name, value):
        if value not in self.choices:
            raise ValueError(f"Param '{name}': {value!r} not in {self.choices}")


class RangeRule(Rule):
    def __init__(self, mn=None, mx=None):
        self.mn, self.mx = mn, mx
    def validate(self, name, value):
        if isinstance(value, (int, float)):
            if self.mn is not None and value < self.mn:
                raise ValueError(f"Param '{name}': {value} < min {self.mn}")
            if self.mx is not None and value > self.mx:
                raise ValueError(f"Param '{name}': {value} > max {self.mx}")


class LengthRule(Rule):
    def __init__(self, min_length=None, max_length=None):
        self.min_length, self.max_length = min_length, max_length
    def validate(self, name, value):
        if isinstance(value, (str, list, tuple)):
            l = len(value)
            if self.min_length is not None and l < self.min_length:
                raise ValueError(f"Param '{name}': len {l} < min_length {self.min_length}")
            if self.max_length is not None and l > self.max_length:
                raise ValueError(f"Param '{name}': len {l} > max_length {self.max_length}")


class ItemsRule(Rule):
    def __init__(self, min_items=None, max_items=None):
        self.min_items, self.max_items = min_items, max_items
    def validate(self, name, value):
        if isinstance(value, (list, dict)):
            l = len(value)
            if self.min_items is not None and l < self.min_items:
                raise ValueError(f"Param '{name}': items {l} < min_items {self.min_items}")
            if self.max_items is not None and l > self.max_items:
                raise ValueError(f"Param '{name}': items {l} > max_items {self.max_items}")


class EmptyRule(Rule):
    def __init__(self, allow_empty=True):
        self.allow_empty = allow_empty
    def validate(self, name, value):
        if not self.allow_empty and not value:
            raise ValueError(f"Param '{name}': empty not allowed")


class BlankRule(Rule):
    def __init__(self, allow_blank=True):
        self.allow_blank = allow_blank
    def validate(self, name, value):
        if isinstance(value, str) and not self.allow_blank and not value.strip():
            raise ValueError(f"Param '{name}': blank not allowed")


class NullRule(Rule):
    def __init__(self, allow_null=True):
        self.allow_null = allow_null
    def validate(self, name, value):
        if value is None and not self.allow_null:
            raise ValueError(f"Param '{name}': null not allowed")


class PatternRule(Rule):
    def __init__(self, pat: Union[str, Pattern]):
        self.pat = re.compile(pat) if isinstance(pat, str) else pat
    def validate(self, name, value):
        if isinstance(value, str) and not self.pat.match(value):
            raise ValueError(f"Param '{name}': '{value}' !~ /{self.pat.pattern}/")


class DeprecatedRule(Rule):
    def __init__(self, deprecated=False, desc=""):
        self.deprecated, self.desc = deprecated, desc
    def validate(self, name, value):
        if self.deprecated:
            warnings.warn(f"Param '{name}' deprecated: {self.desc}", DeprecationWarning)
