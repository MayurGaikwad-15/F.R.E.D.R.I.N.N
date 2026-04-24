import os
import logging
import asyncio
import json
import re
import traceback
import groq
from typing import Any, Optional
from dotenv import load_dotenv

import discord
from discord.ext import tasks, commands
from discord.ui import Button, View

from groq import AsyncGroq
from memory import DatabaseManager
from skills.system_ops import TOOL_SCHEMAS, WORKSPACE_DIR
from tool_router import select_tools
from executor import execute_tool, DANGEROUS_TOOLS

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

client_groq = AsyncGroq(api_key=groq_api_key)

discord_user_id = os.getenv("DISCORD_USER_ID")

# --- HITL Button View ---
class ApprovalView(View):
    def __init__(self, user_id, pending_data, bot):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.pending_data = pending_data
        self.bot = bot

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success)
    async def approve_button(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot approve this.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.edit_original_response(content=f"✅ Approved! Executing {self.pending_data['tool_name']}...", view=None)
        await handle_approval_decision(interaction, "approve", self.user_id, self.pending_data, self.bot)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger)
    async def deny_button(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("You cannot deny this.", ephemeral=True)
            return

        await interaction.response.defer()
        await handle_approval_decision(interaction, "deny", self.user_id, self.pending_data, self.bot)


async def handle_approval_decision(interaction: discord.Interaction, decision: str, user_id: str, pending: dict, bot: commands.Bot):
    tool_name = pending["tool_name"]
    tool_args = pending["tool_args"]
    tool_call_id = pending["tool_call_id"]
    messages_payload = pending["messages_payload"]
    
    if decision == "approve":
        logger.info(f"HITL: User {user_id} APPROVED tool '{tool_name}'.")
        tool_result_string = await execute_tool(tool_name, tool_args)
    else:
        logger.info(f"HITL: User {user_id} DENIED tool '{tool_name}'.")
        if tool_name == "send_email":
            from skills.mail_ops import draft_email
            draft_result = draft_email(tool_args.get('to_email', ''), tool_args.get('subject', ''), tool_args.get('body', ''))
            await interaction.edit_original_response(content=f"❌ Email NOT sent. Saved to Drafts instead! ✉️", view=None)
            tool_result_string = "User denied permission to send the email. It has been saved to the Drafts folder instead."
        else:
            await interaction.edit_original_response(content=f"❌ Denied. {tool_name} will not be executed.", view=None)
            tool_result_string = "User denied permission to run this tool."

    logger.info(f"HITL Tool {tool_name} result: {tool_result_string}")

    messages_payload.append({
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": tool_result_string,
    })

    try:
        followup_tools = select_tools(tool_name)
        chat_completion = await client_groq.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
            tools=followup_tools,
            tool_choice="auto"
        )
        final_response = chat_completion.choices[0].message.content
        if final_response:
            db.save_message(user_id, "assistant", final_response)
            await bot.send_long_message(interaction.channel, final_response)
        else:
            await bot.send_long_message(interaction.channel, "Done!")
    except Exception as e:
        logger.error(f"Error: {e}")


