"""
Tool Router — Intelligent tool selection to stay within token limits.
Categorises all 34 tools into groups and selects relevant subsets
based on user message intent, keeping each API call lean.
"""

import re
from skills.system_ops import TOOL_SCHEMAS

# ─────────────────────────────────────────────
# Tool name → group mapping
# ─────────────────────────────────────────────
TOOL_GROUPS = {
    "core": [
        "web_search", "get_current_time", "read_local_file",
        "write_local_file", "schedule_reminder",
    ],
    "browser": [
        "maps", "click_element", "type_text",
    ],
    "email_basic": [
        "search_emails", "send_email", "draft_email",
    ],
    "inbox_engine": [
        "triage_inbox", "get_daily_brief", "smart_draft_email",
        "check_followups", "draft_followup", "extract_email_data",
        "manage_vip_contacts", "label_email", "delete_email", "archive_email",
    ],
    "calendar": [
        "list_calendar_events", "create_calendar_event", "resolve_conflicts",
        "get_day_context", "block_focus_time", "find_free_slots",
        "delete_calendar_event",
    ],
    "research": [
        "daily_intelligence", "summarize_content", "deep_dive_research",
        "manage_research_topics", "manage_bookmarks", "crunch_bookmarks",
    ],
    "summarizer": [
        "summarize_text", "summarize_url_content",
        "summarize_local_file", "summarize_bullet_points", "summarize_email"
    ],
    "linkedin": [
        "post_to_linkedin"
    ],
}

# Build a reverse lookup: tool_name → schema
_SCHEMA_MAP = {schema["function"]["name"]: schema for schema in TOOL_SCHEMAS}

# ─────────────────────────────────────────────
# Intent detection keywords → groups
# ─────────────────────────────────────────────
INTENT_KEYWORDS = {
    "email_basic": [
        "email", "mail", "send", "compose", "write to", "inbox",
        "unread", "reply", "forward",
    ],
    "inbox_engine": [
        "triage", "clean", "sort", "spam", "brief", "digest", "morning",
        "summary", "follow up", "followup", "follow-up", "who owes",
        "pending", "vip", "extract", "archive", "label", "delete email",
        "smart draft", "tone",
    ],
    "calendar": [
        "calendar", "schedule", "meeting", "event", "book", "appointment",
        "conflict", "double book", "focus time", "deep work", "free slot",
        "when am i free", "block time", "cancel meeting",
    ],
    "research": [
        "research", "summarize", "article", "news", "intelligence",
        "bookmark", "read later", "crunch", "deep dive", "report",
        "topic", "investigate", "analyze",
    ],
    "summarizer": [
        "summarize text", "summarize file", "summary of", "tldr",
        "bullet points", "key points", "condense", "shorten",
        "main ideas", "summarize this",
    ],
    "browser": [
        "browse", "website", "navigate", "click", "page", "url",
        "open site", "go to",
    ],
    "linkedin": [
        "linkedin", "post on linkedin", "publish", "linkedinpost", "share on linkedin"
    ],
}


def select_tools(user_message: str) -> list[dict]:
    """
    Analyse the user's message and return only the relevant tool schemas.
    Always includes core tools. Adds specialised groups based on intent.
    
    Returns at most ~12-15 tools instead of all 34.
    """
    msg_lower = user_message.lower()
    
    # Always include core + basic email (they're small and always useful)
    selected_groups = {"core", "email_basic"}
    
    # Scan for intent keywords
    for group, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in msg_lower:
                selected_groups.add(group)
                break
    
    # If inbox_engine is selected, also include email_basic
    if "inbox_engine" in selected_groups:
        selected_groups.add("email_basic")
    
    # If calendar keywords include scheduling from email extraction
    if "inbox_engine" in selected_groups and "calendar" not in selected_groups:
        # Extract might need calendar tools
        if any(kw in msg_lower for kw in ["extract", "itinerary", "flight"]):
            selected_groups.add("calendar")
    
    # Build the selected tool list
    selected_tools = []
    selected_names = set()
    
    for group in selected_groups:
        tool_names = TOOL_GROUPS.get(group, [])
        for name in tool_names:
            if name not in selected_names and name in _SCHEMA_MAP:
                selected_tools.append(_SCHEMA_MAP[name])
                selected_names.add(name)
    
    return selected_tools


def get_all_tools() -> list[dict]:
    """Returns all tool schemas (for cases where we need them all)."""
    return TOOL_SCHEMAS
