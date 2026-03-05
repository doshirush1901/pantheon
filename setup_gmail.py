#!/usr/bin/env python3
"""
Gmail API Setup for IRA
=======================

Run this script to authenticate Gmail for sending emails.

Prerequisites:
1. Go to Google Cloud Console: https://console.cloud.google.com
2. Create a project (or use existing)
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials.json to this directory

Then run:
    python3 setup_gmail.py

This will open a browser for authentication and create token.json
"""

import os
from pathlib import Path

def main():
    # Check for credentials
    creds_path = Path(__file__).parent / "credentials.json"
    token_path = Path(__file__).parent / "token.json"
    
    if not creds_path.exists():
        print("=" * 60)
        print("GMAIL SETUP INSTRUCTIONS")
        print("=" * 60)
        print("""
1. Go to: https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID (Desktop app)
3. Download the JSON file
4. Save it as: credentials.json in this directory
5. Run this script again

The file should look like:
{
  "installed": {
    "client_id": "xxx.apps.googleusercontent.com",
    "project_id": "xxx",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    ...
  }
}
""")
        return
    
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        
        SCOPES = [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly',
        ]
        
        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("[setup] Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                print("[setup] Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save token
            token_path.write_text(creds.to_json())
            print(f"[setup] Token saved to: {token_path}")
        
        print("\n✅ Gmail setup complete!")
        print("You can now send AND read emails with IRA.")
        print("\nTo ingest your mailbox into Ira's knowledge base:")
        print("  python scripts/ingest_mailbox.py --dry-run    # Preview")
        print("  python scripts/ingest_mailbox.py              # Full scan")
        print("  python scripts/ingest_mailbox.py --since 2024-01-01  # Since date")
        print("\nNote: If you previously authorized with send-only scope,")
        print("delete token.json and re-run this script to get read access.")
        
    except ImportError:
        print("Installing required packages...")
        os.system("pip3 install google-auth google-auth-oauthlib google-api-python-client")
        print("\nRun this script again after installation.")

if __name__ == "__main__":
    main()
