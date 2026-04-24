# ─────────────────────────────────────────────────────────────
# Dockerfile — Secure Sandbox for F.R.E.D.R.I.N.N. Bot Demo
# ─────────────────────────────────────────────────────────────
# This creates an isolated container with:
#   - Python 3.12 runtime
#   - Three pre-generated dummy text files in /app/demo_files/
#   - The F.R.E.D.R.I.N.N. bot source code mounted from host
#
# Usage:
#   docker build -t fredrinn-demo .
#   docker compose up
# ─────────────────────────────────────────────────────────────

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for Playwright & other libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir discord.py

# ─── Generate Demo Files ─────────────────────────────────────
# These dummy files simulate a real system environment for safe
# read/write demonstrations during presentations.

RUN mkdir -p /app/demo_files

# File 1: Fake server logs
RUN echo "[2026-04-20 08:00:01] INFO  Server started on port 8080" > /app/demo_files/system_log.txt \
    && echo "[2026-04-20 08:00:02] INFO  Database connection pool initialized (max=10)" >> /app/demo_files/system_log.txt \
    && echo "[2026-04-20 08:01:15] WARN  High memory usage detected: 78% of 16GB" >> /app/demo_files/system_log.txt \
    && echo "[2026-04-20 08:05:33] INFO  Scheduled backup completed: memory.db (2.4 MB)" >> /app/demo_files/system_log.txt \
    && echo "[2026-04-20 08:10:00] INFO  Email polling routine heartbeat — 0 new messages" >> /app/demo_files/system_log.txt \
    && echo "[2026-04-20 08:15:22] ERROR Connection to Gmail API timed out (retry 1/3)" >> /app/demo_files/system_log.txt \
    && echo "[2026-04-20 08:15:25] INFO  Gmail API reconnected successfully" >> /app/demo_files/system_log.txt \
    && echo "[2026-04-20 08:30:00] INFO  Proactive check-in sent to Discord user" >> /app/demo_files/system_log.txt

# File 2: Placeholder user notes
RUN echo "=== F.R.E.D.R.I.N.N. User Notes ===" > /app/demo_files/user_notes.txt \
    && echo "" >> /app/demo_files/user_notes.txt \
    && echo "TODO: Finish calendar integration testing" >> /app/demo_files/user_notes.txt \
    && echo "TODO: Add rate limit retry logic for Groq API" >> /app/demo_files/user_notes.txt \
    && echo "TODO: Test food ordering with edge cases (empty order, unknown items)" >> /app/demo_files/user_notes.txt \
    && echo "" >> /app/demo_files/user_notes.txt \
    && echo "MEETING NOTES (April 18):" >> /app/demo_files/user_notes.txt \
    && echo "- Discussed LinkedIn OAuth scope requirements" >> /app/demo_files/user_notes.txt \
    && echo "- Decided to use discord.py v2 for button interactions" >> /app/demo_files/user_notes.txt \
    && echo "- Next sprint: implement multi-user support" >> /app/demo_files/user_notes.txt \
    && echo "" >> /app/demo_files/user_notes.txt \
    && echo "IDEA: Add voice commands via Whisper API" >> /app/demo_files/user_notes.txt

# File 3: Fake configuration file
RUN echo "# ─── F.R.E.D.R.I.N.N. Configuration ───" > /app/demo_files/config.txt \
    && echo "BOT_NAME=F.R.E.D.R.I.N.N." >> /app/demo_files/config.txt \
    && echo "VERSION=2.1.0" >> /app/demo_files/config.txt \
    && echo "LOG_LEVEL=INFO" >> /app/demo_files/config.txt \
    && echo "MAX_CHAT_HISTORY=10" >> /app/demo_files/config.txt \
    && echo "EMAIL_POLL_INTERVAL_SECONDS=60" >> /app/demo_files/config.txt \
    && echo "PROACTIVE_CHECKIN_MINUTES=30" >> /app/demo_files/config.txt \
    && echo "WORKSPACE_DIR=/app/demo_files" >> /app/demo_files/config.txt \
    && echo "DANGEROUS_TOOLS=send_email,delete_email,write_local_file,delete_calendar_event,post_to_linkedin" >> /app/demo_files/config.txt \
    && echo "LLM_MODEL=llama-3.1-8b-instant" >> /app/demo_files/config.txt \
    && echo "LLM_FALLBACK_MODEL=llama-3.3-70b-versatile" >> /app/demo_files/config.txt \
    && echo "FOOD_DELIVERY_ENABLED=true" >> /app/demo_files/config.txt \
    && echo "MAX_TOOL_LOOPS=10" >> /app/demo_files/config.txt

# Copy application source
COPY . .

# Set the workspace directory to our safe sandbox
ENV WORKSPACE_DIR=/app/demo_files

# Entry point
CMD ["python", "discord_main.py"]
