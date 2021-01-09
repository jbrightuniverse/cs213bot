import asyncio
import numpy as np
import random
import traceback

import discord
from discord.ext import commands

from util.badargs import BadArgs


class SM213(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def sim(self, ctx, debug = None):
        """
        `!sim` __`Launch SM213 simulator`__

        **Usage:** !sim

        **Examples:** `!sim` launches simulator
        """

        MEMORY_SIZE = 100000
        NUM_REGISTERS = 8

        memory = np.zeros((MEMORY_SIZE,), dtype = np.uint8)
        registers = np.zeros((NUM_REGISTERS,), dtype = np.uint32)
        
        special = {
            "PC": 0,
            "insOpCode": 0,
            "insOp0": 0,
            "insOp1": 0,
            "insOp2": 0,
            "insOpImm": 0,
            "insOpExt": 0
        }

        await mbed(ctx, "Discord Simple Machine 213", "Type `help` for a commands list.")

        def reg(r):
            return int(r[1:])

        pcpush = 0
        value = 0

        while True:
            message = await get(self.bot, ctx, "exit")
            if not message: return

            if message.content == "": continue

            command = message.content.lstrip().split("#")[0].lower().split()
            instruction = command[0]
            data = "".join(command[1:])
            operands = data.split(",")

            try:

                if instruction == "ld":
                    if operands[0].startswith("$"):
                        # load immediate
                        number = operands[0][1:]
                        value = int(number, base = [10, 16][number.startswith("0x")])
                        registers[reg(operands[1])] = value

                        special["insOpCode"] = 0
                        special["insOp0"] = reg(operands[1])
                        special["insOp1"] = 0
                        special["insOp2"] = 0
                        special["insOpImm"] = 0
                        special["insOpExt"] = value
                        pcpush = 6
                    
                    elif len(operands) == 2 and "(" in operands[0] and ")" in operands[0]:
                        # load base + distance
                        basedata = operands[0].split("(") # find first bracket
                        if basedata[0] == "": 
                            offset = 0
                        else:
                            offset = int(basedata[0])
                        pos = registers[reg(basedata[1][:-1])] # remove second bracket
                        registers[reg(operands[1])] = int.from_bytes(memory[pos + offset : pos + offset + 4], "big")

                        special["insOpCode"] = 1
                        special["insOp0"] = offset//4
                        special["insOp1"] = reg(basedata[1][:-1])
                        special["insOp2"] = reg(operands[1])
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    elif len(operands) == 4 and operands[0][0] == "(" and operands[2][-1] == ")":
                        # load indexed
                        base = registers[reg(operands[0][1:])]
                        offset = registers[reg(operands[1])]
                        multiplier = int(operands[2][:-1])
                        registers[reg(operands[3])] = int.from_bytes(memory[base + offset * multiplier : base + offset * multiplier + 4], "big")

                        special["insOpCode"] = 2
                        special["insOp0"] = reg(operands[0][1:])
                        special["insOp1"] = reg(operands[1])
                        special["insOp2"] = reg(operands[3])
                        special["insOpImm"] = 4
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "st":
                    if len(operands) == 2 and "(" in operands[1] and ")" in operands[1]:
                        # store base + distance
                        basedata = operands[1].split("(")
                        if basedata[0] == "": 
                            offset = 0
                        else:
                            offset = int(basedata[0])
                        pos = registers[reg(basedata[1][:-1])]
                        memory[pos + offset : pos + offset + 4] = list(int(registers[reg(operands[0])]).to_bytes(4, "big"))

                        special["insOpCode"] = 3
                        special["insOp0"] = reg(operands[0])
                        special["insOp1"] = offset//4
                        special["insOp2"] = reg(basedata[1][:-1])
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    elif len(operands) == 4 and operands[1][0] == "(" and operands[3][-1] == ")":
                        # store indexed
                        base = registers[reg(operands[1][1:])]
                        offset = registers[reg(operands[2])]
                        multiplier = int(operands[3][:-1])
                        memory[base + offset * multiplier : base + offset * multiplier + 4] = list(int(registers[reg(operands[0])]).to_bytes(4, "big"))

                        special["insOpCode"] = 4
                        special["insOp0"] = reg(operands[0])
                        special["insOp1"] = reg(operands[1][1:])
                        special["insOp2"] = reg(operands[2])
                        special["insOpImm"] = 4
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "halt":
                    special["PC"] += 2
                    special["insOpCode"] = 2
                    special["insOp0"] = 0
                    special["insOp1"] = 0
                    special["insOp2"] = 0
                    special["insOpImm"] = 0
                    special["insOpExt"] = 0
                    pcpush = 2
                    return await ctx.send("HALT issued. Stopping execution and closing simulator. In a future release, this will not exit the simulator.")

                elif instruction == "nop":
                    pass

                elif instruction == "mov":
                    if len(operands) == 2:
                        registers[reg(operands[1])] = registers[reg(operands[0])]

                        special["insOpCode"] = 6
                        special["insOp0"] = 0
                        special["insOp1"] = reg(operands[0])
                        special["insOp2"] = reg(operands[1])
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "add":
                    if len(operands) == 2:
                        registers[reg(operands[1])] += registers[reg(operands[0])]

                        special["insOpCode"] = 6
                        special["insOp0"] = 1
                        special["insOp1"] = reg(operands[0])
                        special["insOp2"] = reg(operands[1])
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "and":
                    if len(operands) == 2:
                        registers[reg(operands[1])] &= registers[reg(operands[0])]

                        special["insOpCode"] = 6
                        special["insOp0"] = 2
                        special["insOp1"] = reg(operands[0])
                        special["insOp2"] = reg(operands[1])
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "inc":
                    if len(operands) == 1:
                        registers[reg(operands[0])] += 1

                        special["insOpCode"] = 6
                        special["insOp0"] = 3
                        special["insOp1"] = 0
                        special["insOp2"] = reg(operands[0])
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "inca":
                    if len(operands) == 1:
                        registers[reg(operands[0])] += 4

                        special["insOpCode"] = 6
                        special["insOp0"] = 4
                        special["insOp1"] = 0
                        special["insOp2"] = reg(operands[0])
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "dec":
                    if len(operands) == 1:
                        registers[reg(operands[0])] -= 1

                        special["insOpCode"] = 6
                        special["insOp0"] = 5
                        special["insOp1"] = 0
                        special["insOp2"] = reg(operands[0])
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "deca":
                    if len(operands) == 1:
                        registers[reg(operands[0])] -= 4

                        special["insOpCode"] = 6
                        special["insOp0"] = 6
                        special["insOp1"] = 0
                        special["insOp2"] = reg(operands[0])
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "not":
                    if len(operands) == 1:
                        registers[reg(operands[0])] = ~registers[reg(operands[0])]

                        special["insOpCode"] = 6
                        special["insOp0"] = 7
                        special["insOp1"] = 0
                        special["insOp2"] = reg(operands[0])
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "shl":
                    if len(operands) == 2 and operands[0].startswith("$"):
                        registers[reg(operands[1])] <<= int(operands[0][1:])

                        special["insOpCode"] = 7
                        special["insOp0"] = reg(operands[1])
                        special["insOp1"] = int(hex(int(operands[0][1:]))[2:].zfill(2)[0], 16)
                        special["insOp2"] = int(hex(int(operands[0][1:]))[2:].zfill(2)[1], 16)
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "shr":
                    if len(operands) == 2 and operands[0].startswith("$"):
                        registers[reg(operands[1])] >>= int(operands[0][1:])

                        complement = (~int(operands[0][1:]) + 1) & 0xff
                        special["insOpCode"] = 7
                        special["insOp0"] = reg(operands[1])
                        special["insOp1"] = int(hex(complement)[2:].zfill(2)[0], 16)
                        special["insOp2"] = int(hex(complement)[2:].zfill(2)[1], 16)
                        special["insOpImm"] = 0
                        special["insOpExt"] = 0
                        pcpush = 2

                    else: continue

                elif instruction == "ins":
                    if len(command) == 1: command += [".pos", "0"]
                    if command[1] == ".pos":
                        pos = int(command[2], base = [10, 16][command[2].startswith("0x")])
                        myslice = memory[pos : pos + 80]
                        strn = ""
                        
                        for entry in myslice:
                            strn += hex(entry)[2:].zfill(2)

                        instructions = ["```avrasm", "Assembly:              Bytecode:"]
                        ins, bytecode = get_bytecode(strn)
                        instructions += ins

                        for i in range(2, len(instructions)):
                            instructions[i] = instructions[i].ljust(20) + " | " + bytecode[i - 2]

                        await ctx.send("\n".join(instructions + ["```"]))
                        continue

                    else: continue

                elif instruction == "view":
                    if len(command) == 1: command += [".pos", "0"]
                    if command[1] == ".pos":
                        pos = int(command[2], base = [10, 16][command[2].startswith("0x")])
                        myslice = memory[pos : pos + 80]
                        lines = ["```st", " Addr:  0: 1: 2: 3: Ascii:  Value:"]

                        for i in range(20):
                            num = "0x" + hex(pos + i * 4)[2:].zfill(4)
                            a = hex(myslice[i * 4])
                            b = hex(myslice[i * 4 + 1])
                            c = hex(myslice[i * 4 + 2])
                            d = hex(myslice[i * 4 + 3])
                            asc = [chr(myslice[i * 4 + x]) for x in range(4)]
                            res = ""

                            for char in asc:
                                if ord(char) < 0x20 or ord(char) > 0x7f:
                                    res += " "
                                else:
                                    res += char

                            lines.append(f"{num}: {a[2:].zfill(2)} {b[2:].zfill(2)} {c[2:].zfill(2)} {d[2:].zfill(2)} |{res}|  {int.from_bytes(myslice[i * 4 : i * 4 + 4], 'big')}")
                        
                        registerx = ["", "Registers (dec):"]
                        regcontent = [f"r{i}: {registers[i]}" for i in range(len(registers))]
                        registerx.append(" | ".join(regcontent))
                        registerx.append("Registers (hex):")
                        regcontent = [f"r{i}: {hex(registers[i])}" for i in range(len(registers))]
                        registerx.append(" | ".join(regcontent))
                        registerx.append("")
                        regcontent = [f"{key}: {hex(special[key])}" for key in special]
                        registerx.append("\n".join(regcontent))
                        myslice = memory[special['PC'] - pcpush : special['PC']]
                        content = ""

                        for i in range(len(myslice)):
                            a = hex(myslice[i])
                            res = a[2:].zfill(2)
                            content += res

                        registerx.append(f"instruction: {content}")
                        await ctx.send("\n".join(lines + registerx + ["```"]))
                        continue

                else: continue

                hex1 = hex(special["insOpCode"])[2:] + hex(special["insOp0"])[2:]
                hex2 = hex(special["insOp1"])[2:] + hex(special["insOp2"])[2:]
                myslice = [int(hex1, 16), int(hex2, 16)] + [[], list(int(value).to_bytes(4, "big"))][pcpush == 6]
                memory[special["PC"] : special["PC"] + pcpush] = myslice
                strn = ""

                for entry in myslice:
                    strn += hex(entry)[2:].zfill(2)

                special["PC"] += pcpush
                instructions = ["```avrasm", f"{' '.join(command)} | ({strn})"]
                await ctx.send("\n".join(instructions + ["```"]))

            except Exception as e:
                if debug:
                    etype = type(e)
                    trace = e.__traceback__
                    await ctx.send(("```python\n" + "".join(traceback.format_exception(etype, e, trace, 999)) + "```").replace("home/rq2/.local/lib/python3.9/site-packages/", "").replace("/home/rq2/cs213bot/cs213bot/", ""))
                else: 
                    await ctx.send("ERROR: " + str(e))




def setup(bot):
    bot.add_cog(SM213(bot))



async def get(bot, ctx, exitkey):
    try:
        message = await bot.wait_for("message", timeout = 600, check = lambda m: m.channel == ctx.channel and m.author.id == ctx.author.id)
    except:
        await ctx.send("Timed out waiting for you. Exiting simulator.")
        return None

    if message.content == exitkey:
        await ctx.send("Exiting simulator.")
        return None

    return message


async def mbed(ctx, upper, lower, fields = [], thumbnail = None, footer = None):
    embed = discord.Embed(title = upper, description = lower, color = random.randint(0, 0xffffff))

    for field in fields:
        embed.add_field(name = field[0], value = field[1], inline = False)

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    if footer:
        embed.set_footer(text=footer + f"\nReplying to {ctx.author}")
    else:
        embed.set_footer(text = f"Replying to {ctx.author}")
        
    return await ctx.send(embed = embed)


def get_bytecode(strn):
    counter = 0
    instructions = []
    bytecode = []
    while counter < len(strn):
        # first nibble
        opcode = strn[counter]
        if opcode == "0":
            if counter > 148: break
            cont = strn[counter + 4 : counter + 12].lstrip('0')
            if not cont: cont = 0
            instructions.append(f"ld $0x{cont}, r{strn[counter + 1]}")
            bytecode.append(strn[counter : counter + 12])
            counter += 8
        
        elif opcode == "1":
            instructions.append(f"ld {int(strn[counter + 1]) * 4}(r{strn[counter + 2]}), r{strn[counter + 3]}")
            bytecode.append(strn[counter : counter + 4])

        elif opcode == "2":
            instructions.append(f"ld (r{strn[counter + 1]}, r{strn[counter + 2]}, 4), r{strn[counter + 3]}")
            bytecode.append(strn[counter : counter + 4])

        elif opcode == "3":
            instructions.append(f"st r{strn[counter + 1]}, {int(strn[counter + 2]) * 4}(r{strn[counter + 3]})")
            bytecode.append(strn[counter : counter + 4])

        elif opcode == "4":
            instructions.append(f"ld r{strn[counter + 1]}, (r{strn[counter + 2]}, r{strn[counter + 3]}, 4)")
            bytecode.append(strn[counter : counter + 4])

        elif opcode == "f":
            if strn[counter + 1] == "0":
                instructions.append("halt")
                bytecode.append(strn[counter : counter + 4])
                break

            elif strn[counter + 1] == "f":
                instructions.append("nop")
                bytecode.append(strn[counter : counter + 4])

        elif opcode == "6":
            op0 = strn[counter + 1]
            if op0 == "0":
                instructions.append(f"mov r{strn[counter + 2]}, r{strn[counter + 3]}")
                bytecode.append(strn[counter : counter + 4])

            elif op0 == "1":
                instructions.append(f"add r{strn[counter + 2]}, r{strn[counter + 3]}")
                bytecode.append(strn[counter : counter + 4])

            elif op0 == "2":
                instructions.append(f"and r{strn[counter + 2]}, r{strn[counter + 3]}")
                bytecode.append(strn[counter : counter + 4])

            elif op0 == "3":
                instructions.append(f"inc r{strn[counter + 3]}")
                bytecode.append(strn[counter : counter + 4])

            elif op0 == "4":
                instructions.append(f"inca r{strn[counter + 3]}")
                bytecode.append(strn[counter : counter + 4])

            elif op0 == "5":
                instructions.append(f"dec r{strn[counter + 3]}") 
                bytecode.append(strn[counter : counter + 4])  

            elif op0 == "6":
                instructions.append(f"deca r{strn[counter + 3]}")
                bytecode.append(strn[counter : counter + 4])

            elif op0 == "7":
                instructions.append(f"not r{strn[counter + 3]}")
                bytecode.append(strn[counter : counter + 4])

        elif opcode == "7":
            number = strn[counter + 2 : counter + 4]
            if int(number, base = 16) > 127:
                number = 256 - int(number, base = 16)
                cont = hex(number)[2:].zfill(2).lstrip('0')
                if not cont: cont = 0
                instructions.append(f"shr ${cont}, r{strn[counter + 1]}")
                bytecode.append(strn[counter : counter + 4])

            else:
                cont = number.lstrip('0')
                if not cont: cont = 0
                instructions.append(f"shl ${cont}, r{strn[counter + 1]}")
                bytecode.append(strn[counter : counter + 4])

        counter += 4

    return instructions, bytecode