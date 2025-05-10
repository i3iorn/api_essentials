import json
import asyncio
import logging

import yaml

from api_essentials.auth import OAuth2Auth, ClientCredentials
from api_essentials.factory import APIFactory
from api_essentials.flags import TRUST_UNDEFINED_PARAMETERS

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

async def main():
    with open(r"C:\Users\schrammelb\OneDrive - Dun and Bradstreet\Downloads\swagger.yaml", "r", encoding="utf-8") as f:
        openapi_spec = yaml.safe_load(f)

    my_api = APIFactory.from_openapi(openapi_spec, auth=OAuth2Auth(r"https://login.bisnode.com/sandbox/v1/token.oauth2"), verify=False)

    credentials = ClientCredentials(
        client_id="71a7c376-0f79-4fc5-9db9-6447d2097e21",
        client_secret="Ut0dzd8PWzZpxorrFJ8l0d8D4ZcbLNHsJVncvjc26v9V7A4LlLkCAgF11jsJdOxM",
        scopes=["rgs-decision"]
    )

    endpoint = my_api.get_endpoint("/company/se")

    response = await my_api.request(
        TRUST_UNDEFINED_PARAMETERS,
        auth_info=credentials,
        endpoint=endpoint,
        **{
            "registrationNumber": "9164103864",
            "rulesetKey": "1-1235-4566-7891",
            "reference": "1234567890",
            "duns": "1234567890",
            "endUser": "<EMAIL>",
            "onBehalfOf": "<EMAIL>",
        }
    )
    response.print_http()

if __name__ == "__main__":
    asyncio.run(main())
