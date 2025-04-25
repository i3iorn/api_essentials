import unittest

from api_essentials.auth.info import UserCredentials, ClientCredentials, TokenCredentials, ApiCredentials


class TestCredentials(unittest.TestCase):

    # Positive tests
    def test_client_credentials_get_credentials(self):
        # Positive test for ClientCredentials
        client_creds = ClientCredentials(client_id="client123", client_secret="secret123", scope="read")
        result = client_creds.get_credentials()
        self.assertEqual(result, {
            "client_id": "client123",
            "client_secret": "secret123",
            "scope": "read"
        })

    def test_user_credentials_get_credentials(self):
        # Positive test for UserCredentials
        user_creds = UserCredentials(username="user123", password="password123")
        result = user_creds.get_credentials()
        self.assertEqual(result, {
            "username": "user123",
            "password": "password123"
        })

    def test_token_credentials_get_credentials(self):
        # Positive test for TokenCredentials
        token_creds = TokenCredentials(access_token="token123", refresh_token="refresh123")
        result = token_creds.get_credentials()
        self.assertEqual(result, {
            "access_token": "token123",
            "refresh_token": "refresh123"
        })

    def test_api_credentials_get_credentials(self):
        # Positive test for ApiCredentials
        api_creds = ApiCredentials(api_key="api_key_123", api_secret="api_secret_123")
        result = api_creds.get_credentials()
        self.assertEqual(result, {
            "api_key": "api_key_123",
            "api_secret": "api_secret_123"
        })

    # Negative tests
    def test_client_credentials_missing_fields(self):
        # Test if missing fields in ClientCredentials raises an error
        with self.assertRaises(TypeError):
            ClientCredentials(client_id="client123", client_secret="secret123")

    def test_user_credentials_missing_fields(self):
        # Test if missing fields in UserCredentials raises an error
        with self.assertRaises(TypeError):
            UserCredentials(username="user123")

    def test_token_credentials_missing_fields(self):
        # Test if missing fields in TokenCredentials raises an error
        with self.assertRaises(TypeError):
            TokenCredentials(access_token="token123")

    def test_api_credentials_missing_fields(self):
        # Test if missing fields in ApiCredentials raises an error
        with self.assertRaises(TypeError):
            ApiCredentials(api_key="api_key_123")

    # Test if invalid types are handled correctly (this would depend on the typing validation)
    def test_invalid_client_credentials(self):
        # Test with invalid types for ClientCredentials
        with self.assertRaises(TypeError):
            ClientCredentials(client_id=123, client_secret=456, scope="read")

    def test_invalid_user_credentials(self):
        # Test with invalid types for UserCredentials
        with self.assertRaises(TypeError):
            UserCredentials(username=123, password=456)

    def test_invalid_token_credentials(self):
        # Test with invalid types for TokenCredentials
        with self.assertRaises(TypeError):
            TokenCredentials(access_token=123, refresh_token=456)

    def test_invalid_api_credentials(self):
        # Test with invalid types for ApiCredentials
        with self.assertRaises(TypeError):
            ApiCredentials(api_key=123, api_secret=456)


if __name__ == "__main__":
    unittest.main()
