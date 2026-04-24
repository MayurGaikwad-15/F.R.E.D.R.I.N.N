import os
import logging
import asyncio
import json
import asyncio
import re
import traceback
import groq  # type: ignore
from typing import Any, Optional
from dotenv import load_dotenv  # type: ignore
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup  # type: ignore
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler  # type: ignore
from groq import AsyncGroq
from memory import DatabaseManager
from skills.system_ops import TOOL_SCHEMAS
from tool_router import select_tools
from executor import execute_tool, DANGEROUS_TOOLS
from skills.system_ops import WORKSPACE_DIR

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Initialize memory database
db = DatabaseManager()

# Load SOUL.md system prompt
def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "SOUL.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        logger.error(f"Could not find SOUL.md at {prompt_path}")
        return "You are a helpful assistant."

system_prompt_text = load_system_prompt()

# Initialize Groq client
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    logger.error("GROQ_API_KEY is not set in the .env file.")

client = AsyncGroq(api_key=groq_api_key)

telegram_user_id = os.getenv("TELEGRAM_USER_ID")

# Store pending dangerous tool calls awaiting user approval
# Key: user_id, Value: dict with tool call state
pending_approvals: dict[str, Any] = {}

async def send_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """Async callback for the PTB JobQueue to send a delayed reminder."""
    job = context.job
    await context.bot.send_message(chat_id=job.chat_id, text=job.data)

async def morning_brief_routine(context: ContextTypes.DEFAULT_TYPE):
    """Daily morning brief: inbox digest + calendar context + conflict check."""
    if not telegram_user_id:
        return
    
    logger.info("Running morning brief routine...")
    try:
        from skills.inbox_engine import get_daily_brief
        from skills.calendar_ops import get_day_context, resolve_conflicts
        
        brief = get_daily_brief(50)
        cal_context = get_day_context()
        conflicts = resolve_conflicts(1)
        
        morning_report = (
            "☀️ **Good Morning! Here's your daily briefing:**\n\n"
            f"{brief}\n\n"
            f"{cal_context}\n\n"
            f"{conflicts}"
        )
        
        # Truncate if too long for Telegram
        if len(morning_report) > 4000:
            morning_report = str(morning_report)[:3997] + "..."  # type: ignore
        
        await context.bot.send_message(chat_id=telegram_user_id, text=morning_report)
        db.save_message(telegram_user_id, "assistant", morning_report)
        logger.info("Morning brief sent.")
    except Exception as e:
        logger.error(f"Error in morning brief routine: {e}")

async def followup_check_routine(context: ContextTypes.DEFAULT_TYPE):
    """Periodic check for unanswered emails that need follow-ups."""
    if not telegram_user_id:
        return
    
    logger.info("Running follow-up check routine...")
    try:
        from skills.inbox_engine import check_followups
        
        result = check_followups(3)
        
        # Only notify if there are actual follow-ups needed
        if "Follow-Up Required" in result:
            await context.bot.send_message(chat_id=telegram_user_id, text=result)
            db.save_message(telegram_user_id, "assistant", result)
            logger.info("Follow-up notification sent.")
    except Exception as e:
        logger.error(f"Error in follow-up check routine: {e}")

# Maintain a small file to track which emails we have already automatically summarized
PROCESSED_EMAILS_FILE = os.path.join(WORKSPACE_DIR, "processed_emails.json")

