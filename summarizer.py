"""
Summarizer — Standalone, Reusable Text Summarization Module
============================================================
A self-contained module for LLM-powered summarization using the Groq API.
Can be dropped into any Python project. Only requires: groq, httpx, python-dotenv.

Functions:
    summarize_text(text, max_length)        → Summarize raw text
    summarize_url(url)                      → Fetch URL & summarize
    summarize_file(filepath)                → Read local file & summarize
    summarize_bullet_points(text, num_points) → Extract key bullet points
"""

import os
import re
import logging
from dotenv import load_dotenv
import httpx
from groq import Groq
import PyPDF2  # type: ignore

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Groq Client (standalone — loads its own key)
# ─────────────────────────────────────────────
_groq_api_key = os.getenv("GROQ_API_KEY")
if not _groq_api_key:
    logger.warning("GROQ_API_KEY not found in environment. Summarizer will not work.")

_client = Groq(api_key=_groq_api_key) if _groq_api_key else None

_MODEL = os.getenv("SUMMARIZER_MODEL", "llama-3.1-8b-instant")


# ─────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────
def _llm_summarize(prompt: str, system_msg: str = "You are a concise summarization assistant.") -> str:
    """Sends a prompt to Groq and returns the LLM's response text."""
    if not _client:
        return "ERROR: GROQ_API_KEY is not configured. Cannot summarize."

    try:
        response = _client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            model=_MODEL,
            temperature=0.3,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API error during summarization: {e}")
        return f"ERROR: Summarization failed — {str(e)}"