# --- F.R.E.D.R.I.N.N. Bot Subclass ---
class FredrinnBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        self.proactive_routine.start()
        self.auto_email_summarizer_routine.start()
        # You could also add morning brief and followup checks here just like main.py
        
    async def send_long_message(self, channel, text):
        """Helper to send messages longer than 2000 chars."""
        if len(text) <= 2000:
            await channel.send(text)
        else:
            for i in range(0, len(text), 1990):
                await channel.send(text[i:i+1990])
                
    async def get_user_channel(self):
        if not discord_user_id:
            return None
        user = self.get_user(int(discord_user_id))
        if not user:
            try:
                user = await self.fetch_user(int(discord_user_id))
            except Exception:
                return None
        return user

    @tasks.loop(minutes=120)
    async def proactive_routine(self):
        if not discord_user_id:
            return
            
        logger.info("Running proactive routine heartbeat...")
        try:
            chat_history = db.get_chat_history(discord_user_id, limit=10)
            if not chat_history:
                return

            proactive_addendum = (
                "\n\nYou are waking up proactively. Review our recent chat history. "
                "Generate a short, unprompted message to the user. You could offer a quick morning summary, "
                "a reminder based on past chats, or an interesting thought. Keep it brief. "
                "Do not act like I just asked you a question. "
                "Just type your response as normal text."
            )
            messages_payload = [{"role": "system", "content": system_prompt_text + proactive_addendum}]
            messages_payload.extend(chat_history)
            
            # Don't send tools for proactive routine — just let it talk to save tokens
            chat_completion = await client_groq.chat.completions.create(
                messages=messages_payload,
                model="llama-3.1-8b-instant"
            )
            response_message = chat_completion.choices[0].message
            bot_response = response_message.content
            
            # Simple fallback handling - only using content for proactive text
            if bot_response:
                user_channel = await self.get_user_channel()
                if user_channel:
                    db.save_message(discord_user_id, "assistant", bot_response)
                    await self.send_long_message(user_channel, bot_response)
                    logger.info("Proactive message sent to user.")
                    
        except Exception as e:
            logger.error(f"Error in proactive routine: {e}")

    @tasks.loop(seconds=60)
    async def auto_email_summarizer_routine(self):
        """Automatically polls Gmail for unread emails and pushes them."""
        if not discord_user_id:
            return
            
        try:
            from skills.mail_ops import get_gmail_service
            from summarizer import summarize_email
            
            service = get_gmail_service()
            results = service.users().messages().list(userId='me', q="is:unread", maxResults=5).execute()
            messages = results.get('messages', [])
            if not messages:
                return
                
            PROCESSED_EMAILS_FILE = os.path.join(WORKSPACE_DIR, 'processed_emails.json')
            
            def load_processed_emails():
                if os.path.exists(PROCESSED_EMAILS_FILE):
                    try:
                        with open(PROCESSED_EMAILS_FILE, 'r') as f: return json.load(f)
                    except Exception: return []
                return []
                
            processed = load_processed_emails()
            new_emails = [m for m in messages if m['id'] not in processed]
            if not new_emails:
                return
                
            msg = new_emails[0]
            msg_id = msg['id']
            summary_text = await asyncio.to_thread(summarize_email, msg_id) if not asyncio.iscoroutinefunction(summarize_email) else await summarize_email(msg_id)
            
            processed.append(msg_id)
            if len(processed) > 500: processed = processed[-500:]
            with open(PROCESSED_EMAILS_FILE, 'w') as f: json.dump(processed, f)
            
            if "ERROR:" not in summary_text and summary_text:
                header = "📩 **New Email Alert!**\n\n"
                safe_summary = re.sub(r'http[s]?://\S+', '[LINK REMOVED FOR ANTI-SPAM]', str(summary_text))
                alert_text = header + safe_summary
                
                user_channel = await self.get_user_channel()
                if user_channel:
                    await asyncio.sleep(3)
                    await self.send_long_message(user_channel, alert_text)
                    db.save_message(discord_user_id, "assistant", alert_text)
                    
        except Exception as e:
            logger.error(f"Error in auto summarizer: {e}")

bot = FredrinnBot()

from demo_file_ops import setup_demo_commands
setup_demo_commands(bot)

@bot.event
async def on_ready():
    logger.info(f"Discord Bot {bot.user} has connected to Discord!")

