import logging
import typing
from typing import TYPE_CHECKING, Generator, AsyncGenerator

import httpx
from httpx import Auth, Request, Response
from enum import Enum

from api_essentials.utils.log import register_secret, setup_secret_filter
from .token import OAuth2Token

if TYPE_CHECKING:
    from .config import OAuth2Config

ClientType = typing.Union[httpx.Client, httpx.AsyncClient]

class OAuth2ResponseType(Enum):
    """
    Enum to represent the OAuth2 response types.
    """
    CODE = "code"
    TOKEN = "token"


class BaseAuth(Auth):
    pass

class BaseOAuth2(BaseAuth):
    requires_request_body:  bool = True
    requires_response_body: bool = True

    def __init__(self, config: "OAuth2Config") -> None:
        register_secret(config.client_secret)
        setup_secret_filter()

        self.config: "OAuth2Config" = config
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.logger.debug("BaseOAuth2 initialized with config: %s", config)

    def sync_auth_flow(
        self, request: Request
    ) -> Generator[Request, Response, None]:
        """
        Synchronous authentication flow for OAuth2.
        Arguments:
            request (Request): The request to authenticate.
        Returns:
            Request: (Yields) The authenticated request.
        Raises:
            RuntimeError: If the token acquisition fails.
        """
        self.logger.debug("Starting OAuth2 sync auth flow with request: %s", request)
        request = self._setup_auth_flow(request)
        self.logger.debug("Yielding request in sync auth flow: %s", request)
        yield request

    async def async_auth_flow(
        self, request: Request
    ) -> AsyncGenerator[Request, Response]:
        """
        Asynchronous authentication flow for OAuth2.

        Arguments:
            request (Request): The request to authenticate.
        Returns:
            Request: (Yields) The authenticated request.
        Raises:
            RuntimeError: If the token acquisition fails.
        """
        self.logger.debug("Starting OAuth2 async auth flow with request: %s", request)
        request = self._setup_auth_flow(request)
        self.logger.debug("Yielding request in async auth flow: %s", request)
        yield request

    def _setup_auth_flow(self, request: httpx.Request) -> httpx.Request:
        """
        Set up the authentication flow for the request.

        Arguments:
            request (httpx.Request): The request to set up the authentication flow for.
        Returns:
            httpx.Request: The request with the authentication flow set up.
        Raises:
            RuntimeError: If the token acquisition fails.
        """
        self.logger.debug("Setting up OAuth2 auth flow for request: %s", request)
        try:
            token: OAuth2Token = self._get_token()
            self.logger.debug("Obtained token: %s", token)
        except AttributeError:
            self.logger.error("AttributeError encountered during token acquisition.")
            raise
        except Exception as e:
            self.logger.error("Failed to get OAuth2 token: %s", str(e))
            raise RuntimeError("Failed to get OAuth2 token.") from e
        request.headers["Authorization"] = f"Bearer {token.access_token}"
        request.headers["Content-Type"] = "application/json"
        self.logger.debug("Request headers updated for OAuth2 auth flow: %s", request.headers)
        return request

    def _get_token(self) -> "OAuth2Token":
        """
        Get the access token for the OAuth2 configuration.

        Arguments:
            None
        Returns:
            OAuth2Token: The access token for the OAuth2 configuration.
        Raises:
            RuntimeError: If no token class is provided or if the token acquisition fails.
        """
        config: OAuth2Config = self.config
        access_token: OAuth2Token = config.access_token
        refresh_token: OAuth2Token = config.refresh_token

        # Check if the token is expired
        if access_token and access_token.is_valid:
            self.logger.debug("Access token is valid.")
            return access_token

        # If the token is expired, refresh it
        if refresh_token and refresh_token.is_valid:
            self.logger.debug("Access token is expired, refreshing token.")
            return refresh_token.refresh(config)

        self.logger.debug("Access token is expired, requesting new token.")
        if access_token:
            return access_token.request_new(config)

        if config.token_class is not None:
            self.logger.debug("Requesting new token.")
            return config.token_class.request_new(config)
        else:
            self.logger.error("No token class provided.")
            raise RuntimeError("No token class provided.")

