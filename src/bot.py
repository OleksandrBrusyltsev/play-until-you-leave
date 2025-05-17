import asyncio
import logging
import os
import threading

import discord
from discord.ext import commands
from dotenv import load_dotenv
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_fixed

from api import run_api
from music import play_music, play_music_in_channel

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
DEFAULT_TRACK = "top playlist"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def any_voice_users(guild: discord.Guild) -> bool:
    return any(
        not member.bot for channel in guild.voice_channels for member in channel.members
    )

async def join_and_play(channel: discord.VoiceChannel, query: str = DEFAULT_TRACK) -> None:
    voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)
    if voice_client and voice_client.channel == channel and voice_client.is_connected():
        logger.debug("Already connected to the voice channel.")
        return
    if voice_client:
        logger.debug("Disconnecting from previous voice channel.")
        await voice_client.disconnect()
        await asyncio.sleep(2)
    voice_client = await channel.connect()
    try:
        await play_music_with_retry(voice_client, query)
        logger.info(f"Playing music in {channel.name}")
    except Exception as e:
        logger.error(f"Playback failed after retries: {e}")
        await voice_client.disconnect()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def play_music_with_retry(voice_client, query: str):
    if not voice_client.is_connected():
        logger.warning("Voice client disconnected. Reconnecting to voice channel...")
        try:
            await voice_client.disconnect()
        except Exception:
            pass
        voice_client = await voice_client.channel.connect()
    await play_music_in_channel(voice_client, query)

async def music_presence_checker() -> None:
    await bot.wait_until_ready()
    guild = bot.get_guild(GUILD_ID)
    channel = bot.get_channel(CHANNEL_ID)
    logger.debug(f"Startup checker:{GUILD_ID=}, {CHANNEL_ID=}, {guild=},{channel=}")
    if not guild or not channel:
        logger.error(f"Guild or channel not found: {GUILD_ID=}, {CHANNEL_ID=}")

    while not bot.is_closed():
        logger.debug(f"Current voice_clients: {bot.voice_clients}")
        voice_client = discord.utils.get(bot.voice_clients, guild=guild)
        try:
            has_users = await any_voice_users(guild)
            logger.debug(f"Any voice users: {has_users}, voice_client: {voice_client}")
            if has_users and not voice_client:
                logger.info("Voice users detected, joining channel...")
                await join_and_play(channel)
            elif not has_users and voice_client:
                await voice_client.disconnect()
                logger.info("No voice users, disconnected from voice channel.")
        except Exception as e:
            logger.exception(f"Unhandled occupancy error: {e}")
        await asyncio.sleep(30)

@bot.event
async def on_ready() -> None:
    logger.info(f"Bot {bot.user.name} started")
    bot.loop.create_task(music_presence_checker())

@bot.command()
async def play(ctx: commands.Context, *, query: str = DEFAULT_TRACK) -> None:
    if not ctx.author.voice:
        await ctx.send("Join a voice channel first!")
        return
    try:
        await play_music(ctx, query)
        logger.info(f"Play SC command executed by {ctx.author}")
    except Exception as e:
        logger.error(f"Play SC command error: {e}")
        await ctx.send(f"Playback error: {e}")

@bot.command()
async def leave(ctx: commands.Context) -> None:
    if voice_client := discord.utils.get(bot.voice_clients, guild=ctx.guild):
        await voice_client.disconnect()
        await ctx.send("Left voice channel")
        logger.info(f"Left voice channel in {ctx.guild.name}")
    else:
        await ctx.send("Not in a voice channel")

if __name__ == "__main__":
    threading.Thread(
        target=run_api, daemon=True
    ).start()  # uvicorn needs its own event loop
    bot.run(TOKEN)
