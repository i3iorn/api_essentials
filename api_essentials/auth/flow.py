import base64
import logging
from datetime import datetime, timedelta

from typing import Generator, Mapping, Dict, Callable, Optional, List, Tuple, AsyncGenerator

import httpx
from httpx import Auth, Request, Response, URL

from api_essentials.auth.info import ClientCredentials
from api_essentials.logging_decorator import log_method_calls
from api_essentials.strategies import Strategy
from api_essentials.utils import rebuild_request

GRACE_PERIOD = 60  # seconds
DEFAULT_TOKEN_NAME = "access_token"
DEFAULT_EXPIRATION_NAME = "expires_in"
AUTHORIZATION_HEADER_NAME = "Authorization"

@log_method_calls()
class OAuth2Auth(Auth):
    """
    OAuth2 Bearer Token authentication.

    This class adds an Authorization header using the Bearer scheme.
    It is used for APIs that require OAuth2 authentication and supports
    automatic token refresh. It takes care of token management, including
    refreshing the token when it expires.

    Attributes:
        client_id (str): The client ID for the OAuth2 application.
        client_secret (str): The client secret for the OAuth2 application.
        token_url (str): The URL to obtain a new access token.
        scope (str): The scope of the access token.
        token (str): The OAuth2 bearer token.
    """
    def __init__(
            self,
            token_url:                  str,
            grant_type:                 str = None,
            headers:                    Mapping[str, str] = None,
            token_extractor:            Optional[Callable[[Dict], Optional[str]]] = None,
            token_expiration_extractor: Optional[Callable[[Dict], int]] = None,
            scope_strategy:             Optional[Strategy] = None
    ) -> None:
        self._validate_input(
            token_url=token_url,
            grant_type=grant_type,
            headers=headers,
            token_extractor=token_extractor,
            token_expiration_extractor=token_expiration_extractor,
            scope_strategy=scope_strategy
        )

        self.token_url                      = URL(token_url)
        self.grant_type                     = grant_type or "client_credentials"
        self.headers                        = headers or []
        self.token_extractor                = token_extractor or self._default_token_extractor
        self.token_expiration_extractor     = token_expiration_extractor or self._default_token_expiration_extractor
        self.token: str | None              = None
        self.token_data: Dict | None        = None
        self.expires_at: datetime | None    = datetime.now()
        self.token_requests: List[httpx.Request] = []
        self.token_responses: List[httpx.Response] = []

    def _validate_input(
            self,
            token_url: str,
            grant_type: str,
            headers: Mapping[str, str],
            token_extractor: Optional[Callable[[Dict], Optional[str]]],
            token_expiration_extractor: Optional[Callable[[Dict], int]],
            scope_strategy: Optional[Strategy]
    ) -> None:
        """
        Validates the input parameters for the OAuth2Auth class.

        Args:
            auth_info (ClientCredentials): The client credentials.
            token_url (str): The URL to obtain a new access token.
            grant_type (str): The grant type for the OAuth2 flow.
            headers (List[Mapping[str, str]]): Additional headers for the request.
            token_extractor (Optional[Callable[[Dict], Optional[str]]]): Function to extract the token from the response.
            token_expiration_extractor (Optional[Callable[[Dict], int]]): Function to extract the expiration time from the response.

        Raises:
            TypeError: If any of the input parameters are of the wrong type.
            ValueError: If any of the input parameters are invalid.
        """
        if not isinstance(token_url, str):
            raise TypeError("token_url must be a string.")
        if grant_type and not isinstance(grant_type, str):
            raise TypeError("grant_type must be a string.")
        if headers and not isinstance(headers, list):
            raise TypeError("headers must be a list of dictionaries.")
        if token_extractor and token_extractor and not callable(token_extractor):
            raise TypeError("token_extractor must be a callable function.")
        if token_expiration_extractor and token_expiration_extractor and not callable(token_expiration_extractor):
            raise TypeError("token_expiration_extractor must be a callable function.")
        if headers and not all(isinstance(header, dict) for header in headers):
            raise TypeError("All headers must be dictionaries.")
        if headers and not all("name" in header and "value" in header for header in headers):
            raise ValueError("Each header dictionary must contain 'name' and 'value' keys.")
        if headers and not all(header["name"] and header["value"] for header in headers):
            raise ValueError("Header names and values must be non-empty strings.")
        if scope_strategy is not None and not isinstance(scope_strategy, Strategy):
            raise TypeError("scope_strategy must be an instance of Strategy.")

        URL(token_url)

    def _default_token_extractor(self, response: Dict[str, str]) -> Optional[str]:
        """
        Default token extractor function.

        Args:
            response (Dict[str, str]): The response from the token endpoint.

        Returns:
            str: The access token.
        """
        return response.get(DEFAULT_TOKEN_NAME, None)

    def _default_token_expiration_extractor(self, response: Dict[str, str]) -> datetime:
        """
        Default token expiration extractor function.

        Args:
            response (Dict[str, str]): The response from the token endpoint.

        Returns:
            int: The expiration time in seconds.
        """
        return datetime.now() + timedelta(seconds=response.get(DEFAULT_EXPIRATION_NAME, 0))

    async def async_auth_flow(
        self, request: Request
    ) -> AsyncGenerator[Request, Response]:
        if self.has_expired():
            await self.refresh_token(request.extensions.get("auth_info"))

        request.extensions["token_requests"] = self.token_requests
        request.extensions["token_responses"] = self.token_responses
        request.headers[AUTHORIZATION_HEADER_NAME] = f"Bearer {self.token}"
        response = yield request

        if response.status_code == 401:
            await self.refresh_token(request.extensions.get("auth_info"))
            retry = await rebuild_request(response.request)
            retry.headers[AUTHORIZATION_HEADER_NAME] = f"Bearer {self.token}"
            yield retry

    def has_expired(self) -> bool:
        """
        Checks if the token has expired.

        Returns:
            bool: True if the token has expired, False otherwise.
        """
        return self.expires_at < datetime.now() or self.token is None

    async def refresh_token(self, auth_info, **kwargs) -> None:
        self._verify_request_kwargs(kwargs)

        auth_str = f"{auth_info.client_id}:{auth_info.client_secret}"
        basic_token = base64.b64encode(auth_str.encode()).decode()

        data = {"grant_type": self.grant_type, "scope": auth_info.get_scope()}
        data.update(kwargs.pop("data", {}))

        # Start with Basic auth header
        headers = {
            AUTHORIZATION_HEADER_NAME: f"Basic {basic_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        # Merge in any extra headers (our list of dicts)
        for hdr in self.headers:
            headers[hdr["name"]] = hdr["value"]
        # Finally allow overrides via kwargs
        headers.update(kwargs.pop("headers", {}))

        async with httpx.AsyncClient(
                timeout=kwargs.get("timeout", 10.0),
                verify=kwargs.get("verify", True)
        ) as client:
            request = client.build_request(
                method="POST",
                url=self.token_url,
                data=data,
                headers=headers,
                params=kwargs.get("params")
            )
            self.token_requests.append(request)
            token_response = await client.send(request)
            self.token_responses.append(token_response)

        if token_response.status_code != 200:
            logging.error(
                f"Token request failed: {token_response.status_code} {token_response.text}"
            )
            raise ValueError(f"Failed to obtain token: {token_response.text}. \nBody was {token_response.request.content} \nHeaders were {token_response.request.headers}")

        token_data = token_response.json()
        # store raw payload
        self.token_data = token_data
        # extract token & expiration
        self.token = self.token_extractor(token_data)
        expires = self.token_expiration_extractor(token_data)
        # if expiration is a delta, unify here:
        if isinstance(expires, (int, float)):
            expires = datetime.now() + timedelta(seconds=expires)
        self.expires_at = expires - timedelta(seconds=GRACE_PERIOD)

        logging.debug("refresh_token() completed", extra={"payload": None})

    def _verify_request_kwargs(self, kwargs):
        """
        Verifies the request kwargs.

        Args:
            kwargs (dict): The request kwargs.

        Raises:
            ValueError: If the request kwargs are invalid.
        """
        #Check if kwargs are valid input for requests.post
        if not isinstance(kwargs, dict):
            raise ValueError("Request kwargs must be a dictionary.")
        if "data" in kwargs and "json" in kwargs:
            raise ValueError("Cannot specify both 'data' and 'json' in request kwargs.")
        if "headers" in kwargs and not isinstance(kwargs["headers"], dict):
            raise ValueError("Headers must be a dictionary.")
        if "params" in kwargs and not isinstance(kwargs["params"], dict):
            raise ValueError("Params must be a dictionary.")
        if "timeout" in kwargs and not isinstance(kwargs["timeout"], (int, float)):
            raise ValueError("Timeout must be an integer or float.")
        if "allow_redirects" in kwargs and not isinstance(kwargs["allow_redirects"], bool):
            raise ValueError("allow_redirects must be a boolean.")
        if "verify" in kwargs and not isinstance(kwargs["verify"], (bool, str)):
            raise ValueError("verify must be a boolean or string.")
        if "proxies" in kwargs and not isinstance(kwargs["proxies"], dict):
            raise ValueError("Proxies must be a dictionary.")
        if "stream" in kwargs and not isinstance(kwargs["stream"], bool):
            raise ValueError("stream must be a boolean.")
        if "cert" in kwargs and not isinstance(kwargs["cert"], (str, tuple)):
            raise ValueError("cert must be a string or tuple.")
        if "hooks" in kwargs and not isinstance(kwargs["hooks"], dict):
            raise ValueError("hooks must be a dictionary.")
        if "auth" in kwargs and not isinstance(kwargs["auth"], (tuple, Auth)):
            raise ValueError("auth must be a tuple or an Auth object.")
        if "files" in kwargs and not isinstance(kwargs["files"], dict):
            raise ValueError("files must be a dictionary.")
        if "json" in kwargs and not isinstance(kwargs["json"], (dict, list)):
            raise ValueError("json must be a dictionary or list.")


def validate_auth_class(auth_class: Auth):
    if not isinstance(auth_class, Auth):
        raise TypeError("auth_class must be an instance of httpx.Auth.")
    if not hasattr(auth_class, "auth_flow"):
        raise ValueError("auth_class must have an 'auth_flow' method.")
    return auth_class