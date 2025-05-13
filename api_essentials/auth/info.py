from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import List, Optional, Dict

from api_essentials.logging_decorator import log_method_calls
from api_essentials.strategies import Strategy, StandardScopeStrategy


@log_method_calls()
class AbstractCredentials(ABC):
    """
    Abstract class for credentials.
    """

    def __init__(self):
        self._body = None

    @abstractmethod
    def get_body(self) -> dict:
        """
        Get credentials as a dictionary.
        """
        pass


@log_method_calls()
class ClientCredentials(AbstractCredentials):
    """
    Class for client credentials.
    """
    def __init__(self,
            clientId: str,
            client_secret: str,
            scopes: List[str] = None,
            send_as: str = "header",
            scope_strategy: Optional[Strategy] = StandardScopeStrategy(),
            headers: Optional[Dict[str, str]] = None,
            **kwargs
        ):
            super().__init__()
            self._body = None
            self.client_id = clientId
            self.client_secret = client_secret
            self.scopes = scopes
            self.send_as = send_as
            self.scope_strategy = scope_strategy
            self.headers = headers if headers is not None else {}

    def __post_init__(self):
        if not self.client_id or not self.client_secret:
            raise ValueError("Client ID and secret cannot be empty.")
        if not isinstance(self.client_id, str) or not isinstance(self.client_secret, str):
            raise TypeError("Client ID and secret must be strings.")
        if not isinstance(self.scopes, List):
            raise TypeError("Scope must be a string.")

        if self.scope_strategy and not isinstance(self.scope_strategy, Strategy):
            raise TypeError("Scope strategy must be an instance of Strategy.")

        self._body = None

    def get_body(self) -> dict:
        if self._body is not None:
            return self._body
        return {
            "scope": self.get_scope(),
            "grant_type": "client_credentials"
        }

    def set_body(self, body: Dict[str, str]):
        """
        Set the body of the credentials.
        """
        if body is not None and not isinstance(body, dict):
            raise TypeError("Body must be a dictionary or None.")
        self._body = body

    def get_scope(self):
        """
        Get the scope as a string.
        """
        if not self.scopes:
            return []
        return self.scope_strategy.apply(self.scopes)


@dataclass
@log_method_calls()
class UserCredentials(AbstractCredentials):
    """
    Class for user credentials.
    """
    username: str
    password: str

    def __post_init__(self):
        if not self.username or not self.password:
            raise ValueError("Username and password cannot be empty.")
        if not isinstance(self.username, str) or not isinstance(self.password, str):
            raise TypeError("Username and password must be strings.")

    def get_body(self) -> Optional[dict]:
        return None


@dataclass
@log_method_calls()
class TokenCredentials(AbstractCredentials):
    """
    Class for token credentials.
    """
    access_token: str
    refresh_token: str

    def __post_init__(self):
        if not self.access_token or not self.refresh_token:
            raise ValueError("Access token and refresh token cannot be empty.")
        if not isinstance(self.access_token, str) or not isinstance(self.refresh_token, str):
            raise TypeError("Access token and refresh token must be strings.")

    def get_body(self) -> Optional[dict]:
        return None


@dataclass
@log_method_calls()
class ApiCredentials(AbstractCredentials):
    """
    Class for API credentials.
    """
    api_key: str
    api_secret: str

    def __post_init__(self):
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret cannot be empty.")
        if not isinstance(self.api_key, str) or not isinstance(self.api_secret, str):
            raise TypeError("API key and secret must be strings.")

    def get_credentials(self) -> Optional[dict]:
        return None