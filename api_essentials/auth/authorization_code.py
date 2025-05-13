from api_essentials.auth.oauth_base import OAuth2FlowBase
import httpx

class AuthorizationCodeOAuth2Flow(OAuth2FlowBase):
    def __init__(self, token_url: str, redirect_uri: str, **kwargs):
        super().__init__(token_url, **kwargs)
        self.redirect_uri = redirect_uri

    async def fetch_token(self, auth_info, **kwargs) -> dict:
        data = {
            "grant_type": "authorization_code",
            "code": auth_info.code,
            "redirect_uri": self.redirect_uri,
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
