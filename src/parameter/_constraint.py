from dataclasses import dataclass
from re import Pattern
from typing import Optional, Sequence, Any, Union, List

from ._enums import ParameterValueType
from src.endpoint.rules import (Rule, NullRule, TypeRule, EnumRule, RangeRule, LengthRule, ItemsRule, EmptyRule, BlankRule,
                                PatternRule, DeprecatedRule)
from ..logging_decorator import log_method_calls


@dataclass
@log_method_calls()
class ParameterConstraint:
    value_type:             ParameterValueType      = ParameterValueType.STRING
    enum:                   Optional[Sequence[Any]] = None
    default:                Optional[Any]           = None
    example:                Optional[Any]           = None
    deprecated_description: Optional[str]           = None
    minimum:                Optional[float]         = None
    maximum:                Optional[float]         = None
    min_length:             Optional[int]           = None
    max_length:             Optional[int]           = None
    min_items:              Optional[int]           = None
    max_items:              Optional[int]           = None
    pattern:                Optional[Union[str, Pattern]] = None
    description:            Optional[str]           = None
    deprecated:             bool                    = False
    allow_empty:            bool                    = True
    allow_null:             bool                    = True
    allow_blank:            bool                    = True
    required:               bool                    = False

    def __post_init__(self):
        self._validate_input()
        self._add_rules()

    def _add_rules(self):
        self._rules: List[Rule] = []
        self._rules.append(NullRule(self.allow_null))
        self._rules.append(TypeRule(self.value_type))
        if self.enum:      self._rules.append(EnumRule(self.enum))
        if self.minimum is not None or self.maximum is not None:
            self._rules.append(RangeRule(self.minimum, self.maximum))
        if self.min_length or self.max_length:
            self._rules.append(LengthRule(self.min_length, self.max_length))
        if self.min_items or self.max_items:
            self._rules.append(ItemsRule(self.min_items, self.max_items))
        self._rules.append(EmptyRule(self.allow_empty))
        self._rules.append(BlankRule(self.allow_blank))
        if self.pattern:  self._rules.append(PatternRule(self.pattern))
        self._rules.append(DeprecatedRule(self.deprecated, self.deprecated_description))

    def _validate_input(self):
        if isinstance(self.value_type, str):
            self.value_type = ParameterValueType.from_name(self.value_type)
        if not isinstance(self.value_type, ParameterValueType):
            raise TypeError(f"Parameter value type {self.value_type} is not a ParameterValueType or a ParameterValueType name")
        if self.enum and not isinstance(self.enum, Sequence):
            raise TypeError(f"Parameter enum type {self.enum} is not a Sequence")
        if self.minimum and not isinstance(self.minimum, int):
            raise TypeError(f"Parameter minimum type {self.minimum} is not an integer")
        if self.maximum and not isinstance(self.maximum, int):
            raise TypeError(f"Parameter maximum type {self.maximum} is not an integer")
        if self.min_length and not isinstance(self.min_length, int):
            raise TypeError(f"Parameter min_length type {self.min_length} is not an integer")
        if self.max_length and not isinstance(self.max_length, int):
            raise TypeError(f"Parameter max_length type {self.max_length} is not an integer")
        if self.min_items and not isinstance(self.min_items, int):
            raise TypeError(f"Parameter min_items type {self.min_items} is not an integer")
        if self.max_items and not isinstance(self.max_items, int):
            raise TypeError(f"Parameter max_items type {self.max_items} is not an integer")
        if self.pattern and not isinstance(self.pattern, Pattern):
            raise TypeError(f"Parameter pattern type {self.pattern} is not a Pattern")
        if self.description and not isinstance(self.description, str):
            raise TypeError(f"Parameter description type {self.description} is not a String")
        if self.deprecated and not isinstance(self.deprecated, bool):
            raise TypeError(f"Parameter deprecated type {self.deprecated} is not a bool")
        if self.allow_empty and not isinstance(self.allow_empty, bool):
            raise TypeError(f"Parameter allow_empty type {self.allow_empty} is not a bool")
        if self.allow_null and not isinstance(self.allow_null, bool):
            raise TypeError(f"Parameter allow_null type {self.allow_null} is not a bool")
        if self.allow_blank and not isinstance(self.allow_blank, bool):
            raise TypeError(f"Parameter allow_blank type {self.allow_blank} is not a bool")
        if self.required and not isinstance(self.required, bool):
            raise TypeError(f"Parameter required type {self.required} is not a bool")

    def validate(self, name: str, value: Any) -> None:
        for r in self._rules:
            r.validate(name, value)

    def coerce(self, name: str, raw: Any) -> Any:
        val = self.value_type.coerce(raw)
        self.validate(name, val)
        return val
