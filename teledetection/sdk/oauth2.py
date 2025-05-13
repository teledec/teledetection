"""Module dedicated to OAuth2 device flow."""

import datetime
import io
import time
from abc import abstractmethod
from typing import Dict
import qrcode

from .logger import get_logger_for  # type: ignore
from .utils import create_session
from .model import JWT, DeviceGrantResponse
from .settings import ENV

log = get_logger_for(__name__)


def retrieve_token_endpoint():
    """Retrieve the token endpoint from the s3 signing endpoint."""
    openapi_url = ENV.tld_signing_endpoint + "openapi.json"
    log.debug("Fetching OAuth2 endpoint from openapi url %s", openapi_url)
    _session = create_session()
    res = _session.get(
        openapi_url,
        timeout=10,
    )
    res.raise_for_status()
    data = res.json()
    return data["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"][
        "password"
    ]["tokenUrl"]


class RefreshTokenError(Exception):
    """Unable to refresh token."""


class ExpiredAuthLinkError(Exception):
    """Authentication link has expired."""


class GrantMethodBase:
    """Base class for grant methods."""

    client_id: str
    headers: Dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"}
    _token_endpoint: str | None = None

    def get_token_endpoint(self):
        """Get the token endpoint."""
        if not self._token_endpoint:
            self._token_endpoint = retrieve_token_endpoint()
        return retrieve_token_endpoint()

    @abstractmethod
    def get_first_token(self) -> JWT:
        """Provide the first used token."""
        raise NotImplementedError

    @property
    def data_base(self) -> Dict[str, str]:
        """Base payload."""
        return {
            "client_id": self.client_id,
            "scope": "openid offline_access",
        }

    def refresh_token(self, old_jwt: JWT) -> JWT:
        """Refresh the token."""
        log.debug("Refreshing token")
        assert old_jwt, "JWT is empty"
        data = self.data_base.copy()
        data.update(
            {
                "refresh_token": old_jwt.refresh_token,
                "grant_type": "refresh_token",
            }
        )
        ret = create_session().post(
            self.get_token_endpoint(),
            headers=self.headers,
            data=data,
            timeout=10,
        )
        if ret.status_code == 200:
            log.debug(ret.text)
            return JWT.from_dict(ret.json())
        raise RefreshTokenError


class DeviceGrant(GrantMethodBase):
    """Device grant method."""

    client_id = "gdal"

    def get_first_token(self) -> JWT:
        """Get the first JWT token."""
        device_endpoint = f"{self.get_token_endpoint().rsplit('/', 1)[0]}/auth/device"

        req = create_session()
        log.debug("Getting token using device authorization grant")
        ret = req.post(
            device_endpoint,
            headers=self.headers,
            data=self.data_base,
            timeout=10,
        )
        if ret.status_code == 200:
            response = DeviceGrantResponse(**ret.json())
            verif_url_comp = response.verification_uri_complete
            log.info("Open the following URL in your browser to grant access:")
            log.info("\033[92m %s \033[0m", verif_url_comp)

            # QR code
            qr_code = qrcode.QRCode()
            qr_code.add_data(verif_url_comp)
            buffer = io.StringIO()
            qr_code.print_ascii(out=buffer)
            buffer.seek(0)
            log.info(buffer.read())

            log.info("Waiting for authentication...")
            start = time.time()
            data = self.data_base.copy()
            grant_type = "urn:ietf:params:oauth:grant-type:device_code"
            data.update(
                {
                    "device_code": response.device_code,
                    "grant_type": grant_type,
                }
            )
            while True:
                ret = req.post(
                    self.get_token_endpoint(),
                    headers=self.headers,
                    data=data,
                    timeout=10,
                )
                elapsed = time.time() - start
                log.debug(
                    "Elapsed: %.0f, status: %s (%.0f seconds left)",
                    elapsed,
                    ret.status_code,
                    response.expires_in - elapsed,
                )
                if elapsed > response.expires_in:
                    raise ExpiredAuthLinkError
                if ret.status_code != 200:
                    time.sleep(response.interval)
                else:
                    return JWT.from_dict(ret.json())
        raise ConnectionError("Unable to authenticate with the SSO")


class OAuth2Session:
    """Class to start an OAuth2 session."""

    def __init__(self, grant_type: type[GrantMethodBase] = DeviceGrant):
        """Initialize."""
        self.grant = grant_type()
        self.jwt_ttl_margin_seconds = 60
        self.jwt_issuance = datetime.datetime(year=1, month=1, day=1)
        self.jwt: JWT | None = None

    def save_token(self, now: datetime.datetime):
        """Save the JWT to disk."""
        if self.jwt:
            self.jwt_issuance = now
            self.jwt.to_config_dir()
        else:
            log.warning("No OAuth2 credentials to save")

    def _init_jwt(self):
        """Initialize the JWT."""
        if not self.jwt:
            # First JWT initialisation
            self.jwt = JWT.from_config_dir()
        if not self.jwt:
            # When JWT is still `None`, we use the grant method
            self.jwt = self.grant.get_first_token()
            self.save_token(datetime.datetime.now())

    def _refresh_if_needed(self):
        """Refresh the token if ttl is too short."""
        self._init_jwt()
        ttl_margin_seconds = 30
        now = datetime.datetime.now()
        jwt_expires_in = datetime.timedelta(seconds=self.jwt.expires_in)
        access_token_ttl = self.jwt_issuance + jwt_expires_in - now
        access_token_ttl_seconds = access_token_ttl.total_seconds()
        log.debug("access_token_ttl is %s", access_token_ttl_seconds)
        if access_token_ttl_seconds < ttl_margin_seconds:
            # Access token in not valid, but refresh might be
            try:
                self.jwt = self.grant.refresh_token(self.jwt)
            except RefreshTokenError as con_err:
                log.warning(
                    "Unable to refresh token (reason: %s). "
                    "Renewing initial authentication.",
                    con_err,
                )
                self.jwt = self.grant.get_first_token()
        else:
            # Token is still valid
            log.debug("Credentials still valid")
            return
        self.save_token(now)

    def get_access_token(self) -> str:
        """Return the access token."""
        self._init_jwt()
        self._refresh_if_needed()
        assert self.jwt
        return self.jwt.access_token
