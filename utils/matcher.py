from typing import Dict, List, Set
from datetime import datetime

"""
Music Matching Algorithm Implementation
Author: Rexaintreal

Implements the core matching algorithm for comparing user music preferences.
"""


class MusicMatcher:
    """
    Implements music taste matching algorithm between users.
    Uses weighted scoring across artists, genres, and tracks.
    """
    def __init__(self):
        self.weights = {
            'artists': 0.50,  # Increased to 50% - Most important
            'genres': 0.30,   # 30% - Genre matching
            'tracks': 0.20    # 20% - Track matching
        }

    def calculate_match(self, user1: Dict, user2: Dict) -> Dict:
        """
        Calculate match percentage between two users based on their music taste
        """
        try:
            print(f"\n=== Calculating Match ===")
            print(f"User 1: {user1.get('instagram_username')}")
            print(f"User 2: {user2.get('instagram_username')}")

            # 1. Calculate Artist Match (50%)
            user1_artists = {artist['name'].lower() for artist in user1['top_artists']}
            user2_artists = {artist['name'].lower() for artist in user2['top_artists']}
            shared_artists = user1_artists & user2_artists
            
            artist_score = len(shared_artists) / max(len(user1_artists), len(user2_artists)) if user1_artists and user2_artists else 0
            print(f"Shared Artists: {shared_artists}")
            print(f"Artist Score: {artist_score * 100}%")

            # 2. Calculate Genre Match (30%)
            user1_genres = {genre.lower() for genre in user1['top_genres']}
            user2_genres = {genre.lower() for genre in user2['top_genres']}
            shared_genres = user1_genres & user2_genres
            
            genre_score = len(shared_genres) / max(len(user1_genres), len(user2_genres)) if user1_genres and user2_genres else 0
            print(f"Shared Genres: {shared_genres}")
            print(f"Genre Score: {genre_score * 100}%")

            # 3. Calculate Track Match (20%)
            user1_tracks = {track['name'].lower() for track in user1['top_tracks']}
            user2_tracks = {track['name'].lower() for track in user2['top_tracks']}
            shared_tracks = user1_tracks & user2_tracks
            
            track_score = len(shared_tracks) / max(len(user1_tracks), len(user2_tracks)) if user1_tracks and user2_tracks else 0
            print(f"Shared Tracks: {shared_tracks}")
            print(f"Track Score: {track_score * 100}%")

            # Calculate final weighted score
            final_score = (
                (artist_score * self.weights['artists']) +
                (genre_score * self.weights['genres']) +
                (track_score * self.weights['tracks'])
            ) * 100

            print(f"Final Match Score: {final_score}%")

            # Get profile image from first artist if available
            profile_image = None
            if user2['top_artists'] and user2['top_artists'][0].get('image'):
                profile_image = user2['top_artists'][0]['image']

            match_data = {
                'percentage': round(final_score, 1),
                'shared_artists': list(shared_artists)[:3],
                'shared_genres': list(shared_genres)[:2],
                'shared_tracks': list(shared_tracks)[:2],
                'top_artist': list(shared_artists)[0] if shared_artists else user2['top_artists'][0]['name'] if user2['top_artists'] else 'Unknown',
                'profile_image': profile_image,
                'instagram_url': f"https://instagram.com/{user2['instagram_username']}",
                'breakdown': {
                    'artist_score': round(artist_score * 100, 1),
                    'genre_score': round(genre_score * 100, 1),
                    'track_score': round(track_score * 100, 1)
                }
            }

            print("\nMatch Details:")
            print(f"Percentage: {match_data['percentage']}%")
            print(f"Top Shared Artist: {match_data['top_artist']}")
            print(f"Shared Artists: {match_data['shared_artists']}")
            print(f"Shared Genres: {match_data['shared_genres']}")
            
            return match_data

        except Exception as e:
            print(f"Error calculating match: {e}")
            return {
                'percentage': 0,
                'shared_artists': [],
                'shared_genres': [],
                'shared_tracks': [],
                'top_artist': 'Unknown',
                'profile_image': None,
                'instagram_url': f"https://instagram.com/{user2.get('instagram_username', '')}",
                'breakdown': {
                    'artist_score': 0,
                    'genre_score': 0,
                    'track_score': 0
                }
            }

    def get_initials(self, username: str) -> str:
        """Get initials from username"""
        return ''.join([word[0].upper() for word in username.split('_')])[:2]