@bot.command(name="getfile")
async def getfile_cmd(ctx, *, filename: str = None):
    """Fetch a file by name — just type the filename, no path needed."""
    if not discord_user_id or str(ctx.author.id) != discord_user_id:
        return
        
    if not filename:
        await ctx.send("Usage: `/getfile <filename>`\nExample: `/getfile config.txt`")
        return

    # Auto-search for the file in common directories
    filename = filename.strip().strip('"').strip("'")
    search_dirs = [
        os.path.join(os.path.dirname(__file__), "demo_files"),
        WORKSPACE_DIR,
        os.path.dirname(__file__),  # project root
    ]
    
    found_path = None
    # First check if it's already a valid path
    if os.path.isfile(filename):
        found_path = filename
    else:
        # Search each directory for the filename
        for search_dir in search_dirs:
            candidate = os.path.join(search_dir, filename)
            if os.path.isfile(candidate):
                found_path = candidate
                break
            # Also search subdirectories one level deep
            if os.path.isdir(search_dir):
                for sub in os.listdir(search_dir):
                    sub_path = os.path.join(search_dir, sub, filename)
                    if os.path.isfile(sub_path):
                        found_path = sub_path
                        break
    
    if not found_path:
        # List available files to help the user
        available = []
        for search_dir in search_dirs:
            if os.path.isdir(search_dir):
                for f in os.listdir(search_dir):
                    if os.path.isfile(os.path.join(search_dir, f)):
                        available.append(f)
        available = sorted(set(available))
        file_list = "\n".join(f"• `{f}`" for f in available[:15])
        await ctx.send(f"❌ File `{filename}` not found.\n\n📂 **Available files:**\n{file_list}")
        return
        
    from file_sender import send_file_to_user
    await send_file_to_user(ctx.channel, found_path, f"📥 Here is `{os.path.basename(found_path)}`!")

@bot.command(name="linkedinpost")
async def linkedinpost_cmd(ctx, *, content=None):
    """Directly posts to LinkedIn, bypassing the LLM to avoid token limits."""
    if not discord_user_id or str(ctx.author.id) != discord_user_id:
        return

    if not content:
        await ctx.send("Usage: `/linkedinpost [your text here]`")
        return

    # Show HITL approval buttons — skip the LLM entirely since we know the exact tool
    approval_text = (
        f"🚨 **I want to POST to LinkedIn!**\n\n"
        f"**Content:**\n{content}\n\n"
        f"Do you approve?"
    )
    
    # Create a special view that calls post_to_linkedin directly
    class LinkedInApprovalView(View):
        def __init__(self):
            super().__init__(timeout=None)
            
        @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success)
        async def approve(self, interaction: discord.Interaction, button: Button):
            if str(interaction.user.id) != discord_user_id:
                await interaction.response.send_message("Unauthorized.", ephemeral=True)
                return
            await interaction.response.edit_message(content="✅ Approved! Posting to LinkedIn...", view=None)
            from skills.linkedin_ops import post_to_linkedin
            result = post_to_linkedin(content)
            await interaction.channel.send(result)
            
        @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger)
        async def deny(self, interaction: discord.Interaction, button: Button):
            if str(interaction.user.id) != discord_user_id:
                await interaction.response.send_message("Unauthorized.", ephemeral=True)
                return
            await interaction.response.edit_message(content="❌ LinkedIn post cancelled.", view=None)
    
    await ctx.send(approval_text, view=LinkedInApprovalView())


# Track processed message IDs to prevent duplicate processing on reconnect
_processed_msg_ids = set()
_MAX_TRACKED_IDS = 200

