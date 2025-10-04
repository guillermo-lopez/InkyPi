#!/usr/bin/env python3
"""Google Calendar OAuth2 authentication module."""

import os
import json
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from typing import Optional, Tuple
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv


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
        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)

        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        with open(self.token_file, 'w') as f:
            json.dump(token_data, f, indent=2)

        self._print_token_info(credentials)

    def _print_token_info(self, credentials: Credentials) -> None:
        """Print token information for debugging."""
        print("\nToken Information:")
        print("=" * 80)
        print(f"Access Token: {credentials.token[:50]}..." if credentials.token else "None")
        print(f"Refresh Token: {'Present' if credentials.refresh_token else 'Missing'}")
        print(f"Token Expiry: {credentials.expiry}")
        print("\nScopes:")
        for scope in credentials.scopes:
            print(f"  - {scope}")
        print("=" * 80)
        print(f"\nTokens saved to: {self.token_file}")
        print("The plugin will automatically refresh tokens when needed.\n")

    def load_tokens(self) -> Optional[Credentials]:
        """Load OAuth2 credentials from JSON file."""
        if not os.path.exists(self.token_file):
            return None

        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                return Credentials(
                    token=token_data['token'],
                    refresh_token=token_data['refresh_token'],
                    token_uri=token_data['token_uri'],
                    client_id=token_data['client_id'],
                    client_secret=token_data['client_secret'],
                    scopes=token_data['scopes']
                )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading token file: {e}")
            return None

    def get_valid_credentials(self) -> Optional[Credentials]:
        """
        Get valid credentials, automatically refreshing if expired.

        Returns:
            Credentials object if valid, None if authentication is required
        """
        credentials = self.load_tokens()
        if not credentials:
            print("No Google Calendar token file found.")
            print("Run: python3 src/plugins/task_calendar/auth/google_auth.py")
            return None

        # Check if token needs refresh
        if self._needs_refresh(credentials):
            print("Token expired or expiring soon, attempting refresh...")
            refreshed = self.refresh_access_token(credentials)
            if refreshed:
                print("Successfully refreshed access token!")
                return refreshed

            print("Failed to refresh token - may be invalid or revoked.")
            print("Run: python3 src/plugins/task_calendar/auth/google_auth.py")
            return None

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
        if not credentials or not credentials.refresh_token:
            return None

        try:
            credentials.refresh(Request())
            self.save_tokens(credentials)
            return credentials
        except Exception as e:
            print(f"Error refreshing token: {e}")
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
