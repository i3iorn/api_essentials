import asyncio
import logging
import time
from datetime import datetime, timedelta

from typing import Mapping, Dict, Callable, Optional, List, AsyncGenerator, Any, Generator

import httpx
from httpx import Auth, Request, URL

from api_essentials.constants import AUTHORIZATION_HEADER_NAME, GRACE_PERIOD, DEFAULT_TOKEN_NAME, \
    DEFAULT_EXPIRATION_NAME
from api_essentials.response import Response
from api_essentials.auth.info import ClientCredentials
from api_essentials.strategies import Strategy, CredentialEncodingStrategy
from api_essentials.utils import rebuild_request

logger = logging.getLogger(__name__)


class TokenFlow(Auth):
    """
    Token authentication.

    This class adds an Authorization header using the Bearer scheme.
    It is used for APIs that require token authentication.

    Attributes:
        token (str): The token to be used for authentication.
    """
    def __init__(self, token: str, header_name: str = "API-KEY") -> None:
        self.token = token
        self.header_name = header_name

    def async_auth_flow(
        self, request: Request
    ) -> AsyncGenerator[Request, Response]:
        """
        Asynchronous authentication flow.

        Args:
            request (Request): The HTTP request to be authenticated.

        Yields:
            Request: The authenticated request.
        """
        request.headers[self.header_name] = self.token
        yield request