@bot.event
async def on_message(message: discord.Message):
    # Ignore bot's own messages
    if message.author.bot:
        return
    
    # Auth check
    if not discord_user_id or str(message.author.id) != discord_user_id:
        return

    # ─── DEDUPLICATION: skip if we already handled this message ───
    if message.id in _processed_msg_ids:
        return
    _processed_msg_ids.add(message.id)
    if len(_processed_msg_ids) > _MAX_TRACKED_IDS:
        # Remove oldest entries
        excess = len(_processed_msg_ids) - _MAX_TRACKED_IDS
        for _ in range(excess):
            _processed_msg_ids.pop()

    # Process explicit /commands
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    # ─── FILE INTENT DETECTION (runs BEFORE food to prevent false matches) ───
    msg_lower = message.content.lower().strip()
    try:
        file_handled = await _handle_file_intent(message, msg_lower)
        if file_handled:
            return
    except Exception as e:
        logger.error(f"Error in file intent handler: {e}")

    # ─── FOOD INTENT DETECTION (handled directly, no LLM needed) ───
    try:
        food_handled = await _handle_food_intent(message, msg_lower)
        if food_handled:
            return
    except Exception as e:
        logger.error(f"Error in food intent handler: {e}")

    # Handle document uploads
    if message.attachments:
        await message.channel.send(f"📁 Received `{message.attachments[0].filename}`. Downloading...")
        file_path = os.path.join(WORKSPACE_DIR, f"upload_{message.attachments[0].filename}")
        await message.attachments[0].save(fp=file_path)
        
        prompt = (
            f"I have uploaded a file named '{message.attachments[0].filename}'. I saved it locally to this exact path: `{file_path}`.\n"
            f"CRITICAL SYSTEM INSTRUCTION: You MUST invoke the `summarize_local_file` tool to process this.\n"
            f"You MUST include the JSON argument `\"filepath\": \"{file_path}\"` precisely. Do not output empty arguments!"
        )
        await process_llm_chain(message, custom_text=prompt)
        return

    await process_llm_chain(message)


async def _handle_file_intent(message: discord.Message, msg_lower: str) -> bool:
    """
    Detects natural language file requests like:
      - 'get me the config file'
      - 'I want the course file'
      - 'grab me team_contacts.csv'
      - 'send me the system log'
      - 'fetch the meeting schedule'
    
    Searches demo_files/ and workspace for matching files and sends them.
    Returns True if handled, False to pass through to other handlers.
    """
    # Keywords that indicate a file request
    file_trigger_words = ["file", "document", "doc", "fetch", "grab", "download", "attachment"]
    action_phrases = [
        "get me", "give me", "send me", "fetch me", "grab me", "bring me",
        "i want the", "i need the", "can i get the", "show me the",
        "i want", "i need", "get the", "fetch the", "grab the",
        "download", "send the"
    ]
    
    # Check if this looks like a file request (must have a file-related word)
    has_file_word = any(word in msg_lower for word in file_trigger_words)
    has_action = any(phrase in msg_lower for phrase in action_phrases)
    
    # Also check if message contains an actual filename with extension
    has_extension = bool(re.search(r'\b\w+\.\w{2,4}\b', msg_lower))
    
    # Must have EITHER (file word + action phrase) OR an actual filename
    if not (has_file_word and has_action) and not has_extension:
        return False
    
    # Build the list of available files
    search_dirs = [
        os.path.join(os.path.dirname(__file__), "demo_files"),
        WORKSPACE_DIR,
    ]
    
    available_files = {}  # filename -> full_path
    for search_dir in search_dirs:
        if os.path.isdir(search_dir):
            for f in os.listdir(search_dir):
                full_path = os.path.join(search_dir, f)
                if os.path.isfile(full_path):
                    available_files[f.lower()] = full_path
    
    if not available_files:
        return False
    
    # Try to find which file the user wants
    found_path = None
    found_name = None
    
    # Method 1: Direct filename match (e.g., "config.txt", "team_contacts.csv")
    for fname, fpath in available_files.items():
        if fname in msg_lower:
            found_path = fpath
            found_name = fname
            break
    
    # Method 2: Filename without extension (e.g., "config", "team_contacts")
    if not found_path:
        for fname, fpath in available_files.items():
            name_no_ext = os.path.splitext(fname)[0].lower()
            if name_no_ext in msg_lower:
                found_path = fpath
                found_name = fname
                break
    
    # Method 3: Fuzzy — match words from the filename (e.g., "system log" → "system_log.txt")
    if not found_path:
        msg_words = set(re.findall(r'[a-z]+', msg_lower))
        # Remove common stop words
        stop_words = {"the", "a", "an", "me", "my", "i", "want", "get", "give", "send",
                      "fetch", "grab", "bring", "can", "file", "files", "from", "of",
                      "please", "need", "show", "demo", "course", "document", "doc"}
        content_words = msg_words - stop_words
        
        best_match = None
        best_score = 0
        for fname, fpath in available_files.items():
            file_words = set(re.findall(r'[a-z]+', os.path.splitext(fname)[0].lower()))
            overlap = len(content_words & file_words)
            if overlap > best_score:
                best_score = overlap
                best_match = (fname, fpath)
        
        if best_match and best_score > 0:
            found_path = best_match[1]
            found_name = best_match[0]
    
    # If we found a file, send it
    if found_path:
        from file_sender import send_file_to_user
        await send_file_to_user(message.channel, found_path, f"📥 Here is `{found_name}`!")
        return True
    
    # If we detected file intent but couldn't find the file, show available files
    if has_file_word:
        file_list = "\n".join(f"• `{f}`" for f in sorted(available_files.keys()))
        await message.channel.send(
            f"🔍 I understood you want a file, but I couldn't find a match.\n\n"
            f"📂 **Available files:**\n{file_list}\n\n"
            f"💡 Try: *\"get me the config file\"* or *\"grab team_contacts.csv\"*"
        )
        return True
    
    return False


