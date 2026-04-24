"""
authorize_drive.py — One-time Google Drive OAuth Setup
======================================================
Run this ONCE to open the browser consent page and generate drive_token.json.
After that, file_sender.py will work silently without browser prompts.

Usage:
    python authorize_drive.py
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = 'drive_token.json'
CREDENTIALS_FILE = 'credentials.json'

def main():
    creds = None

    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[~] Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("[*] Opening browser for Google OAuth consent...")
            print("   -> Sign in with your Google account")
            print("   -> Click Allow on the permissions screen")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the token
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        print("\n[OK] drive_token.json saved successfully!")
        print("     Google Drive integration is now active.")
    else:
        print("[OK] drive_token.json already exists and is valid. No action needed.")

if __name__ == '__main__':
    main()
