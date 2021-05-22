import time
import subprocess

import discord
from discord.ext import commands

def can_connect(server_ip):
    # https://github.com/Person314159/cs221bot/blob/master/cogs/server_checker.py
    try:
        # Command from https://stackoverflow.com/a/47166507
        output = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "PubkeyAuthentication=no", "-o",
                                 "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
                                 "-o", "ChallengeResponseAuthentication=no", server_ip,
                                 "2>&1"], capture_output=True, timeout=5).stderr.decode("utf-8")

        return "Permission denied" in output or "verification failed" in output
    except subprocess.TimeoutExpired:
        return False

class Tools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def assign(self, ctx):
        """
        `!assign` __`Displays current PL assignments for CPSC 213`__

        **Usage:** !assign

        **Examples:**
        `!assign` [embed]

        """
        embed = discord.Embed(title = f"Current Assessments on CPSC 213 PrairieLearn", description = f"Requested by {ctx.author}", color = 0x8effc1)
        for assigntype in self.bot.pl_dict:
            entrylist = self.bot.pl_dict[assigntype]
            formattedentries = []
            seenmodes = []
            for entry in entrylist:
                skip = False
                formatted = f"`{entry['label']}` **[{entry['name']}](https://ca.prairielearn.org/pl/course_instance/2316/assessment/{entry['id']}/)**\nCredit:\n"
                for mode in entry["modes"]:
                    if mode['end'] and mode['credit'] == 100:
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
        

    @commands.command()
    async def checkservers(self, ctx):
        """
        `!checkservers` __`Shows status of UBC CS department servers`__

        **Usage:** !checkservers
        """
        # https://github.com/Person314159/cs221bot/blob/master/cogs/server_checker.py
        msgs = []
        for server_name in ["thetis", "remote", "annacis", "anvil", "bowen", "lulu", "gambier"]:
            ip = f"{server_name}.students.cs.ubc.ca"
            connect = can_connect(ip)
            msgs.append(f"{['⚠️', '✅'][connect]} {server_name} is {['offline', 'online'][connect]}")

        await ctx.send("\n".join(msgs))


    @commands.command()
    async def ref(self, ctx):
        """
        `!ref` __`Displays reference for SM213`__

        **Usage:** !ref

        **Examples:**
        `!ref' [embed]
        """
        await ctx.send("""https://media.discordapp.net/attachments/752006091021484052/804239570345787422/unknown.png
https://media.discordapp.net/attachments/752006091021484052/804239617134034984/unknown.png
https://media.discordapp.net/attachments/752006091021484052/804239471658795028/unknown.png""")


def setup(bot):
    bot.add_cog(Tools(bot))