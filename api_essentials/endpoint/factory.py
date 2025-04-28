from typing import Dict, Any, List

from api_essentials.api import AbstractAPI
from api_essentials.endpoint import Endpoint, EndpointDefinition
from api_essentials.parameter import ParameterValueType, ParameterConstraint, ParameterDefinition, ParameterLocation


class EndpointFactory:
    @staticmethod
    def from_openapi(api: AbstractAPI, api_spec: Dict[str, Any]) -> List[Endpoint]:
        endpoints = []

        paths = api_spec.get("paths", {})
        if not isinstance(paths, dict):
            raise ValueError("Invalid OpenAPI spec: 'paths' must be a dictionary")

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue  # skip malformed entries

            for method, spec in methods.items():
                if not isinstance(spec, dict):
                    continue  # skip unexpected structures

                parameters = []

                for param in spec.get("parameters", []):
                    if not isinstance(param, dict):
                        continue  # skip invalid parameter definitions

                    param_name = param.get("name")
                    param_location = param.get("in")
                    param_required = param.get("required", False)
                    param_description = param.get("description")
                    param_schema = param.get("schema", {})

                    if not param_name or not param_location:
                        continue  # skip incomplete definitions

                    try:
                        value_type = ParameterValueType.from_name(param_schema.get("type", "string"))
                    except ValueError:
                        value_type = ParameterValueType.STRING  # fallback default

                    constraint = ParameterConstraint(
                        value_type=value_type,
                        default=param_schema.get("default"),
                        enum=param_schema.get("enum", []),
                        example=param_schema.get("example")
                    )

                    try:
                        parameter = ParameterDefinition(
                            name=param_name,
                            location=ParameterLocation(param_location),
                            required=param_required,
                            description=param_description,
                            constraint=constraint,
                            deprecated=param.get("deprecated", False),
                            deprecated_description=param.get("x-deprecatedDescription")
                        )
                        parameters.append(parameter)
                    except ValueError as e:
                        # Skip invalid parameter definition (e.g., non-required path param)
                        continue

                definition = EndpointDefinition(
                    path=path,
                    method=method,
                    description=spec.get("description"),
                    parameters=parameters
                )

                endpoint = Endpoint(api=api, definition=definition)
                endpoints.append(endpoint)

        return endpoints
