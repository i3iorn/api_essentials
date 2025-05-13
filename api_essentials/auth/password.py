from api_essentials.auth.oauth_base import OAuth2FlowBase
import httpx

class PasswordOAuth2Flow(OAuth2FlowBase):
    async def fetch_token(self, auth_info, **kwargs) -> dict:
        data = {
            "grant_type": "password",
            "username": auth_info.username,
            "password": auth_info.password,
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
