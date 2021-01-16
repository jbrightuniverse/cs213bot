import asyncio
import numpy as np
import os
import random
import traceback
import time

import discord
from discord.ext import commands

class SM213(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    @commands.is_owner()
    async def commit(self, ctx):
        message = ctx.message.content[8:]
        if not message: 
            return await ctx.send("Message?")

        text = os.popen(f"git add-commit -m '{message}'").read()
        if not text: 
            return await ctx.send("Failed.")

        os.popen(f"git push origin master").read()
        await ctx.send(text + "\nPushed to master.")


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

        MEMORY_SIZE = 2**16
        NUM_REGISTERS = 8

        # initialize main memory and primary registers
        memory = np.zeros((MEMORY_SIZE,), dtype = np.uint8)
        registers = np.zeros((NUM_REGISTERS,), dtype = np.uint32)
        
        # special registers for instruction feedback
        splreg = {
            "PC": 0,
            "insOpCode": 0,
            "insOp0": 0,
            "insOp1": 0,
            "insOp2": 0,
            "insOpImm": 0,
            "insOpExt": 0
        }

        # some pointers
        memptr = 0
        should_execute = True
        should_tick = False
        instruction = []

        # time check variables
        start_time = 0
        current_time = 0
        should_ping_time = False
        sent_ping = False

        await mbed(ctx, "Discord Simple Machine 213", "**Type `help` for a commands list.**\n\nNOTE: branching commands do not currently exhibit expected behaviour. Please refrain from relying on their current characteristics for learning.")

        while True:
            if (not should_execute or memptr == splreg["PC"]) and not should_tick:
                # check if last execution has finished and a ping was sent
                if sent_ping:
                    await ctx.send("```Execution finished```")
                    sent_ping = False

                # wait for a message
                message = await get(self.bot, ctx, "exit")
                if not message: return # exit on return condition from get function
                if message.content == "": continue # skip if blank

                commands = message.content.lower().split("\n")
                bytecodes = []
                working_commands = []
                ins_found = False

                for originalcommand in commands:
                    # extract the command, delete any comments or leading whitespace
                    command = originalcommand.lstrip().split("#")[0].split()

                    # if that was a blank line or entirely comment, command is invalid
                    if len(command) == 0: 
                        working_commands.append("# " + originalcommand)
                        bytecodes.append("invalid instruction")
                        continue
                    
                    elif command[0] in ["view", "ins", "auto", "help"]:
                        # run one of the special commands
                        retval = await special_commands(ctx, command, memory, registers, should_execute, memptr, splreg)
                        if command[0] == "auto": should_execute = retval
                        # its still an invalid command
                        working_commands.append("# " + originalcommand)
                        bytecodes.append("invalid instruction")
                        continue
                    
                    elif command[0] == "step":
                        should_tick = True
                        if elements_equal(instruction, get_bytes_from_ins(["halt"], memptr)):
                            memptr += 2

                    else:
                        instruction = get_bytes_from_ins(command, memptr)
                        memory, memptr = write_to_mem(instruction, memory, memptr)
                        if len(bytecode := make_byte(instruction)) == 0:
                            bytecode = "# invalid instruction"
                        start_time = time.time()
                        should_ping_time = True

                    if bytecode != "# invalid instruction" and not should_tick: 
                        # instruction was valid, add it directly
                        ins_found = True
                        working_commands.append(originalcommand)
                        bytecodes.append(bytecode)

                    else:
                        # instruction was invalid
                        working_commands.append("# " + originalcommand)
                        bytecodes.append("invalid instruction")

                if ins_found: 
                    instructions = ["```avrasm"] # discord code block formatting
                    for i in range(len(working_commands)):
                        if i >= len(commands): break
                        # add some formatted spacing
                        instructions.append(working_commands[i].ljust(20) + " | " + bytecodes[i])

                    await ctx.send("\n".join(instructions + ["```"]))
            elif should_execute or should_tick:
                # ping if the execution is taking awhile
                if should_ping_time and current_time > start_time + 1:
                    await ctx.send("```Execution still in progress, please wait...```")
                    should_ping_time = False
                    sent_ping = True

                # store previous instruction (empty if first instruction)
                old_instruction = instruction

                # get instruction from memory
                instruction = read_from_mem(memory, splreg["PC"])

                # check if the next two instructions are load zeros
                load_zero = get_bytes_from_ins(["ld", "$0x0,", "r0"], memptr)
                if elements_equal(instruction, load_zero) and elements_equal(read_from_mem(memory, splreg["PC"] + 6), load_zero):
                    instruction = get_bytes_from_ins(["halt"], memptr)
                    memptr = splreg["PC"]
                
                # convert ints to a bytecode string
                strn = ""
                for entry in instruction:
                    strn += hex(entry)[2:].zfill(2)

                # retrieve the instruction from the bytecode
                instructions, _ = bytes_to_assembly_and_bytecode(strn, splreg["PC"])
                originalcommand = instructions[0]

                splreg["PC"] = await step(ctx, instruction, splreg["PC"], memptr, memory, registers, should_execute, debug)
                should_tick = False
                current_time = time.time()

def elements_equal(list1, list2):
    return all(list(map(lambda x, y: x == y, list1, list2)))

async def special_commands(ctx, command, memory, registers, should_execute, memptr, splreg):
    """
    some special non-sm213 commands
    """
    
    instruction = command[0]
    operands = command[1:]
    
    if instruction == "ins":
        # instruction display mode
        if len(command) == 1:
            command += [".pos", "0"]

        if command[1] == ".pos":
            # determine what point in memory to start reading
            pos = int(command[2], base = [10, 16][command[2].startswith("0x")])

            # get memory slice and read a bytecode string
            myslice = memory[pos : pos + 80]
            strn = ""
            for entry in myslice:
                strn += hex(entry)[2:].zfill(2)

            # compile the output
            instructions = ["```avrasm", "Assembly:              Bytecode:"]
            ins, bytecode = bytes_to_assembly_and_bytecode(strn, splreg["PC"])
            instructions += ins

            # add bytecode
            for i in range(2, len(instructions)):
                instructions[i] = instructions[i].ljust(20) + " | " + bytecode[i - 2]

            return await ctx.send("\n".join(instructions + ["```"]))

    elif instruction == "help":
        # simple help text
        fields = []
        spacer = '\u200b\t' # this allows center-justify when multiplied; discord only lets you dupe spaces if they are different characters
        basics = f"If you opened this, you have the simulator open. To execute code, type the line you wish to execute into Discord.\n\nThe line will be executed immediately and saved into memory.\nInstructions start loading at `0x0`.\n\nType multiple lines at once to execute all of them at once. Make sure each instruction is on a new line.\n\n{spacer*10}Aside from the sm213 ISA, the following **special commands** also exist.\n{spacer*10}These are **not part of sm213** and **cannot be used in sm213 programs**\n{spacer*25}but can be used to manipulate the Discord simulator\n{spacer*40}and the Discord simulator **alone**.\n\n_ _"
        fields.append([":1234: Basics\n_ _", basics])
        specialx = "`view`\nDefault view, views registers only.\n\n`view .pos 0x1000`\nViews memory contents, starting from position `0x1000`. Change this value to view a different memory location.\n\n"
        specialx += "`view mem`\nShortcut to view memory at `0x0`.\n\n`view reg`\nViews all register contents.\n\n`view all`\nViews everything.\n\n`view .pos 0x1000 all`\nViews everything with memory starting from `0x1000`.\n\n"
        specialx += "`ins`\nView the current set of instructions. This is done by reading off the memory as if everything were instructions.\n\n`ins .pos 0x1000`\nViews the current set of instructions by reading them off memory from `0x1000`. Change this value to view a different memory location.\n\n"
        specialx += "`auto on`\nActivates auto mode. This means any command you type executes immediately.\n\n`auto off`\nDeactivates auto mode. This turns the system into a text-editor-esque IDE where commands you enter don't execute.\n\n"
        specialx += "`step`\nManually executes the instruction at the current location of the Program Counter (PC). Increments PC accordingly.\n\n"
        specialx += "`help`\nViews this message."
        fields.append([":sparkles: Special Commands\n_ _", specialx])
        return await mbed(ctx, "Discord Simple Machine Docs", "This assumes you have at least some knowledge of the sm213 language. If you don't, please review the language first before continuing.", fields = fields, footer = "Credits:\n\nThe sm213 language was created by Dr. Mike Feeley of the CPSC department at UBCV.\nUsed with permission.\n\nDiscord Simple Machine created by James Yu with feedback from users and friends.\nLoosely inspired by the functionality of the Java Simple Machine 213\nand the web 213/313 simulator.\n")

    elif instruction == "auto":
        # switch between modes
        if len(operands) == 1:
            if operands[0] == "on":
                # interactive mode
                should_execute = True
                await ctx.send("Enabled interactive mode. This means every instruction you print will be executed immediately.")
            elif operands[0] == "off":
                # static mode
                should_execute = False
                await ctx.send("Enabled text editor mode. This means instructions you print will **not** be executed and you must call `step` to run them.")

        return should_execute

    elif instruction == "view":
        # figure out what was sent in the command
        if len(command) == 1: command += [".pos", "0", "reg"]
        elif command == ["view", "all"]: command = ["view", ".pos", "0", "all"]
        elif command == ["view", "reg"]: command = ["view", ".pos", "0", "reg"]
        elif command == ["view", "mem"]: command = ["view", ".pos", "0", "mem"]
        elif len(command) == 3: command += ["mem"] # len == 3 means it was of the form view .pos X

        if command[1] == ".pos":
            if command[3] == "all":
                # include all modes
                mode = ["mem", "reg"]
            else:
                # take original mode
                mode = [command[3]]

            if "mem" in mode:
                # display memory contents
                pos = int(command[2], base = [10, 16][command[2].startswith("0x")])
                myslice = memory[pos : pos + 80]
                lines = ["```st", " Addr:  0: 1: 2: 3: Ascii:  Value:"]

                # we have 20 lines
                for i in range(20):
                    num = "0x" + hex(pos + i * 4)[2:].zfill(4)
                    # extract individual bytes
                    a = hex(myslice[i * 4])
                    b = hex(myslice[i * 4 + 1])
                    c = hex(myslice[i * 4 + 2])
                    d = hex(myslice[i * 4 + 3])

                    # ascii representation
                    asc = [chr(myslice[i * 4 + x]) for x in range(4)]
                    res = ""
                    for char in asc:
                        if ord(char) < 0x20 or ord(char) > 0x7f:
                            # discard unprintable chars
                            res += " "
                        else:
                            res += char

                    # get signed integer value and save line
                    val = to_unsigned(int.from_bytes(myslice[i * 4 : i * 4 + 4], 'big'), 32)
                    lines.append(f"{num}: {a[2:].zfill(2)} {b[2:].zfill(2)} {c[2:].zfill(2)} {d[2:].zfill(2)} |{res}|  {val}")
            
            else:
                # if not displaying memory, have a different header
                lines = ["```st"]

            registerx = []
            if "reg" in mode:
                # display registers
                if "mem" in mode: 
                    # add a spacer if everything is displayed
                    registerx += [""]

                # display decimal and hex registers followed by special registers
                registerx += ["Registers (dec):"]
                regcontent = [f"r{i}: {to_unsigned(registers[i], 32)}" for i in range(len(registers))]
                registerx.append(" | ".join(regcontent))
                registerx.append("Registers (hex):")
                regcontent = [f"r{i}: {'0x'+hex(registers[i])[2:].zfill(8)}" for i in range(len(registers))]
                registerx.append(" | ".join(regcontent))
                registerx.append("")
                regcontent = [f"{key}: {hex(splreg[key])}" for key in splreg]
                registerx.append("\n".join(regcontent))

                # determine what the instruction actually was
                myslice = memory[splreg['PC'] - [2, 6][splreg["insOpCode"] in [0, 11]] : splreg['PC']]
                content = ""
                for i in range(len(myslice)):
                    a = hex(myslice[i])
                    res = a[2:].zfill(2)
                    content += res

                registerx.append(f"instruction: {content}")

            return await ctx.send("\n".join(lines + registerx + [f"Edit Pointer: {hex(memptr)}", f"Mode: {['Text Editor', 'Interactive'][should_execute]}", "```"]))

    # catch-all exit, return None if nothing worked
    return None


def read_num(val): 
    # remove the $ from number input syntax and auto-convert to base 10
    return int(val.replace("$", ""), 0)

def reg(r):
    # remove the r from r# register syntax
    return int(r.replace("r", ""))

def split_instruction(instruction):
    # read the instruction into an easily-accessible dict
    pcr = {}
    for i in range(4):
        pcr[["insOpCode", "insOp0", "insOp1", "insOp2"][i]] = int(hex(instruction[i//2])[2:].zfill(2)[i % 2], base=16)
    if len(instruction) != 2:
        pcr["insOpExt"] = int(hex(instruction[4])[2:].zfill(2) + hex(instruction[5])[2:].zfill(2), 16)
        pcpush = 6
    else:
        pcr["insOpExt"] = 0
        pcpush = 2
    return pcr, pcpush

def write_to_mem(instruction, memory, memptr):
    # write the instruction to a certain address in memory

    # length of the instruction
    length = len(instruction)

    # write instruction to memory
    memory[memptr : memptr + length] = instruction

    return memory, memptr + length

def read_from_mem(memory, memptr):
    # read the instruction at a certain address in memory

    # length of the instruction at the address
    if hex(memory[memptr])[2:].zfill(2)[0] in "0b": length = 6
    else: length = 2

    # get instruction from memory
    instruction = memory[memptr : memptr + length]

    return instruction

def make_byte(instruction):
    bytecode = ""
    for entry in instruction:
        bytecode += hex(entry)[2:].zfill(2)

    return bytecode

async def step(ctx, instruction, pc, memptr, memory, registers, should_execute, debug):
    """
    step through and/or execute instruction
    """

    try:
        pcr, pcpush = split_instruction(instruction)
        # automatic execution mode
        # if the instruction fails, simply nothing happens
        opcode = pcr["insOpCode"]
        if opcode == 0:
            # load immediate
            registers[pcr["insOp0"]] = pcr["insOpExt"]
        elif opcode == 1:
            # load base + distance
            offset = pcr["insOp0"] * 4
            pos = registers[pcr["insOp1"]]
            registers[pcr["insOp2"]] = int.from_bytes(memory[pos + offset : pos + offset + 4], "big")
        elif opcode == 2:
            # load indexed
            base = registers[pcr["insOp0"]]
            offset = registers[pcr["insOp1"]]
            multiplier = 4
            pcr["insOpImm"] = 1 # i don't really know why and this may be wrong
            registers[pcr["insOp2"]] = int.from_bytes(memory[base + offset * multiplier : base + offset * multiplier + 4], "big")
        elif opcode == 3:
            # store base + distance
            offset = pcr["insOp1"] * 4
            pos = registers[pcr["insOp2"]]
            memory[pos + offset : pos + offset + 4] = list(int(registers[pcr["insOp0"]]).to_bytes(4, "big"))
        elif opcode == 4:
            # store indexed
            base = registers[pcr["insOp1"]]
            offset = registers[pcr["insOp2"]]
            multiplier = 4
            pcr["insOpImm"] = 1 # i'm assuming store is the same as load but didn't check
            memory[base + offset * multiplier : base + offset * multiplier + 4] = list(int(registers[pcr["insOp0"]]).to_bytes(4, "big"))
        elif opcode == 6:
            # register-register interactions
            function = pcr["insOp0"]
            if function == 0: # mov
                registers[pcr["insOp2"]] = registers[pcr["insOp1"]]
            elif function == 1: # add
                registers[pcr["insOp2"]] += registers[pcr["insOp1"]]
            elif function == 2: # and
                registers[pcr["insOp2"]] &= registers[pcr["insOp1"]]
            elif function == 3: # inc
                registers[pcr["insOp2"]] += 1
            elif function == 4: # inca
                registers[pcr["insOp2"]] += 4
            elif function == 5: # dec
                registers[pcr["insOp2"]] -= 1
            elif function == 6: # deca
                registers[pcr["insOp2"]] -= 4
            elif function == 7: # not
                registers[pcr["insOp2"]] = ~ registers[pcr["insOp2"]]
            elif function == 15: # gpc
                registers[pcr["insOp2"]] = pc + pcr["insOp1"] * 2

        elif opcode == 7: 
            # shifts
            num = compile_byte(pcr["insOp1"], pcr["insOp2"])
            pcr["insOpImm"] = num
            if num < 128:
                # shift left
                registers[pcr["insOp0"]] <<= num
            else:
                # shift right by the negative of the signed value
                # e.g. 255 signed is -1, which becomes a right shift of 1
                num = 256 - num
                registers[pcr["insOp0"]] >>= num

        elif opcode == 8:
            # branch
            pp = to_unsigned(compile_byte(pcr["insOp1"], pcr["insOp2"]), 8)
            pc = pc + pp * 2 - pcpush

        elif opcode == 9:
            # branch equals
            pp = to_unsigned(compile_byte(pcr["insOp1"], pcr["insOp2"]), 8)
            if registers[pcr["insOp0"]] == 0:
                pc = pc + pp * 2 - pcpush

        elif opcode == 10:
            # branch greater
            pp = to_unsigned(compile_byte(pcr["insOp1"], pcr["insOp2"]), 8)
            if registers[pcr["insOp0"]] > 0:
                pc = pc + pp * 2 - pcpush

        elif opcode == 11:
            # jump immediate
            pc = pcr["insOpExt"] - pcpush

        elif opcode == 12:
            # jump base + distance
            pp = to_unsigned(compile_byte(pcr["insOp1"], pcr["insOp2"]))
            pc = registers[pcr["insOp0"]] + pp * 2 - pcpush

        elif opcode == 13:
            # jump indirect base + distance
            pp = to_unsigned(compile_byte(pcr["insOp1"], pcr["insOp2"]))
            pc = memory[registers[pcr["insOp0"]] + pp * 4] - pcpush

        elif opcode == 14:
            # jump indirect indexed
            pc = memory[registers[pcr["insOp0"]] + registers[pcr["insOp1"]] * 4] - pcpush

        elif opcode == 15 and pcr["insOp0"] == 0:
            # halt
            if should_execute:
                pc -= pcpush

        pc += pcpush

    except Exception as e:
        if debug:
            # print a nicely formatted thing
            etype = type(e)
            trace = e.__traceback__
            await ctx.send(("```python\n" + "".join(traceback.format_exception(etype, e, trace, 999)) + "```").replace("home/rq2/.local/lib/python3.9/site-packages/", "").replace("/home/rq2/cs213bot/cs213bot/", ""))
        else: 
            # basic formatting
            await ctx.send("ERROR: " + str(e))

    return pc

def to_unsigned(val, size):
    """
    converts val into a unsigned binary in decimal
    """
    mx = 2**size
    mi = (mx - 1) // 2

    if val > mx:
        raise Exception(f"to_unsigned(): value to large for size. max value for size is {mx}.")

    if val > mi:
        val = -(mx - val)

    return val

    
def to_signed(val, size):
    """
    converts val into a signed binary in decimal
    """
    mx = (2**size - 1) // 2
    mn = mx + 1
    
    if val > mx // 2:
        raise Exception(f"to_signed(): value to large for size. max value for size is {mx}.")
    elif val > mn:
        raise Exception(f"to_signed(): value to small for size. min value for size is {mn}.")

    if val < 0:
        val += 2**size

    return val

def get_bytes_from_ins(command, memptr):
    """
    given an sm213 instruction, returns the bytecode as a list of bytes
    """

    # read the instruction string and split the name from the operands
    instruction = command[0]
    data = "".join(command[1:])
    operands = data.split(",")

    # read the instruction name
    if instruction == "ld": 
        # load
        if len(operands) == 2 and "(" not in operands[0]:
            # load immediate: 0d--vvvvvvvv 
            # e.g. ld $0x100, r0
            return compress_bytes(0, reg(operands[1]), 0, 0, read_num(operands[0]))
            
        elif len(operands) == 2 and "(" in operands[0] and operands[0][-1] == ")":
            # load base + distance: 1psd
            # e.g. ld 4(r0), r1
            sourceregister, offset = get_offset_reg(operands[0])
            return compress_bytes(1, offset//4, sourceregister, reg(operands[1]))

        elif len(operands) == 4 and operands[0][0] == "(" and operands[2][-1] == ")":
            # load indexed: 2sid
            # e.g. ld (r0, r1, 4), r2
            # we assume the brackets are in the right place for now
            return compress_bytes(2, reg(operands[0][1:]), reg(operands[1]), reg(operands[3]))

        else: return [] # if the instruction is invalid we just return an empty list
    
    elif instruction == "st":
        # store
        if len(operands) == 2 and "(" in operands[1] and operands[1][-1] == ")":
            # store base + distance: 3spd
            # e.g. st r0, 8(r1)
            destregister, offset = get_offset_reg(operands[1])
            return compress_bytes(3, reg(operands[0]), offset//4, destregister)

        elif len(operands) == 4 and operands[1][0] == "(" and operands[3][-1] == ")":
            # store indexed: 4sdi
            # e.g. st r0, (r1, r2, 4)
            return compress_bytes(4, reg(operands[0]), reg(operands[1][1:]), reg(operands[2]))

        else: return []

    elif instruction == "halt":
        # halt: F000
        return compress_bytes(15, 0, 0, 0)
        
    elif instruction == "nop":
        # nop: FF00
        return compress_bytes(15, 15, 0, 0)

    elif instruction == "mov" and len(operands) == 2:
        # mov: 60sd
        # e.g. mov r0, r1
        return compress_bytes(6, 0, reg(operands[0]), reg(operands[1]))

    elif instruction == "add" and len(operands) == 2:
        # add: 61sd
        # e.g. add r0, r1
        return compress_bytes(6, 1, reg(operands[0]), reg(operands[1]))

    elif instruction == "and" and len(operands) == 2:
        # and: 62sd
        # e.g. and r0, r1
        return compress_bytes(6, 2, reg(operands[0]), reg(operands[1]))

    elif instruction == "inc" and len(operands) == 1:
        # inc: 63-d
        # e.g. inc r0
        return compress_bytes(6, 3, 0, reg(operands[0]))

    elif instruction == "inca" and len(operands) == 1:
        # inca: 64-d
        # e.g. inca r0
        return compress_bytes(6, 4, 0, reg(operands[0]))

    elif instruction == "dec" and len(operands) == 1:
        # dec: 65-d
        # e.g. dec r0
        return compress_bytes(6, 5, 0, reg(operands[0]))

    elif instruction == "deca" and len(operands) == 1:
        # deca: 66-d
        # e.g. deca r0
        return compress_bytes(6, 6, 0, reg(operands[0]))

    elif instruction == "not" and len(operands) == 1:
        # not: 67-d
        # e.g. not r0
        return compress_bytes(6, 7, 0, reg(operands[0]))

    elif instruction == "shl" and len(operands) == 2:
        # shl: 7dvv
        # e.g. shl $2, r0
        op1, op2 = get_hexits(read_num(operands[0]))
        return compress_bytes(7, reg(operands[1]), op1, op2)

    elif instruction == "shr" and len(operands) == 2:
        # shr: 7dvv
        # e.g. shr $2, r0
        complement = (~read_num(operands[0]) + 1) & 0xff # the number is stored as 2s complement shl
        op1, op2 = get_hexits(complement)
        return compress_bytes(7, reg(operands[1]), op1, op2)

    elif instruction == "br" and len(operands) == 1:
        # branch: 8-pp
        # e.g. br 0x1000
        pp = to_signed((read_num(operands[0]) - memptr)//2, 8)
        op1, op2 = get_hexits(pp)
        return compress_bytes(8, 0, op1, op2)

    elif instruction == "beq" and len(operands) == 2:
        # branch if equal: 9spp
        # e.g. beq r0, 0x1000
        pp = to_signed((read_num(operands[1]) - memptr)//2, 8)
        op1, op2 = get_hexits(pp)
        return compress_bytes(9, reg(operands[0]), op1, op2)

    elif instruction == "bgt" and len(operands) == 2:
        # branch if greater: Aspp
        # e.g. bgt r0, 0x1000
        pp = to_signed((read_num(operands[1]) - memptr)//2, 8)
        return compress_bytes(10, reg(operands[0]), op1, op2)

    elif instruction == "gpc" and len(operands) == 2:
        # get pc: 6Fpd
        # e.g. gpc $6, r6
        return compress_bytes(6, 15, read_num(operands[0])//2, reg(operands[1]))
    
    elif instruction == "j":
        # jump
        if len(operands) == 1:
            if "(" not in operands[0]:
                # jump immediate: B--- aaaaaaaa
                # e.g. j 0x1000
                num = read_num(operands[0])
                return compress_bytes(11, 0, 0, 0, num)

            elif "*" not in operands[0] and "(" in operands[0]:
                # jump base + distance: Cspp
                # e.g. j 4(r0)
                sourceregister, offset = get_offset_reg(operands[0])
                pp = offset//2
                op1, op2 = get_hexits(pp)
                return compress_bytes(12, sourceregister, op1, op2)

            elif operands[0][0] == "*" and "(" in operands[0]:
                # jump indirect base + distance: Dspp
                # e.g. j *4(r0)
                sourceregister, offset = get_offset_reg(operands[0][1:])
                pp = offset//4
                op1, op2 = get_hexits(pp)
                return compress_bytes(13, sourceregister, op1, op2)

            else: return []
            
        elif len(operands) == 3 and operands[0][:2] == "*(":
            # jump indirect indexed: Esi-
            # e.g. j *(r0, r1, 4)
            return compress_bytes(14, reg(operands[0][2:]), reg(operands[1]), 0)

        else: return []

    return []


def get_hexits(val):
    """
    converts a byte into a pair of hexits
    """

    # convert to hex, buffer to 2 digits, remove the 0x
    hexit_pair = hex(val)[2:].zfill(2) 
    # get integers back
    return int(hexit_pair[0], 16), int(hexit_pair[1], 16)


def compile_byte(val1, val2):
    """
    converts a pair of hexits into a byte
    """

    # convert hexits to hex and remove the 0x
    merged_hexits = hex(val1)[2:] + hex(val2)[2:]

    # get integer back
    return int(merged_hexits, 16)


def get_offset_reg(operand):
    """
    extract the register number and offset from a bracketed operand
    format is #(r#) where # is a number
    """

    basedata = operand.split("(") # find first bracket
    if basedata[0] == "": 
        # we support a blank instead of a zero for no-offset storage
        offset = 0
    else:
        offset = read_num(basedata[0])

    # the second bracket should be at the end of the other half of the split
    register = int(basedata[1][:-1]) 
    return register, offset


def compress_bytes(opcode, op0, op1, op2, value = None):
    """
    take a bytecode instruction and compress it into a list of bytes
    """

    # convert integer values to compressed hex
    # this takes the hex values (guaranteed to be single character as each input is a single hexit), without the 0x, 
    # and puts them side by side
    hex1 = hex(opcode)[2:] + hex(op0)[2:]
    hex2 = hex(op1)[2:] + hex(op2)[2:]

    # start array
    myslice = [int(hex1, 16), int(hex2, 16)]
    if value:
        # add bytecode extension if large immediate value present
        myslice += list(int(value).to_bytes(4, "big"))
    
    return myslice


def bytes_to_assembly(strn, pc):
    """
    given a string of hex bytes, return the sm213 instruction string
    """

    # find the opcode hexit
    opcode = strn[0]
    if opcode == "0" and len(strn) >= 12:
        # load immediate
        cont = strn[4:12].lstrip('0')
        if not cont: cont = 0 # lstrip would wipe the string if it were only zeroes so we account for this
        return f"ld $0x{cont}, r{strn[1]}"

    elif opcode == "1":
        # load base + distance
        return f"ld {int(strn[1], 16) * 4}(r{strn[2]}), r{strn[3]}"

    elif opcode == "2":
        # load indexed
        return f"ld (r{strn[1]}, r{strn[2]}, 4), r{strn[3]}"

    elif opcode == "3":
        # store base + distance
        return f"st r{strn[1]}, {int(strn[2], 16) * 4}(r{strn[3]})"

    elif opcode == "4":
        # store indexed
        return f"ld r{strn[1]}, (r{strn[2]}, r{strn[3]}, 4)" 

    elif opcode == "f":
        if strn[1] == "0":
            return "halt"
        elif strn[1] == "f":
            return "nop"

    elif opcode == "6":
        # register-register operations, see instruction name for purpose
        op0 = strn[1]
        if op0 == "0":
            return f"mov r{strn[2]}, r{strn[3]}"
        elif op0 == "1":
            return f"add r{strn[2]}, r{strn[3]}"
        elif op0 == "2":
            return f"and r{strn[2]}, r{strn[3]}"
        elif op0 == "3":
            return f"inc r{strn[3]}"
        elif op0 == "4":
            return f"inca r{strn[3]}"
        elif op0 == "5":
            return f"dec r{strn[3]}" 
        elif op0 == "6":
            return f"deca r{strn[3]}"
        elif op0 == "7":
            return f"not r{strn[3]}"
        elif op0 == "f":
            return f"gpc ${2*int(strn[2], 16)}, r{strn[3]}"

    elif opcode == "7":
        # shl, shr
        number = strn[2:4]
        if int(number, base = 16) > 127:
            # shr: get negative of the number
            number = 256 - int(number, base = 16)
            cont = hex(number)[2:].zfill(2).lstrip('0')
            if not cont: cont = 0
            return f"shr ${cont}, r{strn[1]}"
        else:
            # shl: just read the number
            cont = number.lstrip('0')
            if not cont: cont = 0 # account for lstrip overshoot
            return f"shl ${cont}, r{strn[1]}"

    elif opcode == "8":
        # branch
        number = strn[2:4].lstrip('0')
        if not number: number = 0
        return f"br 0x{number}"

    elif opcode == "9":
        # branch if equal
        number = strn[2:4].lstrip('0')
        if not number: number = 0
        return f"beq r{strn[1]}, 0x{number}"

    elif opcode == "a":
        # branch if greater
        number = strn[2:4].lstrip('0')
        if not number: number = 0
        return f"bgt r{strn[1]}, 0x{number}"

    elif opcode == "b" and len(strn) >= 12:
        # jump immediate
        cont = strn[4:12].lstrip('0')
        if not cont: cont = 0
        return f"j 0x{cont}"

    elif opcode == "c":
        # jump base + distance
        return f"j {int(strn[2:4], 16) * 2}(r{strn[1]})"

    elif opcode == "d":
        # jump indirect base + distance
        return f"j *{int(strn[2:4], 16) * 4}(r{strn[1]})"

    elif opcode == "e":
        # jump indirect indexed
        return f"j *(r{strn[1]}, r{strn[2]}, 4)"

    return "# invalid instruction"


def bytes_to_assembly_and_bytecode(strn, pc):
    """
    given a string of bytes from memory, reads off the bytes into a list of sm213 instructions and bytecodes
    """

    counter = 0
    instructions = []
    bytecode = []
    # iterate over memory
    while counter < len(strn):
        # determine the size of the instruction by reading the opcode
        length = [4, 12][strn[counter] in "0b"]
        instruction = strn[counter:counter+length]
        # find the instruction
        instructions.append(bytes_to_assembly(instruction, pc))
        bytecode.append(instruction)
        # go to the next instruction
        counter += length

    return instructions, bytecode


async def get(bot, ctx, exitkey):
    """
    custom utility for message-getting
    """

    try:
        message = await bot.wait_for("message", timeout = 600, check = lambda m: m.channel == ctx.channel and m.author.id == ctx.author.id)
    except:
        # after 10 minutes of inactivity, exit
        await ctx.send("Timed out waiting for you. Exiting simulator.")
        return None

    if message.content == exitkey:
        # if the exit key was sent, exit
        await ctx.send("Exiting simulator.")
        return None

    return message


async def mbed(ctx, upper, lower, fields = [], thumbnail = None, footer = None):
    """
    custom utility for embed-making
    """

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


def setup(bot):
    # module loader
    bot.add_cog(SM213(bot))
