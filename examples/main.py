import logging

import httpx
from httpx import URL

from auth.config import OAuth2Config
from auth.oauth2 import BaseOAuth2

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

config = OAuth2Config(
    client_id="client_id",
    client_secret="zQUaX2dbLZLZqwvboaewod1RbW7ZqxbtPv6p2u5fRg3FftGLY22yWb4rhFHfitdc6SjfAH",
    token_url=URL("https://login.example.com/oauth2")
)
config.scope = "credit_data_persons"
auth = BaseOAuth2(config)
client = httpx.Client(
    auth=auth,
    base_url="https://api.example.com/v2",
    verify=False
)
config.attach_client(client)
response = client.post(
    "/path/to/endpoint",
    json={
        "my_data": "value"
    }
)
print(response.status_code)
print(response.json())
