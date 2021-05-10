import math
import asyncio
import os
import random
from datetime import datetime
from os.path import isfile, join

import discord
from discord.ext import commands

from util.badargs import BadArgs
import json

from collections import defaultdict
import matplotlib.pyplot as plt

from io import BytesIO


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def die(self, ctx):
        await self.bot.logout()

    @commands.command()
    @commands.is_owner()
    async def clear(self, ctx, num):
        await ctx.message.delete()
        n = int(num)
        loops = math.floor(n / 100)
        left = n - loops
        for i in range(loops):
            await ctx.channel.purge(limit=100)
        await ctx.channel.purge(limit=left)
        msg = await ctx.send(f"**{num}** message{['','s'][n!=1]} deleted.")
        await asyncio.sleep(3)
        await msg.delete()

    @commands.command(hidden = True)
    @commands.is_owner()
    async def pull(self, ctx):
        resdict = defaultdict(list)
        guild = self.bot.get_guild(796222302483251241)
        for channel in guild.text_channels:
            print(channel.name)
            messages = await channel.history(limit=None).flatten()
            for msg in messages:
                reactions = msg.reactions
                names = [r.emoji for r in reactions]
                ref = msg.reference
                if ref:
                    msgref = str(ref.message_id)
                else:
                    msgref = "none"
                resdict[str(msg.author.id)].append(str(len(msg.mentions)) + " " + str(names) + " " + msgref)

        with open("result2.json", "w") as f:
            json.dump(dict(resdict), f)

        await ctx.send("done")


    @commands.command(hidden = True)
    @commands.is_owner()
    async def pull2(self, ctx):
        emojidict = defaultdict(list)
        guild = self.bot.get_guild(796222302483251241)
        for channel in guild.text_channels:
            print(channel.name)
            messages = await channel.history(limit=None).flatten()
            for msg in messages:
                reactions = msg.reactions
                for reaction in reactions:
                    users = await reaction.users().flatten()
                    emojidict[str(reaction.emoji)].extend([u.id for u in users])
                

        with open("result3.json", "w") as f:
            json.dump(dict(emojidict), f)

        await ctx.send("done")

    @commands.command()
    async def topreact(self, ctx, amt = "20", start = "0"):
        """
        `!topreact` __`Returns reactions data`__

        **Usage:** !topreact [optional amt]

        **Examples:**
        `!topreact` [text]
        """
        with open("result2.json") as f:
            dat = json.load(f)
        with open("result3.json") as f:
            dat2 = json.load(f)
        total_replies = 0
        total_pings = 0
        emojidict = defaultdict(lambda: 0)
        data2 = {}
        for user in dat:
            messages = dat[user]
            my_replies = 0
            my_pings = 0
            my_emojidict = defaultdict(lambda: 0)
            for data in messages:
                content = data.split(" ")
                num_pings = int(content[0])
                total_pings += num_pings
                has_reply = content[-1]
                my_pings += num_pings
                if has_reply != "none":
                    total_replies += 1
                    my_replies += 1
            data2[user] = {"pings": my_pings, "replies": my_replies, "emoji": defaultdict(lambda: 0)}

        for emo in dat2:
            emojidict[emo] += len(dat2[emo])
            for user in dat2[emo]:
                if str(user) not in data2:
                    data2[str(user)] = {"pings":0, "replies":0, "emoji": defaultdict(lambda: 0)}
                data2[str(user)]["emoji"][emo] += 1

        people = list(data2.keys())
        people.sort(key = lambda x: -1 * (data2[x]["pings"] + data2[x]["replies"] + sum(data2[x]["emoji"].values())))
        output = []
        for x in people:
            output.append(f"{self.bot.get_user(int(x))}: **{data2[x]['pings']}** pings, **{data2[x]['replies']}** replies, **{sum(data2[x]['emoji'].values())}** reacts")

        if not amt.isdigit(): amt = 20
        else: 
            try: amt = int(amt)
            except: amt = 20
        if start.isdigit():
            try: start = int(start)
            except: start = 0

        res = "\n".join(output[start:amt])
        if len(res) > 2000:
            await ctx.send("Too many specified. Sorry.")
        await ctx.send(res)
        
        #await ctx.send(f"**{total_replies}** total uses of the reply button")
        #await ctx.send(f"**{total_pings}** total pings to people")
        #emojis = list(dict(emojidict).keys())
        #emojis.sort(key = lambda x: -1 * emojidict[x])
        #await ctx.send("\n".join([f"{x}: {emojidict[x]}" for x in emojis][:len(emojis)//2]))
        #await ctx.send("\n".join([f"{x}: {emojidict[x]}" for x in emojis][len(emojis)//2:]))



    @commands.command()
    async def topusers(self, ctx, amt = "30", start = "0"):
        """
        `!topusers` __`Returns top n users`__

        **Usage:** !topusers [optional val]

        **Examples:**
        `!topusers` [text]
        """
        if not amt.isdigit(): amt = 30
        else: 
            try: amt = int(amt)
            except: amt = 30
        if start.isdigit():
            try: start = int(start)
            except: start = 0

        with open("result.json") as f:
            dat = json.load(f)

        userdict = defaultdict(list)
        for channel in dat:
            messages = dat[channel]
            for message in messages:
                userdict[message.split(" ")[2]].append(message)

        users = list(userdict.keys())
        users.sort(key = lambda x: -1 * len(userdict[x]))
        output = []
        for user in users:
            output.append(f"{self.bot.get_user(int(user))}: {len(userdict[user])} messages total")

        res = "\n".join(output[start:amt])
        if len(res) > 2000:
            await ctx.send("Too many specified. Sorry.")
        await ctx.send(res)

    @commands.command()
    async def superstats(self, ctx, id = None):
        """
        `!superstats` __`Check user profile and stats`__

        **Usage:** !superstats <USER ID OR PING>

        **Examples:** `!superstats 375445489627299851` [embed]
        """

        with open("result.json") as f:
            dat = json.load(f)

        userdict = defaultdict(list)
        for channel in dat:
            messages = dat[channel]
            for message in messages:
                userdict[message.split(" ")[2]].append(message)

        users = list(userdict.keys())
        users.sort(key = lambda x: -1 * len(userdict[x]))

        if len(ctx.message.mentions):
            id = str(ctx.message.mentions[0].id)
        elif id == None: id = str(ctx.author.id)
        if id not in userdict: return await ctx.send("User not found.")
        msgdict = defaultdict(lambda: 0)
        for msg in userdict[id]:
            msgdict[msg.split(" ")[0]] += 1

        channeluserdict = defaultdict(lambda: 0)
        for channel in dat:
            messages = dat[channel]
            for message in messages:
                if message.split(" ")[2] == id:
                    channeluserdict[channel] += 1

        fig, ax = plt.subplots()
        theuser = self.bot.get_user(int(id))
        fig.suptitle(f"Daily usage trends for {theuser}")
        plt.xlabel("Date")
        plt.ylabel("Number of Messages")
        keys_ordered = list(msgdict.keys())
        keys_ordered.reverse()
        keys_ordered.sort()
        
        plt.plot(["/".join([b.lstrip("0") for b in k[5:].split("-")]) for k in keys_ordered], [msgdict[k] for k in keys_ordered])
        for n, label in enumerate(ax.xaxis.get_ticklabels()):
            if n % 12 != 0:
                label.set_visible(False)

        filex = BytesIO()
        fig.savefig(filex, format = "png")
        filex.seek(0)
        plt.close()
        await ctx.send(file=discord.File(filex, "daily.png"))

        fig, ax = plt.subplots()
        theuser = self.bot.get_user(int(id))
        fig.suptitle(f"Cumulative Daily usage trends for {theuser}")
        plt.xlabel("Date")
        plt.ylabel("Number of Messages")
        keys_ordered = list(msgdict.keys())
        keys_ordered.reverse()
        keys_ordered.sort()

        counter = 0
        res = []
        for k in keys_ordered:
            counter += msgdict[k]
            res.append(counter)
        
        plt.plot(["/".join([b.lstrip("0") for b in k[5:].split("-")]) for k in keys_ordered], res)
        for n, label in enumerate(ax.xaxis.get_ticklabels()):
            if n % 12 != 0:
                label.set_visible(False)

        filex = BytesIO()
        fig.savefig(filex, format = "png")
        filex.seek(0)
        plt.close()
        await ctx.send(file=discord.File(filex, "daily_cumulative.png"))
        channelkeys = list(channeluserdict.keys())
        channelkeys.sort(key = lambda x: -1 * channeluserdict[x])
        data2 = "\n".join([f"{x}: **{channeluserdict[x]}** messages" for x in channelkeys])
        await ctx.send(f"**Additional Metrics for {theuser}:**\n\nTotal number of messages: **{len(userdict[id])}**\nRank in server (0-indexed): **{users.index(id)}**\nMost used channels: {data2}\n\n*Data only updated to beginning of April 30th, 2021.")

        with open("result2.json") as f:
            dat = json.load(f)
        with open("result3.json") as f:
            dat2 = json.load(f)

        data2 = {}
        user = str(id)
        messages = dat[user]
        my_replies = 0
        my_pings = 0
        for data in messages:
            content = data.split(" ")
            num_pings = int(content[0])
            has_reply = content[-1]
            my_pings += num_pings
            if has_reply != "none":
                my_replies += 1

        emojicount = 0
        edict = defaultdict(lambda: 0)
        for emo in dat2:
            for u in dat2[emo]:
                if str(u) == user:
                    emojicount += 1
                    edict[emo] += 1

        emoji = list(edict.keys())
        emoji.sort(key = lambda x: -1 * edict[x])
        eresult = []
        for e in emoji:
            if e.startswith("<:"):
                e2 = e[2:-20]
            else: e2 = e
            eresult.append(f"{e2}: **{edict[e]}**")
        
        await ctx.send(f"**{my_pings}** pings\n**{my_replies}** replies (may overlap with pings)\n**{emojicount}** emoji reactions")
        await ctx.send("Top Emoji Used:\n\n" + "\n".join(eresult[:10]))


    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(self, ctx, *arg):
        """
        `!help` __`Returns list of commands or usage of command`__

        **Usage:** !help [optional cmd]

        **Examples:**
        `!help` [embed]
        """

        if not arg:
            embed = discord.Embed(title="CS213 Bot", description="Commands:", colour=random.randint(0, 0xFFFFFF), timestamp=datetime.utcnow())
            embed.add_field(name=f"❗ Current Prefix: `{self.bot.command_prefix}`", value="\u200b", inline=False)

            for k, v in self.bot.cogs.items():
                embed.add_field(name=k, value=" ".join(f"`{i}`" for i in v.get_commands() if not i.hidden), inline=False)

            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.add_field(name = "_ _\nSupport Bot Development: visit the CS213Bot repo at https://github.com/jbrightuniverse/cs213bot/", value = "_ _\nCS213Bot is based on CS221Bot. Support them at https://github.com/Person314159/cs221bot/\n\nCall ++help to access C++Bot from within this bot.\nhttps://github.com/jbrightuniverse/C-Bot")
            embed.set_footer(text=f"The sm213 language was created by Dr. Mike Feeley of the CPSC department at UBCV.\nUsed with permission.\n\nRequested by {ctx.author.display_name}", icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=embed)
        else:
            help_command = arg[0]

            comm = self.bot.get_command(help_command)

            if not comm or not comm.help or comm.hidden:
                raise BadArgs("That command doesn't exist.")

            await ctx.send(comm.help)

    @commands.command(hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reload(self, ctx, *modules):
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.delete()

        if not modules:
            modules = [f[:-3] for f in os.listdir("cogs") if isfile(join("cogs", f) and f != "__init__.py")]

        for extension in modules:
            Reload = await ctx.send(f"Reloading the {extension} module")

            try:
                self.bot.reload_extension(f"cogs.{extension}")
            except Exception as exc:
                return await ctx.send(exc)
            await Reload.edit(content=f"{extension} module reloaded.")

        self.bot.reload_extension("cogs.meta")

        await ctx.send("Done")


def setup(bot):
    bot.add_cog(Meta(bot))
