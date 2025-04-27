import urllib.parse
from abc import ABC, abstractmethod
from typing import Dict, Any

import httpx

from ..utils.url import URL
from ._enums import ParameterLocation
from ._definition import ParameterDefinition


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


class HeaderApplier(ParameterApplier):
    def apply(self, req, pd, val):
        req.headers[pd.name] = val
        return req


class BodyApplier(ParameterApplier):
    def apply(self, req, pd, val):
        req.content = val
        return req


class PathApplier(ParameterApplier):
    def apply(self, req, pd, val):
        if isinstance(req.url, str):
            req.url = req.url.replace(f"{{{pd.name}}}", str(val))
        elif isinstance(req.url, URL):
            req.url = req.url.add_path(str(val))
        return req


