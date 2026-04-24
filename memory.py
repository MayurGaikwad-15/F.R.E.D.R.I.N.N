import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path="memory.db"):
        if db_path == "bot_memory.db" or db_path == "memory.db":
            self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory.db')
        else:
            self.db_path = db_path
        # Create persistent connection and ensure .db file exists on disk
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT CHECK(role IN ('user', 'assistant')) NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def save_message(self, user_id: str, role: str, content: str):
        """Insert a new message into the database."""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)',
            (user_id, role, content)
        )
        self.conn.commit()

    def get_chat_history(self, user_id: str, limit: int = 10):
        """
        Retrieves the last N messages for a specific user, ordered chronologically.
        Returns a list of dictionaries in the format {'role': '...', 'content': '...'}.
        """
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        cursor.execute(
            'SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?',
            (user_id, limit)
        )
        
        rows = cursor.fetchall()

        # Reverse the rows to return them chronologically (oldest to newest within the limit)
        history = [{'role': row['role'], 'content': row['content']} for row in reversed(rows)]
        return history

    async def compact_history(self, user_id: str, llm_client):
        """
        Checks if the user has more than 15 messages. If so, fetches the oldest 10,
        summarizes them using the LLM, deletes them, and inserts the summary 
        as a system message at the top of the history.
        """
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # Check total message count
        cursor.execute('SELECT COUNT(*) as count FROM messages WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()['count']
        
        if count <= 15:
            return # No need to compact
            
        # Fetch the oldest 10 messages
        cursor.execute(
            'SELECT id, role, content FROM messages WHERE user_id = ? ORDER BY id ASC LIMIT 10',
            (user_id,)
        )
        oldest_messages = cursor.fetchall()
        
        if not oldest_messages:
            return

        # Prepare messages for LLM summarization
        history_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in oldest_messages])
        prompt = (
            f"Summarize the following conversation history concisely. "
            f"Focus on preserving facts, preferences, and the current state of tasks:\n\n{history_text}"
        )

        try:
            # Request summary from LLM
            chat_completion = await llm_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
            )
            summary_text = chat_completion.choices[0].message.content
            
            # Save the new summary and delete the old messages
            cursor = self.conn.cursor()
            
            # Get the IDs of the messages to delete
            ids_to_delete = [msg['id'] for msg in oldest_messages]
            
            # Delete the old messages
            placeholders = ','.join('?' * len(ids_to_delete))
            cursor.execute(f'DELETE FROM messages WHERE id IN ({placeholders})', ids_to_delete)
            
            cursor.execute(
                'INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)',
                (user_id, "assistant", f"[COMPACTED MEMORY]: {summary_text}")
            )
            
            # Re-order: summary first, then remaining
            cursor.execute('SELECT role, content FROM messages WHERE user_id = ? ORDER BY id ASC', (user_id,))
            all_current = cursor.fetchall()
            
            summary_msg = all_current[-1]
            remaining_msgs = all_current[:-1]
            
            # Delete everything for this user
            cursor.execute('DELETE FROM messages WHERE user_id = ?', (user_id,))
            
            # Re-insert summary first
            cursor.execute(
                'INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)',
                (user_id, summary_msg['role'], summary_msg['content'])
            )
            
            # Re-insert the rest
            for r_msg in remaining_msgs:
                cursor.execute(
                    'INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)',
                    (user_id, r_msg['role'], r_msg['content'])
                )
            
            self.conn.commit()
                
        except Exception as e:
            print(f"Error during memory compaction: {e}")
