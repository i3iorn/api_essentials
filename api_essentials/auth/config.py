import logging
from dataclasses import dataclass
from typing import Optional, List, Union, Type

import httpx
from httpx import URL, AsyncClient, Client

from api_essentials.strategy.strategies.scope_strategies import ScopeStrategy
from api_essentials.auth.token import OAuth2Token
from .grant_type import OAuth2GrantType
from .oauth2 import OAuth2ResponseType, ClientType
from .constants import AUTH_TIMEOUT, AUTH_REDIRECTS, SSL_VERIFICATION


class ConfigValidator:
    """
    Class to validate the configuration of OAuth2.
    """

    @staticmethod
    def validate(config: "OAuth2Config") -> None:
        """
        Validate the OAuth2 configuration.
        :param config: The OAuth2 configuration to validate.
        :raises ValueError: If any configuration value is invalid.
        """
        if not isinstance(config.client_id, str) or not config.client_id:
            raise ValueError("Client ID must be a non-empty string.")
        if not isinstance(config.client_secret, str) or not config.client_secret:
            raise ValueError("Client secret must be a non-empty string.")
        # TODO: This check gives a lot of false positives, so it is commented out.
        #  Needs to be improved.
        # if not isinstance(config.token_url, URL) or not getattr(config.token_url, 'host', None):
        #     raise ValueError("Token URL must be a valid URL with a host. URL: {}".format(config.token_url))
        if config.token_url.scheme not in ["http", "https"]:
            raise ValueError("Token URL must use HTTP or HTTPS scheme.")
        if config.token_url.host is None or "." not in config.token_url.host:
            raise ValueError("Token URL must have a valid domain.")
        if config.redirect_uri and (not isinstance(config.redirect_uri, URL) or not getattr(config.redirect_uri, 'host', None)):
            raise ValueError("Redirect URI must be a valid URL with a host.")
        if config.client and not isinstance(config.client, (Client, AsyncClient)):
            raise ValueError("Client must be an instance of httpx.Client or httpx.AsyncClient.")
        if config.access_token and not isinstance(config.access_token, OAuth2Token):
            raise ValueError("Access token must be an instance of OAuth2Token.")
        if config.refresh_token and not isinstance(config.refresh_token, OAuth2Token):
            raise ValueError("Refresh token must be an instance of OAuth2Token.")
        if config.token_class is not None and not (isinstance(config.token_class, type) and issubclass(config.token_class, OAuth2Token)):
            raise ValueError("Token class must be a subclass of OAuth2Token.")
        if config._scope and (not isinstance(config._scope, list) or not all(isinstance(item, str) for item in config._scope)):
            raise ValueError("Scope must be a list of strings.")
        if config._scope_strategy and not isinstance(config._scope_strategy, ScopeStrategy):
            raise ValueError("Scope strategy must be an instance of ScopeStrategy.")
        if config._grant_type and not isinstance(config._grant_type, OAuth2GrantType):
            raise ValueError("Grant type must be an instance of OAuth2GrantType.")
        if config._response_type and not isinstance(config._response_type, OAuth2ResponseType):
            raise ValueError("Response type must be an instance of OAuth2ResponseType.")