class OAuth2Flow(Auth):
    """
    OAuth2 Bearer Token authentication.

    This class adds an Authorization header using the Bearer scheme.
    It is used for APIs that require OAuth2 authentication and supports
    automatic token refresh. It takes care of token management, including
    refreshing the token when it expires.

    Works only with client_credentials grant type.

    Attributes:
        token_url (str): The URL to obtain a new access token.
        scope (str): The scope of the access token.
        token (str): The OAuth2 bearer token.
    """
    def __init__(
            self,
            token_url:                  str,
            headers:                    Mapping[str, str] = None,
            token_extractor:            Optional[Callable[[Dict], Optional[str]]] = None,
            token_expiration_extractor: Optional[Callable[[Dict], int]] = None,
            scope_strategy:             Optional[Strategy] = None,
            credential_encoding_strategy: Optional[Strategy] = None,
    ) -> None:
        self._validate_input(
            token_url=token_url,
            headers=headers,
            token_extractor=token_extractor,
            token_expiration_extractor=token_expiration_extractor,
            scope_strategy=scope_strategy
        )

        self.credential_encoding_strategy   = credential_encoding_strategy or CredentialEncodingStrategy()
        self.token_url                      = URL(token_url)
        self.headers                        = headers or []
        self.token_extractor                = token_extractor or self._default_token_extractor
        self.token_expiration_extractor     = token_expiration_extractor or self._default_token_expiration_extractor
        self.token: str | None              = None
        self.token_data: Dict | None        = None
        self.expires_at: datetime | None    = datetime.now()
        self.token_request: httpx.Request | None  = None
        self.token_response: Response | None = None
        self._lock: asyncio.Lock            = asyncio.Lock()

    def _validate_input(
            self,
            token_url: str,
            headers: Mapping[str, str],
            token_extractor: Optional[Callable[[Dict], Optional[str]]],
            token_expiration_extractor: Optional[Callable[[Dict], int]],
            scope_strategy: Optional[Strategy]
    ) -> None:
        """
        Validates the input parameters for the OAuth2Flow class.

        Args:
            token_url (str): The URL to obtain a new access token.
            headers (List[Mapping[str, str]]): Additional headers for the request.
            token_extractor (Optional[Callable[[Dict], Optional[str]]]): Function to extract the token from the response.
            token_expiration_extractor (Optional[Callable[[Dict], int]]): Function to extract the expiration time from the response.

        Raises:
            TypeError: If any of the input parameters are of the wrong type.
            ValueError: If any of the input parameters are invalid.
        """
        URL(token_url)
        if not isinstance(token_url, str):
            raise TypeError("token_url must be a string.")
        if headers and not isinstance(headers, list):
            raise TypeError("headers must be a list")
        if token_extractor and token_extractor and not callable(token_extractor):
            raise TypeError("token_extractor must be a callable function.")
        if token_expiration_extractor and token_expiration_extractor and not callable(token_expiration_extractor):
            raise TypeError("token_expiration_extractor must be a callable function.")
        if scope_strategy is not None and not isinstance(scope_strategy, Strategy):
            raise TypeError("scope_strategy must be an instance of Strategy.")

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

    def auth_flow(self, request: Request) -> Generator[Request, Response, None]:
        """
        Sync auth flow: called by httpx.Client.
        """
        token = self._get_token()
        request.headers["Authorization"] = f"Bearer {token}"
        response = yield request
        if response.status_code == 401:
            # refresh once on 401
            self._fetch_token()
            request.headers["Authorization"] = f"Bearer {self._get_token()}"
            yield request

    def _get_token(self) -> str:
        """
        Get the token.

        Returns:
            str: The access token.
        """
        if self.has_expired():
            raise ValueError("Token has expired.")
        return self.token

    def _fetch_token(self) -> None:
        """
        Fetch the token from the token URL.
        """
        if self.has_expired():
            raise ValueError("Token has expired.")
        if self.token_request is None:
            raise ValueError("Token request is not set.")
        if self.token_response is None:
            raise ValueError("Token response is not set.")

        # Set the token in the request
        self.token = self.token_response.json().get(DEFAULT_TOKEN_NAME, None)
        if self.token is None:
            raise ValueError("Token not found in response.")

    async def async_auth_flow(
        self, request: Request
    ) -> AsyncGenerator[Request, Response]:
        if self.has_expired():
            await self.refresh_token(request.extensions.get("auth_info"))

        request.extensions["token_request"] = self.token_request
        request.extensions["token_response"] = self.token_response
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

    async def refresh_token(self, auth_info: ClientCredentials, **kwargs: Any) -> None:
        async with self._lock:
            if self.has_expired():
                self._verify_request_kwargs(kwargs)
                request_parameters: Dict = {"method": "POST", "url": self.token_url}
                logger.debug(f"Refreshing token for {auth_info.client_id}", extra={"payload": None})

                data = auth_info.get_body()
                data.update(kwargs.pop("data", {}))
                logger.debug(f"Token request data: {data}", extra={"payload": None})

                # Start with Basic auth header
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                logger.debug(f"Token request headers: {headers}", extra={"payload": None})

                headers.update(self.headers)
                headers.update(kwargs.pop("headers", {}))
                headers.update(auth_info.headers)
                logger.debug(f"Token request headers: {headers}", extra={"payload": None})

                if auth_info.send_as == "header":
                    basic_token = self.credential_encoding_strategy.apply(auth_info.client_id, auth_info.client_secret)
                    headers["Authorization"] = f"Basic {basic_token}"
                elif auth_info.send_as == "body":
                    data.update(
                        {
                            "client_id": auth_info.client_id,
                            "client_secret": auth_info.client_secret
                        }
                    )
                logger.debug(f"Token request data: {data}", extra={"payload": None})

                request_parameters["headers"] = headers

                if headers["Content-Type"] == "application/json":
                    request_parameters["json"] = data
                elif headers["Content-Type"] == "multipart/form-data":
                    request_parameters["files"] = data
                else:
                    request_parameters["data"] = data
                logger.debug(f"Token request parameters: {request_parameters}", extra={"payload": None})

                async with httpx.AsyncClient(
                        timeout=kwargs.get("timeout", 10.0),
                        verify=kwargs.get("verify", True)
                ) as client:
                    start = time.perf_counter()
                    request = client.build_request(**request_parameters)

                    end = time.perf_counter()
                    self.token_request = request
                    token_response = await client.send(request)
                    self.token_response = Response(token_response, end - start)
                    logger.debug(f"Token response was {token_response.status_code} - {token_response.text}", extra={"payload": None})

                logger.debug(f"Token request took {end - start:.2f} seconds", extra={"payload": None})

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

                logging.debug(f"Token expires at {self.expires_at} ({self.expires_at - datetime.now()}). \nToken was {self.token}")

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