import numpy as np
import math
import os
import random
import signal
import sys

import discord
from discord.ext import commands

from util.badargs import BadArgs

def handler(signum, frame):
    raise Exception("overtime")

class Tools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dchannels = []
        self.inquiz = []


    @commands.command()
    async def ref(self, ctx, links = None):
        """
        `!ref` __`Displays reference for SM213`__

        **Usage:** !ref [choice]

        **Examples:**
        `!ref' [embed]
        `!ref ins` [embed with instructions]
        `!ref ex` [embed with examples]

        """

        if links == "ins":
            return await ctx.send("https://media.discordapp.net/attachments/752006091021484052/804239617134034984/unknown.png")
        elif links == "ex":
            return await ctx.send("https://media.discordapp.net/attachments/752006091021484052/804239471658795028/unknown.png")
        await ctx.send("https://media.discordapp.net/attachments/752006091021484052/804239570345787422/unknown.png\nhttps://media.discordapp.net/attachments/752006091021484052/804239617134034984/unknown.png\nhttps://media.discordapp.net/attachments/752006091021484052/804239471658795028/unknown.png")



    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def endian(self, ctx):
        """
        `!endian` __`Displays various representations of a number given operations`__

        **Usage:** !endian [equation]

        **Examples:**
        `!endian 0xDEADBEEF + 0x1337` [embed]
        `!endian` [embed with random expression]

        \*Explicit expressions can only be used by TAs. Students when using this command will be provided with random results.
        """
        if ctx.author.id in self.inquiz: return await ctx.send("Oops! Can't use this when using `!quiz`.")


        role = discord.utils.get(ctx.guild.roles, name="TA")
        role2 = discord.utils.get(ctx.guild.roles, name="Prof/Staff")
        if (role in ctx.author.roles or role2 in ctx.author.roles) and len(ctx.message.content[8:]):
            val = ctx.message.content[8:]

            ops = val.split("+")
            nums = []
            for num in ops:
                nums.append(np.int32(int(num, 0)))
            
            a = sum(nums)
        
        else:
            nums = [np.int32(random.randint(-65535, 65534)), np.int32(random.randint(-65535, 65534))]
            a = sum(nums)
            val = f"{nums[0]} + {nums[1]}"

        result = a
        embed = discord.Embed(title = "Integer Visualizations", description = f"Operation: {val}", color = random.randint(0, 0xffffff))
        numbers = nums + [result]
        
        for i in range(len(numbers)):
            numx = numbers[i]
            if numx < 0: 
                num = numx + 4294967296
            else:
                num = numx

            end = int(num).to_bytes(4, "big")
            end = ['0x' + hex(int(n))[2:].zfill(2) for n in end]
            big = end.copy()
            big = ','.join(big)
            end.reverse()
            end = ','.join(end)
            versions = f"**Unsigned Int**:\n{num}\n**Hex**:\n{hex(num)}\n**Binary**:\n{bin(num)}\n**Big Endian 4 byte**:\n{big}\n**Little Endian 4 byte**:\n{end}"
            if i == len(numbers) - 1:
                embed.add_field(name = f"Signed Result:\n{val} = {numx}", value = versions)
            else:
                embed.add_field(name = f"Signed Operand: {numx}", value = versions)

        embed.set_footer(text = f"Replying to {ctx.author}")

        await ctx.send(embed = embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def quiz(self, ctx, key = None):
        """
        `!quiz` __`Brings up a question on number conversions.`__

        **Usage:** !quiz [type]

        **Examples:**
        `!quiz` [embed]
        `!quiz hex` [embed]
        `!quiz endian` [embed]
        """

        if key == "hex": key = random.randrange(2)
        elif key == "endian": key = random.randint(2, 3)
        else:
            key = random.randrange(4)

        if key == 0:
            number = random.randint(0, 65535)
            await ctx.send(f"QUESTION: Convert {number} to hex.")
            res = await get(ctx, self.bot, who = True)
            if res.lower() != hex(number).lower():
                return await ctx.send(f"False. {number} is {hex(number)} in hex.")
            else:
                return await ctx.send("Correct!")

        elif key == 1:
            number = random.randint(0, 65535)
            await ctx.send(f"QUESTION: Convert {hex(number)} to base 10.")
            res = await get(ctx, self.bot, who = True)
            if res != str(number):
                return await ctx.send(f"False. {hex(number)} is {number} in base 10.")
            else:
                return await ctx.send("Correct!")

        elif key == 2:
            number = random.randint(0, 4294967296)
            await ctx.send(f"QUESTION: what is the Big Endian representation of {hex(number)}?\nEnter hex numbers: e.g. 0x12 0x34 0x56 0x78")
            res = await get(ctx, self.bot, who = True)
            res = res.replace(",", "").replace(" ", "").replace("0x", "")
            if "0x" + res.lstrip("0") != hex(number):
                result = hex(number)[2:].zfill(8)
                result = " ".join(["0x" + result[i:i+2] for i in range(0, 8, 2)])
                return await ctx.send(f"False. {hex(number)} is {result} in Big Endian form.")
            else:
                return await ctx.send("Correct!")

        else:
            number = random.randint(0, 4294967296)
            await ctx.send(f"QUESTION: what is the Little Endian representation of {hex(number)}?\nEnter hex numbers: e.g. 0x12 0x34 0x56 0x78")
            res = await get(ctx, self.bot, who = True)
            res = res.replace(",", " ").split()
            res.reverse()
            res = " ".join(res).replace(" ", "").replace("0x", "")
            if "0x" + res.lstrip("0") != hex(number):
                result = hex(number)[2:].zfill(8)
                result = ["0x" + result[i:i+2] for i in range(0, 8, 2)]
                result.reverse()
                result = " ".join(result)
                return await ctx.send(f"False. {hex(number)} is {result} in Little Endian form.")
            else:
                return await ctx.send("Correct!")




    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pyth(self, ctx):
        """
        `!pyth` __`Runs Python and Python Fake C. Type lines to execute them.`__

        **Usage:** !pyth

        **Examples:**
        `!pyth` [opens IDE]
        """

        try:
            if ctx.channel.id in self.dchannels:
                return await ctx.send("Already running here. You can program in the existing session.")
                
            self.dchannels.append(ctx.channel.id)

            await ctx.send(f"Python {sys.version}\nwith Fake C")
            signal.signal(signal.SIGALRM, handler)

            while True:
                val = await get(ctx, self.bot)

                if val.lower() == "exit":
                    self.dchannels.remove(ctx.channel.id)
                    return await ctx.send("Exiting.")

                val = val.replace("printf", "ctx.send").replace("print", "ctx.send")

                if val.endswith(";"):
                    val = val[:-1]

                if any(val.startswith(x) for x in ["byte", "char", "int", "float", "double", "long"]):
                    val = " ".join(val.split(" ")[1:])

                val = val.replace("(int)", "0xFFFFFFFF & ").replace("(long)", "").replace("(float)", "1.0 * ").replace("(char)", "0XFF & ")

                if any([x.lower() in val.lower() for x in list(globals().keys()) + [";", "eval", "exec", "class", "raise", "dir", "quit", "vars", "filter", "license", "pdb", "import", "ctypes", "globals", "importlib", "open", "format", "breakpoint", "lambda", "enumerate", "print", "input", "iter", "help", "__main__"]]):
                    await ctx.send("ERROR: banned function")
                    continue

                if len(val) > 50:
                    await ctx.send("ERROR: too big")
                    continue
                    
                if val.startswith("#") or val.startswith("'''") or val.startswith('"""'):
                    continue

                if "ctx.send" in val:
                    try: 
                        text = val.replace("\\\"", "'").split("(\"")[1].split("\"")[0]
                        confirmation = val.replace(" ", "").split("\",")[1].split(")")[0]
                        args = "\",".join(val.split("\",")[1:]).split(")")[0].split(",")
                        finalargs = []

                        for arg in args:
                            arg = arg.lstrip().rstrip()
                            if arg in locals():
                                finalargs.append(locals()[arg])
                            elif "\"" not in arg and "'" not in arg:
                                if arg.isdigit():
                                    finalargs.append(int(arg))
                                else:
                                    finalargs.append(float(arg))
                            else:
                                finalargs.append(arg.replace("\"", "").replace("'", ""))

                        text = str(text % tuple(finalargs))
                        await ctx.send(text)
                        continue
                    except Exception as e: 
                        if str(e) != "list index out of range":
                            await ctx.send(str(e))

                signal.alarm(10)
                try:

                    #await ctx.send(sys.getsizeof(locals()))

                    if "ctx" in val:
                        await eval(val)
                    else:
                        res = exec(val)

                    signal.alarm(0)

                except Exception as e:
                    if "invalid syntax" not in str(e) and "is not defined" not in str(e):
                        await ctx.send(str(e))

                    signal.alarm(0)
                    continue

                if " " not in val:
                    try:
                        await ctx.send(str(locals()[val])[:2000])
                        continue
                    except Exception as e:
                        if "is not defined" not in str(e):
                            await ctx.send(str(e))

                        continue

                if res:
                    await ctx.send(res[:2000])
                else:
                    await ctx.send("ok")

        except Exception as e:
            self.dchannels.remove(ctx.channel.id)
            await ctx.send(f"FATAL ERROR: {e}")


async def get(ctx, bot, who = None):
    def check(m):
        nonlocal ww
        ww = m.content
        return m.channel.id == ctx.channel.id and not m.author.bot and (not who or m.author.id == ctx.author.id)

    ww = ""
    try:
        confirm1 = await bot.wait_for("message", timeout = 600, check = check)
    except:
        await ctx.send(f"Ok {ctx.author}, timed out.")
        return "exit"
        
    return ww


def setup(bot):
    bot.add_cog(Tools(bot))