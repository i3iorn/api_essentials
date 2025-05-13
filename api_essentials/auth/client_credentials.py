from api_essentials.auth.oauth_base import OAuth2FlowBase
import httpx

class ClientCredentialsOAuth2Flow(OAuth2FlowBase):
    async def fetch_token(self, auth_info, **kwargs) -> dict:
        data = {
            "grant_type": "client_credentials",
            "scope": auth_info.scope or "",
            **(kwargs.pop("data", {}))
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            **self.headers,
            **(kwargs.pop("headers", {}))
        }

        if auth_info.send_as == "header":
            token = self.credential_strategy.apply(auth_info.client_id, auth_info.client_secret)
            headers["Authorization"] = f"Basic {token}"
        elif auth_info.send_as == "body":
            data["client_id"] = auth_info.client_id
            data["client_secret"] = auth_info.client_secret

        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data, headers=headers)
            response.raise_for_status()
            return response.json()
