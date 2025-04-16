from flask import Flask, redirect, request, session, url_for, render_template, flash
import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from functools import wraps
from utils.db import Database 
from utils.match_cache import MatchCache
from utils.matcher import MusicMatcher
import pytz 

try:
    matcher = MusicMatcher()
except Exception as e:
    print(f"Error initializing MusicMatcher: {e}")
    matcher = None

try:
    match_cache = MatchCache()
except Exception as e:
    print(f"Error initializing MatchCache: {e}")
    match_cache = None

load_dotenv()
required_env_vars = [
    'SECRET_KEY',
    'SPOTIFY_CLIENT_ID',
    'SPOTIFY_CLIENT_SECRET'
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
try:
    db = Database()  
except Exception as e:
    print(f"Error initializing database: {e}")
    db = None


# Spotify Configuration
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = "http://localhost:5000/callback"
SCOPE = "user-read-private user-read-email user-top-read"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session or 'spotify_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if not db:
        flash('Database connection error', 'error')
        return render_template('error.html', error='Database connection failed')

    if 'access_token' in session and 'spotify_id' in session:
        try:
            user_data = db.get_user(session['spotify_id'])
            if user_data and user_data.get('setup_complete'):
                return redirect(url_for('dashboard'))
            elif not session.get('instagram_username'):
                return redirect(url_for('setup'))
            return redirect(url_for('dashboard'))
        except Exception as e:
            print(f"Error in index route: {e}")
            session.clear() 
            return render_template('login.html')
    return render_template('login.html')

@app.route('/login')
def login():
    session.clear()
    auth_url = f'{SPOTIFY_AUTH_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={SCOPE}'
    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        flash('Error during authentication', 'error')
        return redirect(url_for('index'))

    try:
        auth_token = request.args.get('code')
        if not auth_token:
            flash('Authentication failed', 'error')
            return redirect(url_for('index'))

        auth_body = {
            'grant_type': 'authorization_code',
            'code': auth_token,
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'show_dialog': 'true',
        }

        post_response = requests.post(SPOTIFY_TOKEN_URL, data=auth_body)

        if post_response.status_code != 200:
            flash('Failed to get access token', 'error')
            return redirect(url_for('index'))

        response_data = json.loads(post_response.text)

        if 'access_token' not in response_data:
            flash('Access token not found in response', 'error')
            return redirect(url_for('index'))

        access_token = response_data['access_token']
        session['access_token'] = access_token

        headers = {'Authorization': f"Bearer {access_token}"}
        user_profile_response = requests.get(f"{SPOTIFY_API_BASE_URL}/me", headers=headers)

        if user_profile_response.status_code != 200:
            flash('Failed to get user profile', 'error')
            return redirect(url_for('index'))

        user_profile = user_profile_response.json()

        spotify_id = user_profile.get('id')
        if not spotify_id:
            flash('User ID not found in profile', 'error')
            return redirect(url_for('index'))

        session['spotify_id'] = spotify_id
        session['display_name'] = user_profile.get('display_name')


        top_artists, top_tracks, top_genres = get_spotify_tops(access_token)

        
        user_data = {
            'spotify_id': spotify_id,
            'display_name': user_profile.get('display_name'),
            'join_date': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S'),
            'top_artists': top_artists,
            'top_tracks': top_tracks,
            'top_genres': top_genres,
            'setup_complete': False,
            'instagram_username': session.get('instagram_username')
        }

        db.save_user(user_data)
        print(f"Saved user data for {spotify_id}") 

        return redirect(url_for('setup'))

    except Exception as e:
        print(f"Error in callback: {e}")
        flash('An error occurred during authentication', 'error')
        session.clear()  
        return redirect(url_for('index'))


def get_spotify_tops(access_token: str):
    headers = {'Authorization': f"Bearer {access_token}"}

    artists_response = requests.get(
        f"{SPOTIFY_API_BASE_URL}/me/top/artists?limit=10&time_range=long_term",
        headers=headers
    )
    top_artists = []
    if artists_response.status_code == 200:
        artists_data = artists_response.json()
        top_artists = [{
            'name': artist['name'],
            'image': artist['images'][0]['url'] if artist['images'] else None,
            'genres': artist['genres'],
            'id': artist['id'], 
            'spotify_url': f"https://open.spotify.com/artist/{artist['id']}",
            'popularity': artist.get('popularity', 0)
        } for artist in artists_data['items']]

    
    tracks_response = requests.get(
        f"{SPOTIFY_API_BASE_URL}/me/top/tracks?limit=10&time_range=long_term",
        headers=headers
    )
    top_tracks = []
    if tracks_response.status_code == 200:
        tracks_data = tracks_response.json()
        top_tracks = [{
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'id': track['id'],  
            'spotify_url': f"https://open.spotify.com/track/{track['id']}"
        } for track in tracks_data['items']]

    
    genre_count = {}
    for artist in top_artists:
        for genre in artist['genres']:
            genre_count[genre] = genre_count.get(genre, 0) + 1
    top_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:10]
    top_genres = [genre[0] for genre in top_genres]

    return top_artists, top_tracks, top_genres

