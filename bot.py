import asyncio
import logging
import os
import discord
import yt_dlp as youtube_dl
import random
import re
from discord.ext import commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
disconnected = False

currentSong = {}

guessing_game_active = {}
song_title_masked = {}
guess_attempts = {}


# Create bot instance with command tree for slash commands
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, application_id=os.getenv('APP'))
        self.song_queue = {}  # A dictionary to keep track of playlists per server
        self.current_volume = {}  # A dictionary to store volume per server
        self.disconnect_timer = {}  # Dictionary to track timers for disconnection

    async def setup_hook(self):
        # Sync the slash commands with Discord
        await bot.tree.sync()
        logger.info("Slash commands have been synchronized.")

# Create bot instance
bot = MyBot()

# Ensure FFmpeg is in the PATH
FFMPEG_PATH = 'ffmpeg'

# Options for yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # IPv4 address
}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.genre = data.get('genre', 'Unknown Genre')

    @classmethod
    async def from_url(cls, url, *, loop=None, volume=0.5):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if 'entries' in data:
            # This is a playlist, return a list of YTDLSource instances for each entry
            return [cls(discord.FFmpegPCMAudio(entry['url'], **ffmpeg_options), data=entry, volume=volume) for entry in
                    data['entries']]

        # This is a single song
        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, volume=volume)

# Event when the bot has connected to Discord
@bot.event
async def on_ready():
    # Reset song queue, volume, and disconnect timers for all guilds
    bot.song_queue = {}  # Reset the song queue for all guilds
    bot.current_volume = {}  # Reset the volume settings for all guilds
    bot.disconnect_timer = {}  # Reset the disconnect timers for all guilds

    # Set the bot's status to "Doing nothing"
    await bot.change_presence(status=discord.Status.online,
                              activity=discord.Game(name="Doing nothing. Use /play to use me."))

    logger.info(f'Logged in as {bot.user}')

    # Optionally notify in the 'dj-remix' channel of each guild that the bot has restarted
    for guild in bot.guilds:
        # If the bot is in a voice channel, disconnect
        voice_client = guild.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()


        # Send a restart notification in the 'dj-remix' channel
        dj_channel = await get_channel(guild)
        if dj_channel:
            await dj_channel.send("I am back and ready!")


# Slash command to play music from YouTube by URL or keyword
@bot.tree.command(name="play", description="Plays a song or playlist from YouTube")
async def play(interaction: discord.Interaction, query: str):
    if not await check_channel(interaction):
        return

    if not interaction.user.voice:
        await interaction.response.send_message("You must be connected to a voice channel to play music.")
        return
    await interaction.response.defer()

    # Connecting bot to channel
    voice_client = interaction.guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        channel = interaction.user.voice.channel
        try:
            await channel.connect()
        except Exception as e:
            await interaction.followup.send(f"Failed to connect to the voice channel: {e}")
            return
        voice_client = interaction.guild.voice_client

    async with interaction.channel.typing():
        try:
            sources = await YTDLSource.from_url(query, loop=bot.loop,
                                                volume=bot.current_volume.get(interaction.guild.id, 0.05))
            is_playlist = isinstance(sources, list)

            # Initialize queue if not present
            if interaction.guild.id not in bot.song_queue:
                bot.song_queue[interaction.guild.id] = []

            added_count = 0

            if is_playlist:
                for player in sources:
                    if player.url not in [song['url'] for song in bot.song_queue[interaction.guild.id]]:
                        bot.song_queue[interaction.guild.id].append({'title': player.title, 'url': player.url})
                        added_count += 1

                if added_count > 0:
                    await interaction.followup.send(f'Added {added_count} songs to the queue.')

                if not voice_client.is_playing() and bot.song_queue[interaction.guild.id]:
                    await play_next_song(interaction.guild)

            else:
                if sources.url not in [song['url'] for song in bot.song_queue[interaction.guild.id]]:
                    bot.song_queue[interaction.guild.id].append({'title': sources.title, 'url': sources.url})
                    added_count += 1

                if not voice_client.is_playing():
                    await play_next_song(interaction.guild)

                elif added_count > 0:
                    await interaction.followup.send(f'Added {added_count} songs to the queue.')
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    logger.debug('Started on voice state update')
    global disconnected
    if disconnected:
        logger.debug('on voice state update aborted because disconnected is true')
        return

    guild = member.guild
    voice_client = guild.voice_client

    if voice_client is None:
        return  # If bot is not in a voice channel, do nothing

    await check_voice_channel(guild)
    logger.debug('on voice state update finished')


