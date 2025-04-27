from typing import Union, Optional, Dict, List
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs

import httpx

from src.utils.components import URLComponents, ParameterType


def validate_components():
    """
    Decorator to validate URL components.
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            for key, value in kwargs.items():
                if key not in self._components.__dict__:
                    raise ValueError(f"Invalid component: {key}")
                if not isinstance(value, (str, int, float, bool, bytes)):
                    raise TypeError(f"Invalid type for {key}: {type(value).__name__}")
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


class URL:
    """
    URL class with a a builder pattern for constructing URLs.

    This class provides a fluent interface for building URLs with various components.
    It allows you to set the scheme, host, port, path, query parameters, and fragment.
    It also provides a method to convert the URL to a string representation.

    Example usage:
        url = URL().scheme("https").host("example.com").port(443).path("/api").query({"key": "value"}).build()
        print(url)  # Output: https://example.com:443/api?key=value
    """
    @classmethod
    def from_string(cls, url: str) -> "URL":
        if not isinstance(url, str):
            raise TypeError(f"URL must be a string, got {type(url).__name__}")

        return cls(url=url)

    @classmethod
    def from_httpx_url(cls, url: httpx.URL) -> "URL":
        if not isinstance(url, httpx.URL):
            raise TypeError(f"URL must be an instance of httpx.URL, got {type(url).__name__}")

        return cls(
            scheme=  url.scheme,
            host=    url.host,
            port=    url.port,
            path=    url.path,
            query=   url.query,
            fragment=url.fragment
        )

    def __init__(
            self,
            url:                 Union["URL", str]  = "",
            drop_invalid_keys:   bool               = False,
            drop_invalid_values: bool               = False,
            **kwargs:            Optional[ParameterType]
    ) -> None:
        valid_input_kwargs = {}
        if kwargs:
            allowed = {
                "scheme":   str,
                "username": str,
                "password": str,
                "userinfo": bytes,
                "host":     str,
                "port":     int,
                "netloc":   bytes,
                "path":     str,
                "query":    bytes,
                "fragment": str,
                "params":   object,
            }

            # Perform type checking for all supported keyword arguments.
            for key, value in kwargs.items():
                if key not in allowed:
                    if not drop_invalid_keys:
                        message = f"{key!r} is an invalid keyword argument for URL()"
                        raise TypeError(message)
                    else:
                        continue
                if value is not None and not isinstance(value, allowed[key]):
                    if not drop_invalid_values:
                        expected = allowed[key].__name__
                        seen = type(value).__name__
                        message = f"Argument {key!r} must be {expected} but got {seen}"
                        raise TypeError(message)
                    else:
                        continue
                if isinstance(value, bytes):
                    valid_input_kwargs[key] = value.decode("utf-8")

            if "params" in kwargs:
                params = kwargs.get("params")
                valid_input_kwargs["query"] = None if not params else str(QueryParams(params))

        # Parse the URL if it's a string
        if isinstance(url, str):
            parsed = urlparse(url)
            self._components = URLComponents(
                scheme= parsed.scheme,
                username= parsed.username,
                password= parsed.password,
                host= parsed.hostname,
                port= parsed.port,
                path= parsed.path,
                query= parsed.query.encode("utf-8") if parsed.query else None,
                fragment= parsed.fragment,
            )
        elif isinstance(url, URL):
            self._components = url._components
        else:
            raise TypeError(f"Invalid type for URL: {type(url).__name__}")

        # Set the components using the valid input keyword arguments
        self.components.update(**valid_input_kwargs)
        
    @property
    def components(self) -> "URLComponents":
        """
        Get the components of the URL.

        Returns:
            URLComponents: The components of the URL.
        """
        return self._components

    @property
    def query_dict(self) -> Dict[str, List[str]]:
        return parse_qs(self.components.query.decode()) if self.components.query else {}

    def _set(self, **kwargs: Optional[ParameterType]) -> None:
        """
        Set multiple components of the URL using keyword arguments.

        Args:
            **kwargs: Keyword arguments representing URL components.
                Valid keys are 'scheme', 'host', 'port', 'path', 'query', and 'fragment'.

        Returns:
            self: The updated URL object.
        """
        for key, value in kwargs.items():
            if (
                    key in self._components and
                    value is not None and
                    (isinstance(value, type(self._components[key])) or self._components[key] is None)
            ):
                self._components[key] = value

    @validate_components()
    def add_path(self, path: str) -> "URL":
        """
        Add a path to the URL.

        Args:
            path (str): The path to add (e.g., '/api/resource').

        Returns:
            self: The updated URL object.
        """
        self.with_path(self.components.path + path.lstrip("/"))
        return self

    @validate_components()
    def with_scheme(self, scheme: str) -> "URL":
        """
        Set the scheme of the URL.

        Args:
            scheme (str): The scheme to set (e.g., 'http', 'https').

        Returns:
            self: The updated URL object.
        """
        if scheme not in ["http", "https"]:
            raise ValueError(f"Scheme must be 'http' or 'https', got {scheme}")

        self.components.scheme = scheme
        return self

    @validate_components()
    def with_host(self, host: str):
        """
        Set the host of the URL.

        Args:
            host (str): The host to set (e.g., 'example.com').

        Returns:
            self: The updated URL object.
        """
        self.components.host = host
        return self

    @validate_components()
    def with_port(self, port: int):
        """
        Set the port of the URL.

        Args:
            port (int): The port to set (e.g., 80, 443).

        Returns:
            self: The updated URL object.
        """
        if port < 0 or port > 65535:
            raise ValueError("Port must be between 0 and 65535")

        self.components.port = port
        return self

    @validate_components()
    def with_path(self, path: str, trailing_slash: bool = False) -> "URL":
        """
        Set the path of the URL.

        Args:
            path (str): The path to set (e.g., '/api/resource').

        Returns:
            self: The updated URL object.
        """
        if not path.startswith("/"):
            path = "/" + path
        if trailing_slash and not path.endswith("/"):
            path += "/"
        self.components.path = path
        return self

    @validate_components()
    def with_query(self, query: Union[str, Dict[str, Union[str, List[str]]]]) -> "URL":
        """
        Set the query parameters of the URL.

        Args:
            query (str): The query string to set (e.g.,
                'key1=value1&key2=value2').

        Returns:
            self: The updated URL object.
        """
        if isinstance(query, dict):
            query = urlencode(query, doseq=True)
        elif not isinstance(query, str):
            raise TypeError("Query must be str or dict")
        self.components.query = query.encode("utf-8")
        return self

    @validate_components()
    def with_fragment(self, fragment: str) -> "URL":
        """
        Set the fragment of the URL.

        Args:
            fragment (str): The fragment to set (e.g., 'section1').

        Returns:
            self: The updated URL object.
        """
        if not fragment.startswith("#"):
            fragment = "#" + fragment
        self.components.fragment = fragment
        return self

    def without_query(self) -> "URL":
        """
        Remove the query parameters from the URL.

        Returns:
            self: The updated URL object.
        """
        self.components.query = None
        return self

    def without_fragment(self) -> "URL":
        """
        Remove the fragment from the URL.

        Returns:
            self: The updated URL object.
        """
        self.components.fragment = None
        return self

    def without_query_param(self, key: str) -> "URL":
        """
        Remove a specific query parameter from the URL.
        Args:
            key (str): The key of the query parameter to remove.

        Returns:
            self: The updated URL object.

        Raises:
            KeyError: If the key is not found in the query parameters.
        """
        qp = self.query_dict
        qp.pop(key, None)
        self.with_query(qp)
        return self

    def secure(self) -> "URL":
        """
        Set the URL to use HTTPS.

        Returns:
            self: The updated URL object.
        """
        self.components.scheme = "https"
        return self

    def build(self) -> str:
        """
        Build the URL and return it as a string.

        Returns:
            str: The constructed URL as a string.
        """
        if not self.components.scheme or not self.components.host:
            raise ValueError("Scheme and host are required to build a valid URL")
        return str(urlunparse((
            self.components.scheme,
            f'{self.components.host}:{self.components.port}' if self.components.port else self.components.host,
            self.components.path or "",
            "",  # params
            str(QueryParams(self.components.query)) if self.components.query else "",
            self.components.fragment or "",
        )))

    def copy(self) -> "URL":
        """
        Create a copy of the URL object.

        Returns:
            URL: A new URL object with the same components.
        """
        return URL(
            scheme=self.components.scheme,
            host=self.components.host,
            port=self.components.port,
            path=self.components.path,
            query=self.components.query,
            fragment=self.components.fragment
        )

    def to_httpx_url(self, without_fragment: bool = True) -> httpx.URL:
        """
        Convert the URL object to an httpx.URL object.

        Returns:
            httpx.URL: The URL as an httpx.URL object.
        """
        data = {
            "scheme": self.components.scheme,
            "host": self.components.host,
            "port": self.components.port,
            "path": self.components.path,
            "query": self.components.query
        }
        if not without_fragment:
            data["fragment"] = self.components.fragment
        return httpx.URL(**data)

    def __str__(self) -> str:
        """
        Get a string representation of the URL.

        Returns:
            str: The URL as a string.
        """
        return self.build()

    def __repr__(self) -> str:
        """
        Get a string representation of the URL.

        Returns:
            str: The URL as a string.
        """
        return f"URL({self.build()})"

    def __eq__(self, other: object) -> bool:
        """
        Check if two URL objects are equal.

        Args:
            other (object): The other object to compare.

        Returns:
            bool: True if the URLs are equal, False otherwise.
        """
        if not isinstance(other, URL):
            return False
        return self.build() == other.build()

    def __hash__(self) -> int:
        """
        Get the hash of the URL object.

        Returns:
            int: The hash of the URL.
        """
        return hash(self.build())

    def __contains__(self, key: str) -> bool:
        """
        Check if the URL contains a specific component.

        Args:
            key (str): The key of the component to check.

        Returns:
            bool: True if the component exists, False otherwise.
        """
        return key in QueryParams(self.components.query)


class QueryParams:
    """
    A class to represent query parameters for a URL.

    This class provides a fluent interface for building query strings with various components.
    It allows you to set the key-value pairs, and it also provides a method to convert the
    query parameters to a string representation.

    Example usage:
        params = QueryParams().add("key1", "value1").add("key2", "value2").build()
        print(params)  # Output: key1=value1&key2=value2
    """

    def __init__(self, params: Optional[Dict[str, Union[str, List[str]]]] = None):
        self.params = params or {}

    def add(self, key: str, value: str):
        if not isinstance(key, str):
            raise TypeError(f"Key must be a string, got {type(key).__name__}")
        if not isinstance(value, str):
            raise TypeError(f"Value must be a string, got {type(value).__name__}")

        if key in self.params:
            if isinstance(self.params[key], list):
                self.params[key].append(value)
            else:
                self.params[key] = [self.params[key], value]
        else:
            self.params[key] = value

        return self

    def build(self):
        return urlencode(self.params, doseq=True)

    def __str__(self):
        return self.build()

    def __getitem__(self, item: str) -> Optional[str]:
        return self.params.get(item)

    def __setitem__(self, key: str, value: str) -> None:
        if not isinstance(key, str):
            raise TypeError(f"Key must be a string, got {type(key).__name__}")
        if not isinstance(value, str):
            raise TypeError(f"Value must be a string, got {type(value).__name__}")

        self.params[key] = value
