"""HTTP connections with various methods."""

from typing import Dict, Any
from ast import literal_eval
from pydantic import BaseModel, ConfigDict
from .logger import get_logger_for
from .utils import create_session
from .oauth2 import OAuth2Session, retrieve_token_endpoint
from .model import ApiKey
from .settings import ENV


log = get_logger_for(__name__)


class BareConnectionMethod(BaseModel):
    """Bare connection method, no extra headers."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    endpoint: str = ENV.tld_signing_endpoint

    def get_headers(self) -> Dict[str, str]:
        """Get the headers."""
        return {}


class OAuth2ConnectionMethod(BareConnectionMethod):
    """OAuth2 connection method."""

    oauth2_session: OAuth2Session = OAuth2Session()

    def get_headers(self):
        """Return the headers."""
        return {"authorization": f"bearer {self.oauth2_session.get_access_token()}"}

    def get_userinfo(self):
        """Override parent method from BareConnectionMethod."""
        openapi_url = retrieve_token_endpoint().replace("/token", "/userinfo")
        return (
            create_session()
            .get(openapi_url, timeout=10, headers=self.get_headers())
            .json()
        )


class ApiKeyConnectionMethod(BareConnectionMethod):
    """API key connection method."""

    api_key: ApiKey

    def get_headers(self):
        """Return the headers."""
        return self.api_key.to_dict()


class HTTPSession:
    """HTTP session class."""

    def __init__(self, timeout=10):
        """Initialize the HTTP session."""
        self.session = create_session()
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._method = None

    def get_method(self):
        """Get method."""
        log.debug("Get method")
        if not self._method:
            # Lazy instantiation
            self.prepare_connection_method()
        return self._method

    def prepare_connection_method(self):
        """Set the connection method."""
        # Custom server without authentication method
        if ENV.tld_disable_auth:
            self._method = BareConnectionMethod(endpoint=ENV.tld_signing_endpoint)

        # API key method
        elif api_key := ApiKey.grab():
            self._method = ApiKeyConnectionMethod(api_key=api_key)

        # OAuth2 method
        else:
            self._method = OAuth2ConnectionMethod()

    def post(self, route: str, params: Dict):
        """Perform a POST request."""
        method = self.get_method()
        url = f"{method.endpoint}{route}"
        headers = {**self.headers, **method.get_headers()}
        log.debug("POST to %s", url)
        response = self.session.post(url, json=params, headers=headers, timeout=10)
        try:
            response.raise_for_status()
        except Exception as e:
            log.error(literal_eval(response.text))
            raise e

        return response


session = HTTPSession()


def get_headers() -> dict[str, Any]:
    """Return the headers needed to authenticate on the system."""
    return session.get_method().get_headers()


def get_userinfo() -> dict[str, str]:
    """Return userinfo."""
    return OAuth2ConnectionMethod().get_userinfo()


def get_username() -> str:
    """Return username."""
    user_info = get_userinfo()
    assert user_info, "Could not fetch user info"
    return user_info["preferred_username"]
