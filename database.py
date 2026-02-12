import sqlite3
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self, db_path="saas_results.db"):
        self.db_url = os.getenv("DATABASE_URL")
        self.db_path = db_path
        self.is_memory = db_path == ":memory:"
        self.is_postgres = self.db_url is not None
        self._conn = None
        
        if self.is_memory:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
        elif self.is_postgres:
            # PostgreSQL connection pool would be better, 
            # but for production check we ensure it works.
            pass
        self._init_db()

    def _get_conn(self):
        if self.is_memory:
            return self._conn
        if self.is_postgres:
            return psycopg2.connect(self.db_url)
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # PostgreSQL uses SERIAL for autoincrement
        id_type = "SERIAL PRIMARY KEY" if self.is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        
        # User Accounts
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS users (
                id {id_type},
                email TEXT UNIQUE,
                name TEXT,
                picture TEXT,
                role TEXT DEFAULT 'user', -- 'admin' or 'user'
                credits_total INTEGER DEFAULT 4000,
                credits_used INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Global Verification Logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT,
                status TEXT,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Knowledge base for domains (RAG - Shared)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS domain_knowledge (
                domain TEXT PRIMARY KEY,
                category TEXT,
                details TEXT
            )
        ''')

        # Domain results cache (Shared)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS domain_cache (
                domain TEXT PRIMARY KEY,
                mx_found INTEGER,
                mx_preferred TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        if not self.is_memory: conn.close()

    # User Management
    def get_user_by_email(self, email):
        conn = self._get_conn()
        cursor = conn.cursor()
        placeholder = "%s" if self.is_postgres else "?"
        cursor.execute(f"SELECT * FROM users WHERE email = {placeholder}", (email,))
        row = cursor.fetchone()
        if not self.is_memory: conn.close()
        return row

    def create_or_update_user(self, email, name, picture, role='user'):
        conn = self._get_conn()
        cursor = conn.cursor()
        placeholder = "%s" if self.is_postgres else "?"
        cursor.execute(f'''
            INSERT INTO users (email, name, picture, role)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
            ON CONFLICT(email) DO UPDATE SET
                name=EXCLUDED.name,
                picture=EXCLUDED.picture
        ''', (email, name, picture, role))
        conn.commit()
        if not self.is_memory: conn.close()

    def update_user_credits(self, user_id, count):
        conn = self._get_conn()
        cursor = conn.cursor()
        placeholder = "%s" if self.is_postgres else "?"
        cursor.execute(f"UPDATE users SET credits_used = credits_used + {placeholder} WHERE id = {placeholder}", (count, user_id))
        conn.commit()
        if not self.is_memory: conn.close()

    # Log Management
    def log_verification(self, user_id, email, status, details):
        conn = self._get_conn()
        cursor = conn.cursor()
        placeholder = "%s" if self.is_postgres else "?"
        cursor.execute(f'''
            INSERT INTO verification_logs (user_id, email, status, details)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
        ''', (user_id, email, status, details))
        conn.commit()
        if not self.is_memory: conn.close()

    def get_user_logs(self, user_id, limit=100):
        conn = self._get_conn()
        cursor = conn.cursor()
        placeholder = "%s" if self.is_postgres else "?"
        cursor.execute(f"SELECT email, status, details, timestamp FROM verification_logs WHERE user_id = {placeholder} ORDER BY timestamp DESC LIMIT {placeholder}", (user_id, limit))
        rows = cursor.fetchall()
        if not self.is_memory: conn.close()
        return rows

    def get_all_logs(self, limit=500):
        conn = self._get_conn()
        cursor = conn.cursor()
        placeholder = "%s" if self.is_postgres else "?"
        cursor.execute(f'''
            SELECT u.email as user_email, v.email, v.status, v.details, v.timestamp 
            FROM verification_logs v
            JOIN users u ON v.user_id = u.id
            ORDER BY v.timestamp DESC LIMIT {placeholder}
        ''', (limit,))
        rows = cursor.fetchall()
        if not self.is_memory: conn.close()
        return rows

    # Domain Shared Logic (Previously in database.py)
    def get_domain_info(self, domain):
        conn = self._get_conn()
        cursor = conn.cursor()
        placeholder = "%s" if self.is_postgres else "?"
        cursor.execute(f"SELECT category FROM domain_knowledge WHERE domain = {placeholder}", (domain,))
        res = cursor.fetchone()
        if res: 
            if not self.is_memory: conn.close()
            return res[0]
        
        cursor.execute(f"SELECT mx_found, mx_preferred FROM domain_cache WHERE domain = {placeholder}", (domain,))
        res = cursor.fetchone()
        if not self.is_memory: conn.close()
        return res

    def save_domain_cache(self, domain, mx_found, mx_preferred):
        conn = self._get_conn()
        cursor = conn.cursor()
        if self.is_postgres:
            cursor.execute('''
                INSERT INTO domain_cache (domain, mx_found, mx_preferred)
                VALUES (%s, %s, %s)
                ON CONFLICT (domain) DO UPDATE SET
                    mx_found = EXCLUDED.mx_found,
                    mx_preferred = EXCLUDED.mx_preferred,
                    timestamp = CURRENT_TIMESTAMP
            ''', (domain, int(mx_found), mx_preferred))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO domain_cache (domain, mx_found, mx_preferred)
                VALUES (?, ?, ?)
            ''', (domain, int(mx_found), mx_preferred))
        conn.commit()
        if not self.is_memory: conn.close()

    def add_domain_knowledge(self, domains, category):
        conn = self._get_conn()
        cursor = conn.cursor()
        placeholder = "%s" if self.is_postgres else "?"
        cursor.executemany(f'''
            INSERT INTO domain_knowledge (domain, category)
            VALUES ({placeholder}, {placeholder})
            ON CONFLICT (domain) DO NOTHING
        ''', [(d, category) for d in domains])
        conn.commit()
        if not self.is_memory: conn.close()
