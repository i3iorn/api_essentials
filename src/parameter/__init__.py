from ._applier import *
from ._core import *
from ._factory import *
from ._spec import *
from ._enums import *
from ._constraint import *
from ._definition import *


applier_registry = ApplierRegistry()

# Create and configure the ApplierRegistry
applier_registry.register(ParameterLocation.QUERY, QueryApplier())
applier_registry.register(ParameterLocation.HEADER, HeaderApplier())
applier_registry.register(ParameterLocation.BODY, BodyApplier())
applier_registry.register(ParameterLocation.PATH, PathApplier())


__all__ = [
    "ParameterValueType",
    "ParameterFactoryService",
    "ParameterApplier",
    "applier_registry",
    "ParameterLocation",
    "ParameterDefinition",
    "ApplierRegistry"
]