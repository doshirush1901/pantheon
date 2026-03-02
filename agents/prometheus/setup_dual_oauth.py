#!/usr/bin/env python3
"""
Setup Dual OAuth for Prometheus Email Testing

This script authenticates BOTH mailboxes:
1. Rushabh's mailbox (rushabh@machinecraft.org) - Sends questions to IRA
2. IRA's mailbox (ira@machinecraft.org) - Sends replies back

Run this script once to set up authentication for both accounts.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Paths for dual credentials
RUSHABH_CREDENTIALS = PROJECT_ROOT / "credentials_rushabh.json"
RUSHABH_TOKEN = PROJECT_ROOT / "token_rushabh.json"

IRA_CREDENTIALS = PROJECT_ROOT / "credentials.json"  # Using existing
IRA_TOKEN = PROJECT_ROOT / "token.json"  # Using existing

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


def authenticate_account(credentials_file: Path, token_file: Path, account_name: str) -> bool:
    """Authenticate a Gmail account."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        
        print(f"\n{'='*60}")
        print(f"  Authenticating: {account_name}")
        print(f"{'='*60}")
        
        if not credentials_file.exists():
            print(f"❌ Credentials file not found: {credentials_file}")
            return False
        
        creds = None
        
        # Check for existing token
        if token_file.exists():
            print(f"  Found existing token: {token_file.name}")
            creds = Credentials.from_authorized_user_file(str(token_file), GMAIL_SCOPES)
        
        # Refresh or create new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("  Token expired, refreshing...")
                creds.refresh(Request())
            else:
                print(f"  Opening browser for {account_name} authentication...")
                print(f"  ⚠️  Please sign in with: {account_name}")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_file), GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save token
            token_file.write_text(creds.to_json())
            print(f"  ✓ Token saved to: {token_file.name}")
        
        # Verify connection
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress')
        
        print(f"  ✓ Connected as: {email}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("  PROMETHEUS DUAL OAUTH SETUP")
    print("  Setting up both mailboxes for email testing")
    print("="*60)
    
    # Check if credentials files exist
    if not RUSHABH_CREDENTIALS.exists():
        print(f"\n❌ Rushabh's credentials not found at: {RUSHABH_CREDENTIALS}")
        print("   Please ensure rushabh_outh_gmail.json exists and copy it to credentials_rushabh.json")
        return
    
    if not IRA_CREDENTIALS.exists():
        print(f"\n❌ IRA's credentials not found at: {IRA_CREDENTIALS}")
        return
    
    results = {}
    
    # Authenticate Rushabh's account
    results['rushabh'] = authenticate_account(
        RUSHABH_CREDENTIALS, 
        RUSHABH_TOKEN, 
        "Rushabh (rushabh@machinecraft.org)"
    )
    
    # Authenticate IRA's account
    results['ira'] = authenticate_account(
        IRA_CREDENTIALS, 
        IRA_TOKEN, 
        "IRA (ira@machinecraft.org)"
    )
    
    # Summary
    print("\n" + "="*60)
    print("  SETUP SUMMARY")
    print("="*60)
    
    if all(results.values()):
        print("  ✅ Both accounts authenticated successfully!")
        print("\n  You can now run Prometheus:")
        print("    python agents/prometheus/email_test_runner.py --all")
    else:
        print("  ⚠️  Some accounts failed to authenticate:")
        for account, success in results.items():
            status = "✓" if success else "✗"
            print(f"    {status} {account}")


if __name__ == "__main__":
    main()
