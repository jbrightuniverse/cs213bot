# TODO List/Roadmap for cs213bot

## sm213: Discord Simple Machine

**Short/Medium-Term:**
- [ ] separate `view` using command flags to separately view memory and registers in smaller messages; make one of these smaller results the default
- [ ] fix the index out of range error when stepping too far
- [ ] every instruction accepting an immediate must be able to accept hex or decimal, and optionally allow a $ at the front or not
- [ ] values display as unsigned; they should be displaying as signed 4 byte integers instead
- [ ] abstract common functions (hex to decimal converter, for example) away from being duplicated
- [ ] branching
     * - [ ] in interactive `auto on` mode, branching should result in the simulator automatically executing any instructions it finds, up until it finds a halt or it reaches an address greater or equal to the address it branched from
     * - [ ] in text editor `auto off` mode, branching should already work; fix if it does not
- [ ] stepping: `step` function needs a parameter
     * - [x] no parameter: step once
     * - [ ] int parameter: step that many times
     * - [ ] `cont`: step infinitely until halt is found
     * - [ ] optional speed parameter for controlling whether each step is displayed explicitly; `1` would edit the message every second, `2` would skip every second instruction, still editing every second, no parameter would not display anything but the last instruction
- [ ] plaintext current instruction in `view`
- [ ] interactive and continuous step mode: treat the existence of a double `000000000000` instruction (two `ld $0, r0` instructions in a row) as a breakpoint when stepping or running indefinitely; set the PC and memory pointer to that of the first `ld`
     * - [ ] use this mechanism to not print exess instructions in `ins`
- [ ] better way of explaining the two different modes

**Long-Term:**
- [ ] abstract the functionality for converting sm213 syntax to bytecode from the actual code execution
     * - [ ] isolated sm213 to bytecode converter
     * - [ ] switch instruction executor (step function) to rely on bytecode inputs
     * - [ ] reduce the number of variables in the signature of the step function
- [ ] better feedback for running commands
     * - [ ] figure out whether it would be useful to display memory or registers when a command executes

## sm213: other

**Long-Term:**
- [ ] integrated reference for the sm213 language
     * - [ ] command for accessing docs for an instruction
     * - [ ] sample programs?

## tools

**Short-Term:**
- [ ] greater variation of questions in `!quiz`

**Long-Term:**
- [ ] further support for C syntax in `!pyth`
    *  - [ ] lists
    *  - [ ] functions
    *  - [ ] structs
- [ ] `!ld` and `!st` commands for visualizing, in GIF form, the movement of data from memory to registers and back
    *  - [ ] ld
    *  - [ ] st
