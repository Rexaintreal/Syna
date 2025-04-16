"""
SQLite Database Handler for Spotify Music Matching Application
Author: Rexaintreal

This module handles all database operations for storing user data, music preferences,
and match information. Uses SQLite for local storage.
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any
import time

class Database:
    """
        Database handler for user data and music preferences.
        Uses SQLite for persistent storage.
        
        Note: Database file 'syna.db' is created in the local directory.
    """
    def __init__(self):
        self.db_path = "syna.db"
        self.init_db()
    
    
    def get_connection(self):
        # Set timeout and enable automatic retrying
        for _ in range(3):  # Try 3 times
            try:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=20,  # Increase timeout
                    isolation_level=None  # Enable autocommit mode
                )
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    time.sleep(1)  # Wait before retrying
                    continue
                raise
        raise Exception("Could not connect to database after 3 attempts")

    def init_db(self):
        try:
            conn = self.get_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        spotify_id TEXT PRIMARY KEY,
                        instagram_username TEXT,
                        display_name TEXT,
                        join_date TEXT,
                        top_artists TEXT,     -- Store as JSON
                        top_tracks TEXT,      -- Store as JSON
                        top_genres TEXT,      -- Store as JSON
                        setup_complete BOOLEAN DEFAULT FALSE
                    )
                """)
        finally:
            if conn:
                conn.close()

    def save_user(self, user_data: Dict[str, Any]) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            with conn:
                conn.execute("""
                    INSERT OR REPLACE INTO users (
                        spotify_id, instagram_username, display_name, join_date,
                        top_artists, top_tracks, top_genres, setup_complete
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_data['spotify_id'],
                    user_data.get('instagram_username'),
                    user_data.get('display_name'),
                    user_data.get('join_date', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')),
                    json.dumps(user_data.get('top_artists', [])),
                    json.dumps(user_data.get('top_tracks', [])),
                    json.dumps(user_data.get('top_genres', [])),
                    user_data.get('setup_complete', False)
                ))
                return True
        except Exception as e:
            print(f"Error saving user data: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_user(self, spotify_id: str) -> Dict[str, Any]:
        conn = None
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            with conn:
                cursor = conn.execute(
                    "SELECT * FROM users WHERE spotify_id = ?", 
                    (spotify_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    user_data = dict(row)
                    try:
                        # Convert JSON strings back to lists with error handling
                        user_data['top_artists'] = json.loads(user_data['top_artists'] or '[]')
                        user_data['top_tracks'] = json.loads(user_data['top_tracks'] or '[]')
                        user_data['top_genres'] = json.loads(user_data['top_genres'] or '[]')
                    except json.JSONDecodeError:
                        user_data['top_artists'] = []
                        user_data['top_tracks'] = []
                        user_data['top_genres'] = []
                    return user_data
                
                return {
                    'spotify_id': spotify_id,
                    'top_artists': [],
                    'top_tracks': [],
                    'top_genres': [],
                    'setup_complete': False
                }
        except Exception as e:
            print(f"Error getting user data: {e}")
            return {
                'spotify_id': spotify_id,
                'top_artists': [],
                'top_tracks': [],
                'top_genres': [],
                'setup_complete': False
            }
        finally:
            if conn:
                conn.close()

    def update_user_tops(self, spotify_id: str, 
                        top_artists: List[Dict], 
                        top_tracks: List[Dict], 
                        top_genres: List[str]) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            with conn:
                conn.execute("""
                    UPDATE users 
                    SET top_artists = ?, top_tracks = ?, top_genres = ?
                    WHERE spotify_id = ?
                """, (
                    json.dumps(top_artists),
                    json.dumps(top_tracks),
                    json.dumps(top_genres),
                    spotify_id
                ))
                return True
        except Exception as e:
            print(f"Error updating user tops: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def update_user_setup(self, spotify_id: str, instagram_username: str) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            with conn:
                conn.execute("""
                    UPDATE users 
                    SET instagram_username = ?, setup_complete = TRUE
                    WHERE spotify_id = ?
                """, (instagram_username, spotify_id))
                return True
        except Exception as e:
            print(f"Error updating user setup: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def update_user_setup(self, spotify_id: str, instagram_username: str) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            with conn:
                conn.execute("""
                    UPDATE users 
                    SET instagram_username = ?, setup_complete = TRUE
                    WHERE spotify_id = ?
                """, (instagram_username, spotify_id))
                return True
        except Exception as e:
            print(f"Error updating user setup: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users from the database"""
        conn = None
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            with conn:
                cursor = conn.execute("SELECT * FROM users WHERE setup_complete = TRUE")
                rows = cursor.fetchall()
                
                users = []
                for row in rows:
                    try:
                        # Convert JSON strings back to lists
                        user_data = dict(row)
                        user_data['top_artists'] = json.loads(user_data['top_artists'] or '[]')
                        user_data['top_tracks'] = json.loads(user_data['top_tracks'] or '[]')
                        user_data['top_genres'] = json.loads(user_data['top_genres'] or '[]')
                        users.append(user_data)
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON for user {user_data.get('spotify_id')}: {e}")
                        continue
                    except Exception as e:
                        print(f"Error processing user data: {e}")
                        continue
                
                return users
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
        finally:
            if conn:
                conn.close()
    