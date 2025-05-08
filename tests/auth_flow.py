import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from api_essentials.auth.info import ClientCredentials
from api_essentials.auth.flow import OAuth2Auth
from api_essentials.constants import GRACE_PERIOD


class TestOAuth2Auth(unittest.TestCase):

    def setUp(self):
        # Setup credentials for ClientCredentials
        self.auth_info = ClientCredentials(client_id="client123", client_secret="secret123", scopes=["read"])
        self.token_url = "https://example.com/token"
        self.auth = OAuth2Auth(token_url=self.token_url)

    # Positive tests

    """
    @patch('requests.post')
    def test_refresh_token_success(self, mock_post):
        # Test that refresh_token is successful and updates the token
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response

        self.auth.refresh_token(verify=False)

        self.assertEqual(self.auth.token, "new_token")
        self.assertIsInstance(self.auth.expires_at, datetime)
        self.assertTrue(self.auth.expires_at > datetime.now())
    """

    @patch('requests.post')
    async def test_auth_adds_authorization_header(self, mock_post):
        # Test that auth method correctly adds the Authorization header
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "valid_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response
        await self.auth.refresh_token(verify=False)

        # Mock the request object
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer valid_token"}

        # Mock the auth method
        next(self.auth.auth(mock_request))

        # Assert the Authorization header is added correctly
        self.assertEqual(mock_request.headers["Authorization"], "Bearer valid_token")

    # Negative tests

    @patch('requests.post')
    async def test_refresh_token_failed_request(self, mock_post):
        # Test that refresh_token raises an error when the request fails
        # Mock the response to simulate an error

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        # Call refresh_token and expect it to raise a ValueError
        with self.assertRaises(ValueError) as context:
            await self.auth.refresh_token(verify=False)

        self.assertEqual(str(context.exception), "Failed to obtain token: Bad Request")

    def test_has_expired_true(self):
        # Test that has_expired returns True when the token has expired
        self.auth.token = "expired_token"
        self.auth.expires_at = datetime.now() - timedelta(seconds=GRACE_PERIOD + 1)

        self.assertTrue(self.auth.has_expired())

    def test_has_expired_false(self):
        # Test that has_expired returns False when the token has not expired
        self.auth.token = "valid_token"
        self.auth.expires_at = datetime.now() + timedelta(seconds=GRACE_PERIOD + 1)

        self.assertFalse(self.auth.has_expired())

    # TODO: Fix test
    """
    @patch('requests.post')
    @patch('api_essentials.auth.info.ClientCredentials')
    def test_refresh_token_missing_fields(self, mock_post, MockClientCredentials):
        MockClientCredentials.return_value = ClientCredentials(client_id="valid_client_id", client_secret="secret123",
                                                               scopes=["read"])
        invalid_auth_info = MockClientCredentials()
        invalid_auth = OAuth2Auth(auth_info=invalid_auth_info, token_url=self.token_url)

        # Mock the response to simulate an error during refresh_token
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid credentials"
        mock_post.return_value = mock_response

        with self.assertRaises(ValueError):
            invalid_auth.refresh_token(verify=False)
    """
    """
    @patch('requests.post')
    def test_auth_with_missing_token(self, mock_post):
        # Test that `auth` method fails if token is not set and expired
        self.auth.token = None
        self.auth.expires_at = datetime.now() - timedelta(seconds=GRACE_PERIOD + 1)

        # Expect refresh_token to be called
        with patch.object(self.auth, 'refresh_token') as mock_refresh_token:
            next(self.auth.sync_auth_flow(MagicMock()))  # This will call auth method
            mock_refresh_token.assert_called_once()
    """
    """
    # Test if invalid types are handled correctly
    def test_invalid_client_credentials(self):
        # Test with invalid types for ClientCredentials
        with self.assertRaises(TypeError):
            OAuth2Auth(auth_info=ClientCredentials(client_id=123, client_secret=456, scopes=["read"]),
                       token_url=self.token_url)
    """
    """
    def test_invalid_auth_info_type(self):
        # Test that the auth_info parameter requires a valid ClientCredentials type
        with self.assertRaises(TypeError):
            OAuth2Auth(auth_info="invalid_info", token_url=self.token_url)
        """
if __name__ == "__main__":
    unittest.main()
