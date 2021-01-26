import argparse
import asyncio
import json
import os
import random
import re
import requests
import time
import traceback

from collections import defaultdict
from datetime import datetime
from os.path import isfile, join

import discord
from discord.ext import commands
from dotenv import load_dotenv

from util.badargs import BadArgs
from util.create_file import create_file_if_not_exists

load_dotenv()
CS213BOT_KEY = os.getenv("CS213BOT_KEY")

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
    files = ["data/poll.json", "data/pl.json"]

    for f in files:
        if not isfile(f):
            create_file_if_not_exists(f)
            bot.writeJSON({}, f)

    for f in ["data/tomorrow.json"]:
        if not isfile(f):
            create_file_if_not_exists(f)
            bot.writeJSON([], f)

    bot.poll_dict = bot.loadJSON("data/poll.json")
    bot.pl_dict = defaultdict(list, bot.loadJSON("data/pl.json"))
    bot.due_tomorrow = bot.loadJSON("data/tomorrow.json")

    for channel in filter(lambda ch: not bot.get_channel(int(ch)), list(bot.poll_dict)):
        del bot.poll_dict[channel]

    for channel in (c for g in bot.guilds for c in g.text_channels if str(c.id) not in bot.poll_dict):
        bot.poll_dict.update({str(channel.id): ""})

    bot.writeJSON(dict(bot.poll_dict), "data/poll.json")

async def wipe_dms():
    guild = bot.get_guild(796222302483251241)

    while True:
        await asyncio.sleep(300)
        bot.get_cog("SM213").queue = list(filter(lambda x: time.time() - x[1] < 300, bot.get_cog("SM213").queue))
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


