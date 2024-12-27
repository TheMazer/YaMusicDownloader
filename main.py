from yandex_music import Client
from support import shuffleString

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3


token = 'y0_AgAAAABXU6vtAAG8XgAAAAEQbCWVAAATTZcPPXxKn6WMIS7DlELNS-jiUQ'
onlySingleArtist = True
shuffleTrackInfo = False
needToDownload = True

client = Client(token).init()
favouriteTracks = client.users_likes_tracks()

totalTracks = len(favouriteTracks)
for i, track in enumerate(favouriteTracks):
    attempts = 3
    while attempts > 0:
        try:
            # Track Data
            trackData = track.fetch_track()

            trackTitle = trackData.title
            trackArtists = trackData.artists_name()

            # Hide Track Info
            if shuffleTrackInfo:
                trackTitle = shuffleString(trackTitle)
                for artist in range(len(trackArtists)):
                    trackArtists[artist] = shuffleString(trackArtists[artist])

            # Show Only Single Artist
            if onlySingleArtist:
                artists = trackArtists[0]
            else:
                artists = ', '.join(trackArtists)

            # Printing Track's Info
            digits = len(str(totalTracks))
            if needToDownload:
                print(f"{i + 1:0{digits}} / {totalTracks}  |  Downloading...  |  {trackTitle} — {artists} [{track.id}]", end='  |  ')
            else:
                print(f"{i + 1:0{digits}} / {totalTracks}  |  {trackTitle} — {artists} [{track.id}]")

            # Downloading
            try:
                if needToDownload:
                    path = f"download/{trackData.title} — {', '.join(trackData.artists_name())} [{track.id}].mp3"
                    trackData.download(path)

                    trackData.downloadCover("cover.png")

                    audio = MP3(path, ID3=EasyID3)

                    audio['title'] = trackData.title
                    audio['artist'] = ', '.join(trackData.artists_name())

                    audio.save()

                    print(f"Success")
            except:
                print(f"Failed")

            break
        except:
            attempts -= 1
            if attempts == 0:
                print(f"Unable to fetch track's info, id: {track.id}")