def _fetch_url_text(url: str) -> str:
    """Fetches a URL and returns cleaned plain text (strips HTML)."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        with httpx.Client(follow_redirects=True, timeout=20.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        # Strip scripts, styles, and HTML tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        return str(text)[:10000]  # type: ignore
    except Exception as e:
        return f"ERROR: Could not fetch URL — {str(e)}"


# ─────────────────────────────────────────────
# 1. Summarize Raw Text
# ─────────────────────────────────────────────
def summarize_text(text: str, max_length: int = 200) -> str:
    """
    Summarizes raw text into a concise overview.

    Args:
        text: The text content to summarize.
        max_length: Approximate target word count for the summary (default 200).

    Returns:
        A structured summary with TL;DR, key takeaways, and action items.
    """
    if not text or not text.strip():
        return "ERROR: No text provided to summarize."

    # Truncate very long inputs to fit within LLM context
    truncated = text[:12000]

    prompt = (
        f"Summarize the following text in approximately {max_length} words. "
        "Structure your response as:\n"
        "**TL;DR:** (one sentence)\n"
        "**Key Takeaways:**\n"
        "- point 1\n"
        "- point 2\n"
        "- ...\n"
        "**Action Items:** (if any, otherwise say 'None')\n\n"
        f"--- TEXT ---\n{truncated}"
    )

    return _llm_summarize(prompt)


# ─────────────────────────────────────────────
# 2. Summarize URL Content
# ─────────────────────────────────────────────
def summarize_url(url: str) -> str:
    """
    Fetches a URL (article, blog, page) and returns a structured summary.

    Args:
        url: The URL to fetch and summarize.

    Returns:
        A summary of the page content, or an error message.
    """
    if not url or not url.strip():
        return "ERROR: No URL provided."

    text = _fetch_url_text(url)
    if text.startswith("ERROR"):
        return text

    word_count = len(text.split())
    prompt = (
        f"Summarize this web page content ({word_count} words extracted from {url}).\n"
        "Structure your response as:\n"
        f"**Source:** {url}\n"
        "**TL;DR:** (one sentence)\n"
        "**Key Takeaways:**\n"
        "- point 1\n"
        "- point 2\n"
        "- ...\n"
        "**Notable Quotes/Data:** (if any)\n"
        "**Action Items:** (if any, otherwise say 'None')\n\n"
        f"--- CONTENT ---\n{text}"
    )

    return _llm_summarize(prompt)


# ─────────────────────────────────────────────
# 3. Summarize Local File
# ─────────────────────────────────────────────
def summarize_file(filepath: str) -> str:
    """
    Reads a local file and returns a summary of its contents.

    Supports text-based files: .txt, .md, .py, .json, .csv, .log, .html, etc.

    Args:
        filepath: Path to the file to summarize.

    Returns:
        A summary of the file contents, or an error message.
    """
    if not filepath or not filepath.strip():
        return "ERROR: No filepath provided."

    abs_path = os.path.abspath(filepath)

    if not os.path.exists(abs_path):
        return f"ERROR: File not found — {abs_path}"

    filename = os.path.basename(abs_path)
    ext = os.path.splitext(filename)[1].lower()

    if ext == '.pdf':
        try:
            with open(abs_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                content = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        content = str(content) + str(text) + "\n"
        except Exception as e:
            return f"ERROR: Could not read PDF — {str(e)}"
    else:
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            return f"ERROR: Cannot read binary file — {abs_path}"
        except PermissionError:
            return f"ERROR: Permission denied — {abs_path}"
        except Exception as e:
            return f"ERROR: Could not read file — {str(e)}"

    if not content.strip():
        return "ERROR: File is empty."

    # Truncate for LLM context
    truncated = content[:30000] # Increased context for PDFs
    word_count = len(content.split())

    prompt = (
        f"Summarize this file: **{filename}** ({ext} file, {word_count} words).\n"
        "Structure your response as:\n"
        f"**File:** {filename}\n"
        "**TL;DR:** (one sentence)\n"
        "**Key Takeaways:**\n"
        "- point 1\n"
        "- point 2\n"
        "- ...\n"
        "**Notable Details:** (if any)\n\n"
        f"--- FILE CONTENT ---\n{truncated}"
    )

    return _llm_summarize(prompt)


# ─────────────────────────────────────────────
# 4. Extract Bullet Points
# ─────────────────────────────────────────────
def summarize_bullet_points(text: str, num_points: int = 5) -> str:
    """
    Extracts the most important points from text as a bullet-point list.

    Args:
        text: The text content to extract points from.
        num_points: Number of bullet points to generate (default 5).

    Returns:
        A numbered list of the most important points.
    """
    if not text or not text.strip():
        return "ERROR: No text provided."

    num_points = max(1, min(15, num_points))
    truncated = text[:12000]

    prompt = (
        f"Extract exactly {num_points} key bullet points from the following text. "
        "Each point should be one concise sentence capturing a critical idea. "
        "Format as a numbered list:\n"
        "1. ...\n"
        "2. ...\n\n"
        f"--- TEXT ---\n{truncated}"
    )

    return _llm_summarize(
        prompt,
        system_msg="You are a precise information extraction assistant. Return only the numbered bullet points, nothing else."
    )


# ─────────────────────────────────────────────
# 5. Summarize Email
# ─────────────────────────────────────────────
def summarize_email(msg_id: str) -> str:
    """
    Fetches a specific email from Gmail by ID and summarizes its full content.
    """
    try:
        from skills.mail_ops import get_gmail_service  # type: ignore
        service = get_gmail_service()
        
        msg = service.users().messages().get(
            userId='me', id=msg_id, format='full'
        ).execute()

        headers = msg.get('payload', {}).get('headers', [])
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')

        # Try to get body text
        body = ""
        if 'parts' in msg.get('payload', {}):
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    import base64
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in msg.get('payload', {}) and 'data' in msg['payload']['body']:
             import base64
             body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
             
        if not body:
            body = msg.get('snippet', 'No readable text body found.')

        word_count = len(body.split())
        # Keep body short to stay under 6000 TPM free-tier limit
        truncated = str(body)[:3000]

        prompt = (
            f"Summarize this email briefly.\n"
            f"From: {sender}\nSubject: {subject}\nDate: {date}\n\n"
            "Reply with:\n"
            "**TL;DR:** (1 sentence)\n"
            "**Key Points:** (2-3 bullets)\n"
            "**Action Items:** (or 'None')\n\n"
            f"--- BODY ---\n{truncated}"
        )

        return _llm_summarize(prompt)

    except Exception as e:
        return f"ERROR summarizing email {msg_id}: {str(e)}"
