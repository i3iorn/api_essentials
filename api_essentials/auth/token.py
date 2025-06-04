import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Protocol

from httpx import URL, BasicAuth, Auth, Client, Response, HTTPStatusError, Request, RequestError

from .constants import TOKEN_GRACE_PERIOD
from .grant_type import OAuth2GrantType
from .exceptions import OAuth2TokenExpired, OAuth2TokenInvalid, OAuth2TokenRevoked
from .other import NoAuth

# Module-level logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class OAuthTokenType(Enum):
    """
    Enum representing the type of OAuth2 token.
    """
    ACCESS = "access"
    REFRESH = "refresh"


class OAuth2ConfigProtocol(Protocol):
    """
    Protocol for OAuth2 configuration. Any config passed to `request_new` or `refresh`
    should conform to this interface.
    """
    client: Optional[Client]
    token_url: URL
    client_id: str
    client_secret: str
    grant_type: OAuth2GrantType | str
    scope: Optional[str]
    token_class: type[OAuth2Token]


class _TokenRequestHelper:
    """
    Internal helper class responsible for performing HTTP requests to the OAuth2 token endpoint.
    """

    @staticmethod
    def _prepare_client(
        existing_client: Optional[Client],
        token_url: URL,
        client_id: str,
        client_secret: str,
    ) -> tuple[Client, Optional[Auth]]:
        """
        Prepare an httpx.Client for a token request. If an existing client is provided, swap in BasicAuth
        and return the original auth so it can be restored later. Otherwise, instantiate a new client.

        Returns:
            - client: Client to use for the request
            - original_auth: The auth that was on the existing client (None if a new client was created)
        """
        if existing_client:
            original_auth = existing_client.auth
            existing_client.auth = BasicAuth(client_id, client_secret)
            logger.debug("Swapped in BasicAuth on existing client for token request.")
            return existing_client, original_auth
        else:
            logger.debug("Creating a new httpx.Client for token request.")
            new_client = Client(
                base_url=str(token_url),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json"
                },
                auth=BasicAuth(client_id, client_secret),
                timeout=10.0  # example default timeout
            )
            return new_client, None

    @staticmethod
    def _finalize_client(
        client: Client,
        original_auth: Optional[Auth],
        used_existing_client: bool
    ) -> None:
        """
        Restore or close the client after the token request:
        - If we used an existing client, restore its original auth.
        - If we created a new client, close it.
        """
        if used_existing_client:
            if original_auth is not None:
                client.auth = original_auth
                logger.debug("Restored original auth on existing client.")
        else:
            client.close()
            logger.debug("Closed temporary httpx.Client after token request.")

    @staticmethod
    def perform_request(
        token_url: URL,
        client_id: str,
        client_secret: str,
        payload: Dict[str, Any],
        existing_client: Optional[Client]
    ) -> Dict[str, Any]:
        """
        Perform an HTTP POST to the token endpoint with BasicAuth. Handles exceptions and returns
        the parsed JSON token data.

        Raises:
            OAuth2TokenInvalid on HTTP status errors or network issues.
        """
        client, original_auth = _TokenRequestHelper._prepare_client(
            existing_client, token_url, client_id, client_secret
        )
        used_existing_client = existing_client is not None

        try:
            logger.debug(
                "Sending token request to %s with payload: %s",
                token_url, payload
            )
            response: Response = client.post(str(token_url), data=payload)
            response.raise_for_status()
            token_data = response.json()
            logger.debug("Token endpoint response data: %s", token_data)
            return token_data
        except HTTPStatusError as http_err:
            status = http_err.response.status_code
            text = http_err.response.text
            logger.error("Token endpoint HTTP error %s: %s", status, text)
            raise OAuth2TokenInvalid(f"Token request failed ({status}): {text}") from http_err
        except RequestError as req_err:
            logger.error("Network error during token request: %s", str(req_err))
            raise OAuth2TokenInvalid(f"Network error during token request: {req_err}") from req_err
        finally:
            _TokenRequestHelper._finalize_client(client, original_auth, used_existing_client)


