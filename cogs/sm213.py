import asyncio
import numpy as np
import random
import traceback

import discord
from discord.ext import commands

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

        The sm213 language was created by Dr. Mike Feeley of the CPSC department at UBCV. 
        Used with permission.

        Run the command and type `help` for more detailed specs.
        """

        MEMORY_SIZE = 100000
        NUM_REGISTERS = 8

        memory = np.zeros((MEMORY_SIZE,), dtype = np.uint8)
        registers = np.zeros((NUM_REGISTERS,), dtype = np.uint32)
        
        specialregisters = {
            "PC": 0,
            "insOpCode": 0,
            "insOp0": 0,
            "insOp1": 0,
            "insOp2": 0,
            "insOpImm": 0,
            "insOpExt": 0
        }
        memptr = 0
        static_mode = False

        await mbed(ctx, "Discord Simple Machine 213", "**Type `help` for a commands list.**")

        pcpush = 0
        value = 0

        while True:
            message = await get(self.bot, ctx, "exit")
            if not message: return
            if message.content == "": continue

            cmd = message.content.lower()
            commands = cmd.split("\n")
            bytecodes = []
            cmdxs = []
            special = {
                "PC": -1,
                "insOpCode": 0,
                "insOp0": 0,
                "insOp1": 0,
                "insOp2": 0,
                "insOpImm": 0,
                "insOpExt": 0
            }

            new = False

            b = 0
            for cmdx in commands:
                command = cmdx.lstrip().split("#")[0].split()
                if len(command) == 0: continue
                
                stepmode = False
                oldstatic = static_mode
                if command[0] == "step":
                    if hex(memory[specialregisters["PC"]])[2:].zfill(2)[0] in ["0", "b"]: thesize = 6
                    else: thesize = 2

                    myslice = memory[specialregisters["PC"] : specialregisters["PC"] + thesize]
                    strn = ""
                    
                    for entry in myslice:
                        strn += hex(entry)[2:].zfill(2)

                    instructions, _ = get_bytecode(strn)
                    command = instructions[0].split()
                    commands[b] = instructions[0]

                    stepmode = True
                    static_mode = False

                args = await step(ctx, stepmode, debug, new, cmdx, command, special, bytecodes, cmdxs, commands, pcpush, value, memptr, static_mode, specialregisters, memory, registers)
                if not args: continue
                memptr, static_mode, pcpush, value, new = args
                if stepmode: 
                    static_mode = oldstatic
                    cmdxs[b] = commands[b]
                b += 1

            if new: 
                instructions = ["```avrasm"]
                i = 0
                j = 0
                
                for c in cmdxs:
                    while commands[i] != cmdxs[j]:
                        instructions.append(f"# {commands[i].ljust(18)} | invalid instruction")
                        i += 1
                        if i >= len(commands): break

                    if i >= len(commands): break

                    instructions.append(cmdxs[j].ljust(20) + " | " + bytecodes[j])
                    j += 1
                    i += 1

                await ctx.send("\n".join(instructions + ["```"]))


def setup(bot):
    bot.add_cog(SM213(bot))

def reg(r):
    return int(r[1:])

async def step(ctx, stepmode, debug, new, cmdx, command, special, bytecodes, cmdxs, commands, pcpush, value, memptr, static_mode, specialregisters, memory, registers):
    instruction = command[0]
    data = "".join(command[1:])
    operands = data.split(",")

    try:

        if instruction == "ld":
            if operands[0].startswith("$"):
                # load immediate
                number = operands[0][1:]
                value = int(number, base = [10, 16][number.startswith("0x")])
                if not static_mode:
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
                if not static_mode:
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
                if not static_mode:
                    registers[reg(operands[3])] = int.from_bytes(memory[base + offset * multiplier : base + offset * multiplier + 4], "big")

                special["insOpCode"] = 2
                special["insOp0"] = reg(operands[0][1:])
                special["insOp1"] = reg(operands[1])
                special["insOp2"] = reg(operands[3])
                special["insOpImm"] = 4
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "st":
            if len(operands) == 2 and "(" in operands[1] and ")" in operands[1]:
                # store base + distance
                basedata = operands[1].split("(")
                if basedata[0] == "": 
                    offset = 0
                else:
                    offset = int(basedata[0])
                pos = registers[reg(basedata[1][:-1])]
                if not static_mode:
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
                if not static_mode:
                    memory[base + offset * multiplier : base + offset * multiplier + 4] = list(int(registers[reg(operands[0])]).to_bytes(4, "big"))

                special["insOpCode"] = 4
                special["insOp0"] = reg(operands[0])
                special["insOp1"] = reg(operands[1][1:])
                special["insOp2"] = reg(operands[2])
                special["insOpImm"] = 4
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "halt":
            special["insOpCode"] = 15
            special["insOp0"] = 0
            special["insOp1"] = 0
            special["insOp2"] = 0
            special["insOpImm"] = 0
            special["insOpExt"] = 0
            pcpush = 2

        elif instruction == "nop":
            special["insOpCode"] = 15
            special["insOp0"] = 15
            special["insOp1"] = 0
            special["insOp2"] = 0
            special["insOpImm"] = 0
            special["insOpExt"] = 0
            pcpush = 2

        elif instruction == "mov":
            if len(operands) == 2:
                if not static_mode:
                    registers[reg(operands[1])] = registers[reg(operands[0])]

                special["insOpCode"] = 6
                special["insOp0"] = 0
                special["insOp1"] = reg(operands[0])
                special["insOp2"] = reg(operands[1])
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "add":
            if len(operands) == 2:
                if not static_mode:
                    registers[reg(operands[1])] += registers[reg(operands[0])]

                special["insOpCode"] = 6
                special["insOp0"] = 1
                special["insOp1"] = reg(operands[0])
                special["insOp2"] = reg(operands[1])
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "and":
            if len(operands) == 2:
                if not static_mode:
                    registers[reg(operands[1])] &= registers[reg(operands[0])]

                special["insOpCode"] = 6
                special["insOp0"] = 2
                special["insOp1"] = reg(operands[0])
                special["insOp2"] = reg(operands[1])
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "inc":
            if len(operands) == 1:
                if not static_mode:
                    registers[reg(operands[0])] += 1

                special["insOpCode"] = 6
                special["insOp0"] = 3
                special["insOp1"] = 0
                special["insOp2"] = reg(operands[0])
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "inca":
            if len(operands) == 1:
                if not static_mode:
                    registers[reg(operands[0])] += 4

                special["insOpCode"] = 6
                special["insOp0"] = 4
                special["insOp1"] = 0
                special["insOp2"] = reg(operands[0])
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "dec":
            if len(operands) == 1:
                if not static_mode:
                    registers[reg(operands[0])] -= 1

                special["insOpCode"] = 6
                special["insOp0"] = 5
                special["insOp1"] = 0
                special["insOp2"] = reg(operands[0])
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "deca":
            if len(operands) == 1:
                if not static_mode:
                    registers[reg(operands[0])] -= 4

                special["insOpCode"] = 6
                special["insOp0"] = 6
                special["insOp1"] = 0
                special["insOp2"] = reg(operands[0])
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "not":
            if len(operands) == 1:
                if not static_mode:
                    registers[reg(operands[0])] = ~registers[reg(operands[0])]

                special["insOpCode"] = 6
                special["insOp0"] = 7
                special["insOp1"] = 0
                special["insOp2"] = reg(operands[0])
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "shl":
            if len(operands) == 2 and operands[0].startswith("$"):
                if not static_mode:
                    registers[reg(operands[1])] <<= int(operands[0][1:])

                special["insOpCode"] = 7
                special["insOp0"] = reg(operands[1])
                special["insOp1"] = int(hex(int(operands[0][1:]))[2:].zfill(2)[0], 16)
                special["insOp2"] = int(hex(int(operands[0][1:]))[2:].zfill(2)[1], 16)
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "shr":
            if len(operands) == 2 and operands[0].startswith("$"):
                if not static_mode:
                    registers[reg(operands[1])] >>= int(operands[0][1:])

                complement = (~int(operands[0][1:]) + 1) & 0xff
                special["insOpCode"] = 7
                special["insOp0"] = reg(operands[1])
                special["insOp1"] = int(hex(complement)[2:].zfill(2)[0], 16)
                special["insOp2"] = int(hex(complement)[2:].zfill(2)[1], 16)
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction in ["br", "bgt", "beq"]:
            if (instruction == "br" and len(operands) == 1) or (instruction in ["beq", "bgt"] and len(operands) == 2):
                number = operands[[1, 0][instruction == "br"]].replace("$", "")
                num = int(number, base = [10, 16][number.startswith("0x")])
                pp = (num - special["PC"])//2
                if instruction == "br" or (registers[reg(operands[0])] == 0 and instruction == "beq") or (registers[reg(operands[0])] > 0 and instruction == "bgt"):
                    if not static_mode:
                        special["PC"] = num

                special["insOpCode"] = {"br": 8, "beq": 9, "bgt": 10}[instruction]
                if instruction == "br": special["insOp0"] = 0
                else: special["insOp0"] = reg(operands[0])
                if pp < 0:
                    pp = (~pp + 1) & 0xff
                special["insOp1"] = int(hex(pp)[2:].zfill(2)[0], 16)
                special["insOp2"] = int(hex(pp)[2:].zfill(2)[1], 16)
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "gpc":
            if len(operands) == 2:
                number = operands[0].replace("$", "")
                num = int(number, base = [10, 16][number.startswith("0x")])
                if not static_mode:
                    registers[reg(operands[1])] = special["PC"] + num

                special["insOpCode"] = 6
                special["insOp0"] = 15
                special["insOp1"] = num//2
                special["insOp2"] = reg(operands[1])
                special["insOpImm"] = 0
                special["insOpExt"] = 0
                pcpush = 2

            else: return None

        elif instruction == "j":
            if len(operands) == 1:
                if "(" not in operands[0]:
                    number = operands[0].replace("$", "")
                    num = int(number, base = [10, 16][number.startswith("0x")])
                    if not static_mode:
                        special["PC"] = num

                    special["insOpCode"] = 11
                    special["insOp0"] = 0
                    special["insOp1"] = 0
                    special["insOp2"] = 0
                    special["insOpImm"] = 0
                    special["insOpExt"] = num
                    pcpush = 6

                elif "*" not in operands[0] and "(" in operands[0]:
                    components = operands[0].split("(")
                    number = operands[0].replace("$", "")
                    offset = int(number, base = [10, 16][number.startswith("0x")])
                    src = registers[reg(components[1][:-1])]
                    if not static_mode:
                        special["PC"] = src + offset

                    pp = offset//2

                    special["insOpCode"] = 12
                    special["insOp0"] = reg(components[1][:-1])
                    special["insOp1"] = int(hex(pp)[2:].zfill(2)[0], 16)
                    special["insOp2"] = int(hex(pp)[2:].zfill(2)[1], 16)
                    special["insOpImm"] = 0
                    special["insOpExt"] = 0
                    pcpush = 2

                elif "*" in operands[0] and "(" in operands[0]:
                    operands[0] = operands[0][1:]
                    components = operands[0].split("(")
                    number = operands[0].replace("$", "")
                    offset = int(number, base = [10, 16][number.startswith("0x")])
                    src = registers[reg(components[1][:-1])]
                    if not static_mode:
                        special["PC"] = memory[src + offset]

                    pp = offset//4

                    special["insOpCode"] = 13
                    special["insOp0"] = reg(components[1][:-1])
                    special["insOp1"] = int(hex(pp)[2:].zfill(2)[0], 16)
                    special["insOp2"] = int(hex(pp)[2:].zfill(2)[1], 16)
                    special["insOpImm"] = 0
                    special["insOpExt"] = 0
                    pcpush = 2

                else: return None
            
            elif len(operands) == 3:
                operands[0] = operands[0][2:]
                source = registers[reg(operands[0])]
                indx = registers[reg(operands[1])]
                if not static_mode:
                    special["PC"] = memory[4 * indx + source]

                special["insOpCode"] = 14
                special["insOp0"] = reg(operands[0])
                special["insOp1"] = reg(operands[1])
                special["insOp2"] = 0
                special["insOpImm"] = 4
                special["insOpExt"] = 0
                pcpush = 2

            else: return None


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
                return None

            else: return None

        elif instruction == "help":
            fields = []
            spacer = '\u200b\t'
            basics = f"If you opened this, you have the simulator open. To execute code, type the line you wish to execute into Discord.\n\nThe line will be executed immediately and saved into memory.\nInstructions start loading at `0x0`.\n\nType multiple lines at once to execute all of them at once. Make sure each instruction is on a new line.\n\n{spacer*10}Aside from the sm213 ISA, the following **special commands** also exist.\n{spacer*10}These are **not part of sm213** and **cannot be used in sm213 programs**\n{spacer*25}but can be used to manipulate the Discord simulator\n{spacer*40}and the Discord simulator **alone**.\n\n_ _"
            fields.append([":1234: Basics\n_ _", basics])
            specialx = "`view`\nView the current memory layout in its entirety, starting from memory position `0x0`.\n\n`view .pos 0x1000`\nDoes the above, but views memory at `0x1000`. Change this value to view a different memory location.\n\n"
            specialx += "`ins`\nView the current set of instructions. This is done by reading off the memory as if everything were instructions.\n\n`ins .pos 0x1000`\nViews the current set of instructions by reading them off memory from `0x1000`. Change this value to view a different memory location.\n\n"
            specialx += "`auto on`\nActivates auto mode. This means any command you type executes immediately.\n\n`auto off`\nDeactivates auto mode. This turns the system into a text-editor-esque IDE where commands you enter don't execute.\n\n"
            specialx += "`step`\nManually executes the instruction at the current location of the Program Counter (PC). Increments PC accordingly.\n\n"
            specialx += "`help`\nViews this message."
            fields.append([":sparkles: Special Commands\n_ _", specialx])
            await mbed(ctx, "Discord Simple Machine Docs", "This assumes you have at least some knowledge of the sm213 language. If you don't, please review the language first before continuing.", fields = fields, footer = "Credits:\n\nThe sm213 language was created by Dr. Mike Feeley of the CPSC department at UBCV.\nUsed with permission.\n\nDiscord Simple Machine created by James Yu with feedback from users and friends.\nLoosely inspired by the functionality of the Java Simple Machine 213\nand the web 213/313 simulator.\n")
            return None

        elif instruction == "auto":
            if len(operands) == 1:
                if operands[0] == "on":
                    static_mode = False
                    await ctx.send("Enabled interactive mode. This means every instruction you print will be executed immediately.")
                elif operands[0] == "off":
                    static_mode = True
                    await ctx.send("Enabled text editor mode. This means instructions you print will **not** be executed and you must call `step` to run them.")

            return memptr, static_mode, pcpush, value, new 

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
                regcontent = [f"r{i}: {'0x'+hex(registers[i])[2:].zfill(8)}" for i in range(len(registers))]
                registerx.append(" | ".join(regcontent))
                registerx.append("")
                regcontent = [f"{key}: {hex(specialregisters[key])}" for key in specialregisters]
                registerx.append("\n".join(regcontent))
                myslice = memory[special['PC'] - pcpush : special['PC']]
                content = ""

                for i in range(len(myslice)):
                    a = hex(myslice[i])
                    res = a[2:].zfill(2)
                    content += res

                registerx.append(f"instruction: {content}")
                await ctx.send("\n".join(lines + registerx + [f"Edit Pointer: {hex(memptr)}", f"Mode: {['Interactive', 'Text Editor'][static_mode]}", "```"]))
                return None

        else: return None

        hex1 = hex(special["insOpCode"])[2:] + hex(special["insOp0"])[2:]
        hex2 = hex(special["insOp1"])[2:] + hex(special["insOp2"])[2:]
        myslice = [int(hex1, 16), int(hex2, 16)] + [[], list(int(value).to_bytes(4, "big"))][pcpush == 6]
        if not stepmode:
            memory[memptr : memptr + pcpush] = myslice
        strn = ""

        for entry in myslice:
            strn += hex(entry)[2:].zfill(2)

        bytecodes.append(strn)
        cmdxs.append(cmdx)

        if not stepmode:    
            memptr += pcpush

        new = True

        if not static_mode:
            for key in special:
                if key != "PC":
                    specialregisters[key] = special[key]
            if special["PC"] != -1: specialregisters["PC"] = special["PC"] + pcpush
            else: specialregisters["PC"] += pcpush
            special["PC"] = -1

    except Exception as e:
        if debug:
            etype = type(e)
            trace = e.__traceback__
            await ctx.send(("```python\n" + "".join(traceback.format_exception(etype, e, trace, 999)) + "```").replace("home/rq2/.local/lib/python3.9/site-packages/", "").replace("/home/rq2/cs213bot/cs213bot/", ""))
        else: 
            await ctx.send("ERROR: " + str(e))

    return memptr, static_mode, pcpush, value, new 


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