async def _handle_food_intent(message: discord.Message, msg_lower: str) -> bool:
    """Returns True if the message was handled as a food intent (no LLM needed)."""
    from skills.food_ops import MENU_DATABASE, delivery_api, parse_order
    import discord as _discord
    from discord.ui import View as _View, Button as _Button

    # ── Menu display ──
    menu_phrases = ["menu", "show me the menu", "what can i order", "food menu", "show menu",
                    "what's on the menu", "food options", "what food"]
    if any(msg_lower == p or msg_lower == p.strip() for p in menu_phrases):
        menu = delivery_api.get_menu()
        embed = _discord.Embed(
            title="🍽️ F.R.E.D.R.I.N.N. Food Menu",
            description="Here's what's available! Use `/order [items]` to place an order.",
            color=0xFF6B35,
        )
        for category, items in menu.items():
            lines = [f"`{name}` — ₹{price}" for name, price in items.items()]
            embed.add_field(name=category, value="\n".join(lines), inline=False)
        embed.set_footer(text="💡 Example: /order one chicken biryani and two cokes")
        await message.channel.send(embed=embed)
        return True

    # ── Order detection ──
    order_phrases = ["order ", "i want to order ", "get me ", "i'd like ", "bring me ",
                     "i would like ", "i'll have ", "can i get ", "please get ",
                     "i want ", "give me "]

    is_order = False
    order_text = msg_lower
    for p in order_phrases:
        if msg_lower.startswith(p):
            order_text = msg_lower[len(p):].strip()
            is_order = True
            break

    # Also match if the message contains a known menu item name
    if not is_order:
        all_items = [name.lower() for items in MENU_DATABASE.values() for name in items]
        if any(item in msg_lower for item in all_items):
            is_order = True
            order_text = msg_lower

    if not is_order or not order_text:
        return False

    # Parse the order
    result = parse_order(order_text)
    if not result["success"]:
        error_msg = "❌ Could not find any matching items on the menu."
        if result["errors"]:
            error_msg += "\n" + "\n".join(f"• {e}" for e in result["errors"])
        error_msg += "\n\nUse `/menu` to see available items."
        await message.channel.send(error_msg)
        return True

    items = result["items"]
    subtotal = sum(i["price"] * i["qty"] for i in items)
    tax = round(subtotal * 0.05)
    delivery_fee = 30
    total = subtotal + tax + delivery_fee

    embed = _discord.Embed(
        title="🛒 Order Confirmation",
        description="Please review your order before confirming:",
        color=0xFFA500,
    )
    order_lines = [f"**{i['qty']}x** {i['item']} — ₹{i['price']} each = ₹{i['price']*i['qty']}" for i in items]
    embed.add_field(name="📋 Items", value="\n".join(order_lines), inline=False)
    cost_breakdown = f"Subtotal: ₹{subtotal}\nGST (5%): ₹{tax}\nDelivery: ₹{delivery_fee}\n**Total: ₹{total}**"
    embed.add_field(name="💰 Cost", value=cost_breakdown, inline=False)

    if result["errors"]:
        embed.add_field(name="⚠️ Not Found", value="\n".join(f"• {e}" for e in result["errors"]), inline=False)

    class _OrderView(_View):
        def __init__(self):
            super().__init__(timeout=120)

        @_discord.ui.button(label="✅ Confirm Order", style=_discord.ButtonStyle.success)
        async def confirm(self, interaction: _discord.Interaction, button: _Button):
            if str(interaction.user.id) != discord_user_id:
                await interaction.response.send_message("Unauthorized.", ephemeral=True)
                return
            await interaction.response.edit_message(content="⏳ Processing your order...", embed=None, view=None)
            receipt = await delivery_api.process_order(items)
            if receipt["success"]:
                r_embed = _discord.Embed(title="✅ Order Placed Successfully!", color=0x2ECC71)
                r_lines = [f"**{i['qty']}x** {i['item']}" for i in receipt["items"]]
                r_embed.add_field(name="📋 Items", value="\n".join(r_lines), inline=False)
                r_embed.add_field(name="🆔 Order ID", value=f"`{receipt['order_id']}`", inline=True)
                r_embed.add_field(name="💰 Total", value=f"₹{receipt['total']}", inline=True)
                r_embed.add_field(name="🕐 ETA", value=f"{receipt['eta_minutes']} minutes", inline=True)
                r_embed.set_footer(text=f"Ordered at {receipt['timestamp']}")
                await interaction.channel.send(embed=r_embed)
            else:
                await interaction.channel.send(f"❌ Order failed: {receipt.get('error', 'Unknown error')}")

        @_discord.ui.button(label="❌ Cancel", style=_discord.ButtonStyle.danger)
        async def cancel(self, interaction: _discord.Interaction, button: _Button):
            if str(interaction.user.id) != discord_user_id:
                await interaction.response.send_message("Unauthorized.", ephemeral=True)
                return
            await interaction.response.edit_message(content="❌ Order cancelled.", embed=None, view=None)

    await message.channel.send(embed=embed, view=_OrderView())
    return True


