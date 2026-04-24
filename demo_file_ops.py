"""
demo_file_ops.py — Live Presentation Demo Script
=================================================
Demonstrates F.R.E.D.R.I.N.N.'s safe file read/write capabilities
inside a Docker sandbox. Import this into your bot or run standalone.

Usage in your bot:
    from demo_file_ops import setup_demo_commands
    setup_demo_commands(bot)

Then in Discord:
    /demo_read system_log.txt
    /demo_read user_notes.txt
    /demo_write user_notes.txt "New note added by F.R.E.D.R.I.N.N. bot!"
    /demo_list
"""

import os
import discord
from discord.ext import commands
from datetime import datetime

# The sandbox directory (set via WORKSPACE_DIR env var or default)
DEMO_DIR = os.environ.get("WORKSPACE_DIR", "./demo_files")


def setup_demo_commands(bot: commands.Bot):
    """Register all demo commands on the bot."""

    @bot.command(name="demo_list")
    async def demo_list(ctx):
        """📂 List all files in the demo sandbox."""
        try:
            files = os.listdir(DEMO_DIR)
            if not files:
                await ctx.send("📂 Demo directory is empty.")
                return

            # Build a rich embed showing all files with sizes
            embed = discord.Embed(
                title="📂 Sandbox Files",
                description=f"Directory: `{DEMO_DIR}`",
                color=0x3498DB,
                timestamp=datetime.now()
            )
            for f in sorted(files):
                full_path = os.path.join(DEMO_DIR, f)
                if os.path.isfile(full_path):
                    size = os.path.getsize(full_path)
                    size_str = f"{size} bytes" if size < 1024 else f"{size/1024:.1f} KB"
                    embed.add_field(
                        name=f"📄 {f}",
                        value=f"Size: {size_str}",
                        inline=True
                    )
            embed.set_footer(text="Use /demo_read <filename> to view contents")
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error listing files: `{e}`")

    @bot.command(name="demo_read")
    async def demo_read(ctx, filename: str = None):
        """
        📖 Read a file from the demo sandbox and display its contents.
        
        Example: /demo_read system_log.txt
        """
        if not filename:
            await ctx.send("❌ Please specify a filename. Example: `/demo_read system_log.txt`")
            return

        file_path = os.path.join(DEMO_DIR, filename)

        # ── Safety check: prevent directory traversal attacks ──
        # Resolve the absolute path and ensure it's within DEMO_DIR
        abs_path = os.path.abspath(file_path)
        abs_demo = os.path.abspath(DEMO_DIR)
        if not abs_path.startswith(abs_demo):
            await ctx.send("🚫 **Access Denied!** Path traversal detected. Files are sandboxed.")
            return

        if not os.path.exists(file_path):
            await ctx.send(f"❌ File `{filename}` not found in sandbox.")
            return

        try:
            # Read the file contents
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Build a pretty embed with the file contents
            embed = discord.Embed(
                title=f"📖 Reading: {filename}",
                color=0x2ECC71,
                timestamp=datetime.now()
            )

            # Discord embed field values are limited to 1024 chars
            if len(content) <= 1024:
                embed.add_field(name="Contents", value=f"```\n{content}\n```", inline=False)
            else:
                # Split into chunks for long files
                embed.description = f"```\n{content[:1900]}\n```"
                if len(content) > 1900:
                    embed.set_footer(text=f"(Showing first 1900 of {len(content)} characters)")

            embed.set_footer(text=f"📁 {abs_path} | {len(content)} chars")
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error reading `{filename}`: `{e}`")

    @bot.command(name="demo_write")
    async def demo_write(ctx, filename: str = None, *, text: str = None):
        """
        ✏️ Append a line to a file in the demo sandbox.
        
        Example: /demo_write user_notes.txt Remember to test calendar sync
        """
        if not filename or not text:
            await ctx.send(
                "❌ Usage: `/demo_write <filename> <text to append>`\n"
                "Example: `/demo_write user_notes.txt Buy groceries tomorrow`"
            )
            return

        file_path = os.path.join(DEMO_DIR, filename)

        # ── Safety check: sandbox enforcement ──
        abs_path = os.path.abspath(file_path)
        abs_demo = os.path.abspath(DEMO_DIR)
        if not abs_path.startswith(abs_demo):
            await ctx.send("🚫 **Access Denied!** Path traversal detected. Files are sandboxed.")
            return

        try:
            # Add a timestamp to the appended line
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line_to_add = f"[{timestamp}] {text}\n"

            # Append to the file (creates it if it doesn't exist)
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(line_to_add)

            # Confirm to the user with a nice embed
            embed = discord.Embed(
                title=f"✅ Written to: {filename}",
                color=0xF39C12,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="📝 Line Added",
                value=f"```\n{line_to_add.strip()}\n```",
                inline=False
            )
            embed.add_field(
                name="📁 File Path",
                value=f"`{abs_path}`",
                inline=False
            )
            embed.set_footer(text="Use /demo_read to verify the changes")
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error writing to `{filename}`: `{e}`")


# ─── Standalone test (run directly to verify files exist) ─────────
if __name__ == "__main__":
    print(f"Demo directory: {os.path.abspath(DEMO_DIR)}")
    if os.path.exists(DEMO_DIR):
        for f in os.listdir(DEMO_DIR):
            full = os.path.join(DEMO_DIR, f)
            print(f"  📄 {f} ({os.path.getsize(full)} bytes)")
    else:
        print("  ⚠️  Demo directory does not exist. Run via Docker to create it.")
