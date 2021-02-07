# TODO List/Roadmap for cs213bot

## sm213: Discord Simple Machine

**Short/Medium-Term:**
- [X] support the use of labels for addresses in memory; allow these labels to be used with branching
     * - [ ] allow labels to be read back in `ins`
     * - [ ] make it so labels can be placed manually
     * - [ ] prevent labels from triggering invalid instruction when written
- [ ] support assignments of static variables in memory with `.long`
- [ ] support integrated usage of `.pos`

**Long-Term:**

## sm213: other

**Long-Term:**

## tools

**Short-Term:**
- [ ] greater variation of questions in `!quiz`
    
## overall

**Long-Term:**
- [ ] use the simulator framework to implement Y86 for CPSC 313 and deploy the bot in the official 313 course Discord server

# PAST TODO LIST:

## sm213: Discord Simple Machine

- [X] separate `view` using command flags to separately view memory and registers in smaller messages; make one of these smaller results the default
- [X] fix the index out of range error when stepping too far
- [X] every instruction accepting an immediate must be able to accept hex or decimal, and optionally allow a $ at the front or not
- [X] values display as unsigned; they should be displaying as signed 4 byte integers instead
- [X] abstract hex to decimal converter away from being duplicated
- [X] abstract the functionality for converting sm213 syntax to bytecode from the actual code execution
     * - [X] isolated sm213 to bytecode converter
     * - [X] switch instruction executor (step function) to rely on bytecode inputs
     * - [X] reduce the number of variables in the signature of the step function
- [X] branching
     * - [X] in interactive `auto on` mode, branching should result in the simulator automatically executing any instructions it finds, up until it finds a halt or it reaches an address greater or equal to the address it branched from
     * - [X] in text editor `auto off` mode, branching should already work; fix if it does not
- [X] plaintext current instruction in `view`
- [X] better feedback for running commands
     * - [X] figure out whether it would be useful to display memory or registers when a command executes
- [X] stepping: `step` function needs a parameter
     * - [x] no parameter: step once
     * - [X] int parameter: step that many times
     * - [X] `cont`: step infinitely until halt is found
     * - [X] optional speed parameter for controlling whether each step is displayed explicitly; ~~`1` would edit the message every second, `2` would skip every second instruction, still editing every second, no parameter would not display anything but the last instruction~~ parameter is called `show`
- [X] fix forward jump infinity glitch: may be related to error in automatic halt
- [X] interactive and continuous step mode: treat the existence of a double `000000000000` instruction (two `ld $0, r0` instructions in a row) as a breakpoint when stepping or running indefinitely; set the PC and memory pointer to that of the first `ld`
     * - [X] use this mechanism to not print exess instructions in `ins`
     * - [X] fix invalid instruction at the end of `ins`
- [X] better way of explaining the two different modes
- [X] add infinite loop cancellation command
- [X] integrated reference for the sm213 language
- [X] syscalls