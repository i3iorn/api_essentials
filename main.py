import asyncio
import logging
from typing import List

from src.api import AbstractAPI
from src.auth import OAuth2Auth, ClientCredentials
from src.endpoint import EndpointDefinition, Endpoint
from src.parameter import ParameterFactoryService, applier_registry


class RGSDecisioning(AbstractAPI):
    def __init__(self):
        base_url="https://sandbox-api.bisnode.com/decision/v3/"
        credentials = ClientCredentials(
            client_id="71a7c376-0f79-4fc5-9db9-6447d2097e21",
            client_secret="Ut0dzd8PWzZpxorrFJ8l0d8D4ZcbLNHsJVncvjc26v9V7A4LlLkCAgF11jsJdOxM",
            scopes=["rgs-decision"]
        )
        auth_class=OAuth2Auth(
            auth_info=credentials,
            token_url="https://login.bisnode.com/sandbox/v1/token.oauth2"
        )
        super().__init__(
            base_url=base_url,
            auth_class=auth_class
        )

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
                    value_type="string",
                ),
                param_factory.query(
                    name="registrationNumber",
                    description="Registration number of the company",
                    required=True,
                    value_type="string",
                    min_length=6,
                    max_length=13,
                ),
                param_factory.query(
                    name="reference",
                    description="Request reference, returned in the response.",
                    required=True,
                    value_type="string",
                    min_length=1,
                )
            ]
        )
        b2b_se_decision = Endpoint(
            api=self,
            definition=b2b_se_decision_definition,
            appliers=applier_registry
        )


        return [
            b2b_se_decision
        ]


async def main():
    decisioning_api = RGSDecisioning()
    await decisioning_api.initialize_client(verify=False)
    response = await decisioning_api.send_request(
        decisioning_api.endpoints()[0], json={
            "registrationNumber": "9164103864",
            "rulesetKey": "1-1235-4566-7891",
            "reference": "1234567890",
        }
    )
    # Print the HTTP Request in standard HTTP format
    response.print_http_formatted_string()

if __name__ == "__main__":
    asyncio.run(main())
