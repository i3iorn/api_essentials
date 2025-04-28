import json
import logging
import urllib.parse
from abc import ABC, abstractmethod
from typing import Dict, Any

import httpx
from httpx import URL

from ._enums import ParameterLocation
from ._definition import ParameterDefinition
from ..logging_decorator import log_method_calls

logger = logging.getLogger(__name__)


@log_method_calls()
class ApplierRegistry:
    """
    Registry for parameter appliers.

    This class is responsible for managing the mapping between
    parameter locations and their corresponding appliers.
    It allows for the registration and retrieval of appliers
    based on the parameter location.

    Attributes:
        _map (Dict[ParameterLocation, ParameterApplier]): A dictionary mapping
            parameter locations to their respective appliers.

    Methods:
        register(loc: ParameterLocation, ap: ParameterApplier) -> None:
            Registers a new parameter applier for a given location.

        get(loc: ParameterLocation) -> ParameterApplier:
            Retrieves the applier for the specified parameter location.
    """
    def __init__(self):
        """
        Initializes the ApplierRegistry with an empty mapping of parameter locations
        """
        self._map: Dict[ParameterLocation, "ParameterApplier"] = {}
    def register(self, loc, ap):
        """
        Registers a new parameter applier for a given location.
        Args:
            loc (ParameterLocation): The location of the parameter.
            ap (ParameterApplier): The applier to register.

        Raises:
            ValueError: If the location is already registered.
        """
        self._map[loc] = ap
    def get(self, loc):
        """
        Retrieves the applier for the specified parameter location.

        Args:
            loc (ParameterLocation): The location of the parameter.

        Returns:
            ParameterApplier: The applier for the specified location.
        """
        if loc not in self._map:
            raise ValueError(f"No applier for {loc}")
        return self._map[loc]


@log_method_calls()
class ParameterApplier(ABC):
    """
    Abstract base class for parameter appliers.
    This class defines the interface for applying parameters
    to an HTTP request.
    Subclasses should implement the `apply` method
    to handle specific parameter locations.
    Attributes:
        location (ParameterLocation): The location of the parameter.
        
    """
    @abstractmethod
    def apply(self, req: httpx.Request, pd: ParameterDefinition, val: Any) -> httpx.Request:
        ...


@log_method_calls()
class QueryApplier(ParameterApplier):
    def apply(self, req, pd, val):
        if isinstance(req.url, str):
            req.url = req.url.replace(f"{{{pd.name}}}", str(val))
        elif isinstance(req.url, URL):
            query = req.url.query.copy()
            query[pd.name] = str(val)
            req.url = req.url.copy_with(query=query)
        else:
            raise ValueError(f"Unsupported URL type: {type(req.url)}")
        return req


@log_method_calls()
class HeaderApplier(ParameterApplier):
    def apply(self, req, pd, val):
        if isinstance(req.headers, dict):

            logger.debug(f"Setting new header '{pd.name}' with value '{val}'")
            req.headers[pd.name] = str(val)
        elif isinstance(req.headers, httpx.Headers):

            logger.debug(f"Setting new header '{pd.name}' with value '{val}'")
            req.headers.add(pd.name, str(val))
        else:
            raise ValueError(f"Unsupported headers type: {type(req.headers)}")

        req.headers[pd.name] = val
        return req


@log_method_calls()
class BodyApplier(ParameterApplier):
    def apply(self, req: httpx.Request, pd: ParameterDefinition, val: Any):
        current_content = req.content
        # Add the new parameter to the body
        if isinstance(current_content, bytes):
            current_content = current_content.decode("utf-8")
        elif isinstance(current_content, str):
            current_content = current_content
        else:
            raise ValueError(f"Unsupported content type: {type(current_content)}")

        # Parse the current content as JSON
        if current_content == "":
            current_content = {}
        else:
            try:
                current_content = json.loads(current_content)
            except json.JSONDecodeError:
                raise ValueError("Current content is not valid JSON")

        # Update the content with the new parameter
        current_content[pd.name] = val

        # Convert the updated content back to JSON
        current_content = json.dumps(current_content).encode("utf-8")

        # Create a new request with the updated content
        new_req = httpx.Request(
            method=req.method,
            url=req.url,
            headers=req.headers,
            content=current_content
        )

        return new_req


@log_method_calls()
class PathApplier(ParameterApplier):
    def apply(self, req, pd, val):
        if isinstance(req.url, str):
            req.url = req.url.replace(f"{{{pd.name}}}", str(val))
        elif isinstance(req.url, URL):
            req.url = req.url.add_path(str(val))
        return req


