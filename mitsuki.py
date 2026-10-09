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

antrian = {}

ytdl = yt_dlp.YoutubeDL({
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
})

ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


def putar_lagu_berikutnya(ctx, error=None):
    vc = ctx.guild.voice_client
    if vc is None:
        return

    daftar = antrian.get(ctx.guild.id, [])

    if daftar:
        lagu = daftar.pop(0)
        vc.play(
            discord.FFmpegPCMAudio(lagu["url"], **ffmpeg_opts),
            after=lambda e: putar_lagu_berikutnya(ctx, e),
        )
        asyncio.run_coroutine_threadsafe(
            ctx.send(f"lagi mutar: **{lagu['judul']}**"), bot.loop
        )
    else:
        asyncio.run_coroutine_threadsafe(ctx.send("Antrean habis!"), bot.loop)

class PilihLagu(discord.ui.View):
    def __init__(self, daftar_lagu, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx

        for i, lagu in enumerate(daftar_lagu[:5]):
            judul = lagu["title"]
            artis = lagu["artists"][0]["name"] if lagu.get("artists") else "Unknown"

            tombol = discord.ui.Button(
                label=f"{i+1}. {judul} - {artis}"[:80],
                style=discord.ButtonStyle.primary,
            )
            tombol.callback = self.bikin_aksi(lagu["videoId"], f"{judul} - {artis}")
            self.add_item(tombol)

    def bikin_aksi(self, video_id, nama_lagu):
        async def aksi(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                return await interaction.response.send_message(
                    "Cuma yang request yang bisa klik!", ephemeral=True
                )

            await interaction.response.edit_message(
                content=f"mencari: **{nama_lagu}**...", view=None
            )

            try:
                info = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: ytdl.extract_info(
                        f"https://www.youtube.com/watch?v={video_id}", download=False
                    ),
                )
            except Exception as e:
                print("error yt-dlp:", e)
                return await self.ctx.send("lagunya nggak ada!")

            lagu = {"judul": nama_lagu, "url": info["url"]}
            antrian.setdefault(self.ctx.guild.id, [])

            vc = self.ctx.guild.voice_client

            if vc.is_playing() or vc.is_paused():
                antrian[self.ctx.guild.id].append(lagu)
                await self.ctx.send(f"masuk list: **{nama_lagu}**")
            else: 
                vc.play(
                    discord.FFmpegPCMAudio(lagu["url"], **ffmpeg_opts),
                    after=lambda e: putar_lagu_berikutnya(self.ctx, e),
                )
                await self.ctx.send(f"lagi mutar: **{nama_lagu}**")

        return aksi
    

@bot.event
async def on_ready():
    print(f'Haiii!! {bot.user.name} siap!!')


@bot.command()
async def play(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send("Masuk voice dulu oii!!")

    if ctx.guild.voice_client is None:
        await ctx.author.voice.channel.connect()

    await ctx.send(f"Mencari **{query}**...")

    hasil = await asyncio.get_event_loop().run_in_executor(
        None, lambda: ytmusic.search(query, filter="songs")
    )

    if not hasil:
        return await ctx.send("Emmm, lagunya nggak ada.")

    await ctx.send("Pilih lagunya ya:", view=PilihLagu(hasil, ctx))


@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("stop bentar")


@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Lanjut muter musik.")


@bot.command()
async def skip(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("Skip")


@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        antrian.get(ctx.guild.id, []).clear()   # kosongin antrian
        await ctx.voice_client.disconnect()      # keluar dari voice
        await ctx.send("Log antrian bersih saatnya pergi, byee.")


bot.run(os.getenv('DISCORD_TOKEN'))