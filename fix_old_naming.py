import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TXXX
from support import Config


def fixOldNaming(directory):
    for fileName in os.listdir(directory):
        if not fileName.endswith(".mp3"):
            print(f"Found not mp3 file: {fileName}")
            continue

        filePath = os.path.join(directory, fileName)

        # Find track ID in square brackets
        idStart = fileName.rfind("[") + 1
        idEnd = fileName.rfind("]")
        if idStart > 0 and idEnd > idStart:
            trackId = fileName[idStart:idEnd]

            # Remove track ID from filename
            newFileName = fileName[:idStart - 1].strip() + ".mp3"
            newFilePath = os.path.join(directory, newFileName)

            try:
                os.remove(newFilePath)
                os.rename(filePath, newFilePath)

                # Write track ID into metadata
                audio = MP3(newFilePath, ID3=ID3)
                audio.tags.add(
                    TXXX(
                        encoding=3,  # UTF-8 encoding
                        desc='trackID',  # Description of the custom tag
                        text=str(trackId)  # Store the track ID as a string
                    )
                )
                audio.save()

                print(f"Processed: {newFileName} (trackId: {trackId})")
            except Exception as e:
                print(f"Error processing {fileName}: {e}")


config = Config('config.ini')
targetDirectory = config.get('downloadFolder')
if not targetDirectory:
    targetDirectory = input("Введите папку с треками: ").replace('\\', '/')
    config.set('downloadFolder', targetDirectory)
    config.save()

fixOldNaming(targetDirectory)