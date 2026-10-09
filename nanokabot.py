import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv('token.env')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Setup bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# konfig ytdlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

music_queue = {}

def play_next(ctx):
    server_id = ctx.message.guild.id
    if server_id in music_queue and len(music_queue[server_id]) > 0:
        url = music_queue[server_id].pop(0)
        vc = ctx.message.guild.voice_client
        vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_options), after=lambda e: play_next(ctx))
    else:
        asyncio.run_coroutine_threadsafe(ctx.send("Antrean habis!"), bot.loop)

@bot.event
async def on_ready():
    print(f'Hai! aku {bot.user.name} udah siap muter lagu')

@bot.command(name='play', help='Kasih judulnya')
async def play(ctx, *, query):
    if not ctx.message.author.voice:
        return await ctx.send("Masuk ke voice channel dulu dong!")
    
    channel = ctx.message.author.voice.channel
    vc = ctx.message.guild.voice_client

    if not vc:
        vc = await channel.connect()

    await ctx.send(f"Memproses: `{query}`...")
    
    # nyari lagu di yt modal ytdlp
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{query}", download=False))
    
    if 'entries' in data:
        data = data['entries'][0]
    
    url2 = data['url']
    server_id = ctx.message.guild.id

    if server_id not in music_queue:
        music_queue[server_id] = []

    if vc.is_playing():
        music_queue[server_id].append(url2)
        await ctx.send(f"Ok, lagunya masuk antrian: **{data['title']}**")
    else:
        vc.play(discord.FFmpegPCMAudio(url2, **ffmpeg_options), after=lambda e: play_next(ctx))
        await ctx.send(f"Lagi muter: **{data['title']}**")

@bot.command(name='pause', aliases=['mute'], help='stop bentar')
async def pause(ctx):
    vc = ctx.message.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("Lagunya berhenti dulu")
    else:
        await ctx.send("Mau dengerin apa nih? nggak ada yang muter soalnya")

@bot.command(name='resume', aliases=['start'], help='Lanjut!!!')
async def resume(ctx):
    vc = ctx.message.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("Lanjut muter")
    else:
        await ctx.send("Lagu nggak dipause.")

@bot.command(name='skip', help='Skip')
async def skip(ctx):
    vc = ctx.message.guild.voice_client
    if vc and vc.is_playing():
        vc.stop() 
        await ctx.send("Lagunya diskip")
    else:
        await ctx.send("Apa yang mau diskip?.")

@bot.command(name='stop', help='Stop and cleaning queue...')
async def stop(ctx):
    vc = ctx.message.guild.voice_client
    server_id = ctx.message.guild.id
    if vc:
        if server_id in music_queue:
            music_queue[server_id].clear() # Bersihin antrean
        vc.stop()
        await vc.disconnect()
        await ctx.send("ok, byeee have a nice dayy")

bot.run(DISCORD_TOKEN)