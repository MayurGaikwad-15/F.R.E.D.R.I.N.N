"""
file_sender.py — Smart File Transfer Module for F.R.E.D.R.I.N.N. Bot
=====================================================================
Handles sending files to Discord users with automatic Google Drive fallback.

Logic:
  - Files < 25MB  → Direct Discord upload (discord.File)
  - Files >= 25MB → Upload to Google Drive → Share link in chat

Requirements:
  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

Setup:
  1. Go to Google Cloud Console → APIs & Services → Credentials
  2. Create OAuth 2.0 Client ID (Desktop App)
  3. Enable "Google Drive API" in the API Library
  4. Download the JSON → rename to credentials.json → place in project root
  5. First run will open a browser for OAuth consent → generates drive_token.json
"""

import os
import discord
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ─── Constants ───────────────────────────────────────────────────────
DISCORD_FILE_LIMIT = 25 * 1024 * 1024  # 25 MB in bytes (free tier limit)
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']  # Only manage files created by this app
DRIVE_TOKEN_FILE = 'drive_token.json'       # Saved OAuth token (auto-generated)
DRIVE_CREDENTIALS_FILE = 'credentials.json'  # OAuth client secret from Google Cloud Console
DRIVE_UPLOAD_FOLDER_ID = None  # Set this to a specific Drive folder ID, or None for root


# ─── Google Drive Authentication ─────────────────────────────────────
def _get_drive_service():
    """
    Authenticate with Google Drive API using OAuth 2.0.
    
    First run: Opens a browser window for user consent.
    Subsequent runs: Uses cached token from drive_token.json.
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated Drive API service object.
    
    Raises:
        FileNotFoundError: If credentials.json is missing.
    """
    creds = None

    # Step 1: Try loading existing token
    if os.path.exists(DRIVE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(DRIVE_TOKEN_FILE, DRIVE_SCOPES)

    # Step 2: If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token expired but refresh token is available — refresh silently
            creds.refresh(Request())
        else:
            # No token at all — need full OAuth flow
            if not os.path.exists(DRIVE_CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"'{DRIVE_CREDENTIALS_FILE}' not found! "
                    "Download it from Google Cloud Console → APIs & Services → Credentials → "
                    "OAuth 2.0 Client IDs → Download JSON."
                )
            flow = InstalledAppFlow.from_client_secrets_file(DRIVE_CREDENTIALS_FILE, DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)  # Opens browser for consent

        # Step 3: Save the token for future runs
        with open(DRIVE_TOKEN_FILE, 'w') as token_file:
            token_file.write(creds.to_json())

    # Step 4: Build and return the Drive API service
    return build('drive', 'v3', credentials=creds)


# ─── Google Drive Upload ─────────────────────────────────────────────
def _upload_to_drive(file_path: str) -> str:
    """
    Upload a file to Google Drive and return a shareable link.
    
    The file is uploaded to the configured folder (or Drive root),
    then permissions are set to "anyone with the link can view".
    
    Args:
        file_path: Absolute or relative path to the local file.
    
    Returns:
        str: Shareable Google Drive link (https://drive.google.com/file/d/...)
    
    Raises:
        FileNotFoundError: If the local file doesn't exist.
        Exception: If Drive API call fails.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    service = _get_drive_service()
    file_name = os.path.basename(file_path)

    # Step 1: Prepare file metadata
    file_metadata = {'name': file_name}
    if DRIVE_UPLOAD_FOLDER_ID:
        # Upload into a specific folder if configured
        file_metadata['parents'] = [DRIVE_UPLOAD_FOLDER_ID]

    # Step 2: Upload the file with resumable upload (handles large files gracefully)
    media = MediaFileUpload(
        file_path,
        resumable=True  # Supports large files with automatic chunking
    )
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'  # We only need the ID — we'll build the link ourselves
    ).execute()

    file_id = uploaded_file.get('id')

    # Step 3: Set permissions — "Anyone with the link can view"
    # This MUST happen before sharing the link
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }
    service.permissions().create(
        fileId=file_id,
        body=permission
    ).execute()

    # Step 4: Build proper shareable links manually
    # The webViewLink from API uses ?usp=drivesdk which often doesn't work externally
    view_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    download_link = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    return view_link, download_link


# ─── Main Public Function ────────────────────────────────────────────
async def send_file_to_user(
    channel: discord.abc.Messageable,
    file_path: str,
    message: Optional[str] = None
) -> bool:
    """
    Smart file sender — automatically chooses the best method.
    
    - Files < 25MB: Sent directly via Discord's file upload.
    - Files >= 25MB: Uploaded to Google Drive, link shared in chat.
    
    Args:
        channel: Discord channel or DM to send the file to.
                 Any discord.abc.Messageable (TextChannel, DMChannel, etc.)
        file_path: Path to the local file to send.
        message: Optional text message to accompany the file.
    
    Returns:
        bool: True if file was sent successfully, False otherwise.
    
    Usage in your bot:
        from file_sender import send_file_to_user
        
        @bot.command(name="getfile")
        async def get_file(ctx, filepath: str):
            await send_file_to_user(ctx.channel, filepath, "Here's your file!")
    """
    # ── Validate file exists ──
    if not os.path.exists(file_path):
        await channel.send(f"❌ **File not found:** `{file_path}`")
        return False

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    file_size_mb = round(file_size / (1024 * 1024), 2)

    try:
        # ── Route A: Small file → Direct Discord upload ──
        if file_size < DISCORD_FILE_LIMIT:
            upload_msg = message or f"📁 Here's your file: `{file_name}` ({file_size_mb} MB)"
            await channel.send(
                content=upload_msg,
                file=discord.File(file_path, filename=file_name)
            )
            return True

        # ── Route B: Large file → Google Drive upload ──
        else:
            # Notify user that upload is in progress (large files take time)
            progress_msg = await channel.send(
                f"📤 `{file_name}` is {file_size_mb} MB (exceeds Discord's 25 MB limit).\n"
                f"⏳ Uploading to Google Drive..."
            )

            # Upload to Drive and get shareable links
            view_link, download_link = _upload_to_drive(file_path)

            # Edit the progress message with the final links
            await progress_msg.edit(
                content=(
                    f"📁 **File:** `{file_name}` ({file_size_mb} MB)\n"
                    f"☁️ **Uploaded to Google Drive** (too large for Discord)\n\n"
                    f"👁️ **View:** {view_link}\n"
                    f"⬇️ **Direct Download:** {download_link}"
                    + (f"\n\n💬 {message}" if message else "")
                )
            )
            return True

    except FileNotFoundError as e:
        await channel.send(f"❌ **Error:** {str(e)}")
        return False
    except Exception as e:
        await channel.send(
            f"❌ **Failed to send file** `{file_name}`:\n```\n{str(e)}\n```"
        )
        return False
