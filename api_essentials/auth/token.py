from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, TYPE_CHECKING, Dict, Any, Type

from httpx import URL, BasicAuth, Auth, Client, Response, HTTPStatusError, Request

from .constants import TOKEN_GRACE_PERIOD
from .grant_type import OAuth2GrantType
from .exceptions import OAuth2TokenExpired, OAuth2TokenInvalid, OAuth2TokenRevoked
from .other import NoAuth
import logging

if TYPE_CHECKING:
    from .config import OAuth2Config


class OAuthTokenType(Enum):
    """
    Enum to represent the type of OAuth2 token.
    """
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class OAuth2Token:
    """
    Data class to hold OAuth2 token information. This class provides methods to check
    the token's validity, expiration, and to refresh the token if necessary.
    It also provides methods to convert the token to and from a dictionary format.
    This class is immutable and should be instantiated with all required parameters.
    The token is considered valid if it is not expired and has a non-null access token.
    The token is considered expired if the current time is greater than the expiration
    time minus the grace period. The token is considered revoked if the access token is
    null.

    Attributes:
        access_token (str): The access token.
        refresh_token (Optional[str]): The refresh token.
        token_type (Optional[OAuthTokenType]): The type of the token (access or refresh).
        expires_in (Optional[int]): The expiration time in seconds.
        scope (Optional[List[str]]): The scope of the token.
        grant_type (Optional[OAuth2GrantType]): The grant type used to obtain the token.
        token_url (Optional[URL]): The URL to request the token.
        client_id (Optional[str]): The client ID.
        client_secret (Optional[str]): The client secret.
        redirect_uri (Optional[URL]): The redirect URI.
        created_at (Optional[datetime]): The time the token was created.
        logger (Optional[logging.Logger]): Logger instance for logging.
        grace_period (Optional[int]): The grace period for token expiration. The grace
            period is the time before the token is considered expired. Defaults to
            60 seconds. Use environmental variable AUTH_TOKEN_GRACE_PERIOD to set a
            different value.

    Methods:
        expires_at: Returns the expiration time of the token.
        is_expired: Checks if the token is expired.
        is_valid: Checks if the token is valid.
        is_revoked: Checks if the token is revoked.
        token: Returns the access token.
        refresh: Refreshes the token using the refresh_token grant.
        request_new: Requests a new token using the provided OAuth2 configuration.
        to_dict: Converts the OAuth2Token instance to a dictionary.
        from_dict: Creates an OAuth2Token instance from a dictionary.

    Raises:
        OAuth2TokenExpired: If the token is expired.
        OAuth2TokenInvalid: If the token is invalid or cannot be refreshed.
        OAuth2TokenRevoked: If the token is revoked.
    """
    access_token:   str
    refresh_token:  Optional[str]       = None
    token_type:     Optional[OAuthTokenType] = OAuthTokenType.ACCESS
    expires_in:     Optional[int]       = 0
    scope:          Optional[List[str]] = field(default_factory=list)
    grant_type:     Optional[OAuth2GrantType] = None
    token_url:      Optional[URL]       = None
    client_id:      Optional[str]       = None
    client_secret:  Optional[str]       = None
    redirect_uri:   Optional[URL]       = None
    created_at:     Optional[datetime]  = field(default_factory=datetime.now)
    logger:         Optional[logging.Logger] = field(default_factory=logging.getLogger, repr=False)
    grace_period:   Optional[int]       = TOKEN_GRACE_PERIOD

    @property
    def expires_at(self) -> Optional[datetime]:
        """
        Get the expiration time of the token.
        :return: The expiration time as a datetime object.
        """
        if self.expires_in is None:
            return None
        return self.created_at + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        """
        Check if the token is expired.
        :return: True if the token is expired, False otherwise.
        """
        if self.expires_in is None:
            return True
        return datetime.now() > (self.created_at + timedelta(seconds=self.expires_in) - timedelta(seconds=self.grace_period))

    @property
    def is_valid(self) -> bool:
        """
        Check if the token is valid.
        :return: True if the token is valid, False otherwise.
        """
        return not self.is_expired and self.access_token is not None

    @property
    def is_revoked(self) -> bool:
        """
        Check if the token is revoked.
        :return: True if the token is revoked, False otherwise.
        """
        return self.access_token is None

    @property
    def token(self) -> str:
        """
        Get the token.
        :return: The token.
        """
        if self.is_expired:
            raise OAuth2TokenExpired("Token is expired.")
        if self.is_revoked:
            raise OAuth2TokenRevoked("Token is revoked.")
        return self.access_token

    def refresh(self, config: "OAuth2Config") -> "OAuth2Token":
        """
        Refresh this token using the refresh_token grant.

        :param config: OAuth2Config containing:
                       - client: httpx.Client
                       - token_url: URL
                       - client_id / client_secret
                       - scope (optional)
                       - token_class (class to instantiate)
        :return: a fresh OAuth2Token
        :raises OAuth2TokenExpired: if this token has already expired
        :raises OAuth2TokenInvalid: if no refresh_token is present or HTTP fails
        """
        # Must not try to refresh if the current token is already expired
        if self.is_expired:
            self.logger.debug("Token is expired, cannot refresh.")
            raise OAuth2TokenExpired("Cannot refresh: current token is expired.")

        if not self.refresh_token:
            self.logger.debug("No refresh token available, cannot refresh.")
            raise OAuth2TokenInvalid("Cannot refresh: no refresh_token available.")

        original_auth = None
        if config.client is not None:
            original_auth: Auth = config.client.auth
            client = config.client
        else:
            client = Client(
                base_url=str(config.token_url),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json"
                }
            )

        client.auth = BasicAuth(config.client_id, config.client_secret)
        self.logger.debug(f"Swapping in basic auth for refresh request: {client.auth}")

        try:
            payload: Dict[str, Any] = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }
            if config.scope:
                payload["scope"] = config.scope

            response: Response = client.post(
                str(config.token_url),
                data=payload,
            )

            response.raise_for_status()
            token_data: Dict[str, Any] = response.json()
        except HTTPStatusError as e:
            raise OAuth2TokenInvalid(
                f"Failed to refresh token: {e.response.status_code} {e.response.text}"
            ) from e
        finally:
            # Always restore the original auth
            if original_auth is not None:
                client.auth = original_auth

        # Instantiate a new token object, preserving the token_class
        return config.token_class.from_dict(token_data)

    @classmethod
    def request_new(cls, config: "OAuth2Config") -> 'OAuth2Token':
        """
        Request a new token using the provided OAuth2 configuration.
        :param config: The OAuth2 configuration to use for requesting a new token.
        :return: A new OAuth2Token instance with the requested token.
        """
        if config.client is None:
            logging.getLogger(cls.__name__).warning("Client is not set in the configuration. Using new unsecured synchronous client.")
            client = Client(
                base_url=str(config.token_url),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json"
                }
            )
            cur_auth = None
        else:
            client = config.client
            cur_auth: Auth = client.auth
            client.auth = BasicAuth(config.client_id, config.client_secret)

        try:
            request: Request = Request(
                method="POST",
                url=str(config.token_url),
                data={
                    "grant_type": config.grant_type,
                    "scope": config.scope
                }
            )
            logging.getLogger(cls.__name__).debug(f"Request url: {request.url}")
            logging.getLogger(cls.__name__).debug(f"Request headers: {request.headers}")
            logging.getLogger(cls.__name__).debug(f"Request body: {request.content}")

            response: Response = client.send(request)
            response.raise_for_status()
            token_data: Dict[str, Any] = response.json()
        except HTTPStatusError as e:
            raise OAuth2TokenInvalid(f"Failed to request new token: {e.response.status_code} {e.response.text}") from e
        finally:
            # Always restore the original auth
            if cur_auth is not None:
                client.auth = cur_auth

        return config.token_class.from_dict(token_data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the OAuth2Token instance to a dictionary.
        :return: A dictionary representation of the OAuth2Token instance.
        """
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type.value if self.token_type else None,
            "expires_in": self.expires_in,
            "scope": self.scope,
            "token_url": str(self.token_url) if self.token_url else None,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": str(self.redirect_uri) if self.redirect_uri else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OAuth2Token':
        """
        Create an OAuth2Token instance from a dictionary.
        :param data: The dictionary containing token information.
        :return: An OAuth2Token instance.
        """
        logging.getLogger(cls.__name__).warning(
            "Client is not set in the configuration. Using new unsecured synchronous client.")

        return cls(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type"),
            expires_in=data.get("expires_in"),
            scope=data.get("scope"),
            token_url=data.get("token_url"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            redirect_uri=data.get("redirect_uri")
        )

    def __repr__(self):
        return f"OAuth2Token(access_token={self.access_token}, refresh_token={self.refresh_token}, token_type={self.token_type}, expires_at={self.expires_at}, scope={self.scope})"

class RiskAnalyticsToken(OAuth2Token):
    @classmethod
    def request_new(cls, config: "OAuth2Config") -> 'OAuth2Token':
        """
        Request a new token using the provided OAuth2 configuration.
        :param config: The OAuth2 configuration to use for requesting a new token.
        :return: A new OAuth2Token instance with the requested token.
        """
        try:
            request: Request = Request(
                method="POST",
                url=str(config.token_url),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                }
            )
            logging.getLogger(cls.__name__).debug(f"Request headers: {request.headers}")
            logging.getLogger(cls.__name__).debug(f"Request body: {request.content}")

            response: Response = config.client.send(request, auth=NoAuth())
            response.raise_for_status()
            token_data: Dict[str, Any] = response.json()
        except HTTPStatusError as e:
            raise OAuth2TokenInvalid(f"Failed to request new token: {e.response.status_code} {e.response.text}") from e

        return config.token_class.from_dict(token_data)
