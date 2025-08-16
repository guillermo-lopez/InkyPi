#!/usr/bin/env python3

import os
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from typing import Union, Optional, Tuple
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


class GoogleCalendarAuth:
    """Handles Google Calendar OAuth2 authentication flow."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly',  # Read calendar events
        'https://www.googleapis.com/auth/calendar.events.readonly',  # Read calendar events
        'https://www.googleapis.com/auth/calendar.settings.readonly',  # Read calendar settings
        'https://www.googleapis.com/auth/calendar.calendars.readonly'  # Read calendar list
    ]
    REDIRECT_URI = "http://localhost:8000/callback"
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        # Load token file path from environment variable or use default
        token_file_path = os.getenv('GOOGLE_CALENDAR_TOKEN_FILE')
        if token_file_path:
            self.token_file = os.path.expanduser(token_file_path)
        else:
            self.token_file = os.path.expanduser("~/.inkypi/google_calendar_token.json")
        
        print(f"Using token file: {self.token_file}")
        self.client_config = self._build_client_config()

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

    def get_auth_url(self) -> str:
        """Generate and return the authorization URL."""
        flow = InstalledAppFlow.from_client_config(
            self.client_config,
            self.SCOPES,
            redirect_uri=self.REDIRECT_URI
        )
        # Force offline access and consent prompt to ensure refresh token
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent'
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
        
        print("\nToken Information:")
        print("=" * 80)
        print(f"Access Token: {credentials.token}")
        print(f"Refresh Token: {credentials.refresh_token}")
        print(f"Token URI: {credentials.token_uri}")
        print(f"Client ID: {credentials.client_id}")
        print(f"Client Secret: {credentials.client_secret}")
        print("\nScopes:")
        for scope in credentials.scopes:
            print(f"- {scope}")
        print("\nToken Expiry:", credentials.expiry)
        print("=" * 80)
        print(f"\nGoogle Calendar tokens saved to: {self.token_file}")
        print("The plugin will automatically refresh tokens when needed.")

    def load_tokens(self) -> Optional[Credentials]:
        """Load OAuth2 credentials from JSON file only."""
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
            print("Please run the authentication script to set up credentials:")
            print("python3 src/plugins/task_calendar/auth/google_auth.py")
            return None
            
        # Check if token is expired or will expire soon (within 5 minutes)
        if credentials.expired or (credentials.expiry and 
                                 (credentials.expiry.timestamp() - 300) < os.time()):
            print("Google Calendar token expired, attempting to refresh...")
            refreshed_credentials = self.refresh_access_token(credentials)
            if refreshed_credentials:
                print("Successfully refreshed Google Calendar access token!")
                return refreshed_credentials
            else:
                print("Failed to refresh token - refresh token may be invalid or revoked.")
                print("Please re-authenticate by running:")
                print("python3 src/plugins/task_calendar/auth/google_auth.py")
                return None
        
        return credentials

    def refresh_access_token(self, credentials: Credentials) -> Optional[Credentials]:
        """Refresh the OAuth2 access token."""
        if not credentials or not credentials.refresh_token:
            return None
            
        try:
            credentials.refresh(Request())
            self.save_tokens(credentials)
            return credentials
        except Exception as e:
            print(f"Error refreshing Google Calendar token: {e}")
            return None

    def exchange_code_for_tokens(self, auth_code: str) -> Optional[Credentials]:
        """Exchange authorization code for OAuth2 tokens."""
        flow = InstalledAppFlow.from_client_config(
            self.client_config,
            self.SCOPES,
            redirect_uri=self.REDIRECT_URI
        )
        
        # Ensure we're requesting offline access
        flow.authorization_url(
            access_type='offline',
            prompt='consent'
        )
        
        try:
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials
            
            if not credentials.refresh_token:
                print("\nWarning: No refresh token received. User may have already authorized this app.")
                print("Try revoking access at https://myaccount.google.com/permissions and re-running.")
            
            self.save_tokens(credentials)
            return credentials
        except Exception as e:
            print(f"Error during Google Calendar token exchange: {e}")
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
        self.wfile.write(b"Authentication successful! You can close this window.")
    
    def _send_error_response(self):
        """Send error response when no authorization code is received."""
        self.send_error(400, "No authorization code received")
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging."""
        pass


def load_credentials_from_env() -> Tuple[str, str]:
    """Load Google Calendar credentials from environment variables."""
    from dotenv import load_dotenv
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
    
    # Open browser for authentication
    webbrowser.open(auth.get_auth_url())
    
    print("Waiting for Google Calendar authentication...")
    server.handle_request()
    
    if server.auth_code:
        credentials = auth.exchange_code_for_tokens(server.auth_code)
        if credentials:
            print("Successfully authenticated with Google Calendar!")
            return auth
    
    print("Google Calendar authentication failed!")
    return None


def authenticate() -> Optional[GoogleCalendarAuth]:
    """Main authentication function."""
    try:
        client_id, client_secret = load_credentials_from_env()
    except RuntimeError as e:
        print(f"Error: {e}")
        return None
    
    auth = GoogleCalendarAuth(client_id, client_secret)
    
    # Check for existing tokens and try to refresh if needed
    credentials = auth.get_valid_credentials()
    if credentials:
        print("Successfully loaded valid Google Calendar credentials!")
        return auth
    
    # Run OAuth flow if no valid tokens exist
    return run_oauth_flow(auth)


if __name__ == "__main__":
    authenticate()
