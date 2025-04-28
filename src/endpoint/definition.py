from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING

from src.logging_decorator import log_method_calls

if TYPE_CHECKING:
    from src.parameter import ParameterDefinition


@dataclass(frozen=True)
@log_method_calls()
class EndpointDefinition:
    """
    Immutable metadata for an API endpoint.

    This class defines the structure of an API endpoint, including its path,
    HTTP method, description, parameters, and request body.
    It is used to generate OpenAPI specifications and to validate requests
    against the defined schema.

    Attributes:
        path (str): The URL path of the endpoint.
        method (str): The HTTP method (GET, POST, etc.) for the endpoint.
        description (Optional[str]): A brief description of the endpoint.
        parameters (List[ParameterDefinition]): A list of parameters for the endpoint.
    """
    path:            str
    method:          str
    description:     Optional[str]
    parameters:      List["ParameterDefinition"]

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
