#!/usr/bin/env python3
"""Google Calendar OAuth2 authentication module."""

import os
import json
import time
import logging
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from typing import Optional, Tuple
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class GoogleCalendarAuth:
    """Handles Google Calendar OAuth2 authentication flow."""

    SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events.readonly',
        'https://www.googleapis.com/auth/calendar.settings.readonly',
        'https://www.googleapis.com/auth/calendar.calendars.readonly'
    ]
    REDIRECT_URI = "http://localhost:8000/callback"
    TOKEN_EXPIRY_BUFFER = 300  # Refresh token if expiring within 5 minutes

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = self._get_token_file_path()
        self.client_config = self._build_client_config()
        print(f"Using token file: {self.token_file}")

    def _get_token_file_path(self) -> str:
        """Get token file path from environment or use default."""
        token_file_path = os.getenv('GOOGLE_CALENDAR_TOKEN_FILE')
        if token_file_path:
            return os.path.expanduser(token_file_path)
        return os.path.expanduser("~/.inkypi/google_calendar_token.json")

    def _build_client_config(self) -> dict:
        """Build the OAuth2 client configuration."""
        return {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uris": [self.REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }

    def _create_flow(self) -> InstalledAppFlow:
        """Create OAuth flow with proper configuration."""
        return InstalledAppFlow.from_client_config(
            self.client_config,
            self.SCOPES,
            redirect_uri=self.REDIRECT_URI
        )

    def get_auth_url(self) -> str:
        """Generate and return the authorization URL."""
        flow = self._create_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent'  # Force consent to get refresh token
        )
        print(f"\nAuthorization URL: {auth_url}\n")
        return auth_url

    def save_tokens(self, credentials: Credentials) -> None:
        """Save OAuth2 credentials to file."""
        msg = f"Saving tokens to: {self.token_file}"
        logger.info(msg) if logger.hasHandlers() else print(msg)

        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)

        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }

        msg = "Writing token data to file..."
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = f"  Will save access token: {bool(token_data['token'])}"
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = f"  Will save refresh token: {bool(token_data['refresh_token'])}"
        logger.info(msg) if logger.hasHandlers() else print(msg)

        with open(self.token_file, 'w') as f:
            json.dump(token_data, f, indent=2)

        msg = f"✓ Tokens successfully written to: {self.token_file}"
        logger.info(msg) if logger.hasHandlers() else print(msg)

        # Verify the file was written correctly
        import stat
        file_stat = os.stat(self.token_file)
        msg = f"File size: {file_stat.st_size} bytes"
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = f"File permissions: {oct(stat.S_IMODE(file_stat.st_mode))}"
        logger.info(msg) if logger.hasHandlers() else print(msg)

        self._print_token_info(credentials)

    def _print_token_info(self, credentials: Credentials) -> None:
        """Print token information for debugging."""
        import time
        from datetime import datetime, timezone as tz

        msg = "\n" + "=" * 80
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = "TOKEN INFORMATION"
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = "=" * 80
        logger.info(msg) if logger.hasHandlers() else print(msg)

        msg = f"Access Token: {credentials.token[:50]}..." if credentials.token else "Access Token: None"
        logger.info(msg) if logger.hasHandlers() else print(msg)

        if credentials.refresh_token:
            msg = f"Refresh Token: Present ({credentials.refresh_token[:20]}...)"
        else:
            msg = "Refresh Token: MISSING"
        logger.info(msg) if logger.hasHandlers() else print(msg)

        msg = f"Token Expiry: {credentials.expiry}"
        logger.info(msg) if logger.hasHandlers() else print(msg)

        if credentials.expiry:
            # Make now timezone-aware to match credentials.expiry
            now = datetime.now(tz.utc) if credentials.expiry.tzinfo else datetime.now()
            time_until_expiry = (credentials.expiry - now).total_seconds()
            msg = f"Time until expiry: {time_until_expiry:.0f} seconds ({time_until_expiry/60:.1f} minutes)"
            logger.info(msg) if logger.hasHandlers() else print(msg)
            msg = f"Token expired: {credentials.expired}"
            logger.info(msg) if logger.hasHandlers() else print(msg)

        msg = "\nScopes:"
        logger.info(msg) if logger.hasHandlers() else print(msg)
        for scope in credentials.scopes:
            msg = f"  - {scope}"
            logger.info(msg) if logger.hasHandlers() else print(msg)

        msg = "=" * 80
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = f"Tokens saved to: {self.token_file}"
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = "The plugin will automatically refresh tokens when needed."
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = "=" * 80 + "\n"
        logger.info(msg) if logger.hasHandlers() else print(msg)

    def load_tokens(self) -> Optional[Credentials]:
        """Load OAuth2 credentials from JSON file."""
        if not os.path.exists(self.token_file):
            msg = f"Token file not found: {self.token_file}"
            logger.warning(msg) if logger.hasHandlers() else print(msg)
            return None

        try:
            msg = f"Loading tokens from: {self.token_file}"
            logger.info(msg) if logger.hasHandlers() else print(msg)

            with open(self.token_file, 'r') as f:
                token_data = json.load(f)

                # Log what we're loading (without sensitive data)
                msg = f"Token file contents:"
                logger.info(msg) if logger.hasHandlers() else print(msg)
                msg = f"  Has access token: {bool(token_data.get('token'))}"
                logger.info(msg) if logger.hasHandlers() else print(msg)
                msg = f"  Has refresh token: {bool(token_data.get('refresh_token'))}"
                logger.info(msg) if logger.hasHandlers() else print(msg)
                if token_data.get('refresh_token'):
                    msg = f"  Refresh token preview: {token_data['refresh_token'][:20]}..."
                    logger.info(msg) if logger.hasHandlers() else print(msg)
                msg = f"  Has expiry: {bool(token_data.get('expiry'))}"
                logger.info(msg) if logger.hasHandlers() else print(msg)
                if token_data.get('expiry'):
                    msg = f"  Expiry: {token_data['expiry']}"
                    logger.info(msg) if logger.hasHandlers() else print(msg)
                msg = f"  Scopes: {len(token_data.get('scopes', []))}"
                logger.info(msg) if logger.hasHandlers() else print(msg)

                # Parse expiry if present
                from datetime import datetime
                expiry = None
                if token_data.get('expiry'):
                    try:
                        expiry = datetime.fromisoformat(token_data['expiry'])
                    except (ValueError, TypeError) as e:
                        msg = f"  Warning: Could not parse expiry date: {e}"
                        logger.warning(msg) if logger.hasHandlers() else print(msg)

                credentials = Credentials(
                    token=token_data['token'],
                    refresh_token=token_data['refresh_token'],
                    token_uri=token_data['token_uri'],
                    client_id=token_data['client_id'],
                    client_secret=token_data['client_secret'],
                    scopes=token_data['scopes'],
                    expiry=expiry
                )

                msg = f"✓ Successfully loaded credentials from disk"
                logger.info(msg) if logger.hasHandlers() else print(msg)
                return credentials

        except (json.JSONDecodeError, KeyError) as e:
            msg = f"✗ Error loading token file: {e}"
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = f"  Error type: {type(e).__name__}"
            logger.error(msg) if logger.hasHandlers() else print(msg)
            return None

    def get_valid_credentials(self) -> Optional[Credentials]:
        """
        Get valid credentials, automatically refreshing if expired.

        Returns:
            Credentials object if valid, None if authentication is required
        """
        msg = "=" * 80
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = "GETTING VALID CREDENTIALS"
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = "=" * 80
        logger.info(msg) if logger.hasHandlers() else print(msg)

        credentials = self.load_tokens()
        if not credentials:
            msg = "=" * 80
            logger.warning(msg) if logger.hasHandlers() else print(msg)
            msg = "No Google Calendar token file found."
            logger.warning(msg) if logger.hasHandlers() else print(msg)
            msg = "Run: python3 src/plugins/task_calendar/auth/google_auth.py"
            logger.warning(msg) if logger.hasHandlers() else print(msg)
            msg = "=" * 80
            logger.warning(msg) if logger.hasHandlers() else print(msg)
            return None

        # Log current token status
        from datetime import datetime, timezone as tz

        msg = f"Current token state:"
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = f"  Token expiry: {credentials.expiry}"
        logger.info(msg) if logger.hasHandlers() else print(msg)

        if credentials.expiry:
            # Make now timezone-aware to match credentials.expiry
            now = datetime.now(tz.utc) if credentials.expiry.tzinfo else datetime.now()
            time_until_expiry = (credentials.expiry - now).total_seconds()
            msg = f"  Time until expiry: {time_until_expiry:.0f} seconds ({time_until_expiry/60:.1f} minutes)"
            logger.info(msg) if logger.hasHandlers() else print(msg)
        else:
            msg = f"  Time until expiry: Unknown (no expiry set)"
            logger.info(msg) if logger.hasHandlers() else print(msg)

        msg = f"  Token expired: {credentials.expired}"
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = f"  Refresh token present: {bool(credentials.refresh_token)}"
        logger.info(msg) if logger.hasHandlers() else print(msg)

        # Check if token needs refresh
        if self._needs_refresh(credentials):
            msg = "⚠ Token expired or expiring soon (within 5 minutes), attempting refresh..."
            logger.info(msg) if logger.hasHandlers() else print(msg)

            refreshed = self.refresh_access_token(credentials)
            if refreshed:
                msg = "=" * 80
                logger.info(msg) if logger.hasHandlers() else print(msg)
                msg = "✓ Successfully refreshed access token!"
                logger.info(msg) if logger.hasHandlers() else print(msg)
                msg = "=" * 80
                logger.info(msg) if logger.hasHandlers() else print(msg)
                return refreshed

            msg = "=" * 80
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = "✗ Failed to refresh token - may be invalid or revoked."
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = "Run: python3 src/plugins/task_calendar/auth/google_auth.py"
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = "=" * 80
            logger.error(msg) if logger.hasHandlers() else print(msg)
            return None

        msg = "✓ Token is still valid, no refresh needed"
        logger.info(msg) if logger.hasHandlers() else print(msg)
        msg = "=" * 80
        logger.info(msg) if logger.hasHandlers() else print(msg)
        return credentials

    def _needs_refresh(self, credentials: Credentials) -> bool:
        """Check if credentials need to be refreshed."""
        if credentials.expired:
            return True
        if credentials.expiry:
            time_until_expiry = credentials.expiry.timestamp() - time.time()
            return time_until_expiry < self.TOKEN_EXPIRY_BUFFER
        return False

    def refresh_access_token(self, credentials: Credentials) -> Optional[Credentials]:
        """Refresh the OAuth2 access token."""
        from datetime import datetime, timezone as tz

        if not credentials or not credentials.refresh_token:
            msg = "=" * 80
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = "CANNOT REFRESH: Missing credentials or refresh token"
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = f"  Has credentials: {bool(credentials)}"
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = f"  Has refresh token: {bool(credentials.refresh_token) if credentials else False}"
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = "=" * 80
            logger.error(msg) if logger.hasHandlers() else print(msg)
            return None

        try:
            msg = "=" * 80
            logger.info(msg) if logger.hasHandlers() else print(msg)
            msg = "REFRESHING ACCESS TOKEN"
            logger.info(msg) if logger.hasHandlers() else print(msg)
            msg = "=" * 80
            logger.info(msg) if logger.hasHandlers() else print(msg)

            # Log state BEFORE refresh
            msg = "Token state BEFORE refresh:"
            logger.info(msg) if logger.hasHandlers() else print(msg)
            msg = f"  Access token: {credentials.token[:50]}..." if credentials.token else "  Access token: None"
            logger.info(msg) if logger.hasHandlers() else print(msg)
            msg = f"  Refresh token: {credentials.refresh_token[:20]}..." if credentials.refresh_token else "  Refresh token: None"
            logger.info(msg) if logger.hasHandlers() else print(msg)
            msg = f"  Token expiry: {credentials.expiry}"
            logger.info(msg) if logger.hasHandlers() else print(msg)

            if credentials.expiry:
                # Make now timezone-aware to match credentials.expiry
                now = datetime.now(tz.utc) if credentials.expiry.tzinfo else datetime.now()
                time_until_expiry = (credentials.expiry - now).total_seconds()
                msg = f"  Time until expiry: {time_until_expiry:.0f} seconds ({time_until_expiry/60:.1f} minutes)"
                logger.info(msg) if logger.hasHandlers() else print(msg)
                msg = f"  Token expired: {credentials.expired}"
                logger.info(msg) if logger.hasHandlers() else print(msg)

            msg = "\nCalling Google token refresh API..."
            logger.info(msg) if logger.hasHandlers() else print(msg)

            credentials.refresh(Request())

            msg = "\n✓ Token refresh API call successful!"
            logger.info(msg) if logger.hasHandlers() else print(msg)

            # Log state AFTER refresh
            msg = "\nToken state AFTER refresh:"
            logger.info(msg) if logger.hasHandlers() else print(msg)
            msg = f"  Access token: {credentials.token[:50]}..." if credentials.token else "  Access token: None"
            logger.info(msg) if logger.hasHandlers() else print(msg)
            msg = f"  Refresh token: {credentials.refresh_token[:20]}..." if credentials.refresh_token else "  Refresh token: MISSING"
            logger.info(msg) if logger.hasHandlers() else print(msg)
            msg = f"  Token expiry: {credentials.expiry}"
            logger.info(msg) if logger.hasHandlers() else print(msg)

            if credentials.expiry:
                # Make now timezone-aware to match credentials.expiry
                now = datetime.now(tz.utc) if credentials.expiry.tzinfo else datetime.now()
                time_until_expiry = (credentials.expiry - now).total_seconds()
                msg = f"  Time until expiry: {time_until_expiry:.0f} seconds ({time_until_expiry/60:.1f} minutes)"
                logger.info(msg) if logger.hasHandlers() else print(msg)
                msg = f"  Token expired: {credentials.expired}"
                logger.info(msg) if logger.hasHandlers() else print(msg)

            msg = "\nSaving refreshed tokens to disk..."
            logger.info(msg) if logger.hasHandlers() else print(msg)

            self.save_tokens(credentials)
            return credentials

        except Exception as e:
            msg = "=" * 80
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = "✗ ERROR REFRESHING TOKEN"
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = "=" * 80
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = f"Error: {e}"
            logger.error(msg) if logger.hasHandlers() else print(msg)
            msg = f"Error type: {type(e).__name__}"
            logger.error(msg) if logger.hasHandlers() else print(msg)

            # Check for specific error types
            error_msg = str(e)
            if "invalid_grant" in error_msg:
                msg = "\nThis is an 'invalid_grant' error - the refresh token is invalid or revoked."
                logger.error(msg) if logger.hasHandlers() else print(msg)
                msg = "Common causes:"
                logger.error(msg) if logger.hasHandlers() else print(msg)
                msg = "  1. Token has been revoked at https://myaccount.google.com/permissions"
                logger.error(msg) if logger.hasHandlers() else print(msg)
                msg = "  2. Token has expired (6 months for unverified apps)"
                logger.error(msg) if logger.hasHandlers() else print(msg)
                msg = "  3. User changed password"
                logger.error(msg) if logger.hasHandlers() else print(msg)
                msg = "  4. OAuth consent screen settings changed"
                logger.error(msg) if logger.hasHandlers() else print(msg)

            msg = "=" * 80
            logger.error(msg) if logger.hasHandlers() else print(msg)
            return None

    def exchange_code_for_tokens(self, auth_code: str) -> Optional[Credentials]:
        """Exchange authorization code for OAuth2 tokens."""
        flow = self._create_flow()

        # Set authorization parameters
        flow.authorization_url(access_type='offline', prompt='consent')

        try:
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials

            if not credentials.refresh_token:
                print("\nWarning: No refresh token received.")
                print("User may have already authorized. Revoke at:")
                print("https://myaccount.google.com/permissions")

            self.save_tokens(credentials)
            return credentials
        except Exception as e:
            print(f"Error exchanging code for tokens: {e}")
            return None


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth2 callback."""

    def do_GET(self):
        """Handle GET request for OAuth2 callback."""
        if self.path.startswith('/callback'):
            query = parse_qs(urlparse(self.path).query)

            if 'code' in query:
                self.server.auth_code = query['code'][0]
                self._send_success_response()
            else:
                self._send_error_response()
        else:
            self.send_error(404, "Not Found")

    def _send_success_response(self):
        """Send successful authentication response."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        message = b"<h2>Authentication successful!</h2><p>You can close this window.</p>"
        self.wfile.write(message)

    def _send_error_response(self):
        """Send error response when no authorization code is received."""
        self.send_error(400, "No authorization code received")

    def log_message(self, format, *args):
        """Suppress default HTTP server logging."""
        pass


