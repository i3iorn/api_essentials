import logging
from dataclasses import dataclass
from typing import Optional, List, Union, TYPE_CHECKING, Type

import httpx
from httpx import URL, AsyncClient, Client

from api_essentials.strategy.strategies.scope_strategies import ScopeStrategy, ScopeExecutionMode
from api_essentials.auth.token import OAuth2Token
from .grant_type import OAuth2GrantType
from .oauth2 import OAuth2ResponseType, ClientType


class ConfigValidator:
    """
    Class to validate the configuration of OAuth2.
    """

    @staticmethod
    def validate(config: "OAuth2Config") -> None:
        """
        Validate the OAuth2 configuration.
        :param config: The OAuth2 configuration to validate.
        """
        if not isinstance(config.client_id, str):
            raise ValueError("Client ID must be a string.")
        if not isinstance(config.client_secret, str):
            raise ValueError("Client secret must be a string.")
        if not isinstance(config.token_url, URL):
            raise ValueError("Token URL must be a valid URL.")
        if config.token_url.scheme not in ["http", "https"]:
            raise ValueError("Token URL must use HTTP or HTTPS scheme.")
        if config.token_url.host is None:
            raise ValueError("Token URL must have a valid host.")
        if "." not in config.token_url.host:
            raise ValueError("Token URL must have a valid domain.")
        if config.redirect_uri and not isinstance(config.redirect_uri, URL):
            raise ValueError("Redirect URI must be a valid URL.")
        if config.client and not isinstance(config.client, (Client, AsyncClient)):
            raise ValueError("Client must be an instance of httpx.Client or httpx.AsyncClient.")
        if config.access_token and not isinstance(config.access_token, OAuth2Token):
            raise ValueError("Access token must be an instance of OAuth2Token.")
        if config.refresh_token and not isinstance(config.refresh_token, OAuth2Token):
            raise ValueError("Refresh token must be an instance of OAuth2Token.")
        if config.token_class and not issubclass(config.token_class, OAuth2Token):
            raise ValueError("Token class must be a subclass of OAuth2Token.")
        if config._scope and not isinstance(config._scope, list):
            raise ValueError("Scope must be a list of strings.")
        if config._scope_strategy and not isinstance(config._scope_strategy, ScopeStrategy):
            raise ValueError("Scope strategy must be an instance of ScopeStrategy.")
        if config._grant_type and not isinstance(config._grant_type, OAuth2GrantType):
            raise ValueError("Grant type must be an instance of OAuth2GrantType.")
        if config._response_type and not isinstance(config._response_type, OAuth2ResponseType):
            raise ValueError("Response type must be an instance of OAuth2ResponseType.")


@dataclass
class OAuth2Config:
    """
    Data class to hold OAuth2 configuration information.
    """
    client_id:          str
    client_secret:      str
    token_url:          URL
    redirect_uri:       Optional[URL]                 = None
    client:             Optional[Union[Client, AsyncClient]] = None
    access_token:       Optional["OAuth2Token"]       = None
    refresh_token:      Optional["OAuth2Token"]       = None
    token_class:        Optional[Type["OAuth2Token"]] = OAuth2Token
    _scope:             Optional[List[str]]           = None
    _scope_strategy:    Optional[ScopeStrategy]       = ScopeStrategy(delimiter=" ")
    _grant_type:        Optional[OAuth2GrantType]     = OAuth2GrantType.CLIENT_CREDENTIALS
    _response_type:     Optional[OAuth2ResponseType]  = OAuth2ResponseType.CODE

    def __post_init__(self):
        """
        Post-initialization method to set default values for the OAuth2 configuration.
        """
        self.logger = logging.getLogger(__name__)
        ConfigValidator.validate(self)

    @property
    def scope(self) -> str:
        """
        Get the scope for the OAuth2 configuration.
        :return: The scope as a list of strings.
        """
        scopes = self._scope or []
        return self.scope_strategy.merge_scopes(scopes)

    @scope.setter
    def scope(self, value: Union[str, List[str]]):
        """
        Set the scope for the OAuth2 configuration.
        :param value: The scope to set, either as a string or a list of strings.
        """
        if isinstance(value, str):
            value = self._scope_strategy.split_scopes(value)
            if isinstance(value, str):
                value = [value]
        if not isinstance(value, list):
            raise ValueError("Scope must be a string or a list of strings.")
        if not all(isinstance(item, str) for item in value):
            raise ValueError("All items in the scope list must be strings.")

        self.logger.debug(f"Setting scope: {value}")

        self._scope = value

    @property
    def scope_strategy(self) -> ScopeStrategy:
        """
        Get the scope strategy for the OAuth2 configuration.
        :return: The scope strategy.
        """
        return self._scope_strategy

    @scope_strategy.setter
    def scope_strategy(self, value: ScopeStrategy) -> None:
        """
        Set the scope strategy for the OAuth2 configuration.
        :param value: The scope strategy to set.
        """
        if not isinstance(value, ScopeStrategy):
            raise ValueError("Scope strategy must be an instance of ScopeStrategy.")

        self.logger.debug(f"Setting scope strategy: {value}")

        self._scope_strategy = value

    @property
    def grant_type(self) -> str:
        """
        Get the grant type for the OAuth2 configuration.
        :return: The grant type.
        """
        print(f"Grant type: {self._grant_type}")
        return self._grant_type.value

    @grant_type.setter
    def grant_type(self, value: OAuth2GrantType):
        """
        Set the grant type for the OAuth2 configuration.
        :param value: The grant type to set.
        """
        if not isinstance(value, OAuth2GrantType):
            raise ValueError("Grant type must be an instance of OAuth2GrantType.")

        self.logger.debug(f"Setting grant type: {value}")

        self._grant_type: OAuth2GrantType = value

    @property
    def response_type(self) -> str:
        """
        Get the response type for the OAuth2 configuration.
        :return: The response type.
        """
        return self._response_type.value

    @response_type.setter
    def response_type(self, value: OAuth2ResponseType):
        """
        Set the response type for the OAuth2 configuration.
        :param value: The response type to set.
        """
        if not isinstance(value, OAuth2ResponseType):
            raise ValueError("Response type must be an instance of OAuth2ResponseType.")

        self.logger.debug(f"Setting response type: {value}")

        self._response_type: OAuth2ResponseType = value

    def add_scope(self, scope: str) -> None:
        """
        Add a scope to the OAuth2 configuration.
        :param scope: The scope to add.
        """
        if not isinstance(scope, str):
            raise ValueError("Scope must be a string.")
        if self._scope is None:
            self._scope = []

        if scope in self._scope:
            self.logger.debug(f"Scope '{scope}' already exists in the list.")
            return

        self.logger.debug(f"Adding scope: {scope}")

        self._scope.append(scope)

    def attach_client(self, client: ClientType) -> None:
        """
        Attach the client to the OAuth2 configuration.
        :param client: The client to attach.
        """
        if not isinstance(client, (httpx.Client, httpx.AsyncClient)):
            raise ValueError("Client must be an instance of httpx.Client or httpx.AsyncClient.")

        self.logger.debug("Attaching client to OAuth2 configuration.")
        self.client = client