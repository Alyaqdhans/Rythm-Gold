bot_token = "your_bot_token" #change the string to your bot token

import asyncio
import discord
from discord.ext import commands
from youtube_dl import YoutubeDL

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'cachedir': False,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="$", case_insensitive=True, intents=intents)
colour = discord.Colour.dark_gold()

bot.remove_command("help")

@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready.")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="$help"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(colour=colour, description='❌ **Command is missing check `$help`**')
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CheckAnyFailure):
        embed = discord.Embed(colour=colour, description='❌ **You need `DJ` role**')
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(colour=colour, description=f"`{error}`")
        await ctx.send(embed=embed)
        raise error

class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.song_queue = {}
        self.loop = False
        self.skip_time = False
        self.play_time = False
        self.song = None
        self.setup()

    def setup(self):
        for guild in self.bot.guilds:
            self.song_queue[guild.id] = []

    async def search_song(self, amount, song, get_url=False):
        info = await self.bot.loop.run_in_executor(None, lambda: YoutubeDL(YDL_OPTIONS).extract_info(f"ytsearch{amount}:{song}", download=False, ie_key="YoutubeSearch"))
        if len(info["entries"]) == 0: return None
        return [entry["webpage_url"] for entry in info["entries"]] if get_url else info

    async def check_queue(self, ctx):
        if ctx.voice_client is not None:
            members = ctx.voice_client.channel.members
            memids = []
            for member in members:
                if not member.bot:
                    memids.append(member.id)
            if not len(memids) > 0:
                await ctx.voice_client.disconnect()
                if len(self.song_queue[ctx.guild.id]) > 0:
                    self.song_queue[ctx.guild.id].clear()
                self.loop = False
                embed = discord.Embed(colour=colour, description='💀 **Queue Force Ended**')
                embed.set_footer(text="The voice channel is empty.")
                return await ctx.send(embed=embed)
        else:
            if len(self.song_queue[ctx.guild.id]) > 0:
                self.song_queue[ctx.guild.id].clear()
            self.loop = False
            #embed = discord.Embed(colour=colour, description=f'☹ **Why you disconnect me like that.**')
            return #await ctx.send(embed=embed)
        if len(self.song_queue[ctx.guild.id]) > 0:
            await self.play_song(ctx, self.song_queue[ctx.guild.id][0])
            if self.loop:
                self.song_queue[ctx.guild.id].append(self.song_queue[ctx.guild.id][0])
            self.song_queue[ctx.guild.id].pop(0)
        else:
            if ctx.voice_client is not None:
                await ctx.voice_client.disconnect()
            self.loop = False
            embed = discord.Embed(colour=colour, description='🗿 **Queue Ended**')
            await ctx.send(embed=embed)

    async def play_song(self, ctx, song):
        try:
            ydl = YoutubeDL(YDL_OPTIONS)
            #ydl.cache.remove()
            info = ydl.extract_info(song, download=False)
            url = info['formats'][0]['url']
            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=lambda error: self.bot.loop.create_task(self.check_queue(ctx)))
            self.song = song
        except:
            await ctx.voice_client.disconnect()
            if len(self.song_queue[ctx.guild.id]) > 0:
                self.song_queue[ctx.guild.id].clear()
            self.loop = False
            embed = discord.Embed(colour=colour, description=f'☹ **Something went wrong while trying to play [song]({song})**')
            await ctx.send(embed=embed)

    async def time_format(self, sec):
        total_seconds = sec
        hours = (total_seconds - ( total_seconds % 3600))/3600
        seconds_minus_hours = (total_seconds - hours*3600)
        minutes = (seconds_minus_hours - (seconds_minus_hours % 60) )/60
        seconds = seconds_minus_hours - minutes*60
        if total_seconds < 3600:
            return '{}:{:02d}'.format(int(minutes), int(seconds))
        else:
            return '{}:{:02d}:{:02d}'.format(int(hours), int(minutes), int(seconds))
  
    @commands.command()
    async def help(self, ctx):
        em = discord.Embed(colour=colour)
        em.add_field(name = "$play ($p)", value = "Plays music by name or youtube link.")
        em.add_field(name = "$stop", value = "Stops the player (Requires DJ role).")
        em.add_field(name = "$search", value = "Searches 10 youtube links for the song name.")
        em.add_field(name = "$skip", value = "Runs the vote skip for the current song.")
        em.add_field(name = "$forceskip ($fs)", value = "Force skips the current song (Requires DJ role).")
        em.add_field(name = "$queue ($q)", value = "Checks for the current songs in the queue.")
        em.add_field(name = "$pause", value = "Pauses the playing song.")
        em.add_field(name = "$resume", value = "Resumes the paused song.")
        em.add_field(name = "$loop", value = "Repeats the songs in the queue.")
        em.add_field(name = "$remove ($r)", value = "Removes a specific song from the queue (Requires DJ role).")
        em.add_field(name = "$clear", value = "Clears the songs in the queue (Requires DJ role).")
        em.add_field(name = "$nowplaying ($np)", value = "Shows the current playing song.")
        await ctx.send(embed=em)

    @commands.command()
    async def ping(self, ctx):
        embed = discord.Embed(colour=colour, description=f'**My ping is `{round(bot.latency*1000)} ms`**')
        await ctx.send(embed=embed)

    @commands.command(aliases=["disconnect", "leave"])
    @commands.check_any(commands.is_owner(), commands.has_role("DJ"))
    async def stop(self, ctx):
        if ctx.voice_client is None:
            embed = discord.Embed(colour=colour, description='⛔ **I am not in a voice channel**')
            return await ctx.send(embed=embed)

        if ctx.author.voice is None:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in a voice channel**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in my voice channel**')
            return await ctx.send(embed=embed)

        embed = discord.Embed(colour=colour, description='✅ **Player Stopped**')
        await ctx.send(embed=embed)
        await ctx.voice_client.disconnect()

    @commands.command(aliases=["p"])
    async def play(self, ctx, *, song=None):            
        if ctx.author.voice is None:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in a voice channel**')
            return await ctx.send(embed=embed)

        if not ctx.author.voice.channel.permissions_for(ctx.guild.me).connect and ctx.voice_client is None:
            embed = discord.Embed(colour=colour, description='❌ **Missing `connect` permission in your voice channel**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id == ctx.guild.afk_channel.id:
            embed = discord.Embed(colour=colour, description='❌ **Cannot play in AFK channel**')
            return await ctx.send(embed=embed)

        if song is None:
            embed = discord.Embed(colour=colour, description='❌ **You must include a song to play**')
            return await ctx.send(embed=embed)

        if "list" in song:
            embed = discord.Embed(colour=colour, description='❌ **Cannot play playlists**')
            return await ctx.send(embed=embed)

        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect()

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in my voice channel**')
            return await ctx.send(embed=embed)

        if self.play_time:
            embed = discord.Embed(colour=colour, description='❌ **There is a song in process, try again in a few moments.**')
            return await ctx.send(embed=embed)

        self.play_time = True
        """
        if "list" in song:
            try:
                embed = discord.Embed(colour=colour, description='⏱ **Downloading the list, please wait..**')
                temp = await ctx.send(embed=embed)
                ydl = YoutubeDL(YDL_OPTIONS)
                info = ydl.extract_info(song, download=False)
                name = info['entries'][0]['playlist']
                thumbnail = info['entries'][0]['thumbnail']
                total_dur = 0
                num = 0
                for i,_ in enumerate(info['entries']):
                    num += 1
                    url = info['entries'][i]['webpage_url']
                    total_dur += info['entries'][i]['duration']
                    if ctx.voice_client.source is not None:
                        self.song_queue[ctx.guild.id].append(url)
                    else:
                        await self.play_song(ctx, url)
                        self.song = url
                
                embs = discord.Embed(colour=colour, title='Playlist added to the queue', description=f"[{name}]({song})")
                embs.set_thumbnail(url=thumbnail)
                embs.add_field(name="Enqueued", value=f"`{num}` songs")
                dur = await self.time_format(total_dur)
                embs.add_field(name="Duration", value=f"`{dur}`")
                embs.add_field(name="Requested by", value=ctx.author.mention)
                self.play_time = False
                return await temp.edit(embed=embs)
            except:
                embed = discord.Embed(colour=colour, description='☹ **Failed to download the playlist, try again.**')
                if not len(self.song_queue[ctx.guild.id]) > 0:
                    await ctx.voice_client.disconnect()
                self.play_time = False
                return await temp.edit(embed=embed)
        """
        # handle song where song isn't url
        if not ("youtube.com/watch?" in song or "https://youtu.be/" in song):
            embed = discord.Embed(colour=colour, description='⏱ **Searching for song, this may take a few seconds..**')
            embed.set_footer(text="Using the song link is faster than using its name.")
            temp = await ctx.send(embed=embed)

            try:
                result = await self.search_song(1, song, get_url=True)
                
                if result is None:
                    embed = discord.Embed(colour=colour, description='☹ **Sorry, I could not find the given song, try again or use my search command.**')
                    if not len(self.song_queue[ctx.guild.id]) > 0:
                        await ctx.voice_client.disconnect()
                    self.play_time = False
                    return await temp.edit(embed=embed)

                song = result[0]
                embed = discord.Embed(colour=colour, description='⏱ **Downloading the song, please wait..**')
                await temp.edit(embed=embed)
            except:
                embed = discord.Embed(colour=colour, description='☹ **Failed to download the song, try again or use my search command.**')
                if not len(self.song_queue[ctx.guild.id]) > 0 and ctx.voice_client.source is None:
                    await ctx.voice_client.disconnect()
                self.play_time = False
                return await temp.edit(embed=embed)

        else:
            embed = discord.Embed(colour=colour, description='⏱ **Downloading the song, please wait..**')
            temp = await ctx.send(embed=embed)

        try:
            ydl = YoutubeDL(YDL_OPTIONS)
            #ydl.cache.remove()
            info_dict = ydl.extract_info(song, download=False)
            title = info_dict.get('title', None)
            thumbnail = info_dict.get('thumbnail', None)
            duration = info_dict.get('duration', None)
        except:
            embed = discord.Embed(colour=colour, description='☹ **Failed to download the song, try again or use my search command.**')
            if not len(self.song_queue[ctx.guild.id]) > 0 and ctx.voice_client.source is None:
                await ctx.voice_client.disconnect()
            self.play_time = False
            return await temp.edit(embed=embed)
        if ctx.voice_client.source is not None:
            queue_len = len(self.song_queue[ctx.guild.id])
            if self.loop:
                self.song_queue[ctx.guild.id].insert(-1, song)
            else:
                self.song_queue[ctx.guild.id].append(song)
            embs = discord.Embed(colour=colour, title='Added to the queue', description=f"[{title}]({song})")
            embs.set_thumbnail(url=thumbnail)
            embs.add_field(name="Requested by", value=ctx.author.mention)

            durs = await self.time_format(duration)
            embs.add_field(name="Duration", value=f"`{durs}`")
            if queue_len == 1:
                embs.set_footer(text=f"{queue_len} song in the queue.")
            elif queue_len > 1:
                embs.set_footer(text=f"{queue_len} songs in the queue.")
            self.play_time = False
            return await temp.edit(embed=embs)
    
        emb = discord.Embed(colour=colour, title='Now Playing',
        description=f"[{title}]({song})")
        emb.set_thumbnail(url=thumbnail)
        emb.add_field(name="Requested by", value=ctx.author.mention)
        
        dur = await self.time_format(duration)
        emb.add_field(name="Duration", value=f"`{dur}`")

        await self.play_song(ctx, song)
        self.play_time = False
        self.song = song
        await temp.edit(embed=emb)

    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx):
        if ctx.voice_client is None or ctx.voice_client.source is None:
            embed = discord.Embed(colour=colour, description='❌ **I am not playing any song**')
            return await ctx.send(embed=embed)
        embed = discord.Embed(colour=colour, description='⏱ **Checking The Song..**')
        temp = await ctx.send(embed=embed)
        queue_len = len(self.song_queue[ctx.guild.id])
        try:
            ydl = YoutubeDL(YDL_OPTIONS)
            #ydl.cache.remove()
            info_dict = ydl.extract_info(self.song, download=False)
            title = info_dict.get('title', None)
            thumbnail = info_dict.get('thumbnail', None)
            author = info_dict.get('uploader', None)
            duration = info_dict.get('duration', None)
        except:
            embed = discord.Embed(colour=colour, description='☹ **Failed to check the song, try again.**')
            return await temp.edit(embed=embed)

        emb = discord.Embed(colour=colour, title='Now Playing',
        description=f"[{title}]({self.song})")
        emb.set_thumbnail(url=thumbnail)
        emb.add_field(name="Author", value=f"`{author}`")

        dur2 = await self.time_format(duration)
        emb.add_field(name="Duration", value=f"`{dur2}`")
        if queue_len == 1:
            emb.set_footer(text=f"{queue_len} song in the queue.")
        elif queue_len > 1:
            emb.set_footer(text=f"{queue_len} songs in the queue.")
        await temp.edit(embed=emb)

    @commands.command(aliases=["repeat"])
    async def loop(self, ctx):
        if ctx.voice_client is None or ctx.voice_client.source is None:
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song**')
            return await ctx.send(embed=embed)

        if ctx.author.voice is None:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in a voice channel**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in my voice channel**')
            return await ctx.send(embed=embed)
        if self.loop:
            if len(self.song_queue[ctx.guild.id]) > 0:
                self.song_queue[ctx.guild.id].pop()
            self.loop = False
            embed = discord.Embed(colour=colour, description="🔄 **Loop Mode `🔴off`**")
            await ctx.send(embed=embed)
        else:
            self.song_queue[ctx.guild.id].append(self.song)
            self.loop = True
            embed = discord.Embed(colour=colour, description="🔄 **Loop Mode `🟢on`**")
            await ctx.send(embed=embed)

    @commands.command()
    async def search(self, ctx, *, song=None):
        if song is None:
            embed = discord.Embed(colour=colour, description='❌ **You forgot to include a song to search for**')
            return await ctx.send(embed=embed)

        embed = discord.Embed(colour=colour, description='⏱ **Searching, this may take a few seconds..**')
        temp = await ctx.send(embed=embed)

        try:
            info = await self.search_song(10, song)
        except:
            embed = discord.Embed(colour=colour, description='☹ **Sorry, I could not find the given song, try again.**')
            return await temp.edit(embed=embed)

        embed = discord.Embed(title=f"Results for `{song}`:", description="*You can use these URL's to play an exact song if the one you want isn't the first result.*\n", colour=colour)
        
        amount = 0
        i = 1
        for entry in info["entries"]:
            embed.description += f"{i}) [{entry['title']}]({entry['webpage_url']})\n"
            amount += 1
            i += 1

        embed.set_footer(text=f"Displaying the first {amount} results.")
        await temp.edit(embed=embed)

    @commands.command(aliases=["q"])
    async def queue(self, ctx): # display the current guilds queue
        if ctx.voice_client is None:
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song**')
            return await ctx.send(embed=embed)

        if len(self.song_queue[ctx.guild.id]) == 0:
            embed = discord.Embed(colour=colour, description='❌ **The Queue is Empty**')
            return await ctx.send(embed=embed)

        embed = discord.Embed(colour=colour, description='⏱ **Fetching The Queue..**')
        temp = await ctx.send(embed=embed)

        embed = discord.Embed(title="Queue List", description="", colour=colour)
        i = 1
        qd = 0
        try:
            for url in self.song_queue[ctx.guild.id]:
                ydl = YoutubeDL(YDL_OPTIONS)
                #ydl.cache.remove()
                info_dict = ydl.extract_info(url, download=False)
                title = info_dict.get('title', None)
                duration = info_dict.get('duration', None)
                qd += duration
                embed.description += f"{i}) [{title}]({url})\n"
                i += 1
            dur = await self.time_format(qd)
            embed.add_field(name="Queue Duration", value=f"`{dur}`")
            await temp.edit(embed=embed)
        except:
            embed = discord.Embed(colour=colour, description='☹ **Failed to fetch the queue, try again.**')
            return await temp.edit(embed=embed)

    @commands.command()
    async def skip(self, ctx):
        self.skip_time = True
        if ctx.voice_client is None or ctx.voice_client.source is None:
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song**')
            return await ctx.send(embed=embed)

        if ctx.author.voice is None:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in a voice channel**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in my voice channel**')
            return await ctx.send(embed=embed)

        poll = discord.Embed(title=f"Vote to Skip Song by - {ctx.author.name}#{ctx.author.discriminator}", description="**80% of the voice channel must vote to skip for it to pass.**", colour=discord.Colour.blue())
        poll.add_field(name="Skip", value=":white_check_mark:")
        poll.add_field(name="Stay", value=":no_entry_sign:")
        poll.set_footer(text="Voting ends in 15 seconds.")

        poll_msg = await ctx.send(embed=poll) # only returns temporary message, we need to get the cached message to get the reactions
        poll_id = poll_msg.id

        await poll_msg.add_reaction(u"\u2705") # yes
        await poll_msg.add_reaction(u"\U0001F6AB") # no
        
        await asyncio.sleep(15) # 15 seconds to vote

        poll_msg = await ctx.channel.fetch_message(poll_id)
        
        votes = {u"\u2705": 0, u"\U0001F6AB": 0}
        reacted = []

        for reaction in poll_msg.reactions:
            if reaction.emoji in [u"\u2705", u"\U0001F6AB"]:
                async for user in reaction.users():
                    if user.voice.channel.id == ctx.voice_client.channel.id and user.id not in reacted and not user.bot:
                        votes[reaction.emoji] += 1

                        reacted.append(user.id)

        skip = False
        
        if votes[u"\u2705"] > 0:
            if votes[u"\U0001F6AB"] == 0 or votes[u"\u2705"] / (votes[u"\u2705"] + votes[u"\U0001F6AB"]) > 0.79: # 80% or higher
                skip = True
                embed = discord.Embed(title="Skip Successful", description="***Voting to skip the current song was succesful, skipping now.***", colour=discord.Colour.green())

        if not skip:
            embed = discord.Embed(title="Skip Failed", description="*Voting to skip the current song has failed.*\n\n**Voting failed, the vote requires at least 80% of the members to skip.**", colour=discord.Colour.red())

        embed.set_footer(text="Voting has ended.")

        await poll_msg.clear_reactions()
        await poll_msg.edit(embed=embed)

        if skip:
            ctx.voice_client.stop()

        self.skip_time = False

    @commands.command(aliases=["r"])
    @commands.check_any(commands.is_owner(), commands.has_role("DJ"))
    async def remove(self, ctx, index: int=None):
        if ctx.voice_client is None:
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song**')
            return await ctx.send(embed=embed)

        if ctx.author.voice is None:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in a voice channel**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in my voice channel**')
            return await ctx.send(embed=embed)
            
        if index is None:
            embed = discord.Embed(colour=colour, description='❌ **You must include the song number**')
            return await ctx.send(embed=embed)

        if len(self.song_queue[ctx.guild.id]) > 0:
            number = index - 1
            self.song_queue[ctx.guild.id].pop(number)
            embed = discord.Embed(colour=colour, description=f'✅ **({number + 1}) removed from the queue**')
            return await ctx.send(embed=embed)
        else:
            embed = discord.Embed(colour=colour, description='❌ **The Queue is Empty**')
            return await ctx.send(embed=embed)

    @commands.command(aliases=["fs"])
    @commands.check_any(commands.is_owner(), commands.has_role("DJ"))
    async def forceskip(self, ctx):
        if self.skip_time:
            embed = discord.Embed(colour=colour, description='❌ **Vote skip is in progress**')
            return await ctx.send(embed=embed)

        if ctx.voice_client is None or ctx.voice_client.source is None:
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song**')
            return await ctx.send(embed=embed)

        if ctx.author.voice is None:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in a voice channel**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in my voice channel**')
            return await ctx.send(embed=embed)

        ctx.voice_client.stop()
        embed = discord.Embed(colour=colour, description='⏩ **Force Skipped**')
        await ctx.send(embed=embed)

    @commands.command()
    @commands.check_any(commands.is_owner(), commands.has_role("DJ"))
    async def clear(self, ctx):
        if ctx.voice_client is None:
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song**')
            return await ctx.send(embed=embed)

        if ctx.author.voice is None:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in a voice channel**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in my voice channel**')
            return await ctx.send(embed=embed)

        if len(self.song_queue[ctx.guild.id]) < 0:
            embed = discord.Embed(colour=colour, description='❌ **The Queue is Empty**')
            return await ctx.send(embed=embed)

        self.song_queue[ctx.guild.id].clear()
        embed = discord.Embed(colour=colour, description='✅ **Queue Cleared**')
        await ctx.send(embed=embed)

    @commands.command()
    async def pause(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in a voice channel**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in my voice channel**')
            return await ctx.send(embed=embed)

        if ctx.voice_client.is_paused():
            embed = discord.Embed(colour=colour, description='❌ **The song is already paused**')
            return await ctx.send(embed=embed)

        ctx.voice_client.pause()
        embed = discord.Embed(colour=colour, description='⏸ **Paused**')
        await ctx.send(embed=embed)

    @commands.command()
    async def resume(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in a voice channel**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            embed = discord.Embed(colour=colour, description='⛔ **You are not in my voice channel**')
            return await ctx.send(embed=embed)

        if not ctx.voice_client.is_paused():
            embed = discord.Embed(colour=colour, description='❌ **The song is already resuming**')
            return await ctx.send(embed=embed)

        ctx.voice_client.resume()
        embed = discord.Embed(colour=colour, description='▶ **Resumed**')
        await ctx.send(embed=embed)

async def setup():
    await bot.wait_until_ready()
    bot.add_cog(Player(bot))

bot.loop.create_task(setup())
bot.run(bot_token)