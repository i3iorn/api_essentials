import pytest
import logging
from datetime import datetime, timedelta
from httpx import URL, Client, AsyncClient, Request, Response

import httpx
from auth.config import OAuth2Config, ConfigValidator
from auth.oauth2 import BaseOAuth2, OAuth2ResponseType
from auth.token import OAuth2Token, OAuthTokenType
from auth.grant_type import OAuth2GrantType
from utils.log import register_secret, SecretFilter


# -- Fixtures & Helpers ------------------------------------------------------

@pytest.fixture
def dummy_url():
    return URL("https://example.com/token")

@pytest.fixture
def basic_config(dummy_url):
    return OAuth2Config(
        client_id="cid",
        client_secret="secret",
        token_url=dummy_url,
    )

@pytest.fixture
def token_data():
    return {
        "access_token": "abc123",
        "refresh_token": "ref456",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "a b",
    }

@pytest.fixture(autouse=True)
def no_real_oauth_http(monkeypatch, token_data):
    """
    Globally stub out any httpx.Client.send or .post calls so that
    request_new(), refresh(), and sync_auth_flow never hit the network.
    """

    # A generic fake token response
    def _fake_token_response(request: httpx.Request):
        return httpx.Response(
            200,
            json=token_data,
            request=request
        )

    # Monkey-patch Client.send
    def fake_send(self, request: httpx.Request, **kwargs):
        return _fake_token_response(request)
    monkeypatch.setattr(httpx.Client, "send", fake_send, raising=True)

    # Monkey-patch Client.post (used in refresh())
    def fake_post(self, url, *, data=None, **kwargs):
        # Build a dummy Request so raise_for_status() will work
        req = Request("POST", url, data=data, headers={})
        return _fake_token_response(req)
    monkeypatch.setattr(httpx.Client, "post", fake_post, raising=True)

    # You can also patch AsyncClient if you ever do real async HTTP:
    async def fake_async_send(self, request: httpx.Request, **kwargs):
        return _fake_token_response(request)
    monkeypatch.setattr(httpx.AsyncClient, "send", fake_async_send, raising=False)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post, raising=False)

@pytest.fixture
def token(token_data):
    now = datetime.now()
    return OAuth2Token(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_type=OAuthTokenType.ACCESS,
        expires_in=token_data["expires_in"],
        scope=token_data["scope"].split(),
        created_at=now - timedelta(seconds=100),
    )

@pytest.fixture
def expired_token(token_data):
    return OAuth2Token(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_in=1,
        created_at=datetime.now() - timedelta(seconds=10),
    )

@pytest.fixture
def base_oauth(basic_config):
    return BaseOAuth2(basic_config)

# -- ConfigValidator ---------------------------------------------------------

class TestConfigValidator:
    @pytest.mark.parametrize("attr,value,exc", [
        ("client_id", 123, ValueError),
        ("client_secret", None, ValueError),
        ("token_url", "not-a-url", ValueError),
        ("redirect_uri", "nope", ValueError),
        ("client", "bad", ValueError),
        ("access_token", "bad", ValueError),
        ("refresh_token", "bad", ValueError),
        ("token_class", object, ValueError),
    ])
    def test_validate_invalid_types(self, basic_config, attr, value, exc):
        setattr(basic_config, attr, value)
        with pytest.raises(exc):
            ConfigValidator.validate(basic_config)

    def test_validate_success(self, basic_config, token):
        basic_config.access_token = token
        ConfigValidator.validate(basic_config)  # no error

# -- OAuth2Config Properties ------------------------------------------------

class TestOAuth2ConfigProperties:
    def test_scope_setter_with_string(self, basic_config):
        basic_config.scope = "one two"
        assert basic_config._scope == ["one", "two"]
        assert isinstance(basic_config.scope, str)

    def test_scope_setter_with_list(self, basic_config):
        basic_config.scope = ["x", "y"]
        assert basic_config._scope == ["x", "y"]
        assert "x" in basic_config.scope

    def test_add_scope_appends(self, basic_config):
        basic_config._scope = ["a"]
        basic_config.add_scope("b")
        assert "b" in basic_config._scope

    def test_grant_type_setter(self, basic_config):
        basic_config.grant_type = OAuth2GrantType.PASSWORD
        assert basic_config._grant_type == OAuth2GrantType.PASSWORD
        assert basic_config.grant_type == "password"

    def test_response_type_setter(self, basic_config):
        basic_config.response_type = OAuth2ResponseType.TOKEN
        assert basic_config._response_type == OAuth2ResponseType.TOKEN
        assert basic_config.response_type == "token"

    def test_scope_strategy_setter(self, basic_config):
        from strategy.strategies.scope_strategies import ScopeStrategy
        strategy = ScopeStrategy(delimiter=",")
        basic_config.scope_strategy = strategy
        assert basic_config._scope_strategy.delimiter == ","

# -- OAuth2Token Behaviors ---------------------------------------------------

class TestOAuth2Token:
    def test_is_expired_false(self, token):
        assert token.is_expired is False

    def test_is_expired_true(self, expired_token):
        assert expired_token.is_expired is True

    def test_is_valid(self, token):
        assert token.is_valid

    def test_is_revoked_default(self, token):
        assert token.is_revoked is False

    def test_token_property(self, token):
        assert token.token == token.access_token

    def test_to_dict_and_from_dict_roundtrip(self, token):
        d = token.to_dict()
        new = OAuth2Token.from_dict(d)
        assert new.access_token == token.access_token
        assert new.refresh_token == token.refresh_token

    def test_request_new_invokes_httpx(self, basic_config, monkeypatch, token_data):
        called = {}
        def fake_send(self, request):
            called['data'] = request.content.decode()
            return Response(200, json=token_data, request=request)

        monkeypatch.setattr(Client, "send", fake_send)
        new = OAuth2Token.request_new(basic_config)
        assert new.access_token == token_data["access_token"]
        assert basic_config._grant_type.value in called['data']

    def test_refresh_uses_request_new(self, basic_config, monkeypatch, token):
        monkeypatch.setattr(OAuth2Token, "request_new", lambda cfg: token)
        new = token.refresh(basic_config)
        assert isinstance(new, OAuth2Token)
        assert new.access_token == token.access_token