@dataclass(frozen=True)
class OAuth2Token:
    """
    Immutable data class representing an OAuth2 token.
    Provides methods to check expiration, validity, revocation, and to request/refresh tokens.
    """

    access_token: str
    refresh_token: Optional[str] = None
    token_type: Optional[OAuthTokenType] = OAuthTokenType.ACCESS
    expires_in: Optional[int] = 0
    scope: Optional[List[str]] = field(default_factory=list)
    grant_type: Optional[OAuth2GrantType] = None
    token_url: Optional[URL] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[URL] = None
    created_at: Optional[datetime] = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    logger: logging.Logger = field(
        default_factory=lambda: logger, repr=False
    )
    grace_period: Optional[int] = TOKEN_GRACE_PERIOD

    def __post_init__(self) -> None:
        """
        Validate fields after initialization:
        - access_token must not be empty.
        - expires_in must be non-negative if provided.
        - created_at must be timezone-aware (assume UTC if naive).
        """
        self.logger.debug(
            "Initializing OAuth2Token(access_token=%s, expires_in=%s)",
            self.access_token, self.expires_in
        )

        if not self.access_token:
            self.logger.error("Empty access_token on OAuth2Token initialization.")
            raise OAuth2TokenInvalid("Access token cannot be empty.")

        if self.expires_in is not None and self.expires_in < 0:
            self.logger.error("Negative expires_in (%s) on OAuth2Token initialization.", self.expires_in)
            raise OAuth2TokenInvalid("expires_in must be non-negative.")

        if self.created_at and self.created_at.tzinfo is None:
            # Automatically assume UTC if naive
            self.logger.warning("created_at is naive; assuming UTC timezone.")
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=timezone.utc))

    @property
    def expires_at(self) -> Optional[datetime]:
        """
        Compute the absolute expiration datetime based on created_at + expires_in.
        Returns None if expires_in is None.
        """
        if self.expires_in is None:
            self.logger.debug("expires_in is None; expires_at is None.")
            return None

        expiration = self.created_at + timedelta(seconds=self.expires_in)
        self.logger.debug("Computed expires_at: %s", expiration)
        return expiration

    @property
    def is_expired(self) -> bool:
        """
        Determine if the token is expired or within its grace period.
        If expires_at is None, treat as expired (cannot verify).
        """
        exp = self.expires_at
        if exp is None:
            self.logger.debug("expires_at is None; treating token as expired.")
            return True

        # Subtract grace period
        cutoff = exp - timedelta(seconds=self.grace_period or 0)
        now = datetime.now(tz=timezone.utc)
        expired = now > cutoff
        self.logger.debug("Token expiration check: now=%s, cutoff=%s, expired=%s", now, cutoff, expired)
        return expired

    @property
    def is_valid(self) -> bool:
        """
        A token is valid if it has a non-empty access_token and is not expired.
        """
        if not self.access_token:
            self.logger.debug("is_valid: access_token is empty -> invalid.")
            return False

        if self.is_expired:
            self.logger.debug("is_valid: token is expired -> invalid.")
            return False

        self.logger.debug("is_valid: token is valid.")
        return True

    @property
    def is_revoked(self) -> bool:
        """
        A token is considered revoked if access_token is empty or None.
        """
        revoked = not bool(self.access_token)
        self.logger.debug("is_revoked: %s", revoked)
        return revoked

    @property
    def token(self) -> str:
        """
        Return the access_token if still valid and not revoked; otherwise raise.
        """
        if self.is_expired:
            self.logger.error("Attempt to access expired token.")
            raise OAuth2TokenExpired("Token has expired.")
        if self.is_revoked:
            self.logger.error("Attempt to access revoked token.")
            raise OAuth2TokenRevoked("Token has been revoked.")
        return self.access_token

    def refresh(self, config: OAuth2ConfigProtocol) -> "OAuth2Token":
        """
        Refresh this token using the refresh_token grant. Returns a new OAuth2Token.

        Raises:
            - OAuth2TokenExpired: if the current token is already expired.
            - OAuth2TokenInvalid: if refresh_token is missing or HTTP/network failure.
        """
        if self.is_expired:
            self.logger.error("Cannot refresh: token is already expired.")
            raise OAuth2TokenExpired("Cannot refresh: token is expired.")

        if not self.refresh_token:
            self.logger.error("Cannot refresh: missing refresh_token.")
            raise OAuth2TokenInvalid("Cannot refresh: no refresh_token provided.")

        self.logger.debug("Refreshing token via refresh_token grant.")
        payload: Dict[str, Any] = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        if config.scope:
            payload["scope"] = config.scope

        token_data = _TokenRequestHelper.perform_request(
            token_url=self.token_url or config.token_url,
            client_id=self.client_id or config.client_id,
            client_secret=self.client_secret or config.client_secret,
            payload=payload,
            existing_client=config.client
        )

        new_token = config.token_class.from_dict(token_data)
        self.logger.debug("Received refreshed token: %s", new_token)
        return new_token

    @classmethod
    def request_new(cls, config: OAuth2ConfigProtocol) -> "OAuth2Token":
        """
        Request a new token using the grant_type and client credentials provided in config.
        Returns a new OAuth2Token.

        Raises:
            - OAuth2TokenInvalid: on HTTP/network failure.
        """
        request_logger = logging.getLogger(f"{cls.__name__}.request_new")
        request_logger.debug("Requesting new token with grant_type=%s, scope=%s",
                             config.grant_type, config.scope)

        payload: Dict[str, Any] = {
            "grant_type": getattr(config, "grant_type", str(OAuth2GrantType.CLIENT_CREDENTIALS)),
        }
        if config.scope:
            payload["scope"] = config.scope

        token_data = _TokenRequestHelper.perform_request(
            token_url=config.token_url,
            client_id=config.client_id,
            client_secret=config.client_secret,
            payload=payload,
            existing_client=config.client
        )

        new_token = config.token_class.from_dict(token_data)
        request_logger.debug("Received new token: %s", new_token)
        return new_token

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the OAuth2Token to a dictionary for storage or JSON serialization.
        """
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type.value if self.token_type else None,
            "expires_in": self.expires_in,
            "scope": self.scope,
            "grant_type": self.grant_type.value if self.grant_type else None,
            "token_url": str(self.token_url) if self.token_url else None,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": str(self.redirect_uri) if self.redirect_uri else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuth2Token":
        """
        Reconstruct an OAuth2Token from a serialized dictionary.
        Parses token_type, grant_type, created_at, token_url, and redirect_uri as needed.
        """
        # Parse token_type
        raw_type = data.get("token_type")
        token_type = None
        if isinstance(raw_type, str):
            try:
                token_type = OAuthTokenType(raw_type)
            except ValueError:
                token_type = OAuthTokenType.ACCESS

        # Parse grant_type
        raw_grant = data.get("grant_type")
        grant_type = None
        if isinstance(raw_grant, str):
            try:
                grant_type = OAuth2GrantType(raw_grant)
            except ValueError:
                grant_type = None

        # Parse created_at
        created_at_raw = data.get("created_at")
        if created_at_raw:
            try:
                created_at = datetime.fromisoformat(created_at_raw)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                created_at = datetime.now(tz=timezone.utc)
        else:
            created_at = datetime.now(tz=timezone.utc)

        # Parse URLs
        raw_url = data.get("token_url")
        token_url = URL(raw_url) if raw_url else None

        raw_redirect = data.get("redirect_uri")
        redirect_uri = URL(raw_redirect) if raw_redirect else None

        return cls(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token"),
            token_type=token_type,
            expires_in=data.get("expires_in"),
            scope=data.get("scope") or [],
            grant_type=grant_type,
            token_url=token_url,
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            redirect_uri=redirect_uri,
            created_at=created_at,
        )

    def __repr__(self) -> str:
        """
        Custom representation showing key fields.
        """
        exp = self.expires_at.isoformat() if self.expires_at else "None"
        return (
            f"{self.__class__.__name__}("
            f"access_token={self.access_token!r}, "
            f"refresh_token={self.refresh_token!r}, "
            f"token_type={self.token_type!r}, "
            f"expires_at={exp!r}, "
            f"scope={self.scope!r})"
        )


class RiskAnalyticsToken(OAuth2Token):
    """
    Specialized token class for Risk Analytics. Implements a JSON-based token request
    that does not use client credentials in form data but in JSON with NoAuth.
    """

    @classmethod
    def request_new(cls, config: OAuth2ConfigProtocol) -> "RiskAnalyticsToken":
        """
        Request a new RiskAnalyticsToken using JSON payload and NoAuth HTTP client.

        Raises:
            - OAuth2TokenInvalid: on HTTP/network failure or missing client.
        """
        ra_logger = logging.getLogger(f"{cls.__name__}.request_new")
        ra_logger.debug("Requesting new RiskAnalyticsToken with JSON payload.")

        if not config.client:
            ra_logger.error("Config.client is required for RiskAnalyticsToken.request_new.")
            raise OAuth2TokenInvalid("HTTP client is required for RiskAnalyticsToken.")

        json_payload: Dict[str, Any] = {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }

        request = Request(
            method="POST",
            url=str(config.token_url),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=json_payload
        )

        try:
            response: Response = config.client.send(request, auth=NoAuth())
            response.raise_for_status()
            token_data = response.json()
            ra_logger.debug("Received RiskAnalyticsToken data: %s", token_data)
        except HTTPStatusError as http_err:
            status = http_err.response.status_code
            text = http_err.response.text
            ra_logger.error("RiskAnalyticsToken HTTP error %s: %s", status, text)
            raise OAuth2TokenInvalid(f"RiskAnalyticsToken request failed ({status}): {text}") from http_err
        except RequestError as req_err:
            ra_logger.error("Network error during RiskAnalyticsToken request: %s", str(req_err))
            raise OAuth2TokenInvalid(f"Network error during RiskAnalyticsToken request: {req_err}") from req_err

        return config.token_class.from_dict(token_data)


# ============================================================================
# Example usage (separate file or test module):
# ============================================================================

# from httpx import Client, URL
# from mypackage.oauth2 import OAuth2Config, OAuth2Token, OAuth2GrantType, OAuth2TokenInvalid
#
# # 1. Request a new token with client credentials:
# config = OAuth2Config(
#     client=Client(),
#     token_url=URL("https://example.com/oauth2/token"),
#     client_id="your-client-id",
#     client_secret="your-client-secret",
#     grant_type=OAuth2GrantType.CLIENT_CREDENTIALS,
#     scope="read write",
#     token_class=OAuth2Token
# )
#
# try:
#     token = OAuth2Token.request_new(config)
#     print("Access Token:", token.access_token)
#     print("Expires At:", token.expires_at)
# except OAuth2TokenInvalid as e:
#     print(f"Failed to obtain token: {e}")
#
# # 2. Later, refresh the token:
# try:
#     refreshed = token.refresh(config)
#     print("Refreshed Access Token:", refreshed.access_token)
# except (OAuth2TokenExpired, OAuth2TokenInvalid) as e:
#     print(f"Failed to refresh token: {e}")