# Slash command to skip the current song
@bot.tree.command(name="skip", description="Skips the currently playing song")
async def skip(interaction: discord.Interaction):
    if not await check_channel(interaction):
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None or not voice_client.is_playing():
        await interaction.response.send_message("There is no song currently playing.", ephemeral=True)
        return

    voice_client.stop()  # Stops the current song, which triggers the next one to play
    await interaction.response.send_message("Skipped the current song.")


# Slash command to stop the music and clear the queue
@bot.tree.command(name="stop", description="Stops the music and clears the queue")
async def stop(interaction: discord.Interaction):
    if not await check_channel(interaction):
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None or not (voice_client.is_playing() or voice_client.is_paused()):
        await interaction.response.send_message("There is no music currently playing or paused.", ephemeral=True)
        return

    # Clear the queue and stop the current song
    bot.song_queue[interaction.guild.id] = []  # Clear the song queue
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()  # Stop any song, whether playing or paused

    # Reset the disconnect timer
    await reset_disconnect_timer(interaction.guild)

    await interaction.response.send_message("Stopped the music and cleared the queue.")


# Slash command to view the song queue
@bot.tree.command(name="queue", description="Shows the current playlist")
async def queue(interaction: discord.Interaction):
    # Defer the response to indicate processing time
    await interaction.response.defer()

    queue = bot.song_queue.get(interaction.guild.id, [])

    if not queue:
        await interaction.followup.send("The queue is currently empty.")
        return

    # Create a list of song titles with their positions
    queue_list = [f"{i + 1}. {song['title']}" for i, song in enumerate(queue)]

    # Split the queue into chunks that fit the 2000-character limit
    chunk_size = 1700  # Set a lower limit to account for formatting and possible padding
    chunks = []
    current_chunk = ""

    for item in queue_list:
        if len(current_chunk) + len(item) + 2 > chunk_size:  # +2 for "\n"
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += f"{item}\n"

    # Append the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)

    # Send each chunk as a separate message with error handling
    for chunk in chunks:
        try:
            await interaction.followup.send(chunk)
            await asyncio.sleep(1)  # Small delay to avoid rate limits
        except discord.HTTPException as e:
            logger.info(f"Failed to send message: {e}")
            break  # Exit on error to avoid excessive failures

    # After sending all chunks, inform that the queue has been displayed
    if chunks:
        await interaction.followup.send("Displayed the full queue.")


# Slash command to pause the music
@bot.tree.command(name="pause", description="Pauses the currently playing song")
async def pause(interaction: discord.Interaction):
    if not await check_channel(interaction):
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None or not voice_client.is_playing():
        await interaction.response.send_message("There is no song currently playing.", ephemeral=True)
        return

    if voice_client.is_paused():
        await interaction.response.send_message("The song is already paused.", ephemeral=True)
    else:
        voice_client.pause()

        # Reset the disconnect timer
        await reset_disconnect_timer(interaction.guild)

        await interaction.response.send_message("Paused the song.")


# Slash command to resume the music
@bot.tree.command(name="resume", description="Resumes the paused song")
async def resume(interaction: discord.Interaction):
    if not await check_channel(interaction):
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None or not voice_client.is_paused():
        await interaction.response.send_message("There is no song currently paused.", ephemeral=True)
        return

    voice_client.resume()
    await interaction.response.send_message("Resumed the song.")


# Slash command to adjust the volume
@bot.tree.command(name="volume", description="Adjusts the volume of the music")
async def volume(interaction: discord.Interaction, level: int):
    if not await check_channel(interaction):
        return

    if level < 0 or level > 100:
        await interaction.response.send_message("Please provide a volume level between 0 and 100.", ephemeral=True)
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None or not voice_client.is_playing():
        await interaction.response.send_message("There is no song currently playing.", ephemeral=True)
        return

    bot.current_volume[interaction.guild.id] = level / 100  # Store volume as a decimal
    voice_client.source.volume = bot.current_volume[interaction.guild.id]
    await interaction.response.send_message(f"Set the volume to {level}%.")

