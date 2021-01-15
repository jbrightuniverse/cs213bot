import argparse
import asyncio
import json
import os
import random
import re
import traceback
from datetime import datetime
from os.path import isfile, join

import discord
from discord.ext import commands
from dotenv import load_dotenv

from util.badargs import BadArgs
from util.create_file import create_file_if_not_exists

load_dotenv()
CS213BOT_KEY = "Nzk5MzI5MzUwMTcyMTQ3NzIz.YAB_dw.NYiJrMEdtSLG_iAqmUxjB2YB_f4"

bot = commands.Bot(command_prefix="!", help_command=None, intents=discord.Intents.all())

parser = argparse.ArgumentParser(description="Run CS213Bot")
args = parser.parse_args()


def loadJSON(jsonfile):
    with open(jsonfile, "r") as f:
        return json.load(f)


def writeJSON(data, jsonfile):
    with open(jsonfile, "w") as f:
        json.dump(data, f, indent=4)


async def status_task():
    await bot.wait_until_ready()

    while not bot.is_closed():
        online_members = {member for guild in bot.guilds for member in guild.members if not member.bot and member.status != discord.Status.offline}

        play = ["with the \"help\" command", " ", "with your mind", "ƃuᴉʎɐlԀ", "...something?",
                "a game? Or am I?", "¯\_(ツ)_/¯", f"with {len(online_members)} people", "with the Simple Machine"]
        listen = ["smart music", "... wait I can't hear anything"]
        watch = ["TV", "YouTube vids", "over you",
                 "how to make a bot", "C tutorials", "sm213 execute", "I, Robot"]

        rng = random.randrange(0, 3)

        if rng == 0:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=random.choice(play)))
        elif rng == 1:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=random.choice(listen)))
        else:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(watch)))

        await asyncio.sleep(30)


def startup():
    files = ["data/poll.json"]

    for f in files:
        if not isfile(f):
            create_file_if_not_exists(f)
            bot.writeJSON({}, f)

    bot.poll_dict = bot.loadJSON("data/poll.json")

    for channel in filter(lambda ch: not bot.get_channel(int(ch)), list(bot.poll_dict)):
        del bot.poll_dict[channel]

    for channel in (c for g in bot.guilds for c in g.text_channels if str(c.id) not in bot.poll_dict):
        bot.poll_dict.update({str(channel.id): ""})

    bot.writeJSON(bot.poll_dict, "data/poll.json")

async def wipe_dms():
    guild = bot.get_guild(796222302483251241)

    while True:
        await asyncio.sleep(300)
        now = datetime.utcnow()

        for channel in filter(lambda c: c.name.startswith("213dm-"), guild.channels):
            async for msg in channel.history(limit=1):
                if (now - msg.created_at).total_seconds() >= 86400:
                    await next(i for i in guild.roles if i.name == channel.name).delete()
                    await channel.delete()
                    break
            else:
                await next(i for i in guild.roles if i.name == channel.name).delete()
                await channel.delete()


@bot.event
async def on_ready():
    startup()
    print("Logged in successfully")
    bot.loop.create_task(status_task())
    bot.loop.create_task(wipe_dms())

@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        bot.poll_dict.update({str(channel.id): ""})
        bot.writeJSON(bot.poll_dict, "data/poll.json")


@bot.event
async def on_guild_remove(guild):
    for channel in filter(lambda c: str(c.id) in bot.poll_dict, guild.channels):
        del bot.poll_dict[str(channel.id)]
        bot.writeJSON(bot.poll_dict, "data/poll.json")


@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel):
        bot.poll_dict.update({str(channel.id): ""})
        bot.writeJSON(bot.poll_dict, "data/poll.json")


@bot.event
async def on_guild_channel_delete(channel):
    if str(channel.id) in bot.poll_dict:
        del bot.poll_dict[str(channel.id)]
        bot.writeJSON(bot.poll_dict, "data/poll.json")


@bot.event
async def on_message_edit(before, after):
    await bot.process_commands(after)


@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.abc.PrivateChannel):
        return
        
    if not message.author.bot:
        # debugging
        # with open("messages.txt", "a") as f:
        # 	print(f"{message.guild.name}: {message.channel.name}: {message.author.name}: \"{message.content}\" @ {str(datetime.datetime.now())} \r\n", file = f)
        # print(message.content)

        # this is some weird bs happening only with android users in certain servers and idk why it happens
        # but basically the '@' is screwed up
        if message.channel.id == 797643936603963402 and len(message.attachments):
            await message.add_reaction("⬆️")
        if re.findall(r"<<@&457618814058758146>&?\d{18}>", message.content):
            new = message.content.replace("<@&457618814058758146>", "@")
            await message.channel.send(new)

        await bot.process_commands(message)


if __name__ == "__main__":
    bot.loadJSON = loadJSON
    bot.writeJSON = writeJSON

    for extension in filter(lambda f: isfile(join("cogs", f)) and f != "__init__.py", os.listdir("cogs")):
        bot.load_extension(f"cogs.{extension[:-3]}")
        print(f"{extension} module loaded")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound) or isinstance(error, discord.HTTPException) or isinstance(error, discord.NotFound):
        pass
    elif isinstance(error, BadArgs) or str(type(error)) == "<class 'cogs.meta.BadArgs'>":
        await error.print(ctx)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Oops! That command is on cooldown right now. Please wait **{round(error.retry_after, 3)}** seconds before trying again.", delete_after=error.retry_after)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"The required argument(s) {error.param} is/are missing.", delete_after=5)
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send("This command is disabled.", delete_after=5)
    elif isinstance(error, commands.MissingPermissions) or isinstance(error, commands.BotMissingPermissions):
        await ctx.send(error, delete_after=5)
    else:
        etype = type(error)
        trace = error.__traceback__

        try:
            await ctx.send(("```python\n" + "".join(traceback.format_exception(etype, error, trace, 999)) + "```").replace("home/rq2/.local/lib/python3.9/site-packages/", ""))
        except Exception:
            print(("".join(traceback.format_exception(etype, error, trace, 999))).replace("home/rq2/.local/lib/python3.9/site-packages/", ""))


bot.run(CS213BOT_KEY)
