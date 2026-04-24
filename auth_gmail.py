"""
One-time script to generate token.json for Gmail API access.
Run this locally (not in Docker) to authenticate via browser.
"""
import os
import sys

# Add the project root to path so we can import mail_ops
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skills.mail_ops import get_gmail_service

print("Starting Gmail OAuth authentication flow...")
print("A browser window will open. Sign in with the Google account you want to connect.")
print()

try:
    service = get_gmail_service()
    print("[OK] Authentication successful! token.json has been generated.")
    
    # Quick test: check if we can reach the inbox
    results = service.users().messages().list(userId='me', labelIds=['UNREAD'], maxResults=1).execute()
    count = results.get('resultSizeEstimate', 0)
    print(f"[MAIL] Connection verified. You have approximately {count} unread email(s).")
except Exception as e:
    print(f"[ERROR] {e}")
