import logging

import discord
from discord.ext import commands
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

ydl_opts = {
    "format": "bestaudio",
    "noplaylist": True,
    "quiet": True,
    "default_search": "scsearch",
}


def search_sc(query: str) -> str | None:
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]
            logger.info(f"Found SC track URL for query: {query}")
            return info["url"]
        except Exception as e:
            logger.error(f"SoundCloud search error: {e}")
            return None


async def play_music(ctx: commands.Context, query: str) -> None:
    if not ctx.author.voice:
        await ctx.send("Join a voice channel first!")
        return

    if not (url := search_sc(query)):
        await ctx.send("Failed to find audio stream")
        return

    voice = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
    if not voice:
        voice = await ctx.author.voice.channel.connect()

    if voice.is_playing():
        voice.stop()

    try:
        audio = discord.FFmpegPCMAudio(
            url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            options="-vn",
        )
        voice.play(
            audio,
            after=lambda e: logger.info("Track finished")
            if not e
            else logger.error(f"Playback error: {e}"),
        )
        await ctx.send("Playback started!")
        logger.info(f"Playing SC track for {ctx.author} in {ctx.guild.name}")
    except Exception as e:
        logger.error(f"Playback error: {e}")


async def play_music_in_channel(voice_client: discord.VoiceClient, query: str) -> None:
    if not (url := search_sc(query)):
        logger.error("Failed to find audio stream")
        return

    if voice_client.is_playing():
        voice_client.stop()

    try:
        audio = discord.FFmpegPCMAudio(
            url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            options="-vn",
        )
        voice_client.play(
            audio,
            after=lambda e: logger.info("Track finished")
            if not e
            else logger.error(f"Playback error: {e}"),
        )
        logger.info(f"Playing SC track in {voice_client.channel.name}")
    except Exception as e:
        logger.error(f"Playback error: {e}")
