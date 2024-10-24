## BeatSync for Discord - README
## Overview

Welcome to BeatSync for Discord! This is a powerful and customizable music bot designed to provide your Discord server with high-quality audio streaming from YouTube. The bot includes a variety of music-related commands, a fun "Guess the Song" game, and volume controls to keep your listening experience smooth and enjoyable.
Features

    🎵 Play music from YouTube (supports both single songs and playlists).
    🎧 Join and leave voice channels automatically.
    🎚️ Adjust the playback volume.
    ⏸️ Pause, resume, and skip tracks easily.
    📜 View the current queue of songs.
    ⏱️ Automatic disconnection after inactivity.
    🎤 "Guess the Song" game for added fun.
    ⏩ Seek to specific positions in songs.
    Detailed logging for debugging.

## Prerequisites

- **Docker** installed on your system.
- **Discord API token** (Create a bot at the [Discord Developer Portal](https://discord.com/developers/applications)).
- **Discord Application ID** (Use created bot at  [Discord Developer Portal](https://discord.com/developers/applications)).
- **Discord Channel name** (The name of the your Discord Channel where the interactions with the bot happens)

## Building the Docker Image

1. Clone the repository:

    ```bash
    git clone https://github.com/haeziate/beatsync.git
    cd beatsync
    ```

2. Build the Docker image:

    ```bash
    docker build -t beatsync .
    ```

## Running the Bot

To run the bot, you'll need to create a `.env` file with the following keys:

```plaintext
TOKEN=Your_Discord_Bot_Token
APP=Your_Discord_Application_ID
CHANNEL=Default_Text_Channel_ID
```
## Usage
Commands

    Play a song or playlist:
    /play [song name or URL]
    Starts playing a song from YouTube by searching for a keyword or URL.

    Skip the current song:
    /skip
    Skips to the next song in the queue.

    Stop the music:
    /stop
    Stops the music and clears the queue.

    View the song queue:
    /queue
    Displays the current playlist queue.

    Pause/Resume music:
    /pause, /resume
    Pause or resume the current song.

    Adjust the volume:
    /volume [0-100]
    Adjusts the playback volume.

    Seek to a specific time:
    /seek [MM:SS or seconds]
    Jumps to a specific point in the current song.

    Guess the Song:
    /guess_the_song
    Starts a fun "Guess the Song" game using random YouTube tracks.

    Make a guess:
    /guess [your guess]
    Guess the current song in "Guess the Song" mode.

## Default Behaviors

    The bot will automatically disconnect from a voice channel after 2 minutes of inactivity.
    It sends a notification to the specified CHANNEL whenever it reconnects or disconnects.

## Logging

The bot uses both console and file-based logging (bot.log). Logs provide detailed information about events like voice channel updates, song playback, and errors.
## License

This project is licensed under the MIT License.

Contributions are welcome! If you encounter any bugs or want to suggest new features, feel free to open an issue or create a pull request. Enjoy your music! 🎶


