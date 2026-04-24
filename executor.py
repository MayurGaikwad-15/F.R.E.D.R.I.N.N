from skills.system_ops import get_current_time, read_local_file, write_local_file
from skills.browser_ops import maps, click_element, type_text, web_search
from skills.mail_ops import search_emails, send_email, draft_email
from skills.inbox_engine import (
    triage_inbox, get_daily_brief, smart_draft_email,
    check_followups, draft_followup, extract_email_data,
    manage_vip_contacts, label_email, delete_email, archive_email
)
from skills.calendar_ops import (
    list_calendar_events, create_calendar_event, resolve_conflicts,
    get_day_context, block_focus_time, find_free_slots, delete_calendar_event
)
from skills.research_ops import (
    daily_intelligence, summarize_content, deep_dive_research,
    manage_research_topics, manage_bookmarks, crunch_bookmarks
)
from summarizer import (
    summarize_text, summarize_url, summarize_file, summarize_bullet_points, summarize_email
)
from skills.linkedin_ops import post_to_linkedin

# Tools that require explicit user approval before execution
DANGEROUS_TOOLS = ['write_local_file', 'send_email', 'delete_email', 'delete_calendar_event', 'post_to_linkedin']

async def execute_tool(tool_name: str, arguments: dict) -> str:
    """Routes the tool name to the appropriate function and executes it."""
    
    # ─── Original Tools ───
    if tool_name == "web_search":
        query = arguments.get("query")
        if not query:
            return "ERROR: 'query' argument is required for web_search."
        return await web_search(query)

    elif tool_name == "get_current_time":
        try:
            return get_current_time()
        except Exception as e:
            return f"Error executing get_current_time: {str(e)}"
            
    elif tool_name == "read_local_file":
        filepath = arguments.get("filepath")
        if not filepath:
            return "ERROR: 'filepath' argument is required for read_local_file."
        return str(read_local_file(filepath))

    elif tool_name == "write_local_file":
        filepath = arguments.get("filepath")
        content = arguments.get("content")
        if not filepath:
            return "ERROR: 'filepath' argument is required for write_local_file."
        if content is None:
            return "ERROR: 'content' argument is required for write_local_file."
        return str(write_local_file(filepath, content))

    elif tool_name == "maps":
        url = arguments.get("url")
        if not url:
            return "ERROR: 'url' argument is required for maps."
        return await maps(url)

    elif tool_name == "click_element":
        element_id = arguments.get("element_id")
        if element_id is None:
            return "ERROR: 'element_id' argument is required for click_element."
        return await click_element(int(element_id))

    elif tool_name == "type_text":
        element_id = arguments.get("element_id")
        text = arguments.get("text")
        if element_id is None:
            return "ERROR: 'element_id' argument is required for type_text."
        if text is None:
            return "ERROR: 'text' argument is required for type_text."
        return await type_text(int(element_id), text)

    elif tool_name == "search_emails":
        search_query = arguments.get("search_query", "")
        max_results = arguments.get("max_results", 5)
        try:
            return search_emails(search_query, int(max_results))
        except Exception as e:
            return f"Error searching emails: {str(e)}"

    elif tool_name == "send_email":
        to_email = arguments.get("to_email")
        subject = arguments.get("subject")
        body = arguments.get("body")
        if not to_email:
            return "ERROR: 'to_email' argument is required for send_email."
        if not subject:
            return "ERROR: 'subject' argument is required for send_email."
        if not body:
            return "ERROR: 'body' argument is required for send_email."
        try:
            return send_email(to_email, subject, body)
        except Exception as e:
            return f"Error sending email: {str(e)}"

    elif tool_name == "draft_email":
        to_email = arguments.get("to_email")
        subject = arguments.get("subject")
        body = arguments.get("body")
        if not to_email:
            return "ERROR: 'to_email' argument is required for draft_email."
        if not subject:
            return "ERROR: 'subject' argument is required for draft_email."
        if not body:
            return "ERROR: 'body' argument is required for draft_email."
        try:
            return draft_email(to_email, subject, body)
        except Exception as e:
            return f"Error drafting email: {str(e)}"

    # ─── LinkedIn Tools ───
    elif tool_name == "post_to_linkedin":
        text = arguments.get("text")
        if not text:
            return "ERROR: 'text' argument is required for post_to_linkedin."
        try:
            return post_to_linkedin(text)
        except Exception as e:
            return f"Error posting to LinkedIn: {str(e)}"

    # ─── Inbox Engine Tools ───
    elif tool_name == "triage_inbox":
        max_emails = arguments.get("max_emails", 20)
        try:
            return triage_inbox(int(max_emails))
        except Exception as e:
            return f"Error triaging inbox: {str(e)}"

    elif tool_name == "get_daily_brief":
        max_emails = arguments.get("max_emails", 50)
        try:
            return get_daily_brief(int(max_emails))
        except Exception as e:
            return f"Error generating daily brief: {str(e)}"

    elif tool_name == "smart_draft_email":
        to_email = arguments.get("to_email")
        instruction = arguments.get("instruction")
        context = arguments.get("context", "")
        if not to_email:
            return "ERROR: 'to_email' argument is required for smart_draft_email."
        if not instruction:
            return "ERROR: 'instruction' argument is required for smart_draft_email."
        try:
            return smart_draft_email(to_email, instruction, context)
        except Exception as e:
            return f"Error preparing smart draft: {str(e)}"

    elif tool_name == "check_followups":
        days = arguments.get("days_threshold", 3)
        try:
            return check_followups(int(days))
        except Exception as e:
            return f"Error checking follow-ups: {str(e)}"

    elif tool_name == "draft_followup":
        to_email = arguments.get("to_email")
        subject = arguments.get("original_subject")
        snippet = arguments.get("original_snippet", "")
        if not to_email:
            return "ERROR: 'to_email' argument is required for draft_followup."
        if not subject:
            return "ERROR: 'original_subject' argument is required for draft_followup."
        try:
            return draft_followup(to_email, subject, snippet)
        except Exception as e:
            return f"Error drafting follow-up: {str(e)}"

    elif tool_name == "extract_email_data":
        max_emails = arguments.get("max_emails", 10)
        try:
            return extract_email_data(int(max_emails))
        except Exception as e:
            return f"Error extracting email data: {str(e)}"

    elif tool_name == "manage_vip_contacts":
        action = arguments.get("action", "list")
        email_or_name = arguments.get("email_or_name", "")
        try:
            return manage_vip_contacts(action, email_or_name)
        except Exception as e:
            return f"Error managing VIP contacts: {str(e)}"

    elif tool_name == "label_email":
        msg_id = arguments.get("msg_id")
        add_labels = arguments.get("add_labels", [])
        remove_labels = arguments.get("remove_labels", [])
        if not msg_id:
            return "ERROR: 'msg_id' argument is required for label_email."
        try:
            return label_email(msg_id, add_labels, remove_labels)
        except Exception as e:
            return f"Error labeling email: {str(e)}"

    elif tool_name == "delete_email":
        msg_id = arguments.get("msg_id")
        if not msg_id:
            return "ERROR: 'msg_id' argument is required for delete_email."
        try:
            return delete_email(msg_id)
        except Exception as e:
            return f"Error deleting email: {str(e)}"

    elif tool_name == "archive_email":
        msg_id = arguments.get("msg_id")
        if not msg_id:
            return "ERROR: 'msg_id' argument is required for archive_email."
        try:
            return archive_email(msg_id)
        except Exception as e:
            return f"Error archiving email: {str(e)}"

    # ─── Calendar Tools ───
    elif tool_name == "list_calendar_events":
        days_ahead = arguments.get("days_ahead", 7)
        max_results = arguments.get("max_results", 20)
        try:
            return list_calendar_events(int(days_ahead), int(max_results))
        except Exception as e:
            return f"Error listing calendar events: {str(e)}"

    elif tool_name == "create_calendar_event":
        summary = arguments.get("summary")
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        if not summary:
            return "ERROR: 'summary' argument is required for create_calendar_event."
        if not start_time:
            return "ERROR: 'start_time' argument is required for create_calendar_event."
        if not end_time:
            return "ERROR: 'end_time' argument is required for create_calendar_event."
        try:
            return create_calendar_event(
                summary, start_time, end_time,
                description=arguments.get("description", ""),
                location=arguments.get("location", ""),
                attendees=arguments.get("attendees", ""),
                add_meet_link=arguments.get("add_meet_link", False)
            )
        except Exception as e:
            return f"Error creating calendar event: {str(e)}"

    elif tool_name == "resolve_conflicts":
        days_ahead = arguments.get("days_ahead", 7)
        try:
            return resolve_conflicts(int(days_ahead))
        except Exception as e:
            return f"Error resolving conflicts: {str(e)}"

    elif tool_name == "get_day_context":
        try:
            return get_day_context()
        except Exception as e:
            return f"Error getting day context: {str(e)}"

    elif tool_name == "block_focus_time":
        date = arguments.get("date")
        if not date:
            return "ERROR: 'date' argument is required for block_focus_time."
        try:
            return block_focus_time(
                date,
                start_hour=arguments.get("start_hour", 9),
                end_hour=arguments.get("end_hour", 11),
                title=arguments.get("title", "🔒 Deep Work — Do Not Disturb")
            )
        except Exception as e:
            return f"Error blocking focus time: {str(e)}"

    elif tool_name == "find_free_slots":
        date = arguments.get("date")
        if not date:
            return "ERROR: 'date' argument is required for find_free_slots."
        duration = arguments.get("duration_minutes", 30)
        try:
            return find_free_slots(date, int(duration))
        except Exception as e:
            return f"Error finding free slots: {str(e)}"

    elif tool_name == "delete_calendar_event":
        event_id = arguments.get("event_id")
        if not event_id:
            return "ERROR: 'event_id' argument is required for delete_calendar_event."
        try:
            return delete_calendar_event(event_id)
        except Exception as e:
            return f"Error deleting calendar event: {str(e)}"

    # ─── Research & Knowledge Tools ───
    elif tool_name == "daily_intelligence":
        custom_topics = arguments.get("custom_topics", "")
        try:
            return await daily_intelligence(custom_topics)
        except Exception as e:
            return f"Error generating intelligence brief: {str(e)}"

    elif tool_name == "summarize_content":
        url = arguments.get("url")
        if not url:
            return "ERROR: 'url' argument is required for summarize_content."
        try:
            return await summarize_content(url)
        except Exception as e:
            return f"Error summarizing content: {str(e)}"

    elif tool_name == "deep_dive_research":
        query = arguments.get("query")
        if not query:
            return "ERROR: 'query' argument is required for deep_dive_research."
        depth = arguments.get("depth", 3)
        try:
            return await deep_dive_research(query, int(depth))
        except Exception as e:
            return f"Error during deep-dive research: {str(e)}"

    elif tool_name == "manage_research_topics":
        action = arguments.get("action", "list")
        topic = arguments.get("topic", "")
        try:
            return manage_research_topics(action, topic)
        except Exception as e:
            return f"Error managing research topics: {str(e)}"

    elif tool_name == "manage_bookmarks":
        action = arguments.get("action", "list")
        url = arguments.get("url", "")
        title = arguments.get("title", "")
        try:
            return manage_bookmarks(action, url, title)
        except Exception as e:
            return f"Error managing bookmarks: {str(e)}"

    elif tool_name == "crunch_bookmarks":
        try:
            return await crunch_bookmarks()
        except Exception as e:
            return f"Error crunching bookmarks: {str(e)}"

    # ─── Summarizer Module Tools ───
    elif tool_name == "summarize_text":
        text = arguments.get("text")
        if not text:
            return "ERROR: 'text' argument is required for summarize_text."
        max_length = arguments.get("max_length", 200)
        try:
            return summarize_text(text, int(max_length))
        except Exception as e:
            return f"Error summarizing text: {str(e)}"

    elif tool_name == "summarize_url_content":
        url = arguments.get("url")
        if not url:
            return "ERROR: 'url' argument is required for summarize_url_content."
        try:
            return summarize_url(url)
        except Exception as e:
            return f"Error summarizing URL: {str(e)}"

    elif tool_name == "summarize_local_file":
        filepath = arguments.get("filepath")
        if not filepath:
            return "ERROR: 'filepath' argument is required for summarize_local_file."
        try:
            return summarize_file(filepath)
        except Exception as e:
            return f"Error summarizing file: {str(e)}"

    elif tool_name == "summarize_bullet_points":
        text = arguments.get("text")
        if not text:
            return "ERROR: 'text' argument is required for summarize_bullet_points."
        num_points = arguments.get("num_points", 5)
        try:
            return summarize_bullet_points(text, int(num_points))
        except Exception as e:
            return f"Error extracting bullet points: {str(e)}"

    elif tool_name == "summarize_email":
        msg_id = arguments.get("msg_id")
        if not msg_id:
            return "ERROR: 'msg_id' argument is required for summarize_email."
        try:
            return summarize_email(msg_id)
        except Exception as e:
            return f"Error summarizing email: {str(e)}"

    else:
        return f"Error: The tool '{tool_name}' was not found or is not supported."
