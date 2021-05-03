import asyncio
import numpy as np
import os
import random
import traceback
import time
import binascii

import discord
from discord.ext import commands

class SM213(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.queue = []

    @commands.command()
    @commands.is_owner()
    async def test(self, ctx):
        await ctx.send(self.queue)

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
        FILENAME = "/dev/zero"
        MEMORY_SIZE = 2**24
        NUM_REGISTERS = 8

        """
        for future expansion:
            if adding more syscalls, store the result of the syscall in r0
        """


        # initialize main memory and primary registers
        memory = np.memmap(FILENAME, dtype=np.uint8, mode="c", shape=(MEMORY_SIZE,))
        registers = np.zeros((NUM_REGISTERS,), dtype = np.uint32)
        
        # special registers for instruction feedback
        splreg = {
            "PC": 0,
            "LASTPC": 0,
            "insOpCode": 0,
            "insOp0": 0,
            "insOp1": 0,
            "insOp2": 0,
            "insOpImm": 0,
            "insOpExt": 0
        }

        # labels dictionary
        labels = {}
        undefined_labels = {}

        # some pointers
        memptr = 0
        should_execute = True
        should_tick = False
        instruction = []
        icache = {}

        # time check variables
        start_time = 0
        current_time = 0
        should_ping_time = False
        sent_ping = False

        await mbed(ctx, "Discord Simple Machine 213", "***READ ME FIRST:***\n**Type `help` for a commands list.**\nYou are currently in `automatic execution mode`.\nTo switch modes, type `help` for details.")

        ticker = 0
        num_steps = 1
        showmode = False
        showmessage = None
        while True:
            if ticker % 256 == 0:
                await asyncio.sleep(0)
            ticker += 1
            if ((not should_execute or memptr == splreg["PC"]) and not should_tick and num_steps == 1) or undefined_labels:
                icache = {}

                # check if last execution has finished and a ping was sent
                if sent_ping:
                    await ctx.send("```Execution finished```")
                    await special_commands(ctx, ["view"], memory, registers, should_execute, memptr, splreg)
                    showmode = False
                    showmessage = None
                    sent_ping = False

                # wait for a message
                message = await get(self.bot, ctx, "exit")
                if not message or message.content == "!sim": return # exit on return condition from get function
                if message.content == "": continue # skip if blank

                commands = message.content.lower().split("\n")
                bytecodes = []
                working_commands = []
                ins_found = False

                check_for_undefined_labels = False

                for originalcommand in commands:
                    # extract the command, delete any comments or leading whitespace
                    command = originalcommand.lstrip().split("#")[0].split()
                    bytecode = ""

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

                    elif command[0] == "show":
                        showmessage = await special_commands(ctx, ["view", "all"], memory, registers, should_execute, memptr, splreg)
                        showmode = True
                        continue
                    
                    elif command[0] == "step":
                        should_tick = True
                        sent_ping = True
                        if elements_equal(instruction, get_bytes_from_ins(["halt"], memptr, labels, undefined_labels, MEMORY_SIZE)):
                            memptr += 2

                        num_steps = 1
                        if len(command) >= 2:
                            # take a num_steps argument
                            num_steps = command[1]
                            if num_steps == "cont":
                                num_steps = len(memory)
                            elif not num_steps.isdigit() or int(num_steps) < 1:
                                num_steps = 1
                            else:
                                num_steps = int(num_steps) + 1

                            if command[-1] == "show":
                                showmessage = await special_commands(ctx, ["view", "all"], memory, registers, should_execute, memptr, splreg)
                                showmode = True

                    else:
                        # instruction found
                        instruction = get_bytes_from_ins(command, memptr, labels, undefined_labels, MEMORY_SIZE)
                        check_for_undefined_labels = True
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

                if check_for_undefined_labels:
                    recompile_undefined_labels(memory, labels, undefined_labels)

                if ins_found: 
                    instructions = ["```avrasm"] # discord code block formatting
                    for i in range(len(working_commands)):
                        if i >= len(commands): break
                        # add some formatted spacing
                        instructions.append(working_commands[i].ljust(20) + " | " + bytecodes[i])

                    msg = "\n".join(instructions + ["```"])
                    if len(msg) < 2000:
                        await ctx.send(msg)
                    else:
                        await ctx.send("Message too long.")
            elif (should_execute or should_tick or num_steps > 1) and not undefined_labels:
                # ping if the execution is taking awhile
                if should_ping_time and current_time > start_time + 1:
                    await ctx.send("```Execution still in progress, please wait...type CANCEL to exit...```")
                    should_ping_time = False
                    sent_ping = True

                # store previous instruction (empty if first instruction)
                old_instruction = instruction

                # get instruction from memory
                instruction = read_from_mem(memory, splreg["PC"])

                # check if the next two instructions are load zeros
                if not any(memory[splreg["PC"]:splreg["PC"] + 12]):
                    instruction = [0xF0, 0] # halt
                    memptr = splreg["PC"] + 2

                if num_steps > 1:
                    num_steps -= 1

                if ctx.author.id in [a[0] for a in self.queue] or 375445489627299851 in [a[0] for a in self.queue]:
                    self.queue = list(filter(lambda x: x[0] not in [ctx.author.id, 375445489627299851], self.queue))
                    return await ctx.send("**EXECUTION STOPPED. To prevent system corruption, your session has been terminated.\nPlease type `!sim` to reopen the simulator. You will need to re-type your code.**")
                
                # convert ints to a bytecode string
                #strn = make_byte(instruction)

                # retrieve the instruction from the bytecode
                #instructions, _ = bytes_to_assembly_and_bytecode(strn, splreg["PC"])
                #originalcommand = instructions[0]

                try:
                    await step(ctx, self.bot, instruction, icache, splreg, memptr, memory, registers, labels, should_execute, debug)
                    if showmode:
                        await special_commands(ctx, ["view", "all"], memory, registers, should_execute, memptr, splreg, showmsg = showmessage)
                        await asyncio.sleep(1.001)
                except Exception as e:
                    if debug:
                        # print a nicely formatted thing
                        etype = type(e)
                        trace = e.__traceback__
                        await ctx.send(("```python\n" + "".join(traceback.format_exception(etype, e, trace, 999)) + "```").replace("home/rq2/.local/lib/python3.9/site-packages/", "").replace("/home/rq2/cs213bot/cs213bot/", ""))
                    else: 
                        # basic formatting
                        await ctx.send("ERROR: " + str(e))

                should_tick = False
                current_time = time.time()
            else:
                icache = {}

def recompile_undefined_labels(memory, labels, undefined_labels):
    new_labels = {}
    for pc in undefined_labels.keys():
        if undefined_labels[pc] in labels:
            instruction = read_from_mem(memory, pc)
            opcode = int(hex(instruction[0])[2:].zfill(4)[0], 16)
            reg = int(hex(instruction[0])[2:].zfill(4)[1], 16)

            if opcode in [8, 9, 10]:
                op1, op2 = get_hexits(to_signed((labels[undefined_labels[pc]] - pc)//2, 8))
                if opcode == 8:
                    reg = 0
                write_to_mem(compress_bytes(opcode, reg, op1, op2), memory, pc)
            elif opcode == 11:
                write_to_mem(compress_bytes(opcode, 0, 0, 0, labels[undefined_labels[pc]]), memory, pc)
            elif opcode == 0:
                write_to_mem(compress_bytes(opcode, reg, 0, 0, labels[undefined_labels[pc]]), memory, pc)
        else:
            new_labels[pc] = undefined_labels[pc]
        
    undefined_labels.clear()
    undefined_labels.update(new_labels)

def elements_equal(list1, list2):
    return all(list(map(lambda x, y: x == y, list1, list2)))

async def special_commands(ctx, command, memory, registers, should_execute, memptr, splreg, showmsg = None):
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
            ins, bytecode = bytes_to_assembly_and_bytecode(strn, splreg["PC"], splreg["LASTPC"])
            instructions += ins

            # add bytecode
            for i in range(2, len(instructions)):
                if bytecode[i - 2] == "0000" or bytecode[i-2] == "00000000": 
                    del instructions[i]
                    break
                instructions[i] = instructions[i].ljust(20) + " | " + bytecode[i - 2]

            while (instructions[-1] == "ld $0x0, r0          | 000000000000") and len(instructions) > 3:
                del instructions[-1]

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
        fields.append([":sparkles: Special Commands\n_ _", specialx])
        specialx = "`step`\nManually executes the instruction at the current location of the Program Counter (PC). Increments PC accordingly.\n\n`step 2`\nSteps twice. Replace 2 with how many steps you want to take.\n\n`step cont`\nSteps forever until a halt is found.\n\n`step cont show`\nStep with realtime status feedback.\n\n"
        specialx += "`show`\nAdd this to the end of your instructions to dynamically display PC operations.\n\n"
        specialx += "`help`\nViews this message."
        fields.append(['\u200b', specialx])
        return await mbed(ctx, "Discord Simple Machine Docs", "This assumes you have at least some knowledge of the sm213 language. If you don't, please review the language first before continuing.", fields = fields, footer = "Credits:\n\nThe sm213 language was created by Dr. Mike Feeley of the CPSC department at UBCV.\nUsed with permission.\n\nDiscord Simple Machine created by James Yu with feedback from users and friends.\nLoosely inspired by the functionality of the Java Simple Machine 213\nand the web 213/313 simulator.\nSignificant upgrades by https://github.com/ethanthoma\nSpeed optimizations by https://github.com/Kieran-Weaver")

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
                    mapping = dict(zip("0123456789abcdef", "⁰¹²³⁴⁵⁶⁷⁸⁹ᵃᵇᶜᵈᵉᶠ"))

                    thebytes = ""
                    for j in range(4):
                        a = hex(myslice[i * 4 + j])[2:].zfill(2)
                        exact_position = pos + i * 4 + j
                        if exact_position in range(splreg["LASTPC"], splreg["LASTPC"] + [2, 6][splreg["insOpCode"] in [0, 11]]):
                            for char in mapping:
                                a = a.replace(char, mapping[char])
                        thebytes += " " + a

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
                    lines.append(f"{num}:{thebytes} |{res}|  {val}")
            
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
                regcontent = [f"r{i}: {hex(registers[i])}" for i in range(len(registers))]
                registerx.append(" | ".join(regcontent))
                registerx.append("")
                regcontent = [f"{key}: {hex(splreg[key])}" for key in splreg]
                registerx.append("\n".join(regcontent))

                # determine what the instruction actually was
                content = get_ins_back(splreg)
                registerx.append(f"instruction: {content}")
                if content:
                    last = bytes_to_assembly(content, splreg['PC'], splreg['LASTPC'])
                    registerx.append(f"plaintext: {last}")

            text = "\n".join(lines + registerx + [f"\nEdit Pointer: {hex(memptr)}", f"Mode: {['Text Editor', 'Interactive'][should_execute]}", "```"])
            if showmsg:
                await showmsg.edit(content = text)
                return
            return await ctx.send(text)

    # catch-all exit, return None if nothing worked
    return None

def get_ins_back(splreg):
    """
    get instruction from an instance of specialregisters
    """

    first = hex(splreg["insOpCode"])[2:] + hex(splreg["insOp0"])[2:] + hex(splreg["insOp1"])[2:] + hex(splreg["insOp2"])[2:]
    if splreg["insOpCode"] in [0, 11]:
        first += hex(splreg["insOpExt"])[2:].zfill(8)

    return first

def reg(r):
    # remove the r from r# register syntax
    return int(r.replace("r", ""))

def split_instruction(instruction):
    # read the instruction into an easily-accessible dict
    pcr = {}
    for i in range(4):
        pcr[["insOpCode", "insOp0", "insOp1", "insOp2"][i]] = int(hex(instruction[i//2])[2:].zfill(2)[i % 2], base=16)
    if len(instruction) != 2:
        pcr["insOpExt"] = sum([instruction[5-k]*(256**k) for k in range(4)])
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
    length = 2
    if (memory[memptr] & 0xF0) in [0, 0xB0]: length = 6

    # get instruction from memory
    instruction = memory[memptr : memptr + length]

    return instruction

def make_byte(instruction):
    return binascii.hexlify(bytes(instruction)).decode("utf-8")

async def step(ctx, bot, instruction, icache, splreg, memptr, memory, registers, labels, should_execute, debug):
    """
    step through and/or execute instruction
    """

    pc = splreg["PC"]
    pcr = {}
    pcpush = 0
    if pc not in icache:
        pcr, pcpush = split_instruction(instruction) 
        icache[pc] = (pcr, pcpush)
    else:
        pcr, pcpush = icache[pc]

    for key in pcr:
        splreg[key] = pcr[key]
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
        pp = to_unsigned(compile_byte(pcr["insOp1"], pcr["insOp2"]), 8)
        pc = registers[pcr["insOp0"]] + pp * 2 - pcpush

    elif opcode == 13:
        # jump indirect base + distance
        pp = to_unsigned(compile_byte(pcr["insOp1"], pcr["insOp2"]), 8)
        pc = memory[registers[pcr["insOp0"]] + pp * 4] - pcpush

    elif opcode == 14:
        # jump indirect indexed
        pc = memory[registers[pcr["insOp0"]] + registers[pcr["insOp1"]] * 4] - pcpush

    elif opcode == 15:
        if pcr["insOp0"] == 0:
            # halt
            pass
            #if should_execute:
            #    pc -= pcpush

        elif pcr["insOp0"] == 1:
            # syscalls
            # normally r0 is used as the filedescriptor but since we only write to stdin/stdout, we don't care
            if pcr["insOp2"] == 0:
                # read from input
                bufsize = registers[2]
                await ctx.send("Enter input to save:")
                message = await get(bot, ctx, "exit")
                if message.content:
                    # dump it into memory
                    myslice = [ord(c) for c in message.content][:bufsize]
                    memory[registers[1] : registers[1] + bufsize] = myslice
                    await ctx.send("Input saved.")
            elif pcr["insOp2"] == 1:
                # write to output
                bufsize = registers[2]
                if bufsize > 1980:
                    await ctx.send("ERROR: Buffer cannot be bigger than 1980 chars.")
                else:
                    myslice = memory[registers[1] : registers[1] + bufsize]
                    await ctx.send("".join([chr(c) for c in myslice]))
            elif pcr["insOp2"] == 2:
                bufsize = registers[2]
                if bufsize > 1980:
                    await ctx.send("ERROR: Buffer cannot be bigger than 1980 chars.")
                else:
                    myslice = memory[registers[1] : registers[1] + bufsize]
                    await ctx.send("<<<WOULD EXECUTE " + "".join([chr(c) for c in myslice]) + ">>>")

    pc += pcpush
    splreg["LASTPC"] = splreg["PC"]
    splreg["PC"] = pc

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

def get_bytes_from_ins(command, memptr, labels, undefined_labels, MEMORY_SIZE):
    """
    given an sm213 instruction, returns the bytecode as a list of bytes
    """

    # read the instruction string and split the name from the operands
    instruction = command[0]
    data = "".join(command[1:])
    operands = [x.replace("$", "") for x in data.split(",")] # Remove leading $

    # read the instruction name
    if instruction == "ld": 
        # load
        if len(operands) == 2 and "(" not in operands[0]:
            # load immediate: 0d--vvvvvvvv 
            num = 0
            try:
                # load immediate, e.g. ld $0x100, r0
                num = int(operands[0], 0)
            except:
                # load label, e.g. ld a, r0
                if operands[0] in labels:
                    # label is defined
                    num = labels[operands[0]]
                else:
                    # label is defined later
                    undefined_labels[memptr] = operands[0]
            return compress_bytes(0, reg(operands[1]), 0, 0, num)
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
        op1, op2 = get_hexits(int(operands[0], 0))
        return compress_bytes(7, reg(operands[1]), op1, op2)

    elif instruction == "shr" and len(operands) == 2:
        # shr: 7dvv
        # e.g. shr $2, r0
        complement = (~read_num(operands[0]) + 1) & 0xff # the number is stored as 2s complement shl
        op1, op2 = get_hexits(complement)
        return compress_bytes(7, reg(operands[1]), op1, op2)

    elif instruction == "br" and len(operands) == 1:
        # branch: 8-pp
        if "0x" in operands[0]:
            # e.g. br 0x1000
            pp = to_signed((int(operands[0], 0) - memptr)//2, 8)
        elif operands[0] in labels.keys():
            # e.g. br func
            # label is already defined
            pp = to_signed((labels[operands[0]] - memptr)//2, 8)
        else:
            # e.g. br func
            # label is not yet defined
            pp = 0
            undefined_labels[memptr] = operands[0]
        op1, op2 = get_hexits(pp)
        return compress_bytes(8, 0, op1, op2)

    elif instruction == "beq" and len(operands) == 2:
        # branch if equal: 9spp
        if "0x" in operands[1]:
            # e.g. beq r0, 0x1000
            pp = to_signed((int(operands[1], 0) - memptr)//2, 8)
        elif operands[1] in labels:
            # e.g. beq r0, func
            # label is already defined
            pp = to_signed((labels[operands[1]] - memptr)//2, 8)
        else:
            # e.g. beq r0, func
            # label is not yet defined
            pp = 0
            undefined_labels[memptr] = operands[1]
        op1, op2 = get_hexits(pp)
        return compress_bytes(9, reg(operands[0]), op1, op2)

    elif instruction == "bgt" and len(operands) == 2:
        # branch if greater: Aspp
        if "0x" in operands[1]:
        # e.g. bgt r0, 0x1000
            pp = to_signed((int(operands[1], 0) - memptr)//2, 8)
        elif operands[1] in labels.keys():
            # e.g. bgt r0, func
            # label is already defined
            pp = to_signed((labels[operands[1]] - memptr)//2, 8)
        else:
            # e.g. bgt r0, func
            # label is not yet defined
            pp = 0
            undefined_labels[memptr] = operands[1]
        op1, op2 = get_hexits(pp)
        return compress_bytes(10, reg(operands[0]), op1, op2)

    elif instruction == "gpc" and len(operands) == 2:
        # get pc: 6Fpd
        # e.g. gpc $6, r6
        return compress_bytes(6, 15, int(operands[0], 0)//2, reg(operands[1]))

    elif instruction == "sys" and len(operands) == 1:
        # syscall: F1nn
        # e.g. sys $2
        # TEMPORARILY ONLY SUPPORTS SINGLE DIGIT SYSCALLS
        return compress_bytes(15, 1, 0, int(operands[0], 0))
    
    elif instruction == "j":
        # jump
        if len(operands) == 1:
            if "(" not in operands[0]:
                # jump immediate: B--- aaaaaaaa
                if "0x" in operands[0]:
                    # e.g. j 0x1000
                    num = int(operands[0], 0)
                elif operands[0] in labels.keys():
                    # e.g. j func
                    # label is already defined
                    num = labels[operands[0]]
                else:
                    # e.g. j func
                    # label is not yet defined
                    num = MEMORY_SIZE
                    undefined_labels[memptr] = operands[0]
                    
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
    elif instruction[len(instruction) - 1] == ":":
        # label setter
        labels[instruction[:len(instruction) - 1]] = memptr
        return []
    elif instruction == ".long":
        longs = []
        for op in operands:
            longs.extend(int(operands[0], 0).to_bytes(4, "big"))
        return longs

    return []

def get_hexits(val):
    """
    converts a byte into a pair of hexits
    """

    # For upper hexit, divide by 16
    # For lower hexit, and with the bitmask 0x0F, which is 0b00001111
    return val // 16, val & 0x0F

def compile_byte(val1, val2):
    """
    converts a pair of hexits into a byte
    """

    # Multiply by 16
    return val1 * 16 + val2

def get_offset_reg(operand):
    """
    extract the register number and offset from a bracketed operand
    format is #(r#) where # is a number
    """

    basedata = operand.split("(") # find first bracket
    if not basedata[0]: 
        # we support a blank instead of a zero for no-offset storage
        offset = 0
    else:
        offset = int(basedata[0], 0)

    # the second bracket should be at the end of the other half of the split
    register = reg(basedata[1][:-1])
    return register, offset


def compress_bytes(opcode, op0, op1, op2, value = None):
    """
    take a bytecode instruction and compress it into a list of bytes
    """

    # convert integer values to compressed hex
    # this takes the hex values (guaranteed to be single character as each input is a single hexit), without the 0x, 
    # and puts them side by side

    # start array
    myslice = [(opcode << 4) + op0, (op1 << 4) + op2]
    if value != None: # account for zero
        # add bytecode extension if large immediate value present
        if value < 0: # support signed values
            myslice.extend(int(value).to_bytes(4, "big", signed=True))
        else: # support unsigned values
            myslice.extend(int(value).to_bytes(4, "big"))

    return myslice

def bytes_to_assembly(strn, pc, lastpc):
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
        elif strn[1] == "1":
            return f"sys ${strn[3]}"
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
        if not number: number = "0"
        as_signed = int(number, 16)
        if as_signed > 127: as_signed = -1 * (256 - as_signed)
        return f"br {hex(as_signed * 2 + lastpc)}"

    elif opcode == "9":
        # branch if equal
        number = strn[2:4].lstrip('0')
        if not number: number = "0"
        as_signed = int(number, 16)
        if as_signed > 127: as_signed = -1 * (256 - as_signed)
        return f"beq r{strn[1]}, {hex(as_signed * 2 + lastpc)}"

    elif opcode == "a":
        # branch if greater
        number = strn[2:4].lstrip('0')
        if not number: number = "0"
        as_signed = int(number, 16)
        if as_signed > 127: as_signed = -1 * (256 - as_signed)
        return f"bgt r{strn[1]}, {hex(as_signed * 2 + lastpc)}"

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


def bytes_to_assembly_and_bytecode(strn, pc, lastpc):
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
        instructions.append(bytes_to_assembly(instruction, pc, lastpc))
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