@app.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    if not db:
        flash('Database connection error', 'error')
        return render_template('error.html', error='Database connection failed')

    if request.method == 'POST':
        instagram_username = request.form.get('instagram')
        if instagram_username:
            
            if db.update_user_setup(session['spotify_id'], instagram_username):
                session['instagram_username'] = instagram_username
                return redirect(url_for('dashboard'))
            else:
                flash('Error saving data. Please try again.', 'error')
    return render_template('setup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if not matcher or not match_cache:
        flash('Service temporarily unavailable', 'error')
        return render_template('error.html', error='Service configuration error')

    if 'spotify_id' not in session or 'access_token' not in session:
        return redirect(url_for('logout'))

    if 'instagram_username' not in session:
        return redirect(url_for('setup'))

    try:
        current_user_id = session['spotify_id']
        current_user = db.get_user(current_user_id)

        if not current_user:
            return redirect(url_for('logout'))

        cached_matches = match_cache.get_matches(current_user_id)

        if not cached_matches:
            all_users = [user for user in db.get_all_users()
                        if user['spotify_id'] != current_user_id]

            matches = []
            for other_user in all_users:
                try:
                    match_data = matcher.calculate_match(current_user, other_user)

                    profile_image = None
                    if other_user.get('top_artists') and other_user['top_artists'][0].get('image'):
                        profile_image = other_user['top_artists'][0]['image']

                    matches.append({
                        'instagram': other_user['instagram_username'],
                        'match_percentage': match_data['percentage'],
                        'top_artist': match_data['top_artist'],
                        'initials': matcher.get_initials(other_user['instagram_username']),
                        'shared_artists': match_data['shared_artists'],
                        'shared_genres': match_data['shared_genres'],
                        'shared_tracks': match_data['shared_tracks'],
                        'profile_image': profile_image,
                        'instagram_url': f"https://instagram.com/{other_user['instagram_username']}",
                        'breakdown': match_data['breakdown']
                    })
                except Exception as e:
                    print(f"Error calculating match: {e}")
                    continue

            matches.sort(key=lambda x: x['match_percentage'], reverse=True)

            match_cache.update_matches(current_user_id, matches)
        else:
            matches = cached_matches

        return render_template('dashboard.html',
                            username=session.get('instagram_username'),
                            display_name=current_user['display_name'],
                            matches=matches,
                            current_time=datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        print(f"Error in dashboard: {e}")
        return redirect(url_for('logout'))

@app.route('/top-charts')
@login_required
def top_charts():
    if 'spotify_id' not in session:
        return redirect(url_for('login'))

    try:
        access_token = session['access_token']
        spotify_id = session['spotify_id']
        current_time = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')

        headers = {'Authorization': f"Bearer {access_token}"}

        artists_response = requests.get(
            f"{SPOTIFY_API_BASE_URL}/me/top/artists?limit=10&time_range=short_term",
            headers=headers
        )

        top_artists = []
        if artists_response.status_code == 200:
            artists_data = artists_response.json()
            top_artists = [{
                'name': artist['name'],
                'image': artist['images'][0]['url'] if artist['images'] else None,
                'genres': artist['genres'],
                'popularity': artist.get('popularity', 0),
                'id': artist['id'], 
                'spotify_url': f"https://open.spotify.com/artist/{artist['id']}"  
            } for artist in artists_data['items']]

       
        tracks_response = requests.get(
            f"{SPOTIFY_API_BASE_URL}/me/top/tracks?limit=10&time_range=short_term",
            headers=headers
        )

        top_tracks = []
        if tracks_response.status_code == 200:
            tracks_data = tracks_response.json()
            top_tracks = [{
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'id': track['id'],  
                'spotify_url': f"https://open.spotify.com/track/{track['id']}"
            } for track in tracks_data['items']]

        
        all_genres = []
        for artist in top_artists:
            all_genres.extend(artist['genres'])

        genre_count = {}
        for genre in all_genres:
            genre_count[genre] = genre_count.get(genre, 0) + 1

        top_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:10]
        top_genres = [genre[0] for genre in top_genres]

        
        user_data = {
            'spotify_id': spotify_id,
            'top_artists': top_artists,
            'top_tracks': top_tracks,
            'top_genres': top_genres,
            'last_updated': current_time
        }

        db.update_user_tops(spotify_id, top_artists, top_tracks, top_genres)

        return render_template('top-charts.html',
                             display_name=session.get('display_name'),
                             current_time=current_time,
                             top_artists=top_artists,
                             top_tracks=top_tracks,
                             top_genres=top_genres)

    except requests.RequestException as e:
        print(f"Spotify API error: {e}")
        return render_template('top-charts.html',
                             display_name=session.get('display_name'),
                             current_time=datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S'),
                             top_artists=[],
                             top_tracks=[],
                             top_genres=[])
    except Exception as e:
        print(f"Error in top_charts: {e}")
        return render_template('top-charts.html',
                             display_name=session.get('display_name'),
                             current_time=datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S'),
                             top_artists=[],
                             top_tracks=[],
                             top_genres=[])


@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        try:
            feedback_data = {
                'username': session.get('instagram_username'),
                'type': request.form.get('type'),
                'category': request.form.get('category'),
                'message': request.form.get('message'),
                'date': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
                }

            with open('feedback.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Date: {feedback_data['date']}\n")
                f.write(f"From: {feedback_data['username']}\n")
                f.write(f"Type: {feedback_data['type']}\n")
                f.write(f"Category: {feedback_data['category']}\n")
                f.write(f"Message:\n{feedback_data['message']}\n")

            flash('Thank you for your feedback!', 'success')
            return redirect(url_for('feedback'))

        except Exception as e:
            print(f"Error saving feedback: {e}")
            flash('Error saving feedback. Please try again.', 'error')
            return redirect(url_for('feedback'))

    return render_template('feedback.html',
                     username=session.get('instagram_username'),
                     current_date=datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    current_time = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
    if request.method == 'POST':
        if 'instagram_username' in request.form:
            new_username = request.form['instagram_username']
            user_data = db.get_user(session['spotify_id'])
            if user_data:
                user_data['instagram_username'] = new_username
                db.save_user(user_data)
            session['instagram_username'] = new_username
            return redirect(url_for('settings'))
        elif 'logout' in request.form:
            return redirect(url_for('logout'))

    try:
        headers = {'Authorization': f"Bearer {session['access_token']}"}
        spotify_response = requests.get(f"{SPOTIFY_API_BASE_URL}/me", headers=headers)

        if spotify_response.status_code == 200:
            spotify_profile = spotify_response.json()
            profile_image = None
            if spotify_profile.get('images'):
                profile_image = spotify_profile['images'][0].get('url')

            user_data = db.get_user(session['spotify_id'])

            join_date = datetime.strptime(user_data.get('join_date', current_time), '%Y-%m-%d %H:%M:%S')
            formatted_join_date = join_date.strftime('%B %d, %Y')

            return render_template('settings.html',
                                username=session.get('instagram_username'),
                                display_name=spotify_profile.get('display_name'),
                                profile_image=profile_image,
                                join_date=formatted_join_date,
                                current_time=current_time)

    except Exception as e:
        print(f"Error in settings: {e}")
        user_data = db.get_user(session['spotify_id'])

        return render_template('settings.html',
                             username=session.get('instagram_username'),
                             display_name=session.get('display_name'),
                             join_date=user_data.get('join_date') if user_data else None,
                             current_time=current_time)




@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html',
                         username=session.get('instagram_username'),
                         current_date=datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/terms')
def terms_of_service():
    return render_template('terms.html',
                         username=session.get('instagram_username'),
                         current_date=datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S'))



@app.route('/disconnect-spotify', methods=['POST'])
@login_required
def disconnect_spotify():
    session.clear()
    return redirect(url_for('index'))

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()