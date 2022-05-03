from flask import Flask, render_template
import spotify_integration
import json

app = Flask(__name__)

spotify = spotify_integration.SpotifyHandler()

@app.route('/')
def index():
    return render_template('index.html', songs=json.dumps(spotify.get_playlists()[0]))


if __name__ == '__main__':
    app.run(host="0.0.0.0")