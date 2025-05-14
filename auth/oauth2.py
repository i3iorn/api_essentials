import logging
import typing
from base64 import b64encode
from typing import TYPE_CHECKING

import httpx
from httpx import Auth, Request, Response
from enum import Enum

from auth.grant_type import OAuth2GrantType
from auth.token import OAuth2Token
from utils.log import register_secret, setup_secret_filter

if TYPE_CHECKING:
    from auth.config import OAuth2Config

ClientType = typing.Union[httpx.Client, httpx.AsyncClient]

class OAuth2ResponseType(Enum):
    """
    Enum to represent the OAuth2 response types.
    """
    CODE = "code"
    TOKEN = "token"

class BaseOAuth2(Auth):
    requires_request_body:  bool = True
    requires_response_body: bool = True

    def __init__(self, config: "OAuth2Config"):
        register_secret(config.client_secret)
        setup_secret_filter()

        self.config: "OAuth2Config" = config
        self.logger = logging.getLogger(__name__)

    def sync_auth_flow(
        self, request: Request
    ) -> typing.Generator[Request, Response, None]:
        """
        Synchronous authentication flow for OAuth2.
        """
        self.logger.debug("Starting OAuth2 sync auth flow.")
        token: OAuth2Token = self._get_token()
        request.headers["Authorization"] = f"Bearer {token.access_token}"
        request.headers["Content-Type"] = "application/json"

        yield request

    def _get_token(self) -> "OAuth2Token":
        """
        Get the access token for the OAuth2 configuration.
        :return: The access token.
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

        return config.token_class.request_new(config)
