import asyncio
import mimetypes
import random
import re
import string
import urllib.parse
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from io import BytesIO
from operator import methodcaller

import discord
import pytz
import requests
import requests.models
import webcolors
from discord.ext import commands
from googletrans import constants, Translator

from util.badargs import BadArgs

# This is a huge hack but it technically works
def _urlencode(*args, **kwargs):
    kwargs.update(quote_via=urllib.parse.quote)
    return urllib.parse.urlencode(*args, **kwargs)


requests.models.urlencode = _urlencode


# ################### COMMANDS ################### #


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.add_instructor_role_counter = 0

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def dm(self, ctx):
        """
        `!dm` __`213DM Generator`__

        **Usage:** !dm <user | close> [user] [...]

        **Examples:**
        `!dm @blankuser#1234` creates 213DM with TAs and blankuser
        `!dm @blankuser#1234 @otheruser#5678` creates 213DM with TAs, blankuser and otheruser
        `!dm close` closes 213DM
        """

        # meant for 213 server
        guild = self.bot.get_guild(838103749372674089)

        if "close" in ctx.message.content.lower():
            if not ctx.channel.name.startswith("213dm-"):
                raise BadArgs("This is not a 213DM.")

            await ctx.send("Closing 213DM.")
            await next(i for i in guild.roles if i.name == ctx.channel.name).delete()
            return await ctx.channel.delete()

        if not ctx.message.mentions:
            raise BadArgs("You need to specify a user or users to add!", show_help=True)

        # check that nobody is already in a 213dm before going and creating everything
        for user in ctx.message.mentions:
            for role in user.roles:
                if role.name.startswith("213dm"):
                    raise BadArgs(f"{user.name} is already in a 213DM.")

        # generate customized channel name to allow customized role
        nam = int(str((datetime.now() - datetime(1970, 1, 1)).total_seconds()).replace(".", "")) + ctx.author.id
        nam = f"213dm-{nam}"
        # create custom role
        role = await guild.create_role(name=nam, colour=discord.Colour(0x88ff88))

        for user in ctx.message.mentions:
            try:
                await user.add_roles(role)
            except (discord.Forbidden, discord.HTTPException):
                pass  # if for whatever reason one of the people doesn't exist, just ignore and keep going

        access = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
        noaccess = discord.PermissionOverwrite(read_messages=False, read_message_history=False, send_messages=False)
        overwrites = {
            # allow Computers and the new role, deny everyone else
            guild.default_role                : noaccess,
            guild.get_role(838103749486051415): access,
            role                              : access
        }
        # this id is id of group dm category
        channel = await guild.create_text_channel(nam, overwrites=overwrites, category=guild.get_channel(838103751175700544))
        await ctx.send("Opened channel.")
        users = (f"<@{usr.id}>" for usr in ctx.message.mentions)
        await channel.send(f"<@{ctx.author.id}> {' '.join(users)}\n" +
                           f"Welcome to 213 private DM. Type `!dm close` to exit when you are finished.")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def emojify(self, ctx):
        """
        `!emojify` __`Emoji text generator`__

        **Usage:** !emojify <text>

        **Examples:**
        `!emojify hello` prints "hello" with emoji
        `!emojify b` prints b with emoji"
        """

        mapping = {"A": "🇦", "B": "🅱", "C": "🇨", "D": "🇩", "E": "🇪", "F": "🇫", "G": "🇬", "H": "🇭", "I": "🇮", "J": "🇯", "K": "🇰", "L": "🇱", "M": "🇲", "N": "🇳", "O": "🇴", "P": "🇵", "Q": "🇶", "R": "🇷", "S": "🇸", "T": "🇹", "U": "🇺", "V": "🇻", "W": "🇼", "X": "🇽", "Y": "🇾", "Z": "🇿", "0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣"}

        text = ctx.message.content[9:].upper()
        output = "".join(mapping[i] + (" " if i in string.ascii_uppercase else "") if i in mapping else i for i in text)

        await ctx.send(output)


    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def join(self, ctx, *arg):
        """
        `!join` __`Adds a role to yourself`__

        **Usage:** !join [role name]

        **Examples:**
        `!join notify` adds the notify role to yourself

        **Valid Roles:**
        notify (`!join notify`), He/Him/His (`!join he`), She/Her/Hers (`!join she`), They/Them/Theirs (`!join they`), Ze/Zir/Zirs (`!join ze`)
        """

        # case where role name is space separated
        name = " ".join(arg).lower()

        # Display help if given no argument
        if not name:
            raise BadArgs("", show_help=True)

        # make sure that you can't add roles like "prof" or "ta"
        valid_roles = ["notify", "He/Him/His", "She/Her/Hers", "They/Them/Theirs", "Ze/Zir/Zirs"]
        aliases = {"he": "He/Him/His", "she": "She/Her/Hers", "ze": "Ze/Zir/Zirs", "they": "They/Them/Theirs"}

        # Convert alias to proper name
        if name.lower() in aliases:
            name = aliases[name].lower()

        # Grab the role that the user selected
        role = next((r for r in ctx.guild.roles if name == r.name.lower()), None)

        # Check that the role actually exists
        if not role:
            raise BadArgs("You can't add that role!", show_help=True)

        # Ensure that the author does not already have the role
        if role in ctx.author.roles:
            raise BadArgs("you already have that role!")

        # Special handling for roles that exist but can not be selected by a student
        if role.name not in valid_roles:    
            raise BadArgs("you cannot add an instructor/invalid role!", show_help=True)

        await ctx.author.add_roles(role)
        await ctx.send("role added!", delete_after=5)


    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leave(self, ctx, *arg):
        """
        `!leave` __`Removes an existing role from yourself`__

        **Usage:** !leave [role name]

        **Examples:**
        `!leave L2A` removes the L2A role from yourself
        """

        # case where role name is space separated
        name = " ".join(arg).lower()

        if not name:
            raise BadArgs("", show_help=True)

        aliases = {"he": "he/him/his", "she": "she/her/hers", "ze": "ze/zir/zirs", "they": "they/them/theirs"}

        # Convert alias to proper name
        if name.lower() in aliases:
            name = aliases[name]

        role = next((r for r in ctx.guild.roles if name == r.name.lower()), None)

        if not role:
            raise BadArgs("that role doesn't exist!")

        if role not in ctx.author.roles:
            raise BadArgs("you don't have that role!")

        await ctx.author.remove_roles(role)
        await ctx.send("role removed!", delete_after=5)


    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shut(self, ctx, on):
        await ctx.message.delete()
        change = ""

        for role in ctx.guild.roles:
            if role.permissions.administrator:
                continue

            new_perms = role.permissions

            if on == "off":
                change = "enabled messaging permissions"
                new_perms.update(send_messages=True)
            else:
                change = "disabled messaging permissions"
                new_perms.update(send_messages=False)
            try:
              await role.edit(permissions=new_perms)
            except:
              await ctx.send("Cannot edit " + role.name)

        await ctx.send(change)


    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def supershut(self, ctx, on):
        await ctx.message.delete()
        change = ""

        for role in ctx.guild.roles:
            if role.permissions.administrator:
                continue

            new_perms = role.permissions

            if on == "off":
                change = "enabled viewing permissions"
                new_perms.update(read_messages=True)
            else:
                change = "disabled viewing permissions"
                new_perms.update(read_messages=False)

            try:
              await role.edit(permissions=new_perms)
            except:
              await ctx.send("Cannot edit " + role.name)

        await ctx.send(change)


    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def userstats(self, ctx, *userid):
        """
        `!userstats` __`Check user profile and stats`__

        **Usage:** !userstats <USER ID>

        **Examples:** `!userstats 375445489627299851` [embed]
        """

        if not userid:
            user = ctx.author
        else:
            try:
                userid = int(userid[0])
            except ValueError:
                raise BadArgs("Please enter a user id", show_help=True)

            user = ctx.guild.get_member(userid)

        if not user:
            raise BadArgs("That user does not exist")

        # we use both user and member objects, since some stats can only be obtained
        # from either user or member object

        async with ctx.channel.typing():
            most_active_channel = 0
            most_active_channel_name = None
            cum_message_count = 0
            yesterday = (datetime.now() - timedelta(days=1)).replace(tzinfo=pytz.timezone("US/Pacific")).astimezone(timezone.utc).replace(tzinfo=None)

            for channel in ctx.guild.text_channels:
                counter = 0

                async for message in channel.history(after=yesterday, limit=None):
                    if message.author == user:
                        counter += 1
                        cum_message_count += 1

                if counter > most_active_channel:
                    most_active_channel = counter
                    most_active_channel_name = "#" + channel.name

            embed = discord.Embed(title=f"Report for user `{user.name}#{user.discriminator}` (all times in UTC)")
            embed.add_field(name="Date Joined", value=user.joined_at.strftime("%A, %Y %B %d @ %H:%M:%S"), inline=True)
            embed.add_field(name="Account Created", value=user.created_at.strftime("%A, %Y %B %d @ %H:%M:%S"), inline=True)
            embed.add_field(name="Roles", value=", ".join([str(i) for i in sorted(user.roles[1:], key=lambda role: role.position, reverse=True)]), inline=True)
            embed.add_field(name="Most active text channel in last 24 h", value=f"{most_active_channel_name} ({most_active_channel} messages)", inline=True)
            embed.add_field(name="Total messages sent in last 24 h", value=str(cum_message_count), inline=True)

            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Commands(bot))
