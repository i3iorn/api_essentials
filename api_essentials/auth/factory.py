from api_essentials.auth.client_credentials import ClientCredentialsOAuth2Flow
from api_essentials.auth.authorization_code import AuthorizationCodeOAuth2Flow
from api_essentials.auth.password import PasswordOAuth2Flow

def get_oauth2_auth(grant_type: str, token_url: str, **kwargs):
    if grant_type == "client_credentials":
        return ClientCredentialsOAuth2Flow(token_url, **kwargs)
    elif grant_type == "authorization_code":
        return AuthorizationCodeOAuth2Flow(token_url, **kwargs)
    elif grant_type == "password":
        return PasswordOAuth2Flow(token_url, **kwargs)
    else:
        raise ValueError(f"Unsupported grant_type: {grant_type}")