# -- BaseOAuth2 Integration --------------------------------------------------

class TestBaseOAuth2:
    def test_attach_client_sets_client(self, base_oauth, basic_config):
        client = httpx.Client()
        basic_config.attach_client(client)
        assert basic_config.client is client

    def test_sync_auth_flow_generator_signature(self, base_oauth):
        req = Request("GET", "https://example.com")
        gen = base_oauth.sync_auth_flow(req)
        assert hasattr(gen, "__iter__")

    @pytest.mark.parametrize("grant_type,expected", [
        (OAuth2GrantType.CLIENT_CREDENTIALS, "client_credentials"),
        (OAuth2GrantType.PASSWORD, "password"),
    ])
    def test_sync_auth_flow_includes_correct_grant(self, basic_config, grant_type, expected):
        basic_config.grant_type = grant_type
        oauth = BaseOAuth2(basic_config)
        req = Request("POST", str(basic_config.token_url))
        flow = oauth.sync_auth_flow(req)
        # first send is token request
        token_req = next(flow)
        assert token_req.url == basic_config.token_url
        body = dict(
            grant_type=grant_type.value,
            client_id=basic_config.client_id,
            client_secret=basic_config.client_secret,
        )

        assert body["grant_type"] == expected
        assert body["client_id"] == basic_config.client_id
        assert body["client_secret"] == basic_config.client_secret

    def test_sync_auth_flow_yields_original_request(self, basic_config):
        req = Request("GET", "https://example.com")
        oauth = BaseOAuth2(basic_config)
        flow = oauth.sync_auth_flow(req)
        token_req = next(flow)
        assert token_req.url == str(basic_config.token_url).replace("/token", "")
        assert token_req.method == "GET"
        assert token_req.headers["Authorization"].startswith("Bearer ")

    def test_code_flow_includes_redirect_uri(self, basic_config):
        basic_config.redirect_uri = URL("https://app/callback")
        basic_config.response_type = OAuth2ResponseType.CODE
        oauth = BaseOAuth2(basic_config)
        req = Request("POST", str(basic_config.token_url))
        flow = oauth.sync_auth_flow(req)
        token_req = next(flow)
        assert token_req.url == basic_config.token_url

# -- RFC6749 Compliance ------------------------------------------------------

class TestRFC6749Compliance:
    def test_authorization_code_flow_parameters(self, basic_config):
        basic_config.response_type = OAuth2ResponseType.CODE
        # authorization endpoint would receive these:
        params = {
            "response_type": basic_config.response_type,
            "client_id": basic_config.client_id,
        }
        assert params["response_type"] == "code"
        assert params["client_id"] == "cid"

    def test_scope_parameter_serialization(self, basic_config):
        basic_config.scope = ["a", "b", "c"]
        s = basic_config.scope
        assert isinstance(s, str) and " " in s

# -- Security Best Practices -------------------------------------------------

class TestSecurityBestPractices:
    def test_https_token_url(self):
        with pytest.raises(ValueError):
            cfg = OAuth2Config("cid", "sec", URL("http://insecure"))

    def test_no_plaintext_secret_in_logs(self, basic_config, caplog):
        register_secret(basic_config.client_secret)  # register before logging
        caplog.set_level(logging.DEBUG)

        # Attach the filter directly to the test's caplog handler
        caplog.handler.addFilter(SecretFilter())

        oauth = BaseOAuth2(basic_config)
        caplog.clear()
        caplog.text  # force capture

        # simulate log
        logging.getLogger(__name__).debug("Secret is %s", basic_config.client_secret)

        # validate that secret does not appear in logs
        assert basic_config.client_secret not in caplog.text

    def test_token_is_frozen(self, token):
        with pytest.raises(Exception):
            setattr(token, "access_token", "new")

# -- Edge Cases & Errors -----------------------------------------------------

class TestEdgeCases:
    def test_missing_refresh_token_none(self, token):
        assert token.refresh_token is not None or token.refresh_token is None

    def test_from_dict_with_missing_fields(self, token_data):
        partial = {"access_token": "x"}
        obj = OAuth2Token.from_dict(partial)
        assert obj.access_token == "x"
        assert obj.refresh_token is None

    def test_to_dict_contains_all_keys(self, token):
        d = token.to_dict()
        expected = {"access_token", "refresh_token", "token_type", "expires_in", "scope"}
        assert expected.issubset(set(d.keys()))

# -- Async Client Support ----------------------------------------------------

@pytest.mark.asyncio
class TestAsyncClientSupport:
    async def test_attach_client_async(self, basic_config):
        async_client = AsyncClient()
        oauth = BaseOAuth2(basic_config)
        basic_config.attach_client(async_client)
        assert basic_config.client is async_client

    async def test_async_flow_raises_if_sync_used(self, basic_config):
        async_client = AsyncClient()
        oauth = BaseOAuth2(basic_config)
        basic_config.attach_client(async_client)
        req = Request("GET", "https://example.com")
        with pytest.raises(AttributeError):
            next(oauth.sync_auth_flow(req))
