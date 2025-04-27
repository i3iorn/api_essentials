from dataclasses import dataclass
from typing import Optional, Dict, Union


ParameterType = Union[str, int, float, bool, bytes, None]


@dataclass
class URLComponents:
    """
    A class to represent the components of a URL.

    This class is used internally by the URL class to store the various components
    of a URL, such as scheme, username, password, host, port, path, query,
    and fragment. It provides a convenient way to access and manipulate these
    components.
    """
    scheme:   Optional[str] =   None
    username: Optional[str] =   None
    password: Optional[str] =   None
    host:     Optional[str] =   None
    port:     Optional[int] =   None
    path:     Optional[str] =   None
    query:    Optional[bytes] = None
    fragment: Optional[str] =   None

    def update(self, components: Dict[str, Optional[ParameterType]] = None, **kwargs: Optional[ParameterType]) -> None:
        """
        Update the components with the provided keyword arguments.

        Args:
            **kwargs: Keyword arguments representing URL components.
                Valid keys are 'scheme', 'host', 'port', 'path', 'query', and 'fragment'.
        """
        if components is None:
            components = {}
        components.update(kwargs)
        for key, value in kwargs.items():
            if key in self.__dict__:
                self.__dict__[key] = value

    def to_dict(self) -> Dict[str, Optional[ParameterType]]:
        """
        Convert the URL components to a dictionary.

        Returns:
            Dict[str, Optional[ParameterType]]: A dictionary representation of the URL components.
        """
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, components: Dict[str, Optional[ParameterType]]) -> "URLComponents":
        """
        Create a URLComponents instance from a dictionary.

        Args:
            components (Dict[str, Optional[ParameterType]]): A dictionary of URL components.

        Returns:
            URLComponents: An instance of URLComponents.
        """
        return cls(**{k: v for k, v in components.items() if v is not None})

    def __getitem__(self, key: str) -> Optional[ParameterType]:
        """
        Get the value of a component by its key.

        Args:
            key (str): The key of the component to retrieve.

        Returns:
            Optional[ParameterType]: The value of the component, or None if not set.
        """
        return self.__dict__.get(key)

    def __setitem__(self, key: str, value: Optional[ParameterType]) -> None:
        """
        Set the value of a component by its key.

        Args:
            key (str): The key of the component to set.
            value (Optional[ParameterType]): The value to set for the component.
        """
        if key in self.__dict__:
            self.__dict__[key] = value
        else:
            raise KeyError(f"Invalid key: {key}")

    def __repr__(self) -> str:
        """
        Get a string representation of the URL components.

        Returns:
            str: A string representation of the URL components.
        """
        return f"URLComponents({', '.join(f'{k}={v}' for k, v in self.__dict__.items() if v is not None)})"

    def __str__(self) -> str:
        """
        Get a string representation of the URL components.

        Returns:
            str: A string representation of the URL components.
        """
        return self.__repr__()
