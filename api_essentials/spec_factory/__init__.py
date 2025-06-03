import json
import logging
from typing import Union, Dict, Any, Optional
from pathlib import Path

from api_essentials.client import APIClient
from api_essentials.auth.config import OAuth2Config

logger = logging.getLogger(__name__)

def create_client_from_spec(
        spec: Union[str, Path, dict],
        oauth_kwargs: Dict[str, Any],
        client_kwargs: Optional[Dict[str, Any]] = None
) -> APIClient:
    """
    Create an APIClient object from an OpenAPI or Swagger specification.

    Args:
        spec (Union[str, Path, dict]): The OpenAPI or Swagger specification. Can be a file path, URL, or dictionary.
        client_kwargs: Additional keyword arguments for the APIClient.
        oauth_kwargs: OAuth2 configuration parameters, such as client_id and client_secret.

    Returns:
        APIClient: Configured API client.

    Raises:
        ValueError: If the specification is invalid or unsupported.
    """
    if client_kwargs is None:
        client_kwargs = {}

    if isinstance(spec, (str, Path)):
        logger.debug("Loading specification from file or URL: %s", spec)
        with open(spec, 'r') as f:
            spec = json.load(f)
    elif not isinstance(spec, dict):
        raise ValueError("Specification must be a file path, URL, or dictionary.")

    version = spec.get("openapi") or spec.get("swagger")
    if not version:
        raise ValueError("Invalid specification: missing 'openapi' or 'swagger' version.")

    logger.info("Detected specification version: %s", version)
    if version.startswith("3."):
        return _create_client_from_openapi_v3(spec, client_kwargs, oauth_kwargs)
    elif version.startswith("2."):
        return _create_client_from_swagger_v2(spec, client_kwargs, oauth_kwargs)
    else:
        raise ValueError(f"Unsupported specification version: {version}")

def _create_client_from_openapi_v3(spec: dict, client_kwargs: Dict[str, Any], oauth_kwargs: Dict[str, Any]) -> APIClient:
    """
    Create an APIClient from an OpenAPI 3.x specification.

    Args:
        spec (dict): The OpenAPI 3.x specification.
        **client_kwargs: Additional keyword arguments for the APIClient.

    Returns:
        APIClient: Configured API client.
    """
    logger.debug("Creating client from OpenAPI 3.x specification.")
    base_url = spec.get("servers", [{}])[0].get("url", "")
    oauth_config = _extract_oauth_config(spec.get("components", {}).get("securitySchemes", {}), oauth_kwargs)
    return APIClient(config=oauth_config, base_url=base_url, **client_kwargs)

def _create_client_from_swagger_v2(spec: dict, client_kwargs: Dict[str, Any], oauth_kwargs: Dict[str, Any]) -> APIClient:
    """
    Create an APIClient from a Swagger 2.0 specification.

    Args:
        spec (dict): The Swagger 2.0 specification.
        **client_kwargs: Additional keyword arguments for the APIClient.

    Returns:
        APIClient: Configured API client.
    """
    logger.debug("Creating client from Swagger 2.0 specification.")
    base_url = spec.get("host", "") + spec.get("basePath", "")
    oauth_config = _extract_oauth_config(spec.get("securityDefinitions", {}), **oauth_kwargs)
    return APIClient(config=oauth_config, base_url=base_url, **client_kwargs)

def _extract_oauth_config(security_schemes: dict, client_id: str, client_secret: str) -> OAuth2Config:
    """
    Extract OAuth2 configuration from security schemes.

    Args:
        security_schemes (dict): Security schemes from the specification.

    Returns:
        OAuth2Config: Configured OAuth2 settings.

    Raises:
        ValueError: If no OAuth2 configuration is found.
    """
    for scheme_name, scheme in security_schemes.items():
        if scheme.get("type") == "oauth2":
            logger.debug("Found OAuth2 security scheme: %s", scheme_name)
            token_url = scheme.get("tokenUrl", "")
            scopes = list(scheme.get("flows", {}).get("clientCredentials", {}).get("scopes", {}).keys())
            return OAuth2Config(
                client_id=client_id,
                client_secret=client_secret,
                token_url=token_url,
                scope=scopes
            )
    raise ValueError("No OAuth2 configuration found in security schemes.")
