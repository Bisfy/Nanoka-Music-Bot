import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
from ytmusicapi import YTMusic

load_dotenv('token.env')
ytmusic = YTMusic()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

music_queue = {}

ytdl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'cookiesfrombrowser': ('chrome',) 
}
ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn -b:a 192k'
}
ytdl = yt_dlp.YoutubeDL(ytdl_opts)

def play_next(ctx):
    gid = ctx.guild.id
    if gid in music_queue and music_queue[gid]:
        url = music_queue[gid].pop(0)
        ctx.guild.voice_client.play(discord.FFmpegPCMAudio(url, **ffmpeg_opts), after=lambda e: play_next(ctx))
    else:
        asyncio.run_coroutine_threadsafe(ctx.send("Nggak ada lagi musik yang diputar.."), bot.loop)

class SongSelect(discord.ui.View):
    def __init__(self, tracks, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        for i, t in enumerate(tracks[:5]):
            title = t['title']
            artist = t.get('artists', [{'name': 'Unknown'}])[0]['name']
            label = f"{i+1}. {title} - {artist}"[:80] # NOT3 : Maksimal 80 huruf biar tombol ga error
            
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.primary)
            btn.callback = self.make_callback(t['videoId'], f"{title} - {artist}")
            self.add_item(btn)

    def make_callback(self, vid_id, name):
        async def cb(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                return await interaction.response.send_message("YRRA, Yang Request Request Aja", ephemeral=True)
            
            await interaction.response.edit_message(content=f"Nyari audio: **{name}**...", view=None)
            
            url = f"https://www.youtube.com/watch?v={vid_id}"
            data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            stream_url = data['url']
            
            vc, gid = self.ctx.guild.voice_client, self.ctx.guild.id
            if gid not in music_queue: 
                music_queue[gid] = []
            
            if vc.is_playing():
                music_queue[gid].append(stream_url)
                await self.ctx.send(f"Masuk list: **{name}**")
            else:
                vc.play(discord.FFmpegPCMAudio(stream_url, **ffmpeg_opts), after=lambda e: play_next(self.ctx))
                await self.ctx.send(f"Lagi muter: **{name}**")
        return cb

@bot.event
async def on_ready():
    print(f'Haaiiii!!{bot.user.name} siap!!')

@bot.command()
async def play(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send("Masuk voice channel dulu oii!")
    
    vc = ctx.guild.voice_client or await ctx.author.voice.channel.connect()
    await ctx.send(f"Mencari **{query}**...")

    tracks = ytmusic.search(query, filter="songs")
    if not tracks:
        return await ctx.send("Eeee, lagunya nggak ketemu")
    
    await ctx.send("Pilih lagunya:", view=SongSelect(tracks, ctx))

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Berhenti sebentar")

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Lanjut")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skip.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        music_queue.get(ctx.guild.id, []).clear()
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("Antrian bersih, saatnya pergi.. Byee")

bot.run(os.getenv('DISCORD_TOKEN'))