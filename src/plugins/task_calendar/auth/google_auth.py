#!/usr/bin/env python3

import os
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


class GoogleCalendarAuth:
    """Handles Google Calendar OAuth2 authentication flow."""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    REDIRECT_URI = "http://localhost:8000/callback"
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = os.path.expanduser("~/.inkypi/google_calendar_token.json")
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
        
        print("New Google Calendar access token saved")

    def load_tokens(self) -> Credentials | None:
        """Load OAuth2 credentials from file or environment variables."""
        # Try to load from token file first
        if os.path.exists(self.token_file):
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
        
        # Fallback to environment variable
        load_dotenv()
        access_token = os.getenv('GOOGLE_CALENDAR_ACCESS_TOKEN')
        if access_token:
            return Credentials(
                token=access_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.SCOPES
            )
            
        return None

    def refresh_access_token(self, credentials: Credentials) -> Credentials | None:
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

    def exchange_code_for_tokens(self, auth_code: str) -> Credentials | None:
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
            
            print("\nToken Information:")
            print(f"Access Token: {credentials.token}")
            print(f"Refresh Token: {credentials.refresh_token}")
            print(f"Token URI: {credentials.token_uri}")
            print(f"Scopes: {credentials.scopes}\n")
            
            if not credentials.refresh_token:
                print("Warning: No refresh token received. User may have already authorized this app.")
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


def load_credentials_from_env() -> tuple[str, str]:
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


def run_oauth_flow(auth: GoogleCalendarAuth) -> GoogleCalendarAuth | None:
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


def authenticate() -> GoogleCalendarAuth | None:
    """Main authentication function."""
    try:
        client_id, client_secret = load_credentials_from_env()
    except RuntimeError as e:
        print(f"Error: {e}")
        return None
    
    auth = GoogleCalendarAuth(client_id, client_secret)
    
    # Check for existing tokens
    credentials = auth.load_tokens()
    if credentials:
        # Try to refresh the token
        refreshed_credentials = auth.refresh_access_token(credentials)
        if refreshed_credentials:
            print("Successfully refreshed Google Calendar access token!")
            return auth
    
    # Run OAuth flow if no valid tokens exist
    return run_oauth_flow(auth)


if __name__ == "__main__":
    authenticate()
