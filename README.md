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

## Getting the Docker Image

You can either build the Docker image yourself or pull the pre-built image from Docker Hub. To pull the image, run the following command:

```bash
docker pull hasuuka/beatsync
```

This command will download the latest version of Beatsync for Discord image. You can
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
## Using Docker Run

To run the bot using the docker run command, you'll need to create a `.env`file with the following keys:

```plaintext
TOKEN=Your_Discord_Bot_Token
APP=Your_Discord_Application_ID
CHANNEL=Default_Text_Channel_ID
```

Once your .env file is set up, run the container with:

````bash

docker run -d --name beatsync --env-file .env hasuuka/beatsync
````
## Using Docker Compose

If you prefer using Docker Compose for easier management, you can create a docker-compose.yml file in your project directory. Here’s an example configuration:

```yaml
services:
  beatsync:
    image: hasuuka/beatsync
    container_name: beatsync
    env_file:
      - .env
    restart: unless-stopped
```
To start the bot using Docker Compose, run:

```bash
docker-compose up -d
```
This command will start Containeer in detached mode.

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

This project is licensed under the GNU General Public License v3.0.

Contributions are welcome! If you encounter any bugs or want to suggest new features, feel free to open an issue or create a pull request. Enjoy your music! 🎶