def load_processed_emails():
    if os.path.exists(PROCESSED_EMAILS_FILE):
        try:
            with open(PROCESSED_EMAILS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_processed_emails(msg_ids):
    with open(PROCESSED_EMAILS_FILE, 'w') as f:
        json.dump(msg_ids, f)

async def auto_email_summarizer_routine(context: ContextTypes.DEFAULT_TYPE):
    """Automatically polls Gmail for unread emails every few minutes and pushes them to the user."""
    if not telegram_user_id:
        return
    
    try:
        from skills.mail_ops import get_gmail_service  # type: ignore
        from summarizer import summarize_email  # type: ignore
        
        service = get_gmail_service()
        # Fetch up to 5 unread messages
        results = service.users().messages().list(userId='me', q="is:unread", maxResults=5).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return
            
        processed = load_processed_emails()
        new_emails = [m for m in messages if m['id'] not in processed]
        
        # Only process ONE email per 5-second tick to completely avoid API burst throttling!
        # The next scheduled tick will naturally process the next email in the queue.
        msg = new_emails[0]
        msg_id = msg['id']
        logger.info(f"New automated email detected {msg_id}! Summarizing...")
        
        # Call the LLM summarizer we built
        summary_text = await asyncio.to_thread(summarize_email, msg_id) if not asyncio.iscoroutinefunction(summarize_email) else await summarize_email(msg_id)
        
        # ALWAYS Save first so an unexpected Telegram crash doesn't infinite-loop our API tokens
        processed.append(msg_id)
        if len(processed) > 500:
            processed = processed[-500:]
        save_processed_emails(processed)
        
        if "ERROR:" not in summary_text and summary_text:
            header = "📩 **New Email Alert!**\n\n"
            
            # Anti-spam measure: Strip out actual http/https links from automated summaries
            import re
            safe_summary = re.sub(r'http[s]?://\S+', '[LINK REMOVED FOR ANTI-SPAM]', str(summary_text))
            
            alert_text = str(header) + safe_summary
            
            # Add artificial delay to avoid Telegram ping limit
            await asyncio.sleep(3.0)
            await context.bot.send_message(chat_id=telegram_user_id, text=alert_text, parse_mode="Markdown")
            db.save_message(telegram_user_id, "assistant", alert_text)
            
    except Exception as e:
        logger.error(f"Error in auto_email_summarizer_routine: {e}")


async def proactive_routine(context: ContextTypes.DEFAULT_TYPE):
    if not telegram_user_id:
        logger.error("TELEGRAM_USER_ID is not set in the .env file. Skipping proactive routine.")
        return

    logger.info("Running proactive routine heartbeat...")

    try:
        chat_history = db.get_chat_history(telegram_user_id, limit=10)

        proactive_addendum = (
            "\n\nYou are waking up proactively. Review our recent chat history. "
            "Generate a short, unprompted message to the user. You could offer a quick morning summary, "
            "a reminder based on past chats, or an interesting thought. Keep it brief. "
            "Do not act like I just asked you a question. "
            "Just type your response as normal text."
        )
        messages_payload = [
            {"role": "system", "content": system_prompt_text + proactive_addendum}
        ]
        messages_payload.extend(chat_history)

        # Use core tools only for proactive routine
        proactive_tools = select_tools("proactive check inbox calendar")
        max_tool_loops = 10
        for _ in range(max_tool_loops):
            chat_completion = await client.chat.completions.create(
                messages=messages_payload,
                model="llama-3.1-8b-instant",
                tools=proactive_tools,
                tool_choice="auto"
            )

            response_message = chat_completion.choices[0].message

            if response_message.tool_calls:
                # The LLM used a tool natively — execute it and loop
                messages_payload.append(response_message)
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}
                        logger.error(f"Failed to parse arguments for tool {tool_name}: {tool_call.function.arguments}")

                    logger.info(f"Proactive LLM called tool: {tool_name} with args: {tool_args}")

                    if tool_name == "schedule_reminder":
                        try:
                            seconds = int(tool_args.get("seconds", 0))
                            reminder_text = tool_args.get("reminder_text", "")
                            if seconds > 0 and reminder_text and context.job_queue:
                                context.job_queue.run_once(
                                    send_reminder_job,
                                    when=seconds,
                                    chat_id=telegram_user_id,
                                    data=f"⏰ Reminder: {reminder_text}"
                                )
                                tool_result_string = f"Successfully scheduled reminder for {seconds} seconds from now."
                            else:
                                tool_result_string = "Error: Invalid arguments or job queue not available."
                        except Exception as e:
                            tool_result_string = f"Error scheduling reminder: {e}"
                    else:
                        tool_result_string = await execute_tool(tool_name, tool_args)

                    logger.info(f"Proactive Tool {tool_name} returned: {tool_result_string}")

                    messages_payload.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result_string,
                    })
                continue  # Loop to let the LLM read the tool result

            else:
                # No tools called — the LLM is just talking
                bot_response = response_message.content
                if bot_response:
                    db.save_message(telegram_user_id, "assistant", bot_response)
                    await context.bot.send_message(chat_id=telegram_user_id, text=bot_response)
                    logger.info(f"Proactive message sent to user {telegram_user_id}.")
                break  # Exit the loop

        else:
            logger.warning(f"Hit maximum tool iterations ({max_tool_loops}) during proactive routine.")

    except Exception as e:
        logger.error(f"Error communicating with Groq API during proactive routine: {e}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles file uploads from the user."""
    user_id = str(update.message.from_user.id)
    document = update.message.document
    
    if not document:
        return
        
    logger.info(f"Received document from user {user_id}: {document.file_name}")
    await update.message.reply_text(f"📁 Received `{document.file_name}`. Downloading...")
    
    try:
        # Get the file from Telegram servers
        file = await context.bot.get_file(document.file_id)
        
        # Save to the workspace directory
        safe_filename = "".join([c for c in document.file_name if c.isalpha() or c.isdigit() or c in ' ._-']).rstrip()
        file_path = os.path.join(WORKSPACE_DIR, f"upload_{safe_filename}")
        
        await file.download_to_drive(file_path)
        
        # Inject a message into the LLM flow simulating the user asking to process it
        prompt = (
            f"I have uploaded a file named '{document.file_name}'. I saved it locally to this exact path: `{file_path}`.\n"
            f"CRITICAL SYSTEM INSTRUCTION: You MUST invoke the `summarize_local_file` tool to process this.\n"
            f"You MUST include the JSON argument `\"filepath\": \"{file_path}\"` precisely. Do not output empty arguments!"
        )
        
        # Pass the constructed prompt to the main handle logic without mutating the readonly update object
        await handle_message(update, context, custom_text=prompt)
        
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await update.message.reply_text(f"❌ Error downloading file: {str(e)}")


async def handle_linkedinpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explicitly handles the /linkedinpost command."""
    user_id = str(update.message.from_user.id)
    text = update.message.text
    
    # Extract the post content
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: `/linkedinpost [your text here]`", parse_mode="Markdown")
        return
        
    post_content = parts[1]
    logger.info(f"Received explicit /linkedinpost command from {user_id}")
    
    # We map this directly into the LLM flow by prompting it to use the tool
    prompt = (
        f"The user has explicitly asked to post the following text to LinkedIn:\n\n"
        f'"{post_content}"\n\n'
        f"CRITICAL SYSTEM INSTRUCTION: You MUST invoke the `post_to_linkedin` tool to process this.\n"
        f"You MUST include the JSON argument `\"text\": \"{post_content}\"` precisely."
    )
    
    # Pass the constructed prompt to the main handle logic without mutating the readonly update object
    await handle_message(update, context, custom_text=prompt)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, custom_text: Optional[str] = None):
    user_text = custom_text if custom_text else update.message.text
    user_id = str(update.message.from_user.id)
    
    logger.info(f"Received message: {user_text} from user {user_id}")

    # Save user message to database
    db.save_message(user_id, "user", user_text)

    # Trigger memory compaction asynchronously in the background
    asyncio.create_task(db.compact_history(user_id, client))

    try:
        # Retrieve last 10 messages from history
        chat_history = db.get_chat_history(user_id, limit=10)

        # Construct the initial payload
        messages_payload = [
            {"role": "system", "content": system_prompt_text}
        ]
        messages_payload.extend(chat_history)
        
        # Smart tool selection based on user intent
        selected_tools = select_tools(user_text)
        logger.info(f"Selected {len(selected_tools)} tools for this request.")
        
        # Tool execution loop
        max_tool_loops = 10
        for _ in range(max_tool_loops):
            try:
                chat_completion = await client.chat.completions.create(
                    messages=messages_payload,
                    model="llama-3.1-8b-instant",
                    tools=selected_tools,
                    tool_choice="auto"
                )
                response_message = chat_completion.choices[0].message
            except groq.BadRequestError as e:
                err_dict = e.response.json()
                failed_gen = err_dict.get('error', {}).get('failed_generation', '')
                if not failed_gen:
                    raise e
                
                logger.warning(f"Groq API blocked hallucinated tool call: {failed_gen}")
                
                class MockMessage:
                    def __init__(self, content):
                        self.content = content
                        self.tool_calls = None
                        self.role = "assistant"
                
                response_message = MockMessage(content=failed_gen)
            
            # --- Fallback to catch Groq XML-style hallucinations ---
            if not response_message.tool_calls and response_message.content:
                # Robust regex to extract function name and JSON regardless of hallucinated bracket placements
                func_match = re.search(r"<function=(\w+)", response_message.content)
                json_match = re.search(r"(\{.*?\})", response_message.content, re.DOTALL)
                
                if func_match:
                    logger.warning(f"Caught XML tool call hallucination: {response_message.content}")
                    from groq.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
                    func_name = func_match.group(1)
                    func_args = json_match.group(1).strip() if json_match else "{}"
                    
                    # Create a mock tool call object
                    mock_tool_call = ChatCompletionMessageToolCall(
                        id=f"call_{func_name}",
                        function=Function(name=func_name, arguments=func_args),
                        type="function"
                    )
                    response_message.tool_calls = [mock_tool_call]
            
            if response_message.tool_calls:
                # The LLM used a tool natively — execute it and loop
                # Convert the object to a standard dict to prevent JSON serialization crashes
                messages_payload.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": [
                        {
                            "id": t.id,
                            "type": "function",
                            "function": {
                                "name": t.function.name,
                                "arguments": t.function.arguments
                            }
                        } for t in response_message.tool_calls
                    ]
                })
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}
                        logger.error(f"Failed to parse arguments for tool {tool_name}: {tool_call.function.arguments}")

                    logger.info(f"LLM called tool: {tool_name} with args: {tool_args}")
                    
                    # --- HITL CHECK: Pause for dangerous tools ---
                    if tool_name in DANGEROUS_TOOLS:
                        logger.info(f"HITL: Tool '{tool_name}' requires user approval. Pausing.")
                        pending_approvals[user_id] = {
                            "tool_name": tool_name,
                            "tool_args": tool_args,
                            "tool_call_id": tool_call.id,
                            "messages_payload": messages_payload,
                        }
                        keyboard = [
                            [
                                InlineKeyboardButton("✅ Approve", callback_data="approve"),
                                InlineKeyboardButton("❌ Deny", callback_data="deny"),
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        # Custom message for send_email
                        if tool_name == "send_email":
                            approval_text = (
                                f"🚨 **I want to SEND an email!**\n\n"
                                f"**To:** {tool_args.get('to_email')}\n"
                                f"**Subject:** {tool_args.get('subject')}\n\n"
                                f"**Body:**\n{tool_args.get('body')}\n\n"
                                f"Do you approve?"
                            )
                        else:
                            approval_text = (
                                f"🚨 I want to execute the tool **{tool_name}** with arguments:\n"
                                f"`{json.dumps(tool_args, indent=2)}`\n\n"
                                f"Do you approve?"
                            )

                        await update.message.reply_text(
                            approval_text,
                            reply_markup=reply_markup,
                            parse_mode="Markdown",
                        )
                        return  # Stop processing; wait for callback

                    if tool_name == "schedule_reminder":
                        try:
                            seconds = int(tool_args.get("seconds", 0))
                            reminder_text = tool_args.get("reminder_text", "")
                            if seconds > 0 and reminder_text and context.job_queue:
                                context.job_queue.run_once(
                                    send_reminder_job,
                                    when=seconds,
                                    chat_id=user_id,
                                    data=f"⏰ Reminder: {reminder_text}"
                                )
                                tool_result_string = f"Successfully scheduled reminder for {seconds} seconds from now."
                            else:
                                tool_result_string = "Error: Invalid arguments or job queue not available."
                        except Exception as e:
                            tool_result_string = f"Error scheduling reminder: {e}"
                    else:
                        tool_result_string = await execute_tool(tool_name, tool_args)
                    
                    logger.info(f"Tool {tool_name} returned: {tool_result_string}")
                    
                    # --- SHORTCUT FOR SUMMARIZER TOOLS ---
                    # The summarizer already formats perfect markdown output. 
                    # Returning it directly prevents the 70B model from infinite looping
                    # and saves us from hitting heavy Groq rate limits.
                    if tool_name.startswith("summarize_"):
                        if tool_result_string:
                            db.save_message(user_id, "assistant", tool_result_string)
                            await update.message.reply_text(tool_result_string, parse_mode="Markdown")
                        return  # Completely exit the handler!

                    messages_payload.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result_string,
                    })
                continue  # Loop to let the LLM read the tool result

            else:
                # No tools called — the LLM is just talking to the user
                bot_response = response_message.content
                if bot_response:
                    db.save_message(user_id, "assistant", bot_response)
                    await update.message.reply_text(bot_response)
                break  # Exit the loop

        else:
            # If we exit the loop, we hit the max iterations — failsafe break
            logger.warning(f"Hit maximum tool iterations ({max_tool_loops}) for user {user_id}.")
            await update.message.reply_text("I am struggling to process this request right now. Please try again in a moment.")

    except Exception as e:
        logger.error(f"Error communicating with Groq API: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("Sorry, I encountered an error while processing your request.")

async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles Approve/Deny button presses for dangerous tool calls."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press
    
    user_id = str(query.from_user.id)
    decision = query.data  # "approve" or "deny"
    
    pending = pending_approvals.pop(user_id, None)
    if not pending:
        await query.edit_message_text("⚠️ No pending action found. It may have expired.")
        return
    
    tool_name = pending["tool_name"]
    tool_args = pending["tool_args"]
    tool_call_id = pending["tool_call_id"]
    messages_payload = pending["messages_payload"]
    
    if decision == "approve":
        logger.info(f"HITL: User {user_id} APPROVED tool '{tool_name}'.")
        await query.edit_message_text(f"✅ Approved! Executing {tool_name}...")
        tool_result_string = await execute_tool(tool_name, tool_args)
    else:
        logger.info(f"HITL: User {user_id} DENIED tool '{tool_name}'.")
        # If denied send_email, fallback to saving as draft
        if tool_name == "send_email":
            from skills.mail_ops import draft_email
            draft_result = draft_email(
                tool_args.get('to_email', ''),
                tool_args.get('subject', ''),
                tool_args.get('body', '')
            )
            logger.info(f"HITL: Denied send_email, saved as draft: {draft_result}")
            await query.edit_message_text(f"❌ Email NOT sent. Saved to Drafts instead! ✉️")
            tool_result_string = "User denied permission to send the email. It has been saved to the Drafts folder instead."
        else:
            await query.edit_message_text(f"❌ Denied. {tool_name} will not be executed.")
            tool_result_string = "User denied permission to run this tool."
    
    logger.info(f"HITL Tool {tool_name} result: {tool_result_string}")
    
    # Append the tool result and make the follow-up LLM call
    messages_payload.append({
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": tool_result_string,
    })
    
    try:
        # Use minimal tools for the follow-up response
        followup_tools = select_tools(tool_name)
        chat_completion = await client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
            tools=followup_tools,
            tool_choice="auto"
        )
        
        final_response = chat_completion.choices[0].message.content
        
        if final_response:
            db.save_message(user_id, "assistant", final_response)
            await context.bot.send_message(chat_id=user_id, text=final_response)
        else:
            await context.bot.send_message(chat_id=user_id, text="Done!")
    except Exception as e:
        logger.error(f"Error during HITL follow-up LLM call: {e}")
        await context.bot.send_message(chat_id=user_id, text="Sorry, I encountered an error after processing the tool.")

def main():
    # Load token from .env
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set in the .env file.")
        return

    # Initialize the application with longer timeouts
    application = (
        ApplicationBuilder()
        .token(token)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )
    
    # Add message handlers
    application.add_handler(CommandHandler("linkedinpost", handle_linkedinpost))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Add HITL callback handler for approve/deny buttons
    application.add_handler(CallbackQueryHandler(handle_approval_callback))
    
    # Add proactive job routines
    if application.job_queue:
        # General proactive check every 30 minutes
        application.job_queue.run_repeating(proactive_routine, interval=1800, first=10)
        
        # Morning brief daily at 8:00 AM (calculate seconds until next 8 AM)
        from datetime import datetime, timedelta
        now = datetime.now()
        next_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now >= next_8am:
            next_8am += timedelta(days=1)
        seconds_until_8am = (next_8am - now).total_seconds()
        application.job_queue.run_repeating(
            morning_brief_routine, interval=86400, first=seconds_until_8am
        )
        logger.info(f"Morning brief scheduled in {seconds_until_8am:.0f} seconds.")
        
        # Follow-up check every 6 hours
        application.job_queue.run_repeating(followup_check_routine, interval=21600, first=300)
        
        # Continuously monitor unread inbox every 60 seconds (Anti-spam rate limit)
        application.job_queue.run_repeating(auto_email_summarizer_routine, interval=60, first=30)
    else:
        logger.warning("Job queue is not initialized. Proactive routines will not run.")

    logger.info("Bot started")
    
    # Run the bot until you press Ctrl-C
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
