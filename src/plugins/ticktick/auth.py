import os
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from urllib.parse import parse_qs, urlparse
from dotenv import load_dotenv

class TickTickAuth:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = "http://localhost:8000/callback"
        self.token_file = os.path.expanduser("~/.inkypi/ticktick_token.json")

    def get_auth_url(self):
        return f"https://ticktick.com/oauth/authorize?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&scope=tasks:read"

    def save_tokens(self, access_token, refresh_token=None):
        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        token_data = {
            'access_token': access_token,
        }
        if refresh_token:
            token_data['refresh_token'] = refresh_token
            
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f)
        print(f"New access token: {access_token}")

    def load_tokens(self):
        # First try to load from token file
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                return json.load(f)
        
        # If token file doesn't exist, try to load from .env
        load_dotenv()
        access_token = os.getenv('TICKTICK_ACCESS_TOKEN')
        if access_token:
            return {'access_token': access_token}
            
        return None

    def refresh_access_token(self, refresh_token):
        if not refresh_token:
            return None
            
        response = requests.post(
            "https://ticktick.com/oauth/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
        )
        if response.status_code == 200:
            data = response.json()
            self.save_tokens(
                data.get('access_token'),
                data.get('refresh_token')
            )
            return data.get('access_token')
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
    client_id = os.getenv('TICKTICK_CLIENT_ID')
    client_secret = os.getenv('TICKTICK_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        raise RuntimeError("TICKTICK_CLIENT_ID and TICKTICK_CLIENT_SECRET must be set in .env file")
    
    auth = TickTickAuth(client_id, client_secret)
    
    # Check for existing tokens
    tokens = auth.load_tokens()
    if tokens:
        # Try to refresh the token
        new_access_token = auth.refresh_access_token(tokens.get('refresh_token'))
        if new_access_token:
            print("Successfully refreshed access token!")
            return auth

    # Start local server to receive callback
    server = HTTPServer(('localhost', 8000), CallbackHandler)
    server.auth_code = None
    
    # Open browser for authentication
    webbrowser.open(auth.get_auth_url())
    
    # Wait for callback
    print("Waiting for authentication...")
    server.handle_request()
    
    if server.auth_code:
        # Exchange code for tokens
        response = requests.post(
            "https://ticktick.com/oauth/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": server.auth_code,
                "redirect_uri": auth.redirect_uri
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            auth.save_tokens(
                data.get('access_token'),
                data.get('refresh_token')
            )
            print("Successfully authenticated!")
            return auth
    
    print("Authentication failed!")
    return None

if __name__ == "__main__":
    authenticate() 
