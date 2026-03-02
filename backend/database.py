import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "model_forge.db"

def init_db():
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create deployments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deployments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        container_id TEXT NOT NULL,
        internal_id TEXT UNIQUE NOT NULL,
        model_name TEXT NOT NULL,
        framework TEXT NOT NULL,
        task TEXT NOT NULL,
        host_port INTEGER,
        url TEXT,
        status TEXT DEFAULT 'running',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def add_deployment(
    container_id: str,
    internal_id: str,
    model_name: str,
    framework: str,
    task: str,
    host_port: int,
    url: str
):
    """Save a new deployment record to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO deployments (container_id, internal_id, model_name, framework, task, host_port, url)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (container_id, internal_id, model_name, framework, task, host_port, url))
    
    conn.commit()
    conn.close()

def get_all_deployments() -> List[Dict[str, Any]]:
    """Fetch all deployment records from the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM deployments ORDER BY created_at DESC')
    rows = cursor.fetchall()
    
    result = [dict(row) for row in rows]
    conn.close()
    return result

def remove_deployment(container_id: str):
    """Remove a deployment record by container ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM deployments WHERE container_id = ?', (container_id,))
    
    conn.commit()
    conn.close()

def remove_all_deployments():
    """Remove all deployment records from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM deployments')
    
    conn.commit()
    conn.close()

def update_status(container_id: str, status: str):
    """Update the status of a deployment."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE deployments SET status = ? WHERE container_id = ?', (status, container_id))
    
    conn.commit()
    conn.close()


# ── User functions ──────────────────────────────────────────

def add_user(username: str, password_hash: str) -> int:
    """Add a new user. Returns the user ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO users (username, password_hash) VALUES (?, ?)',
        (username, password_hash)
    )
    user_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return user_id


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Fetch a user by username. Returns None if not found."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None
