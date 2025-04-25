import asyncio
from time import sleep

from api_essentials.api import AbstractAPI
from api_essentials.auth import OAuth2Auth, ClientCredentials


class Decisioning(AbstractAPI):
    def __init__(self):
        base_url="https://api.bisnode.com/decision/v3/"
        credentials = ClientCredentials(
            client_id="71a7c376-0f79-4fc5-9db9-6447d2097e21",
            client_secret="Ut0dzd8PWzZpxorrFJ8l0d8D4ZcbLNHsJVncvjc26v9V7A4LlLkCAgF11jsJdOxM",
            scopes=["rgs-decision"]
        )
        auth_class=OAuth2Auth(
            auth_info=credentials,
            token_url="https://login.bisnode.com/sandbox/v1/token.oauth2",
        )
        super().__init__(
            base_url=base_url,
            auth_class=auth_class
        )

    def endpoints(self):
        return {
            "decision": "company/se"
        }


async def main():
    decisioning_api = Decisioning()
    await decisioning_api.initialize_client(verify=False)
    response = await decisioning_api.get(decisioning_api.endpoints()["decision"])
    print(response.json())

if __name__ == "__main__":
    asyncio.run(main())
