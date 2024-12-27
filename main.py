from yandex_music import Client
from support import Config, shuffleString, sanitizeFileName

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
import os

# Configuration settings
config = Config('config.ini')
token = config.get('token')
if not token:
    token = input("Введите токен: ")
    config.set('token', token)
    config.save()
downloadFolder = config.get('downloadFolder')
onlySingleArtist = config.get('onlySingleArtist') == 'True'
shuffleTrackInfo = config.get('shuffleTrackInfo') == 'True'
needToDownload = config.get('needToDownload') == 'True'

# Initialize Yandex Music client
client = Client(token).init()
favouriteTracks = client.users_likes_tracks()


# Get list of downloaded tracks
def get_downloaded_tracks(directory = downloadFolder):
    downloaded = set()
    if os.path.exists(directory):
        for file in os.listdir(directory):
            if file.endswith(".mp3"):
                try:
                    track_id = file[file.rfind("[") + 1:file.rfind("]")]
                    downloaded.add(track_id)
                except Exception:
                    continue
    return downloaded


# Compare playlists
def compare_playlists(favourite_tracks, downloaded_tracks):
    server_track_ids = {str(track.id) for track in favourite_tracks}
    missing_tracks = server_track_ids - downloaded_tracks
    extra_tracks = downloaded_tracks - server_track_ids
    return missing_tracks, extra_tracks


downloadedTracks = get_downloaded_tracks()
missingTracks, extraTracks = compare_playlists(favouriteTracks.tracks, downloadedTracks)

if len(missingTracks) == 0 or len(extraTracks) == 0:
    print("\nПлейлист синхронизирован.")
    print(f"  Всего {len(downloadedTracks)} треков.")
    exit()


# Summary
def print_summary(missing, extra):
    print(f"\nПлейлист не синхронизирован:")
    print(f"  {len(missing)} треков отсутствует.")
    print(f"  {len(extra)} треков лишние.")
    print("\nВыберите режим работы:")
    print("  [0] Выход")
    print("  [1] Скачать недостающие треки")
    print("  [2] Скачать недостающие треки + Удалить лишние")

print_summary(missingTracks, extraTracks)

# User choice
choice = input("Введите номер команды: ")
if choice == "0":
    exit()
if choice in ["1", "2"]:
    # Download missing tracks
    totalTracks = len(missingTracks)
    for i, track_id in enumerate(missingTracks):
        attempts = 3
        while attempts > 0:
            try:
                # Fetch track data
                track = next((t for t in favouriteTracks.tracks if str(t.id) == track_id), None)
                if not track:
                    raise ValueError("Track not found on server.")
                trackData = client.tracks([track_id])[0]

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
                print(f"{i + 1:0{digits}} / {totalTracks}  |  Downloading...  |  {trackTitle} — {artists} [{track_id}]", end='  |  ')

                # Handle downloading
                path = f"{downloadFolder}/{sanitizeFileName(trackData.title)} — {sanitizeFileName(', '.join(trackData.artists_name()))} [{track_id}].mp3"
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
                break
            except (FileNotFoundError, OSError) as e:
                print(f"File error: {e}. Skipping track.")
                break
            except Exception as e:
                print(f"Failed: {e}")
                attempts -= 1
                if attempts == 0:
                    print(f"Unable to fetch track's info, id: {track_id}")

    # Delete extra tracks if option 2 is chosen
    if choice == "2":
        for extra_id in extraTracks:
            file_to_remove = next((f for f in os.listdir(downloadFolder) if f.endswith(f"[{extra_id}].mp3")), None)
            if file_to_remove:
                os.remove(os.path.join(downloadFolder, file_to_remove))
                print(f"Deleted extra track: {file_to_remove}")