# Slash command to seek to a specific time in the current song
@bot.tree.command(name="seek", description="Seeks to a specific time in the current song")
async def seek(interaction: discord.Interaction, position: str):
    if not await check_channel(interaction):
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None or not voice_client.is_playing():
        await interaction.response.send_message("There is no song currently playing.", ephemeral=True)
        return

    # Parse the position input (MM:SS format or seconds)
    try:
        if ":" in position:
            minutes, seconds = map(int, position.split(":"))
            seek_position = minutes * 60 + seconds
        else:
            seek_position = int(position)
    except ValueError:
        await interaction.response.send_message("Invalid time format. Please use MM:SS or seconds.", ephemeral=True)
        return

    next_song_info = currentSong
    song_url = next_song_info['url']

    # Stop the current playback
    voice_client.stop()

    # Play the song from the seek position
    await play_song_with_seek(voice_client, song_url, seek_position, interaction.guild)
    await interaction.response.send_message(f"Seeked to {seek_position} seconds.")

# Slash command to start "Guess the Song" mode
@bot.tree.command(name="guess_the_song", description="Starts a 'Guess the Song' game with random YouTube songs.")
async def guess_the_song(interaction: discord.Interaction):
    if not await check_channel(interaction):
        return

    if not interaction.user.voice:
        await interaction.response.send_message("You must be connected to a voice channel to play 'Guess the Song'.")
        return

    await interaction.response.defer()

    # Connecting bot to voice channel if not already connected
    voice_client = interaction.guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        channel = interaction.user.voice.channel
        try:
            await channel.connect()
        except Exception as e:
            await interaction.followup.send(f"Failed to connect to the voice channel: {e}")
            return
        voice_client = interaction.guild.voice_client

    # Search for random songs on YouTube
    random_query = random.choice([
        "top hits 2024", "most popular songs", "underrated tracks", "classic rock hits",
        "hip-hop top 10", "EDM random mix", "90s pop hits", "current trending music"
    ])
    try:
        # Fetch random song results from YouTube
        sources = await YTDLSource.from_url(random_query, loop=bot.loop, volume=bot.current_volume.get(interaction.guild.id, 0.05))
        if isinstance(sources, list):
            # If it's a playlist, pick one song randomly
            source = random.choice(sources)
        else:
            source = sources

        # Save the current song title for guessing game
        guessing_game_active[interaction.guild.id] = True
        song_title_masked[interaction.guild.id] = re.sub(r'[^\s]', '_', source.title)  # Mask the song title
        guess_attempts[interaction.guild.id] = 0

        # Get the initials of the song title
        song_initials = ' '.join(word[0].upper() for word in source.title.split())

        # Store genre and song details
        currentSong[interaction.guild.id] = {
            'title': source.title,
            'url': source.url,
            'genre': source.genre,
            'initials': song_initials
        }

        # Add the song to the queue and start playing it
        bot.song_queue[interaction.guild.id] = [{'title': source.title, 'url': source.url}]
        await play_next_song(interaction.guild)

        # Announce the game
        await interaction.followup.send(
            f"🎵 Guess the song! Here's a clue: **{song_title_masked[interaction.guild.id]}**\n"
            f"Initials: **{song_initials}**\n"
            f"Genre: **{source.genre}**")

    except Exception as e:
        await interaction.followup.send(f"An error occurred while searching for a random song: {e}")

# Command for users to guess the song
@bot.tree.command(name="guess", description="Make a guess for the 'Guess the Song' game.")
async def guess_song(interaction: discord.Interaction, guess: str):
    if not guessing_game_active.get(interaction.guild.id, False):
        await interaction.response.send_message("There's no active 'Guess the Song' game right now.", ephemeral=True)
        return

    current_song = currentSong.get('title', '').lower()
    guess = guess.lower()

    guess_attempts[interaction.guild.id] += 1

    if guess in current_song:
        await interaction.response.send_message(f"🎉 Correct! The song was **{currentSong['title']}**.")
        guessing_game_active[interaction.guild.id] = False  # End the game
    else:
        await interaction.response.send_message(f"❌ Incorrect guess. Keep trying! Current clue: **{song_title_masked[interaction.guild.id]}**")

