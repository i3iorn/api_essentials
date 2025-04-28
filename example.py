import asyncio
import logging
from time import sleep
from typing import List

from httpx import URL

from src.api import AbstractAPI
from src.auth import OAuth2Auth, ClientCredentials
from src.client import APIClient
from src.endpoint import EndpointDefinition, Endpoint
from src.flags import ALLOW_UNSECURE
from src.logging_decorator import log_method_calls
from src.parameter import ParameterFactoryService


class MyFormatter(logging.Formatter):
    def __init__(
            self,
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d, %H:%M:%S",
            style='%',
            validate=True
    ):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)

    def format(self, record):
        # first produce the standard formatted message
        base = super().format(record)

        # extract your extra payload (or {} if missing)
        extra = getattr(record, 'payload', {})

        # append it (repr‑style) if present
        if extra:
            base = f"{base} | payload={extra!r}"

        return base


# Set up logging
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(MyFormatter())

logging.basicConfig(level=logging.DEBUG, handlers=[stream_handler])


@log_method_calls()
class RGSDecisioning(AbstractAPI):
    def __init__(self, client: APIClient):
        super().__init__(client)

    def endpoints(self) -> List[Endpoint]:
        param_factory = ParameterFactoryService()
        b2b_se_decision_definition = EndpointDefinition(
            path="/company/se",
            method="POST",
            description="Decisioning API endpoint",
            parameters=[
                param_factory.header(
                    name="Authorization",
                    description="Bearer token",
                    required=True,
                ),
                param_factory.body(
                    name="registrationNumber",
                    description="Registration number of the company",
                    required=True,
                    min_length=6,
                    max_length=13,
                ),
                param_factory.body(
                    name="reference",
                    description="Request reference, returned in the response.",
                    required=True,
                    min_length=1,
                ),
                param_factory.body(
                    name="duns",
                    description="D-U-N-S number of the company",
                    value_type="integer",
                ),
                param_factory.body(
                    name="endUser",
                    description="End-User making the request",
                    deprecated=True,
                ),
                param_factory.body(
                    name="onBehalfOf",
                    description="Internal id (not national id number) of person or client company that triggered the request.",
                ),
                param_factory.body(
                    name="rulesetKey",
                    description="Ruleset key to use for the decisioning",
                    required=True,
                    min_length=16,
                    max_length=16,
                ),
            ]
        )
        b2b_se_decision = Endpoint(
            api=self,
            definition=b2b_se_decision_definition
        )


        return [
            b2b_se_decision
        ]


async def main():
    credentials = ClientCredentials(
        client_id="71a7c376-0f79-4fc5-9db9-6447d2097e21",
        client_secret="Ut0dzd8PWzZpxorrFJ8l0d8D4ZcbLNHsJVncvjc26v9V7A4LlLkCAgF11jsJdOxM",
        scopes=["rgs-decision"]
    )
    auth_class = OAuth2Auth(
        token_url="https://login.bisnode.com/sandbox/v1/token.oauth2"
    )
    client = APIClient(
        base_url=URL("https://sandbox-api.bisnode.com/decision/v3/"),
        auth=auth_class,
        timeout=10.0,
        headers={"Content-Type": "application/json"},
        flags=(ALLOW_UNSECURE,),
    )

    decisioning_api = RGSDecisioning(client)
    response = await decisioning_api.request(
        auth_info=credentials,
        endpoint=decisioning_api.endpoints()[0],
        **{
            "registrationNumber": "9164103864",
            "rulesetKey": "1-1235-4566-7891",
            "reference": "1234567890",
            "duns": "1234567890",
            "endUser": "<EMAIL>",
            "onBehalfOf": "<EMAIL>",
        }
    )
    # Print the HTTP Request in standard HTTP format
    sleep(1)
    response.print_http()

if __name__ == "__main__":
    asyncio.run(main())
