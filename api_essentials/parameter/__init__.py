from ._applier import ApplierRegistry, ParameterApplier, BodyApplier, QueryApplier, PathApplier, HeaderApplier
from ._factory import ParameterFactoryService
from ._spec import OpenApiVisitor
from._enums import ParameterValueType
from ._constraint import ParameterConstraint
from ._definition import ParameterDefinition, ParameterLocation


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
    "ApplierRegistry",
    "OpenApiVisitor",
    "BodyApplier",
    "QueryApplier",
    "PathApplier",
    "HeaderApplier",
    "ParameterConstraint"
]