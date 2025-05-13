from api_essentials.auth.oauth_base import OAuth2FlowBase
import secrets, hashlib, base64
import httpx

class AuthorizationCodeOAuth2Flow(OAuth2FlowBase):
    def __init__(self, token_url: str, redirect_uri: str, **kwargs):
        super().__init__(token_url, **kwargs)
        self.redirect_uri = redirect_uri

    async def fetch_token(self, auth_info, **kwargs) -> dict:
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

        data = {
            "grant_type": "authorization_code",
            "code": auth_info.code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            **(kwargs.pop("data", {}))
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            **self.headers,
            **(kwargs.pop("headers", {}))
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data, headers=headers)
            response.raise_for_status()
            return response.json()
