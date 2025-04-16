"""
Match Cache Handler for Spotify Music Matching Application
Author: Rexaintreal

Handles caching of user music matches to improve performance and reduce API calls.
"""
import json
from datetime import datetime
from typing import Dict, List
import os

class MatchCache:
    """
    Caches match results between users to improve performance.
    Uses local JSON file for storage.
    """
    def __init__(self):
        self.cache_file = "matches_cache.json"
        self.init_cache()

    def init_cache(self):
        if not os.path.exists(self.cache_file):
            with open(self.cache_file, 'w') as f:
                json.dump({
                    "last_updated": "",
                    "matches": {}
                }, f, indent=4)

    def update_matches(self, user_id: str, matches: List[Dict]) -> bool:
        try:
            # Load existing cache
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)

            # Update matches for user
            cache_data["matches"][user_id] = {
                "last_updated": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                "matches": matches
            }

            # Save updated cache
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=4)

            return True
        except Exception as e:
            print(f"Error updating match cache: {e}")
            return False

    def get_matches(self, user_id: str) -> List[Dict]:
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            user_matches = cache_data["matches"].get(user_id, {}).get("matches", [])
            return user_matches
        except Exception as e:
            print(f"Error reading match cache: {e}")
            return []