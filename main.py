import asyncio
import pafy
import discord
from discord.ext import commands
from youtube_dl import YoutubeDL
#import os
#import keep_alive
#from time import strftime
#from time import gmtime

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
  'default_search': 'auto',
  'source_address': '0.0.0.0',
  }

FFMPEG_OPTIONS = {
  'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
  'options': '-vn',
}

intents = discord.Intents.default()
intents.members = True
loop = False
sk = False

bot = commands.Bot(command_prefix="$", intents=intents)
colour = discord.Colour.dark_gold()

@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready.")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="$help"))

class NewHelpName(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            em = discord.Embed(colour=colour)
            em.add_field(name = "$play", value = "Plays music by name or youtube link.")
            em.add_field(name = "$stop", value = "Stops the player (Requires DJ role).")
            em.add_field(name = "$search", value = "Searches 10 youtube links for the song name.")
            em.add_field(name = "$skip", value = "Runs the vote skip for the current song.")
            em.add_field(name = "$forceskip ($fs)", value = "Force skips the current song (Requires DJ role).")
            em.add_field(name = "$queue", value = "Checks for the current songs in the queue.")
            em.add_field(name = "$pause", value = "Pauses the playing song.")
            em.add_field(name = "$resume", value = "Resumes the paused song.")
            em.add_field(name = "$loop", value = "Repeats the songs in the queue.")
            em.add_field(name = "$remove", value = "Removes a specific song from the queue (Requires DJ role).")
            em.add_field(name = "$clear", value = "Clears the songs in the queue (Requires DJ role).")
            em.add_field(name = "$nowplaying ($np)", value = "Shows the current playing song.")

            """
            em.description = "**Commands:**\n **$play** plays music by name or youtube link.\n **$search** searches 10 youtube links for the song name.\n **$skip** runs the vote skip for the current song.\n **$queue** checks for the current songs in the queue.\n **$pause** pauses the playing song.\n **$resume** resumes the paused song.\n **$loop** repeats the songs in the queue.\n\n **Commands that requires DJ role:**\n **$stop** stops the current playing music, clears the queue, and discconects the bot.\n **$fs** force skips the current song.\n **$clear** clears the songs in the queue.\n **$remove** removes a specific song from the queue."
            """
            await destination.send(embed=em)
bot.help_command = NewHelpName()

class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.song_queue = {}

        self.setup()

    def setup(self):
        for guild in self.bot.guilds:
            self.song_queue[guild.id] = []

    async def search_song(self, amount, song, get_url=False):
        info = await self.bot.loop.run_in_executor(None, lambda: YoutubeDL(YDL_OPTIONS).extract_info(f"ytsearch{amount}:{song}", download=False, ie_key="YoutubeSearch"))
        if len(info["entries"]) == 0: return None
        return [entry["webpage_url"] for entry in info["entries"]] if get_url else info

    async def check_queue(self, ctx):
        global loop
        if ctx.voice_client is not None:
            members = ctx.voice_client.channel.members
            memids = []
            for member in members:
                if not member.bot:
                    memids.append(member.id)
            if not len(memids) > 0:
                await ctx.voice_client.disconnect()
                if len(self.song_queue[ctx.guild.id]) > 0:
                    self.song_queue[ctx.guild.id] = []
                loop = False
                embed = discord.Embed(colour=colour, description='☠ **The queue has been force ended.**')
                embed.set_footer(text="Because no one is in the voice channel.")
                return await ctx.send(embed=embed)
        else:
            if len(self.song_queue[ctx.guild.id]) > 0:
                self.song_queue[ctx.guild.id] = []
            loop = False
            #embed = discord.Embed(colour=colour, description=f'☹ **Why you discconect me like that.**')
            return #await ctx.send(embed=embed)
        if len(self.song_queue[ctx.guild.id]) > 0:
            await self.play_song(ctx, self.song_queue[ctx.guild.id][0])
            if loop:
                self.song_queue[ctx.guild.id].append(self.song_queue[ctx.guild.id][0])
            self.song_queue[ctx.guild.id].pop(0)
        else:
            if ctx.voice_client is not None:
                await ctx.voice_client.disconnect()
            loop = False
            #await ctx.send("The queue has ended.")
            embed = discord.Embed(colour=colour, description='🗿 **The queue has ended.**')
            await ctx.send(embed=embed)

    async def play_song(self, ctx, song):
        #with YoutubeDL(YDL_OPTIONS) as ydl:
            #info = ydl.extract_info(song, download=False)
            #url2 = info['formats'][0]['url']
            #source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
            #ctx.voice_client.play(source, after=lambda error: self.bot.loop.create_task(self.check_queue(ctx)))
        try:
            url = pafy.new(song).getbestaudio().url
            ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)), after=lambda error: self.bot.loop.create_task(self.check_queue(ctx)))
        except:
            self.song_queue[ctx.guild.id].append(song)
            if not len(self.song_queue[ctx.guild.id]) > 0:
                self.check_queue(ctx)
            embed = discord.Embed(colour=colour, description=f'☹ **Something went wrong while trying to play [song]({song}), it has been re added to the queue.**')
            await ctx.send(embed=embed)

        global musics
        musics = song

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
            
            #if vduration < 3600:
                #dur = strftime("%M:%S", gmtime(vduration))
            #else:
                #dur = strftime("%H:%M:%S", gmtime(vduration))
  
    @commands.command()
    async def ping(self, ctx):
        #await ctx.send(f"My ping is {round(bot.latency*1000)}.")
        embed = discord.Embed(colour=colour, description=f'**My ping is `{round(bot.latency*1000)} ms`**')
        await ctx.send(embed=embed)

    @commands.command(aliases=["disconnect", "leave"])
    async def stop(self, ctx):
        role = discord.utils.find(lambda r: r.name == 'DJ', ctx.message.guild.roles)
        if role in ctx.author.roles:
            if ctx.voice_client is None or ctx.voice_client.source is None:
                #return await ctx.send("I am not playing any song.")
                embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song.**')
                return await ctx.send(embed=embed)

            if ctx.author.voice is None:
                #return await ctx.send("You are not connected to any voice channel.")
                embed = discord.Embed(colour=colour, description='⛔ **You are not connected to any voice channel.**')
                return await ctx.send(embed=embed)

            if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
                #return await ctx.send("I am not currently playing any songs for you.")
                embed = discord.Embed(colour=colour, description='⛔ **I am not currently playing any songs for you.**')
                return await ctx.send(embed=embed)

            #await ctx.send("The player has stopped and the queue has been cleared.")
            embed = discord.Embed(colour=colour, description='✅ **The player has been stopped.**')
            await ctx.send(embed=embed)
            await ctx.voice_client.disconnect()
        else:
            embed = discord.Embed(colour=colour, description='❌ **You need "DJ" role.**')
            await ctx.send(embed=embed)

    @commands.command(aliases=["p"])
    async def play(self, ctx, *, song=None):
        global loop
        if ctx.author.voice is None:
            embed = discord.Embed(colour=colour, description='⛔ **You are not connected to any voice channel.**')
            return await ctx.send(embed=embed)

        if song is None:
            #return await ctx.send("You must include a song to play.")
            embed = discord.Embed(colour=colour, description='❌ **You must include a song to play.**')
            return await ctx.send(embed=embed)

        #if "youtube.com/playlist?" in song:
            #embed = discord.Embed(colour=colour, description='❌ **Cannot play playlists.**')
            #return await ctx.send(embed=embed)

        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect()

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            embed = discord.Embed(colour=colour, description='⛔ **I am not currently playing any songs for you.**')
            return await ctx.send(embed=embed)

        # handle song where song isn't url
        if not ("youtube.com/watch?" in song or "https://youtu.be/" in song or "youtube.com/playlist?" in song):
            #await ctx.send("Searching for song, this may take a few seconds.")
            embed = discord.Embed(colour=colour, description='⏱ **Searching for song, this may take a few seconds.**')
            embed.set_footer(text="Using the song link is faster than using its name.")
            temp = await ctx.send(embed=embed)

            result = await self.search_song(1, song, get_url=True)
            
            if result is None:
                #return await ctx.send("Sorry, I could not find the given song, try using my search command.")
                embed = discord.Embed(colour=colour, description='☹ **Sorry, I could not find the given song, try again or use my search command.**')
                return await temp.edit(embed=embed)

            song = result[0]
            embed = discord.Embed(colour=colour, description='⏱ **Downloading the song(s), please wait.**')
            await temp.edit(embed=embed)

        else:
            embed = discord.Embed(colour=colour, description='⏱ **Downloading the song(s), please wait.**')
            temp = await ctx.send(embed=embed)

        if not "youtube.com/playlist?" in song:
            with YoutubeDL(YDL_OPTIONS) as ydl:
                try:
                    info_dict = ydl.extract_info(song, download=False)
                    vtitle = info_dict.get('title', None)
                    vthumbnail = info_dict.get('thumbnail', None)
                    #vauthor = info_dict.get('uploader', None)
                    vduration = info_dict.get('duration', None)
                except:
                    embed = discord.Embed(colour=colour, description='☹ **Failed to download the song, try again or use my search command.**')
                    return await temp.edit(embed=embed)
                if ctx.voice_client.source is not None:
                    queue_len = len(self.song_queue[ctx.guild.id])
                    self.song_queue[ctx.guild.id].append(song)
                    #return await ctx.send(f"I am currently playing a song, this song has been added to the queue at position {queue_len+1}.")
                    embs = discord.Embed(colour=colour, title='Added to the queue', description=f"[{vtitle}]({song})")
                    embs.set_thumbnail(url=vthumbnail)
                    #embs.add_field(name="Author", value=f"`{vauthor}`")
                    embs.add_field(name="Requested by", value=ctx.author.mention)

                    durs = await self.time_format(vduration)
                    embs.add_field(name="Duration", value=f"`{durs}`")
                    embs.set_footer(text=f"{queue_len} song(s) in the queue.")
                    return await temp.edit(embed=embs)
            
                #await ctx.send(f"Now playing **{entry['title']}**")
                emb = discord.Embed(colour=colour, title='Now Playing',
                description=f"[{vtitle}]({song})")
                emb.set_thumbnail(url=vthumbnail)
                #emb.add_field(name="Author", value=f"`{vauthor}`")
                emb.add_field(name="Requested by", value=ctx.author.mention)
                
                dur = await self.time_format(vduration)
                emb.add_field(name="Duration", value=f"`{dur}`")

            await self.play_song(ctx, song)
            await temp.edit(embed=emb)

            global music
            music = song
            global musics
            musics = song

        else:
            try:
                with YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(song, download=False)
                    pname = info['entries'][0]['playlist']
                    total_dur = 0
                    num = 0
                    for i, item in enumerate(info['entries']):
                        num += 1
                        url = info['entries'][i]['webpage_url']
                        total_dur += info['entries'][i]['duration']
                        if ctx.voice_client.source is not None:
                            self.song_queue[ctx.guild.id].append(url)
                        else:
                            await self.play_song(ctx, url)
                        asyncio.sleep(0.01)
                        #if num > 100:
                            #embed = discord.Embed(colour=colour, description='❌ **Cannot download playlists with more than 100 songs.**')
                            #return await temp.edit(embed=embed)

                    embs = discord.Embed(colour=colour, title='Playlist added to the queue', description=f"[{pname}]({song})")
                    embs.add_field(name="Enqueued", value=f"`{num}` songs")
                    dur = await self.time_format(total_dur)
                    embs.add_field(name="Playlist duration", value=f"`{dur}`")
                    embs.add_field(name="Requested by", value=ctx.author.mention)
            except:
                embed = discord.Embed(colour=colour, description='☹ **Failed to download the playlist, try again.**')
                return await temp.edit(embed=embed)
                
            await temp.edit(embed=embs)

    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx):
        if ctx.voice_client is None or ctx.voice_client.source is None:
            embed = discord.Embed(colour=colour, description='❌ **I am not playing any song.**')
            return await ctx.send(embed=embed)
        #await ctx.send("Checking the song.")
        embed = discord.Embed(colour=colour, description='⏱ **Checking the song.**')
        temp = await ctx.send(embed=embed)
        queue_len = len(self.song_queue[ctx.guild.id])
        with YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info_dict = ydl.extract_info(musics, download=False)
                vtitle = info_dict.get('title', None)
                vthumbnail = info_dict.get('thumbnail', None)
                vauthor = info_dict.get('uploader', None)
                vduration = info_dict.get('duration', None)
            except:
                embed = discord.Embed(colour=colour, description='☹ **Failed to check the song, try again.**')
                return await temp.edit(embed=embed)

            emb = discord.Embed(colour=colour, title='Now Playing',
            description=f"[{vtitle}]({musics})")
            emb.set_thumbnail(url=vthumbnail)
            emb.add_field(name="Author", value=f"`{vauthor}`")

            dur2 = await self.time_format(vduration)
            emb.add_field(name="Duration", value=f"`{dur2}`")
            emb.set_footer(text=f"{queue_len} song(s) in the queue.")
            await temp.edit(embed=emb)

    @commands.command()
    async def loop(self, ctx):
        if ctx.voice_client is None or ctx.voice_client.source is None:
            #return await ctx.send("I am not playing any song.")
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song.**')
            return await ctx.send(embed=embed)

        if ctx.author.voice is None:
            #return await ctx.send("You are not connected to any voice channel.")
            embed = discord.Embed(colour=colour, description='⛔ **You are not connected to any voice channel.**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            #return await ctx.send("I am not currently playing any songs for you.")
            embed = discord.Embed(colour=colour, description='⛔ **I am not currently playing any songs for you.**')
            return await ctx.send(embed=embed)
        global loop
        if loop:
            #await ctx.send("Loop mode is **Off**.")
            if len(self.song_queue[ctx.guild.id]) > 0:
                self.song_queue[ctx.guild.id].pop()
            loop = False
            embed = discord.Embed(colour=colour, description="🔄 **Loop Mode** `❌︱OFF`")
            await ctx.send(embed=embed)
        else:
            #await ctx.send("Loop mode is **On**.")
            self.song_queue[ctx.guild.id].append(music)
            loop = True
            embed = discord.Embed(colour=colour, description="🔄 **Loop Mode** `✅︱ON`")
            await ctx.send(embed=embed)

    @commands.command()
    async def search(self, ctx, *, song=None):
        if song is None:
            #return await ctx.send("You forgot to include a song to search for.")
            embed = discord.Embed(colour=colour, description='❌ **You forgot to include a song to search for.**')
            return await ctx.send(embed=embed)

        #await ctx.send("Searching for song, this may take a few seconds.")
        embed = discord.Embed(colour=colour, description='⏱ **Searching for song, this may take a few seconds.**')
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
            #return await ctx.send("I am not playing any song.")
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song.**')
            return await ctx.send(embed=embed)

        if len(self.song_queue[ctx.guild.id]) == 0:
            #return await ctx.send("There are currently no songs in the queue.")
            embed = discord.Embed(colour=colour, description='❌ **There are currently no songs in the queue.**')
            return await ctx.send(embed=embed)

        #await ctx.send("Fetching the queue songs, please wait.")
        embed = discord.Embed(colour=colour, description='⏱ **Fetching the queue, please wait.**')
        temp = await ctx.send(embed=embed)

        embed = discord.Embed(title="Queue List", description="", colour=colour)
        i = 1
        qd = 0
        try:
            for url in self.song_queue[ctx.guild.id]:
                with YoutubeDL(YDL_OPTIONS) as ydl:
                    info_dict = ydl.extract_info(url, download=False)
                    title = info_dict.get('title', None)
                    duration = info_dict.get('duration', None)
                    qd += duration
                    embed.description += f"{i}) [{title}]({url})\n"
                    i += 1
            #embed.set_footer(text="Thanks for using me!")
            dur = await self.time_format(qd)
            embed.add_field(name="Queue Duration", value=f"`{dur}`")
            await temp.edit(embed=embed)
        except:
            embed = discord.Embed(colour=colour, description='☹ **Failed to fetch the queue, try again or the queue might be too long.**')
            return await temp.edit(embed=embed)

    @commands.command()
    async def skip(self, ctx):
        global sk
        sk = True
        if ctx.voice_client is None or ctx.voice_client.source is None:
            #return await ctx.send("I am not playing any song.")
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song.**')
            return await ctx.send(embed=embed)

        if ctx.author.voice is None:
            #return await ctx.send("You are not connected to any voice channel.")
            embed = discord.Embed(colour=colour, description='⛔ **You are not connected to any voice channel.**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            #return await ctx.send("I am not currently playing any songs for you.")
            embed = discord.Embed(colour=colour, description='⛔ **I am not currently playing any songs for you.**')
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

        sk = False

    @commands.command()
    async def remove(self, ctx, index: int=None):
        role = discord.utils.find(lambda r: r.name == 'DJ', ctx.message.guild.roles)
        if role in ctx.author.roles:
            if ctx.voice_client is None:
                #return await ctx.send("I am not playing any song.")
                embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song.**')
                return await ctx.send(embed=embed)

            if ctx.author.voice is None:
                #return await ctx.send("You are not connected to any voice channel.")
                embed = discord.Embed(colour=colour, description='⛔ **You are not connected to any voice channel.**')
                return await ctx.send(embed=embed)

            if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
                #return await ctx.send("I am not currently playing any songs for you.")
                embed = discord.Embed(colour=colour, description='⛔ **I am not currently playing any songs for you.**')
                return await ctx.send(embed=embed)
                
            if index is None:
                embed = discord.Embed(colour=colour, description='❌ **You must include the song number.**')
                return await ctx.send(embed=embed)

            if len(self.song_queue[ctx.guild.id]) > 0:
                number = index - 1
                self.song_queue[ctx.guild.id].pop(number)
                #await ctx.send(f"Removed the {number + 1} song in the queue.")
                embed = discord.Embed(colour=colour, description=f'✅ **({number + 1}) has been removed from the queue.**')
                return await ctx.send(embed=embed)
            else:
                #await ctx.send("There is nothing in the queue to remove.")
                embed = discord.Embed(colour=colour, description='❌ **There is nothing in the queue to remove.**')
                return await ctx.send(embed=embed)
        else:
            #await ctx.send("You need **DJ** role.")
            embed = discord.Embed(colour=colour, description='❌ **You need "DJ" role.**')
            await ctx.send(embed=embed)

    @commands.command(aliases=["fs"])
    async def forceskip(self, ctx):
        role = discord.utils.find(lambda r: r.name == 'DJ', ctx.message.guild.roles)
        if role in ctx.author.roles:
            global sk
            if sk:
                embed = discord.Embed(colour=colour, description='❌ **Skip vote is in progress.**')
                return await ctx.send(embed=embed)

            if ctx.voice_client is None or ctx.voice_client.source is None:
                #return await ctx.send("I am not playing any song.")
                embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song.**')
                return await ctx.send(embed=embed)

            if ctx.author.voice is None:
                #return await ctx.send("You are not connected to any voice channel.")
                embed = discord.Embed(colour=colour, description='⛔ **You are not connected to any voice channel.**')
                return await ctx.send(embed=embed)

            if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
                #return await ctx.send("I am not currently playing any songs for you.")
                embed = discord.Embed(colour=colour, description='⛔ **I am not currently playing any songs for you.**')
                return await ctx.send(embed=embed)

            ctx.voice_client.stop()
            #await ctx.send("Force skipped.")
            embed = discord.Embed(colour=colour, description='⏩ **Force Skipped.**')
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(colour=colour, description='❌ **You need "DJ" role.**')
            await ctx.send(embed=embed)

    @commands.command()
    async def clear(self, ctx):
        role = discord.utils.find(lambda r: r.name == 'DJ', ctx.message.guild.roles)
        if role in ctx.author.roles:
            if ctx.voice_client is None:
                #return await ctx.send("I am not playing any song.")
                embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song.**')
                return await ctx.send(embed=embed)

            if ctx.author.voice is None:
                #return await ctx.send("You are not connected to any voice channel.")
                embed = discord.Embed(colour=colour, description='⛔ **You are not connected to any voice channel.**')
                return await ctx.send(embed=embed)

            if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
                #return await ctx.send("I am not currently playing any songs for you.")
                embed = discord.Embed(colour=colour, description='⛔ **I am not currently playing any songs for you.**')
                return await ctx.send(embed=embed)

            if len(self.song_queue[ctx.guild.id]) < 0:
            #return await ctx.send("The queue is already clear.")
                embed = discord.Embed(colour=colour, description='❌ **The queue is already clear.**')
                return await ctx.send(embed=embed)

            self.song_queue[ctx.guild.id] = []
            #await ctx.send("The queue has been cleared.")
            embed = discord.Embed(colour=colour, description='✅ **The queue has been cleared.**')
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(colour=colour, description='❌ **You need "DJ" role.**')
            await ctx.send(embed=embed)

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client is None:
            #return await ctx.send("I am not playing any song.")
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song.**')
            return await ctx.send(embed=embed)

        if ctx.author.voice is None:
            #return await ctx.send("You are not connected to any voice channel.")
            embed = discord.Embed(colour=colour, description='⛔ **You are not connected to any voice channel.**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            #return await ctx.send("I am not currently playing any songs for you.")
            embed = discord.Embed(colour=colour, description='⛔ **I am not currently playing any songs for you.**')
            return await ctx.send(embed=embed)

        if ctx.voice_client.is_paused():
            #return await ctx.send("The song is already paused.")
            embed = discord.Embed(colour=colour, description='❌ **The song is already paused.**')
            return await ctx.send(embed=embed)

        ctx.voice_client.pause()
        #await ctx.send("The current song has been paused.")
        embed = discord.Embed(colour=colour, description='⏸ **The current song has been paused.**')
        await ctx.send(embed=embed)

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client is None:
            #return await ctx.send("I am not playing any song.")
            embed = discord.Embed(colour=colour, description='⛔ **I am not playing any song.**')
            return await ctx.send(embed=embed)

        if ctx.author.voice is None:
            #return await ctx.send("You are not connected to any voice channel.")
            embed = discord.Embed(colour=colour, description='⛔ **You are not connected to any voice channel.**')
            return await ctx.send(embed=embed)

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            #return await ctx.send("I am not currently playing any songs for you.")
            embed = discord.Embed(colour=colour, description='⛔ **I am not currently playing any songs for you.**')
            return await ctx.send(embed=embed)

        if not ctx.voice_client.is_paused():
            #return await ctx.send("The song is already resuming.")
            embed = discord.Embed(colour=colour, description='❌ **The song is already resuming.**')
            return await ctx.send(embed=embed)

        ctx.voice_client.resume()
        #await ctx.send("The current song has been resumed.")
        embed = discord.Embed(colour=colour, description='▶ **The current song has been resumed.**')
        await ctx.send(embed=embed)

async def setup():
    await bot.wait_until_ready()
    bot.add_cog(Player(bot))

#keep_alive.keep_alive()
bot.loop.create_task(setup())
bot.run("ODk4NTU4NzcxOTQzNjA0MjQ0.YWl-EQ.w34gsVHC65T3gaMKvtVrwS1T6_A")
