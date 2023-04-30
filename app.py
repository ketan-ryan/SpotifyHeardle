from flask import Flask, render_template, redirect, request, session
from youtube_search import YoutubeSearch
from requests import ReadTimeout
from flask_socketio import SocketIO, emit
import spotify_integration
from random import randint
from queue import Queue
import subprocess
import threading
import spotipy
import pathlib
import secrets
import shlex
import time
import json

app = Flask(__name__, static_url_path='/downloads', static_folder='downloads')
app.secret_key = secrets.token_urlsafe(16)
socketio = SocketIO(app, async_mode='threading')
spotify = spotify_integration.SpotifyHandler()

CLI_ID = spotify.id
CLI_SEC = spotify.secret

API_BASE = 'https://accounts.spotify.com'

# Make sure you add this to Redirect URIs in the setting of the application dashboard
REDIRECT_URI = 'http://127.0.0.1:8080/callback'

SCOPE = 'user-library-read'

# Set this to True for testing but you probaly want it set to False in production.
SHOW_DIALOG = True

# authorization-code-flow Step 1. Have your application request authorization;
# the user logs in and authorizes access
@app.route('/')
def verify():
    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id = CLI_ID, client_secret = CLI_SEC, redirect_uri = REDIRECT_URI, scope = SCOPE, open_browser=True, cache_path='.spotifycache')
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route('/player_loaded')
def player_loaded():
    global player_loaded_flag
    return str(player_loaded_flag)


def download_song(song_name: str, youtube_url: str) -> bool:
    artist = song_name[:song_name.index(' - ')]
    song = song_name[song_name.index(' - ') + 3:]

    path = pathlib.Path(f'downloads/{artist}')
    if not pathlib.Path.is_dir(path):
        pathlib.Path.mkdir(path)

    path = pathlib.Path(f'downloads/{artist}/{song}.mp3')

    if not pathlib.Path.is_file(path):
        command = f'yt-dlp -v -f bestaudio "{youtube_url}" --external-downloader ffmpeg --external-downloader-args "-ss 00:00 -to 00:16" -o "downloads/{artist}/{song}.mp3"'

        args = shlex.split(command)

        subprocess.run(args)

    with app.test_request_context('/'):
        socketio.emit('loading')


@app.route('/index')
def index():
    setup_spotify()

    try:
        songs, uris = spotify.get_playlists()

        position = randint(0, len(songs))
        random_song = songs[position]
        random_uri = uris[position]

        print(random_song, random_uri)

        # Get the id of the first video result, stripping off the string '/watch?v='
        random_youtube = json.loads(YoutubeSearch(random_song + ' lyrics', max_results=10).to_json())['videos'][0]['url_suffix'][9:]
        random_youtube = random_youtube[:random_youtube.index('&')]
        youtube_url = f'https://www.youtube.com/watch?v={random_youtube}'

        threading.Thread(target=download_song, args=(random_song, youtube_url)).start()

        return render_template('index.html',
            song=json.dumps(random_song), songs=json.dumps(songs), uri=json.dumps(random_uri), youtube=json.dumps(random_youtube))
    except (AttributeError, ReadTimeout):
        return redirect('/')


# authorization-code-flow Step 2.
# Have your application request refresh and access tokens;
# Spotify returns access and refresh tokens
@app.route('/callback')
def api_callback():
    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id = CLI_ID, client_secret = CLI_SEC, redirect_uri = REDIRECT_URI, scope = SCOPE, open_browser=True, cache_path='.spotifycache')
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code, check_cache=False)

    # Saving the access token along with all other token related info
    session['token_info'] = token_info

    return redirect('index')


# authorization-code-flow Step 3.
# Use the access token to access the Spotify Web API;
# Spotify returns requested data
def setup_spotify():
    session['token_info'], authorized = get_token(session)
    session.modified = True

    if not authorized:
        return redirect('/')

    spotify.init_user(spotipy.Spotify(auth=session.get('token_info').get('access_token')))
    return ('/index')


# Checks to see if token is valid and gets a new token if not
def get_token(session):
    token_valid = False
    token_info = session.get('token_info', {})

    # Checking if the session already has a token stored
    if not (session.get('token_info', False)):
        token_valid = False
        return token_info, token_valid

    # Checking if token has expired
    now = int(time.time())
    is_token_expired = session.get('token_info').get('expires_at') - now < 60

    # Refreshing token if it has expired
    if (is_token_expired):
        # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
        sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id = CLI_ID, client_secret = CLI_SEC, redirect_uri = REDIRECT_URI, scope = SCOPE, open_browser=True, cache_path='.spotifycache')
        token_info = sp_oauth.refresh_access_token(session.get('token_info').get('refresh_token'))

    token_valid = True
    return token_info, token_valid


if __name__ == '__main__':
    socketio.run(app,
        # host='0.0.0.0',
            port=8080, debug=True)
