import os

AUTH_REDIRECTS = os.getenv("AUTH_REDIRECTS", 10)
AUTH_TIMEOUT = os.getenv("AUTH_TIMEOUT", 6)
SSL_VERIFICATION = os.getenv("AUTH_SSL_VERIFICATION", True)
TOKEN_GRACE_PERIOD = os.getenv("AUTH_TOKEN_GRACE_PERIOD", 60)