async def send_reminder_job(bot, channel_id, data):
    channel = bot.get_channel(channel_id)
    if not channel:
        user = await bot.fetch_user(channel_id)
        if user: await user.send(data)
    else:
        await channel.send(data)


async def process_llm_chain(message: discord.Message, custom_text: Optional[str] = None):
    # This is equivalent to handle_message in Telegram
    user_text = custom_text if custom_text else message.content
    user_id = str(message.author.id)
    
    logger.info(f"Received message: {user_text} from user {user_id}")
    db.save_message(user_id, "user", user_text)
    asyncio.create_task(db.compact_history(user_id, client_groq))
    
    try:
        chat_history = db.get_chat_history(user_id, limit=10)
        messages_payload = [{"role": "system", "content": system_prompt_text}]
        messages_payload.extend(chat_history)
        
        selected_tools = select_tools(user_text)
        max_tool_loops = 10
        
        for _ in range(max_tool_loops):
            try:
                chat_completion = await client_groq.chat.completions.create(
                    messages=messages_payload,
                    model="llama-3.1-8b-instant",
                    tools=selected_tools,
                    tool_choice="auto"
                )
                response_message = chat_completion.choices[0].message
            except groq.BadRequestError as e:
                err_dict = e.response.json()
                failed_gen = err_dict.get('error', {}).get('failed_generation', '')
                if not failed_gen: raise e
                
                class MockMessage:
                    def __init__(self, content):
                        self.content = content; self.tool_calls = None; self.role = "assistant"
                response_message = MockMessage(content=failed_gen)
                
            if not response_message.tool_calls and response_message.content:
                func_match = re.search(r"<function=(\w+)", response_message.content)
                json_match = re.search(r"(\{.*?\})", response_message.content, re.DOTALL)
                
                if func_match:
                    from groq.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
                    func_name = func_match.group(1)
                    func_args = json_match.group(1).strip() if json_match else "{}"
                    response_message.tool_calls = [ChatCompletionMessageToolCall(id=f"call_{func_name}", function=Function(name=func_name, arguments=func_args), type="function")]
                    
            if response_message.tool_calls:
                messages_payload.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": [{"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in response_message.tool_calls]
                })
                
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except:
                        tool_args = {}
                        
                    if tool_name in DANGEROUS_TOOLS:
                        pending_data = {
                            "tool_name": tool_name,
                            "tool_args": tool_args,
                            "tool_call_id": tool_call.id,
                            "messages_payload": messages_payload,
                        }
                        if tool_name == "send_email":
                            app_text = f"🚨 **I want to SEND an email!**\n\n**To:** {tool_args.get('to_email')}\n**Subject:** {tool_args.get('subject')}\n\n**Body:**\n{tool_args.get('body')}\n\nDo you approve?"
                        else:
                            app_text = f"🚨 I want to execute the tool **{tool_name}** with arguments:\n`{json.dumps(tool_args, indent=2)}`\n\nDo you approve?"
                            
                        view = ApprovalView(user_id, pending_data, bot)
                        await message.channel.send(app_text, view=view)
                        return # wait for view callback
                        
                    if tool_name == "schedule_reminder":
                        # simplified for discord - just use asyncio
                        seconds = int(tool_args.get("seconds", 0))
                        asyncio.get_event_loop().call_later(seconds, lambda: asyncio.create_task(send_reminder_job(bot, message.channel.id, f"⏰ Reminder: {tool_args.get('reminder_text')}")))
                        tool_result_string = "Rule saved"
                    else:
                        tool_result_string = await execute_tool(tool_name, tool_args)
                        
                    if tool_name.startswith("summarize_"):
                        if tool_result_string:
                            db.save_message(user_id, "assistant", tool_result_string)
                            await bot.send_long_message(message.channel, tool_result_string)
                        return
                        
                    messages_payload.append({
                        "role": "tool", "tool_call_id": tool_call.id, "name": tool_name, "content": tool_result_string
                    })
                continue
            else:
                bot_response = response_message.content
                if bot_response:
                    # Filter out hallucinated tool call syntax that the LLM sometimes outputs as text
                    hallucination_patterns = [
                        r'<function=\w+>',  r'</function>',
                        r'\(send_email>', r'\(schedule_reminder>',
                        r'\(place_food_order>', r'\(add_item_to_order>',
                        r'\(check_order>', r'\{["\']to_email["\']',
                    ]
                    is_hallucination = any(re.search(p, bot_response) for p in hallucination_patterns)
                    if is_hallucination:
                        logger.warning(f"Suppressed hallucinated tool call text: {bot_response[:100]}...")
                        break
                    db.save_message(user_id, "assistant", bot_response)
                    await bot.send_long_message(message.channel, bot_response)
                break
        else:
            await message.channel.send("I am struggling to process this request right now. Please try again.")

    except Exception as e:
        logger.error(traceback.format_exc())
        await message.channel.send("Sorry, I encountered an error while processing your request.")

if __name__ == '__main__':
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if not discord_token:
        logger.error("DISCORD_BOT_TOKEN not found in .env!")
    else:
        bot.run(discord_token)