async def crawl_prairielearn():
    channel = bot.get_channel(803495663862022155)
    colormap = {
        "red1": (255, 204, 188),
        "red2": (255, 108, 91),
        "red3": (199, 44, 29),
        "pink1": (255, 188, 216),
        "pink2": (250, 92, 152),
        "pink3": (186, 28, 88),
        "purple1": (220, 198, 224),
        "purple2": (155, 89, 182),
        "purple3": (94, 20, 125),
        "blue1": (57, 212, 225),
        "blue2": (18, 151, 224),
        "blue3": (0, 87, 160),
        "turquoise1": (94, 250, 247),
        "turquoise2": (38, 203, 192),
        "turquoise3": (0, 140, 128),
        "green1": (142, 225, 193),
        "green2": (46, 204, 113),
        "green3": (0, 140, 49),
        "yellow1": (253, 227, 167),
        "yellow2": (245, 171, 53),
        "yellow3": (216, 116, 0),
        "orange1": (255, 220, 181),
        "orange2": (255, 146, 106),
        "orange3": (195, 82, 43),
        "brown1": (246, 196, 163),
        "brown2": (206, 156, 123),
        "brown3": (142, 92, 59),
        "gray1": (224, 224, 224),
        "gray2": (144, 144, 144),
        "gray3": (80, 80, 80)
    }
    while True:
        instance_id = 2295
        new_pl_dict = defaultdict(list)
        total_assignments = get_pl_data(f"https://ca.prairielearn.org/pl/api/v1/course_instances/{instance_id}/assessments")
        for assignment in total_assignments:
            assessment_id = assignment["assessment_id"]
            schedule_data = get_pl_data(f"https://ca.prairielearn.org/pl/api/v1/course_instances/{instance_id}/assessments/{assessment_id}/assessment_access_rules")
            modes = []
            not_started = False
            for mode in schedule_data:
                if mode["start_date"]:
                    offset = int(mode["start_date"][-1])
                else:
                    offset = 0

                if mode["start_date"] and mode["credit"] == 100:
                    start = time.mktime(time.strptime("-".join(mode["start_date"].split("-")[:-1]), "%Y-%m-%dT%H:%M:%S"))
                    now = time.time() - offset * 60
                    if start > now: 
                        not_started = True
                        break
                
                if not mode["end_date"]: 
                    end = None
                    end_unix = 0
                else: 
                    end_unix = time.strptime("-".join(mode["end_date"].split("-")[:-1]), "%Y-%m-%dT%H:%M:%S")
                    end = time.strftime("%H:%M PST, %a, %b, %d", end_unix)
                    end_unix = time.mktime(end_unix)

                modes.append({
                    "credit": mode["credit"],
                    "end":    end,
                    "end_unix": end_unix,
                    "offset": offset
                })

            if not_started:
                continue

            fielddata = {
                "id": assessment_id,
                "color": assignment["assessment_set_color"], 
                "label": assignment["assessment_label"],
                "name":  assignment["title"],
                "modes": modes
            }
            new_pl_dict[assignment["assessment_set_heading"]].append(fielddata)

        sent = False
        for header in new_pl_dict:
            for entry in new_pl_dict[header]:
                if entry not in bot.pl_dict[header]:
                    sent = True
                    embed = discord.Embed(color = int("%x%x%x" % colormap[entry["color"]], 16), title = "CPSC 213 on PrairieLearn: New Assessment", description = f"[**{['Assignment', 'Quiz'][entry['label'].startswith('Q')]} Unlocked: {entry['label']} {entry['name']}**](https://ca.prairielearn.org/pl/course_instance/2295/assessment/{entry['id']}/)")
                    for mode in entry["modes"]:
                        if mode["credit"] == 100 and mode["end"]:
                            embed.set_footer(text = f"Due at {mode['end']}.")
                            break
                    embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
                    await channel.send(embed = embed)

                for mode in entry["modes"]:
                    if mode["credit"] == 100 and mode["end"] and (mode["end_unix"] + 60*mode["offset"]) - time.time() < 86400 and entry["label"] + " " + entry["name"] not in bot.due_tomorrow:
                        bot.due_tomorrow.append(entry["label"]+" "+entry["name"])
                        embed = discord.Embed(color = int("%x%x%x" % colormap[entry["color"]], 16), title = "CPSC 213 on PrairieLearn: Due Date Reminder", description = f"[**{['Assignment', 'Quiz'][entry['label'].startswith('Q')]} Due in <24 Hours: {entry['label']} {entry['name']}**](https://ca.prairielearn.org/pl/course_instance/2295/assessment/{entry['id']}/)")
                        embed.set_footer(text = f"Due at {mode['end']}.")
                        embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
                        await channel.send(embed = embed)
                        sent = True
                        break

        if sent:
            await channel.send("<@&796222302483251244>")

        bot.pl_dict = new_pl_dict
        bot.writeJSON(dict(bot.pl_dict), "data/pl.json")
        bot.writeJSON(bot.due_tomorrow, "data/tomorrow.json")
        await asyncio.sleep(1800)


def get_pl_data(url):
    # based on https://github.com/PrairieLearn/PrairieLearn/blob/master/tools/api_download.py
    headers = {'Private-Token': os.getenv("PLTOKEN")}
    start_time = time.time()
    retry_502_max = 30
    retry_502_i = 0
    while True:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            break
        elif r.status_code == 502:
            retry_502_i += 1
            if retry_502_i >= retry_502_max:
                raise Exception(f'Maximum number of retries reached on 502 Bad Gateway Error for {url}')
            else:
                time.sleep(10)
                continue
        else:
            raise Exception(f'Invalid status returned for {url}: {r.status_code}')

    data = r.json()
    return data


@bot.event
async def on_ready():
    startup()
    print("Logged in successfully")
    bot.loop.create_task(status_task())
    bot.loop.create_task(wipe_dms())
    bot.loop.create_task(crawl_prairielearn())

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

        if message.content.lower() == "cancel":
            bot.get_cog("SM213").queue.append([message.author.id, time.time()])

        await bot.process_commands(message)


if __name__ == "__main__":
    bot.loadJSON = loadJSON
    bot.writeJSON = writeJSON
    bot.pl_dict = defaultdict(list)
    bot.due_tomorrow = []

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