class OAuth2Config:
    """
    Class to hold OAuth2 configuration information.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: URL,
        *, # Using * to enforce keyword-only arguments for the remaining arguments
        redirect_uri: Optional[URL] = None,
        client: Optional[Union[Client, AsyncClient]] = None,
        access_token: Optional["OAuth2Token"] = None,
        refresh_token: Optional["OAuth2Token"] = None,
        token_class: Optional[Type["OAuth2Token"]] = OAuth2Token,
        verify: Optional[bool] = SSL_VERIFICATION,
        timeout: Optional[Union[int, float]] = AUTH_TIMEOUT,
        redirects: Optional[int] = AUTH_REDIRECTS,
        logger: Optional[logging.Logger] = None,
        scope: Optional[List[str]] = None,
        scope_strategy: Optional[ScopeStrategy] = ScopeStrategy(delimiter=" "),
        grant_type: Optional[OAuth2GrantType] = OAuth2GrantType.CLIENT_CREDENTIALS,
        response_type: Optional[OAuth2ResponseType] = OAuth2ResponseType.CODE,
    ) -> None:
        """
        Initialize the OAuth2 configuration.

        Args:
            client_id (str): The client ID for OAuth2.
            client_secret (str): The client secret for OAuth2.
            token_url (URL): The URL to obtain the OAuth2 token.
            redirect_uri (Optional[URL]): The redirect URI for OAuth2.
            client (Optional[Union[Client, AsyncClient]]): The HTTP client to use for requests.
            access_token (Optional[OAuth2Token]): The access token instance.
            refresh_token (Optional[OAuth2Token]): The refresh token instance.
            token_class (Optional[Type[OAuth2Token]]): The class to use for tokens.
            verify (Optional[bool]): Whether to verify SSL certificates.
            timeout (Optional[Union[int, float]]): Request timeout in seconds.
            redirects (Optional[int]): Maximum number of redirects to follow.
            logger (Optional[logging.Logger]): Logger instance for logging.
            scope (Optional[List[str]]): List of scopes for OAuth2.
            scope_strategy (Optional[ScopeStrategy]): Strategy for handling scopes.
            grant_type (Optional[OAuth2GrantType]): Grant type for OAuth2.
            response_type (Optional[OAuth2ResponseType]): Response type for OAuth2.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.redirect_uri = redirect_uri
        self.client = client
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_class = token_class
        self.verify = verify
        self.timeout = timeout
        self.redirects = redirects
        self.logger = logger or logging.getLogger(__name__)
        self._scope = scope or []
        self._scope_strategy = scope_strategy
        self._grant_type = grant_type
        self._response_type = response_type

        self.__post_init__()

    def __post_init__(self) -> None:
        """
        Post-initialization method to set default values for the OAuth2 configuration.
        """
        self.logger = logging.getLogger(__name__)
        ConfigValidator.validate(self)

    @property
    def scope(self) -> str:
        """
        Get the scope for the OAuth2 configuration.
        :return: The scope as a single string (order preserved, deduplicated).
        """
        scopes: List[str] = self._scope or []
        # Order-preserving deduplication
        seen = set()
        scopes_deduped = [x for x in scopes if not (x in seen or seen.add(x))]
        return self.scope_strategy.merge_scopes(scopes_deduped)

    def set_scope(self, value: Union[str, List[str]]) -> None:
        """
        Set the scope for the OAuth2 configuration.
        :param value: The scope to set, either as a string or a list of strings.
        :raises ValueError: If the value is not a string or list of strings.
        """
        if isinstance(value, str):
            value = self._scope_strategy.split_scopes(value)
            if isinstance(value, str):
                value = [value]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("Scope must be a string or a list of strings.")
        self.logger.debug("Setting scope (not logging value for security reasons)")
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
        :raises ValueError: If the value is not a ScopeStrategy instance.
        """
        if not isinstance(value, ScopeStrategy):
            raise ValueError("Scope strategy must be an instance of ScopeStrategy.")
        self.logger.debug("Setting scope strategy (not logging value for security reasons)")
        self._scope_strategy = value

    @property
    def grant_type(self) -> str:
        """
        Get the grant type for the OAuth2 configuration.
        :return: The grant type.
        """
        return self._grant_type.value

    @grant_type.setter
    def grant_type(self, value: OAuth2GrantType) -> None:
        """
        Set the grant type for the OAuth2 configuration.
        :param value: The grant type to set.
        :raises ValueError: If the value is not an OAuth2GrantType instance.
        """
        if not isinstance(value, OAuth2GrantType):
            raise ValueError("Grant type must be an instance of OAuth2GrantType.")
        self.logger.debug("Setting grant type (not logging value for security reasons)")
        self._grant_type: OAuth2GrantType = value

    @property
    def response_type(self) -> str:
        """
        Get the response type for the OAuth2 configuration.
        :return: The response type.
        """
        return self._response_type.value

    @response_type.setter
    def response_type(self, value: OAuth2ResponseType) -> None:
        """
        Set the response type for the OAuth2 configuration.
        :param value: The response type to set.
        :raises ValueError: If the value is not an OAuth2ResponseType instance.
        """
        if not isinstance(value, OAuth2ResponseType):
            raise ValueError("Response type must be an instance of OAuth2ResponseType.")
        self.logger.debug("Setting response type (not logging value for security reasons)")
        self._response_type: OAuth2ResponseType = value

    def add_scope(self, scope: str) -> None:
        """
        Add a scope to the OAuth2 configuration.
        :param scope: The scope to add.
        :raises ValueError: If the scope is not a string.
        """
        if not isinstance(scope, str) or not scope:
            raise ValueError("Scope must be a non-empty string.")
        if self._scope is None:
            self._scope = []
        if scope in self._scope:
            self.logger.debug("Scope already exists in the list (not logging value for security reasons)")
            return
        self.logger.debug("Adding scope (not logging value for security reasons)")
        self._scope.append(scope)

    def attach_client(self, client: ClientType) -> None:
        """
        Attach the client to the OAuth2 configuration.

        Arguments:
            client (ClientType): The client to attach, either httpx.Client or httpx.AsyncClient.
        Raises:
            ValueError: If the client is not an instance of httpx.Client or httpx.AsyncClient.
        Raises:
            TypeError: If the client is not of the expected type.
        """
        if not isinstance(client, (httpx.Client, httpx.AsyncClient)):
            raise TypeError("Client must be an instance of httpx.Client or httpx.AsyncClient.")
        self.logger.debug("Attaching client to OAuth2 configuration.")
        self.client = client
