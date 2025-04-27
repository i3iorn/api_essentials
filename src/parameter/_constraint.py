from dataclasses import dataclass
from re import Pattern
from typing import Optional, Sequence, Any, Union, List

from ._enums import ParameterValueType
from src.endpoint.rules import (Rule, NullRule, TypeRule, EnumRule, RangeRule, LengthRule, ItemsRule, EmptyRule, BlankRule,
                                PatternRule, DeprecatedRule)


@dataclass
class ParameterConstraint:
    value_type: ParameterValueType
    enum:     Optional[Sequence[Any]] = None
    default:  Optional[Any]           = None
    example:  Optional[Any]           = None
    deprecated:            bool        = False
    deprecated_description: str        = ""
    minimum:               Optional[float] = None
    maximum:               Optional[float] = None
    min_length:            Optional[int]   = None
    max_length:            Optional[int]   = None
    min_items:             Optional[int]   = None
    max_items:             Optional[int]   = None
    allow_empty:           bool            = True
    allow_null:            bool            = True
    allow_blank:           bool            = True
    pattern:               Optional[Union[str, Pattern]] = None
    required:              bool            = False
    description:           Optional[str]    = None

    def __post_init__(self):
        # build pipeline of rules
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

    def validate(self, name: str, value: Any) -> None:
        for r in self._rules:
            r.validate(name, value)

    def coerce(self, name: str, raw: Any) -> Any:
        val = self.value_type.coerce(raw)
        self.validate(name, val)
        return val
