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
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = "http://localhost:8000/callback"
        self.token_file = os.path.expanduser("~/.inkypi/google_calendar_token.json")
        self.scopes = ['https://www.googleapis.com/auth/calendar.readonly']

    def get_auth_url(self):
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uris": [self.redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            self.scopes
        )
        return flow.authorization_url()[0]

    def save_tokens(self, credentials):
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
            json.dump(token_data, f)
        print("New Google Calendar access token saved")

    def load_tokens(self):
        # First try to load from token file
        if os.path.exists(self.token_file):
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
        
        # If token file doesn't exist, try to load from .env
        load_dotenv()
        access_token = os.getenv('GOOGLE_CALENDAR_ACCESS_TOKEN')
        if access_token:
            return Credentials(
                token=access_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes
            )
            
        return None

    def refresh_access_token(self, credentials):
        if not credentials or not credentials.refresh_token:
            return None
            
        try:
            credentials.refresh(Request())
            self.save_tokens(credentials)
            return credentials
        except Exception as e:
            print(f"Error refreshing Google Calendar token: {e}")
            return None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/callback'):
            query = parse_qs(urlparse(self.path).query)
            if 'code' in query:
                self.server.auth_code = query['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Authentication successful! You can close this window.")
            else:
                self.send_error(400, "No authorization code received")

def authenticate():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get credentials from environment variables
    client_id = os.getenv('GOOGLE_CALENDAR_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        raise RuntimeError("GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET must be set in .env file")
    
    auth = GoogleCalendarAuth(client_id, client_secret)
    
    # Check for existing tokens
    credentials = auth.load_tokens()
    if credentials:
        # Try to refresh the token
        new_credentials = auth.refresh_access_token(credentials)
        if new_credentials:
            print("Successfully refreshed Google Calendar access token!")
            return auth

    # Start local server to receive callback
    server = HTTPServer(('localhost', 8000), CallbackHandler)
    server.auth_code = None
    
    # Open browser for authentication
    webbrowser.open(auth.get_auth_url())
    
    # Wait for callback
    print("Waiting for Google Calendar authentication...")
    server.handle_request()
    
    if server.auth_code:
        # Exchange code for tokens
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": [auth.redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            auth.scopes
        )
        
        try:
            credentials = flow.fetch_token(
                code=server.auth_code,
                redirect_uri=auth.redirect_uri
            )
            auth.save_tokens(credentials)
            print("Successfully authenticated with Google Calendar!")
            return auth
        except Exception as e:
            print(f"Error during Google Calendar token exchange: {e}")
    
    print("Google Calendar authentication failed!")
    return None

if __name__ == "__main__":
    authenticate() 
