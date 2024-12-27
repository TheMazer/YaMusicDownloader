from yandex_music import Client
from support import shuffleString

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

# Configuration settings
token = 'y0_AgAAAABXU6vtAAG8XgAAAAEQbCWVAAATTZcPPXxKn6WMIS7DlELNS-jiUQ'
onlySingleArtist = True
shuffleTrackInfo = False
needToDownload = True

# Initialize Yandex Music client
client = Client(token).init()
favouriteTracks = client.users_likes_tracks()

totalTracks = len(favouriteTracks)
for i, track in enumerate(favouriteTracks):
    attempts = 3
    while attempts > 0:
        try:
            # Fetch track data
            trackData = track.fetch_track()

            trackTitle = trackData.title
            trackArtists = trackData.artists_name()

            # Optionally shuffle track info
            if shuffleTrackInfo:
                trackTitle = shuffleString(trackTitle)
                for artist in range(len(trackArtists)):
                    trackArtists[artist] = shuffleString(trackArtists[artist])

            # Show only single artist if configured
            if onlySingleArtist:
                artists = trackArtists[0]
            else:
                artists = ', '.join(trackArtists)

            # Print track info
            digits = len(str(totalTracks))
            if needToDownload:
                print(f"{i + 1:0{digits}} / {totalTracks}  |  Downloading...  |  {trackTitle} — {artists} [{track.id}]", end='  |  ')
            else:
                print(f"{i + 1:0{digits}} / {totalTracks}  |  {trackTitle} — {artists} [{track.id}]")

            # Handle downloading if enabled
            if needToDownload:
                try:
                    path = f"download/{trackData.title} — {', '.join(trackData.artists_name())} [{track.id}].mp3"
                    trackData.download(path)

                    # Download cover image
                    coverPath = "cover.png"
                    trackData.downloadCover(coverPath)

                    # Add metadata to the downloaded file
                    audio = MP3(path, ID3=EasyID3)
                    audio['title'] = trackData.title
                    audio['artist'] = ', '.join(trackData.artists_name())
                    audio['album'] = trackData.albums[0].title
                    audio.save()

                    # Add cover image to the file
                    audio = MP3(path, ID3=ID3)
                    with open(coverPath, "rb") as coverFile:
                        coverData = coverFile.read()
                    audio.tags.add(
                        APIC(
                            encoding=0,  # Latin-1
                            mime="image/jpeg" if coverPath.endswith(".jpg") else "image/png",  # MIME type of the image
                            type=3,  # Front cover
                            desc="Cover",
                            data=coverData
                        )
                    )
                    audio.save()

                    print("Success")
                except Exception as e:
                    print(f"Failed: {e}")

            break
        except:
            attempts -= 1
            if attempts == 0:
                print(f"Unable to fetch track's info, id: {track.id}")
