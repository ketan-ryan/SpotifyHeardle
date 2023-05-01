from flask import Flask, render_template, redirect, request, session
from youtube_search import YoutubeSearch
from flask_socketio import SocketIO
from flask_session import Session
from requests import ReadTimeout
from spotify_integration import SpotifyHandler
from random import randint
import subprocess
import threading
import spotipy
import pathlib
import secrets
import shlex
import time
import json

app = Flask(__name__, static_url_path='/downloads', static_folder='downloads')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
app.secret_key = secrets.token_urlsafe(16)
socketio = SocketIO(app, async_mode='threading')
spotify = SpotifyHandler()

CLI_ID = spotify.id
CLI_SEC = spotify.secret

API_BASE = 'https://accounts.spotify.com'

# Make sure you add this to Redirect URIs in the setting of the application dashboard
REDIRECT_URI = 'http://10.0.0.33:8080/callback'

SCOPE = 'user-library-read'

# Set this to True for testing but you probaly want it set to False in production.
SHOW_DIALOG = True

auth_manager = None

# authorization-code-flow Step 1. Have your application request authorization;
# the user logs in and authorizes access
@app.route('/')
def verify():
    global auth_manager
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(scope=SCOPE,
                                               cache_handler=cache_handler,
                                               show_dialog=True, redirect_uri=REDIRECT_URI)

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 1. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return f'<h2><a href="{auth_url}">Sign in</a></h2>'

    # Step 3. Signed in, display data
    return redirect('/index')


def download_song(song_name: str, youtube_url: str) -> bool:
    artist = song_name[:song_name.index(' - ')]
    song = song_name[song_name.index(' - ') + 3:]

    path = pathlib.Path(f'downloads/{artist}')
    if not pathlib.Path.is_dir(path):
        pathlib.Path.mkdir(path)

    path = pathlib.Path(f'downloads/{artist}/{song}.mp3')

    if not pathlib.Path.is_file(path):
        command = f'yt-dlp -v -f bestaudio "{youtube_url}" --downloader ffmpeg --external-downloader-args "-ss 00:00 -to 00:16" -o "downloads/{artist}/{song}.mp3"'

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
    global auth_manager
    print('callback')
    # Step 2. Being redirected from Spotify auth page
    auth_manager.get_access_token(request.args.get("code"))
    return redirect('/')
    # return redirect('/index')


# authorization-code-flow Step 3.
# Use the access token to access the Spotify Web API;
# Spotify returns requested data
def setup_spotify():
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')

    spotify.init_user(spotipy.Spotify(auth_manager=auth_manager))
    return redirect('/index')


if __name__ == '__main__':
    socketio.run(app,
        host='0.0.0.0',
            port=8080, debug=True)
