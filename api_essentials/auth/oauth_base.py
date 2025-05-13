import typing
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Optional

from httpx import Auth, Request, Response

from api_essentials.strategies import (
    CredentialEncodingStrategy,
    BasicAuthEncodingStrategy,
    TokenExtractor,
    DefaultTokenExtractor,
    ExpirationExtractor,
    DefaultExpirationExtractor,
)

GRACE_PERIOD = 60  # seconds

class OAuth2FlowBase(Auth, ABC):
    def __init__(
        self,
        token_url: str,
        credential_strategy: Optional[CredentialEncodingStrategy] = None,
        token_extractor: Optional[TokenExtractor] = None,
        expiration_extractor: Optional[ExpirationExtractor] = None,
        headers: Optional[dict] = None,
    ):
        self.token_url = token_url
        self.credential_strategy = credential_strategy or BasicAuthEncodingStrategy()
        self.token_extractor = token_extractor or DefaultTokenExtractor()
        self.expiration_extractor = expiration_extractor or DefaultExpirationExtractor()
        self.headers = headers or {}
        self.token: Optional[str] = None
        self.expires_at: Optional[datetime] = None
        self.token_data: Optional[dict] = None
        self._refresh_lock: asyncio.Lock = asyncio.Lock()
        self.token_request: Optional[Request] = None
        self.token_response: Optional[Response] = None

    def has_expired(self) -> bool:
        return not self.token or not self.expires_at or self.expires_at <= datetime.now()

    async def async_auth_flow(self, request: Request) -> AsyncGenerator[Request, Response]:
        if self.has_expired():
            await self.refresh_token(request.extensions.get("auth_info"))

        request.headers["Authorization"] = f"Bearer {self.token}"
        response = yield request

        if response.status_code == 401:
            await self.refresh_token(request.extensions.get("auth_info"))
            request = request.copy()
            request.headers["Authorization"] = f"Bearer {self.token}"
            yield request

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        if self.has_expired():
            asyncio.run(self.refresh_token(request.extensions.get("auth_info")))

        request.headers["Authorization"] = f"Bearer {self.token}"
        response = yield request

        if response.status_code == 401:
            self.refresh_token(request.extensions.get("auth_info"))
            request = request.copy()
            request.headers["Authorization"] = f"Bearer {self.token}"
            yield request

    async def refresh_token(self, auth_info, **kwargs):
        async with self._refresh_lock:
            if not self.has_expired():
                return
            token_data = await self.fetch_token(auth_info, **kwargs)
            self.token = self.token_extractor.extract(token_data)
            expires_in = self.expiration_extractor.extract(token_data)
            self.expires_at = datetime.now() + timedelta(seconds=expires_in - GRACE_PERIOD)
            self.token_data = token_data

    @abstractmethod
    async def fetch_token(self, auth_info, **kwargs) -> Dict:
        pass
