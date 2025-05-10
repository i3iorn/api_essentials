from typing import Dict, Any

from api_essentials.api import BaseAPI
from api_essentials.endpoint import EndpointDefinition, Endpoint
from api_essentials.logging_decorator import log_method_calls
from api_essentials.parameter import ParameterFactoryService, ParameterLocation, ParameterValueType


@log_method_calls()
class EndpointFactory:
    @staticmethod
    def from_openapi(api: BaseAPI, api_spec: Dict[str, Any]) -> Dict[str, Endpoint]:
        endpoints = {}
        factory = ParameterFactoryService()

        paths = api_spec.get("paths", {})
        if not isinstance(paths, dict):
            raise ValueError("Invalid OpenAPI spec: 'paths' must be a dictionary")

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue

            for method, spec in methods.items():
                if not isinstance(spec, dict):
                    continue

                parameters = []

                # Handle standard parameters
                for param in spec.get("parameters", []):
                    if not isinstance(param, dict):
                        continue

                    name = param.get("name")
                    location = param.get("in")
                    required = param.get("required", False)
                    description = param.get("description")
                    schema = param.get("schema", {})

                    if not name or not location:
                        continue

                    try:
                        value_type = ParameterValueType.from_name(schema.get("type", "string"))
                    except ValueError:
                        value_type = ParameterValueType.STRING

                    definition = factory._make(
                        name=name,
                        location=ParameterLocation(location),
                        required=required,
                        description=description,
                        value_type=value_type,
                        default=schema.get("default"),
                        enum=schema.get("enum"),
                        example=schema.get("example"),
                        minimum=schema.get("minimum"),
                        maximum=schema.get("maximum"),
                        min_length=schema.get("minLength"),
                        max_length=schema.get("maxLength"),
                        pattern=schema.get("pattern"),
                        deprecated=param.get("deprecated", False),
                        deprecated_description=param.get("x-deprecatedDescription")
                    )
                    parameters.append(definition)

                # Handle requestBody as a JSON parameter
                request_body = spec.get("requestBody")
                if isinstance(request_body, dict):
                    content = request_body.get("content", {})
                    json_content = content.get("application/json")
                    if json_content:
                        schema = json_content.get("schema", {})
                        param_name = schema.get("title", "body")  # default to 'body' if no title

                        value_type = ParameterValueType.OBJECT
                        if "type" in schema:
                            try:
                                value_type = ParameterValueType.from_name(schema["type"])
                            except ValueError:
                                pass

                        definition = factory._make(
                            name=param_name,
                            location=ParameterLocation.JSON,
                            required=request_body.get("required", False),
                            description=request_body.get("description", "Request body"),
                            value_type=value_type,
                            default=schema.get("default"),
                            enum=schema.get("enum"),
                            example=schema.get("example"),
                            minimum=schema.get("minimum"),
                            maximum=schema.get("maximum"),
                            min_length=schema.get("minLength"),
                            max_length=schema.get("maxLength"),
                            pattern=schema.get("pattern"),
                            deprecated=False
                        )
                        parameters.append(definition)

                definition = EndpointDefinition(
                    path=path,
                    method=method,
                    description=spec.get("description"),
                    parameters=parameters
                )

                endpoint = Endpoint(api=api, definition=definition)
                endpoints[path] = endpoint

        return endpoints
