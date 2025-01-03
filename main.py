import yandex_music.exceptions
from yandex_music import Client
from support import Config, shuffleString, sanitizeFileName

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TXXX
import os

# Configuration settings
config = Config('config.ini')

token = config.get('token')
if not token:
    token = input("Введите токен: ")
    config.set('token', token)
    config.save()

# Initialize Yandex Music client
try: client = Client(token).init()
except yandex_music.exceptions.UnauthorizedError:
    print('Failed: Invalid token')
    config.set('token', '')
    config.save()
    exit()

downloadFolder = config.get('downloadFolder')
if not downloadFolder:
    downloadFolder = input("Введите папку для загрузки: ").replace('\\', '/')
    config.set('downloadFolder', downloadFolder)
    config.save()

onlySingleArtist = config.get('onlySingleArtist') == 'True'
shuffleTrackInfo = config.get('shuffleTrackInfo') == 'True'
needToDownload = config.get('needToDownload') == 'True'

# Get list of favourite tracks
favouriteTracks = client.users_likes_tracks()


# Get list of downloaded tracks and remove duplicates
def getDownloadedTracks(directory = downloadFolder):
    downloaded = set()

    if os.path.exists(directory):
        for file in os.listdir(directory):
            if file.endswith(".mp3"):
                try:
                    path = f"{directory}/{file}"
                    audio = MP3(path, ID3=ID3)
                    trackId = audio.get('TXXX:trackID', None)[0]

                    if not trackId: continue

                    if trackId in downloaded:
                        confirm = input(f"Найден дубликат: {file}. Удалить? (y/n): ")
                        if confirm.lower() in ('y', '1', 't', 'yes', 'true'):
                            os.remove(path)
                            print(f"Duplicate removed: {file}")
                    else:
                        downloaded.add(trackId)
                except Exception as e:
                    print(f"Error processing file {file}: {e}")
                    continue
    return downloaded


# Compare playlists
def comparePlaylists(favouriteTracks, downloadedTracks):
    serverTrackIds = {str(track.id) for track in favouriteTracks}
    missingTracks = serverTrackIds - downloadedTracks
    extraTracks = downloadedTracks - serverTrackIds
    return missingTracks, extraTracks


downloadedTracks = getDownloadedTracks()
missingTracks, extraTracks = comparePlaylists(favouriteTracks.tracks, downloadedTracks)

if len(missingTracks) == 0 and len(extraTracks) == 0:
    print("\nПлейлист синхронизирован.")
    print(f"  Всего {len(downloadedTracks)} треков.")
    exit()


# Summary
def printSummary(missing, extra):
    print(f"\nПлейлист не синхронизирован:")
    print(f"  {len(missing)} треков отсутствует.")
    print(f"  {len(extra)} треков лишние.")
    print("\nВыберите режим работы:")
    print("  [0] Выход")
    print("  [1] Скачать недостающие треки")
    print("  [2] Скачать недостающие треки + Удалить лишние")


printSummary(missingTracks, extraTracks)

# User choice
choice = input("Введите номер команды: ")
if choice == "0":
    exit()
if choice in ["1", "2"]:
    # Download missing tracks
    totalTracks = len(missingTracks)
    for i, trackId in enumerate(missingTracks):
        attempts = 3
        while attempts > 0:
            try:
                # Fetch track data
                track = next((t for t in favouriteTracks.tracks if str(t.id) == trackId), None)
                if not track:
                    attempts = 0
                    raise f"Track {trackId} not found on server."
                trackData = client.tracks([trackId])[0]

                trackTitle = trackData.title
                trackArtists = trackData.artists_name()

                # Show only single artist if configured
                if onlySingleArtist: artists = trackArtists[0]
                else: artists = ', '.join(trackArtists)

                # Print & optionally shuffle track info
                digits = len(str(totalTracks))
                if shuffleTrackInfo:
                    shuffledArtists = []
                    for artist in trackArtists: shuffledArtists.append(shuffleString(artist))
                    print(f"{i + 1:0{digits}} / {totalTracks}  |  Downloading...  |  {shuffleString(trackTitle)} — {shuffledArtists} [{trackId}]", end='  |  ')
                else:
                    print(f"{i + 1:0{digits}} / {totalTracks}  |  Downloading...  |  {trackTitle} — {artists} [{trackId}]", end='  |  ')

                # Handle downloading
                sanitizedTitle = sanitizeFileName(trackTitle)
                sanitizedArtists = sanitizeFileName(artists)
                path = f"{downloadFolder}/{sanitizedTitle} — {sanitizedArtists}.mp3"

                # Check if file exists and handle duplicates
                if os.path.exists(path):
                    existingAudio = MP3(path, ID3=ID3)
                    existingTrackId = existingAudio.get('TXXX:trackID', [None])[0]

                    if existingTrackId != trackId:
                        # Appending ID to existing track
                        os.rename(path, f"{downloadFolder}/{sanitizedTitle} — {sanitizedArtists} [{existingTrackId}].mp3")
                        # Appending ID to new track
                        path = f"{downloadFolder}/{sanitizedTitle} — {sanitizedArtists} [{trackId}].mp3"

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

                # Add ID to the file
                audio.tags.add(
                    TXXX(
                        encoding=3,  # UTF-8
                        desc='trackID',  # Description of custom tag
                        text=trackId  # Store the track ID as string
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
                    print(f"Unable to fetch track's info, id: {trackId}")

    # Delete extra tracks if option 2 is chosen
    if choice == "2":
        print(f"\nВыберите действие для удаления лишних треков {len(extraTracks)}:")
        print("  [0] Не удалять лишние треки")
        print("  [1] Запрашивать подтверждение для каждого трека")
        print("  [2] Удалить лишние треки без подтверждения")
        deleteChoice = input("Введите номер команды: ")

        if deleteChoice == "0":
            pass
        elif deleteChoice == "1":
            for extraId in extraTracks:
                for file in os.listdir(downloadFolder):
                    try:
                        path = f"{downloadFolder}/{file}"
                        audio = MP3(path, ID3=ID3)
                        trackId = audio.get('TXXX:trackID', [None])[0]
                        if trackId == extraId:
                            confirm = input(f"Удалить {file}? (y/n): ")
                            if confirm.lower() in ('y', '1', 't', 'yes', 'true'):
                                os.remove(path)
                                print(f"Deleted extra track: {file}\n")
                    except Exception:
                        continue
        elif deleteChoice == "2":
            for extraId in extraTracks:
                for file in os.listdir(downloadFolder):
                    try:
                        path = f"{downloadFolder}/{file}"
                        audio = MP3(path, ID3=ID3)
                        trackId = audio.get('TXXX:trackID', [None])[0]
                        if trackId == extraId:
                            os.remove(path)
                            print(f"Deleted extra track: {file}")
                    except Exception:
                        continue