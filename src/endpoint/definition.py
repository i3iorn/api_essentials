from dataclasses import dataclass
from typing import Optional, List

from src.parameter import ParameterDefinition


@dataclass(frozen=True)
class EndpointDefinition:
    """
    Immutable metadata for an API endpoint.
    """
    path:            str
    method:          str
    description:     Optional[str]
    parameters:      List[ParameterDefinition]
    request_body:    Optional[ParameterDefinition] = None

    @property
    def operation_id(self):
        """
        Generate a unique operation ID based on the method and path.
        """
        return f"{self.method.lower()}_{self.path.replace('/', '_').replace('{', '').replace('}', '')}"

    @property
    def summary(self):
        """
        Generate a summary for the endpoint.
        """
        return f"{self.method.upper()} {self.path}"
