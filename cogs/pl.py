import math
import asyncio
import json
import os
import time
import random
from datetime import datetime
from os.path import isfile, join

import discord
from discord.ext import commands

from util.badargs import BadArgs

class PrairieLearn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def assign(self, ctx, current = None):
        embed = discord.Embed(title = f"{['All', 'Current '][current == 'current']} Assessments on CPSC 213 PrairieLearn", description = f"Requested by {ctx.author}", color = 0x8effc1)
        for assigntype in self.bot.pl_dict:
            entrylist = self.bot.pl_dict[assigntype]
            formattedentries = []
            seenmodes = []
            for entry in entrylist:
                skip = False
                formatted = f"`{entry['label']}` **[{entry['name']}](https://ca.prairielearn.org/pl/course_instance/2295/assessment/{entry['id']}/)**\nCredit:\n"
                for mode in entry["modes"]:
                    if current == "current" and mode['end'] and mode['credit'] == 100:
                        offset = int(mode["end"][-1])
                        now = time.time() - offset * 60
                        if mode['end_unix'] < now:
                            skip = True
                            break

                    fmt = f"· {mode['credit']}% until {mode['end']}\n"
                    if fmt not in seenmodes:
                        formatted += fmt
                        seenmodes.append(fmt)

                if skip: continue

                formattedentries.append(formatted)
            embed.add_field(name = f"\u200b\n***{assigntype.upper()}***", value = "\n".join(formattedentries), inline = False)
        
        embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
        await ctx.send(embed = embed)
        

def setup(bot):
    bot.add_cog(PrairieLearn(bot))