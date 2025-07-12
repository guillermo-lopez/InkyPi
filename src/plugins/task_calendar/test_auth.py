#!/usr/bin/env python3
"""Test script to verify GoogleCalendarAuth functionality."""

import os
import sys
import logging
from auth.google_auth import GoogleCalendarAuth, load_credentials_from_env

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_auth_flow():
    """Test the authentication flow."""
    try:
        # Load client credentials
        client_id, client_secret = load_credentials_from_env()
        logger.info("Successfully loaded client credentials from .env")
        
        # Create auth instance
        auth = GoogleCalendarAuth(client_id, client_secret)
        logger.info("Successfully created GoogleCalendarAuth instance")
        
        # Try to get valid credentials
        credentials = auth.get_valid_credentials()
        if credentials:
            logger.info("Successfully loaded valid credentials from token file")
            logger.info(f"Token expires at: {credentials.expiry}")
            return True
        else:
            logger.warning("No valid credentials found - authentication required")
            return False
            
    except Exception as e:
        logger.error(f"Error in authentication flow: {e}")
        return False

def test_token_file_exists():
    """Check if token file exists."""
    # Load token file path from environment variable or use default
    token_file_path = os.getenv('GOOGLE_CALENDAR_TOKEN_FILE')
    if token_file_path:
        token_file = os.path.expanduser(token_file_path)
    else:
        token_file = os.path.expanduser("~/.inkypi/google_calendar_token.json")
    
    if os.path.exists(token_file):
        logger.info(f"Token file exists at: {token_file}")
        return True
    else:
        logger.warning(f"Token file not found at: {token_file}")
        return False

def main():
    """Main test function."""
    print("Testing GoogleCalendarAuth functionality...")
    print("=" * 50)
    
    # Test 1: Check if token file exists
    token_exists = test_token_file_exists()
    
    # Test 2: Test authentication flow
    auth_success = test_auth_flow()
    
    print("\nTest Results:")
    print("=" * 50)
    print(f"Token file exists: {token_exists}")
    print(f"Authentication successful: {auth_success}")
    
    if not auth_success:
        print("\nTo set up authentication, run:")
        print("python3 src/plugins/task_calendar/auth/google_auth.py")
    
    return auth_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