def load_credentials_from_env() -> Tuple[str, str]:
    """Load Google Calendar credentials from environment variables."""
    load_dotenv()

    client_id = os.getenv('GOOGLE_CALENDAR_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET')

    if not client_id or not client_secret:
        raise RuntimeError(
            "GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET "
            "must be set in .env file"
        )

    return client_id, client_secret


def run_oauth_flow(auth: GoogleCalendarAuth) -> Optional[GoogleCalendarAuth]:
    """Run the OAuth2 authentication flow with local server."""
    server = HTTPServer(('localhost', 8000), CallbackHandler)
    server.auth_code = None

    webbrowser.open(auth.get_auth_url())
    print("Waiting for authentication...")
    server.handle_request()

    if server.auth_code:
        credentials = auth.exchange_code_for_tokens(server.auth_code)
        if credentials:
            print("Successfully authenticated!")
            return auth

    print("Authentication failed!")
    return None


def authenticate() -> Optional[GoogleCalendarAuth]:
    """Main authentication function."""
    try:
        client_id, client_secret = load_credentials_from_env()
    except RuntimeError as e:
        print(f"Error: {e}")
        return None

    auth = GoogleCalendarAuth(client_id, client_secret)

    # Check for existing valid tokens
    credentials = auth.get_valid_credentials()
    if credentials:
        print("Successfully loaded valid credentials!")
        return auth

    # Run OAuth flow if needed
    return run_oauth_flow(auth)


if __name__ == "__main__":
    authenticate()