async def play_song_with_seek(voice_client, song_url, seek_position, guild):
    # Refetch the URL before seeking to ensure it's fresh and hasn't expired
    fresh_song_info = await YTDLSource.from_url(song_url, loop=bot.loop,volume=bot.current_volume.get(guild.id, 0.05))
    fresh_url = fresh_song_info.url

    # Set FFmpeg options with the seek position
    seek_ffmpeg_options = {
        'before_options': f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {seek_position}',
        'options': '-vn'
    }
    logger.info(f"Playing song with seek. {seek_position}")

    # Ensure the FFmpeg source uses the fresh URL and seek options
    player = discord.FFmpegPCMAudio(
        fresh_url,
        **seek_ffmpeg_options,
        executable="ffmpeg"
    )

    current_volume = bot.current_volume.get(guild.id, 0.05)  # Get the current volume, default to 50%
    player_with_volume = discord.PCMVolumeTransformer(player, volume=current_volume)

    # Play the audio with the specified seek position
    voice_client.play(player_with_volume, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(guild), bot.loop))


async def play_next_song(guild):
    global currentSong
    voice_client = guild.voice_client
    if voice_client and not voice_client.is_playing():
        queue = bot.song_queue.get(guild.id)
        if queue and len(queue) > 0:
            # Play the next song
            next_song_info = queue.pop(0)
            currentSong = next_song_info
            next_song_url = next_song_info['url']

            player = await YTDLSource.from_url(next_song_url, loop=bot.loop,volume=bot.current_volume.get(guild.id, 0.05))

            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(guild), bot.loop))
            await bot.change_presence(status=discord.Status.online, activity=discord.Game(name=next_song_info['title']))

            dj_channel = await get_channel(guild)
            if dj_channel:
                if guessing_game_active.get(guild.id, False):
                    await dj_channel.send(
                        f"Now playing a new song for 'Guess the Song'! Clue: **{song_title_masked[guild.id]}**")
                else:
                    await dj_channel.send(f'Now playing: {next_song_info["title"]}')

            # Cancel the existing disconnect timer if playing music
            if guild.id in bot.disconnect_timer:
                bot.disconnect_timer[guild.id].cancel()
                del bot.disconnect_timer[guild.id]

        else:
            # If no more songs in queue, start the disconnect timer
            await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="Use /play to use me."))
            await start_disconnect_timer(guild)

async def get_channel(guild):
    # Get the channel name from the environment variable, with a default value of 'dj-remix'
    channel_name = os.getenv('CHANNEL')
    if not channel_name:
        raise ValueError("No Channel found. Please set the CHANNEL environment variable.")

    # Find the text channel with the name from the environment variable
    for channel in guild.text_channels:
        if channel.name == channel_name:
            return channel

    return None


async def start_disconnect_timer(guild):
    if guild.id not in bot.disconnect_timer:
        bot.disconnect_timer[guild.id] = asyncio.create_task(disconnect_after_timeout(guild))


async def reset_disconnect_timer(guild):
    if guild.id in bot.disconnect_timer:
        bot.disconnect_timer[guild.id].cancel()  # Cancel existing timer
        del bot.disconnect_timer[guild.id]  # Remove the entry
    await start_disconnect_timer(guild)  # Restart the timer


async def disconnect_after_timeout(guild):
    logger.debug('Timer started')
    global disconnected
    await asyncio.sleep(120)  # 2 minutes
    logger.debug('2 min passed')
    voice_client = guild.voice_client
    # Ensure voice_client exists and is not playing any song
    if voice_client and not voice_client.is_playing() and len(bot.song_queue.get(guild.id, [])) == 0:
        disconnected = True
        logger.info('No song in queue and bot not playing. Disconnecting.')
        await voice_client.disconnect()
        dj_channel = await get_channel(guild)
        if dj_channel:
            await dj_channel.send("Disconnected due to inactivity.")
    else:
        logger.info('Timer aborted: Either song is playing or queue is not empty.')

# Check for empty voice channel
async def check_voice_channel(guild):
    logger.debug('Check voice channel started')

    voice_client = guild.voice_client
    if voice_client and len(voice_client.channel.members) == 1:  # Only bot is left in the channel
        logger.info('Bot is alone. Disconnecting.')
        await voice_client.disconnect()
        dj_channel = await get_channel(guild)
        if dj_channel:
            await dj_channel.send("Disconnected because there are no users in the channel.")


# Function to check if the command is invoked in the correct channel
async def check_channel(interaction):
    dj_channel = await get_channel(interaction.guild)
    if interaction.channel != dj_channel:
        await interaction.response.send_message("This command can only be used in the dj-remix channel.",
                                                ephemeral=True)
        return False
    return True


# Retrieve the bot token from the environment variable
bot_token = os.getenv('BOT')

if not bot_token:
    raise ValueError("No bot token found. Please set the BOT environment variable.")

# Run the bot using the token from the environment
bot.run(bot_token)
