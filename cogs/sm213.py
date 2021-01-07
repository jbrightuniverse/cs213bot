import os
import random
from datetime import datetime
from os.path import isfile, join

import discord
from discord.ext import commands

from util.badargs import BadArgs


class Sm213(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def sim(self, ctx):
        """
        `!sim` __`Launch SM213 simulator`__

        **Usage:** !sim

        **Examples:** `!sim` launches simulator
        """
        await ctx.send("ok")


def setup(bot):
    bot.add_cog(Sm213(bot))
