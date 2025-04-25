from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import List


class AbstractCredentials(ABC):
    """
    Abstract class for credentials.
    """
    @abstractmethod
    def get_credentials(self) -> dict:
        """
        Get credentials as a dictionary.
        """
        pass


@dataclass
class ClientCredentials(AbstractCredentials):
    """
    Class for client credentials.
    """
    client_id: str
    client_secret: str
    scopes: List[str]

    def __post_init__(self):
        if not self.client_id or not self.client_secret:
            raise ValueError("Client ID and secret cannot be empty.")
        if not isinstance(self.client_id, str) or not isinstance(self.client_secret, str):
            raise TypeError("Client ID and secret must be strings.")
        if not isinstance(self.scopes, List):
            raise TypeError("Scope must be a string.")

    def get_credentials(self) -> dict:
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scopes": self.scopes
        }


@dataclass
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

    def get_credentials(self) -> dict:
        return {
            "username": self.username,
            "password": self.password
        }


@dataclass
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

    def get_credentials(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token
        }


@dataclass
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

    def get_credentials(self) -> dict:
        return {
            "api_key": self.api_key,
            "api_secret": self.api_secret
        }