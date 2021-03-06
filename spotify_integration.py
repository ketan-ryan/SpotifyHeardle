import spotipy
from spotipy.oauth2 import SpotifyOAuth

class SpotifyHandler:
    scope = 'user-library-read'
    id = ''
    secret = ''
    sp = None


    def __init__(self):
        with open ('secrets.txt', 'r') as fp:
            self.id = fp.readline().strip()
            self.secret = fp.readline().strip()

        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=self.scope, open_browser=True, redirect_uri='http://example.com', client_id=self.id, client_secret=self.secret))

        # Get the user, in the future could store it in a db or find some other way to only pick once per day
        self.user = self.sp.me()['external_urls']['spotify']


    def get_playlists(self):
        i = 0
        songs = []
        uris = []
        while(True):
            # We can't get all at once, so iterate until we have all liked songs
            results = self.sp.current_user_saved_tracks(offset=i*20)
            if (len(results['items']) == 20):
                for idx, item in enumerate(results['items']):
                    track = item['track']
                    songs.append(f"{track['artists'][0]['name']} - {track['name']}")
                    uris.append(track['uri'])
                i += 1
            else:
                break

        # for idx, song in enumerate(songs):
        #     print(song, uris[idx])

        return (songs, uris)


    # https://developer.spotify.com/documentation/embeds/guides/using-the-iframe-api/