from flask import Flask, render_template, redirect, request, session
import spotify_integration
import spotipy
import secrets
import time
import json


app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(16)
spotify = spotify_integration.SpotifyHandler()

CLI_ID = spotify.id
CLI_SEC = spotify.secret

API_BASE = 'https://accounts.spotify.com'

# Make sure you add this to Redirect URIs in the setting of the application dashboard
REDIRECT_URI = "http://192.168.1.204:8080/callback"

SCOPE = 'user-library-read'

# Set this to True for testing but you probaly want it set to False in production.
SHOW_DIALOG = True


# authorization-code-flow Step 1. Have your application request authorization;
# the user logs in and authorizes access
@app.route("/")
def verify():
    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id = CLI_ID, client_secret = CLI_SEC, redirect_uri = REDIRECT_URI, scope = SCOPE, open_browser=True, cache_path='.spotifycache')
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route("/index")
def index():
    setup_spotify()
    return render_template("index.html", songs=json.dumps(spotify.get_playlists()[0]))


# authorization-code-flow Step 2.
# Have your application request refresh and access tokens;
# Spotify returns access and refresh tokens
@app.route("/callback")
def api_callback():
    # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id = CLI_ID, client_secret = CLI_SEC, redirect_uri = REDIRECT_URI, scope = SCOPE, open_browser=True, cache_path='.spotifycache')
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code, check_cache=False)

    # Saving the access token along with all other token related info
    session["token_info"] = token_info

    return redirect("index")


# authorization-code-flow Step 3.
# Use the access token to access the Spotify Web API;
# Spotify returns requested data
def setup_spotify():
    session['token_info'], authorized = get_token(session)
    session.modified = True

    if not authorized:
        return redirect('/')

    spotify.init_user(spotipy.Spotify(auth=session.get('token_info').get('access_token')))
    return ("/index")


# Checks to see if token is valid and gets a new token if not
def get_token(session):
    token_valid = False
    token_info = session.get("token_info", {})

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8080", debug=True)
