from pickle import TRUE
from flask import Flask, render_template, redirect, request
from spotipy.oauth2 import SpotifyOAuth
import spotify_integration
import json

app = Flask(__name__)
spotify = spotify_integration.SpotifyHandler()

auth = SpotifyOAuth(client_id=spotify.id, client_secret=spotify.secret, redirect_uri='http://localhost:8000/callback', cache_path='.cache', scope='user-library-read')

@app.route('/')
def index():
    token_info = auth.get_cached_token()
    if not token_info:
        auth_url = auth.get_authorize_url()
        return redirect(auth_url)

    token = token_info['access_token']
    spotify.init_user(token)

    return render_template('index.html', songs=json.dumps(spotify.get_playlists()[0]))


@app.route('/callback')
def callback():
    url = request.url
    code = auth.parse_response_code(url)
    token = auth.get_access_token(code)
    return redirect('/')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)