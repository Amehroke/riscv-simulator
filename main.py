# RISC-V CPU Simulator with support for specific instructions

# Global variables for the simulator
pc = 0
next_pc = 0
alu_zero = 0
branch_target = 0
rf = [0] * 32  # Register file, initialized with zeros
d_mem = [0] * 1024  # Data memory, initialized with zeros
total_clock_cycles = 0  # Clock cycles

# Control signals
RegWrite = 0
Branch = 0
MemRead = 0
MemtoReg = 0
ALUOp = 0
MemWrite = 0
ALUSrc = 0

# Initializing register file (rf) as specified
rf[1] = 0x20  # x1
rf[2] = 0x5   # x2
rf[10] = 0x70 # x10
rf[11] = 0x4  # x11

# Initializing data memory (d_mem) as specified
d_mem[0x70 // 4] = 0x5  # Address 0x70 contains value 0x5
d_mem[0x74 // 4] = 0x10 # Address 0x74 contains value 0x10

def load_program_from_file(file_path):
    with open(file_path, 'r') as file:
        program = [line.strip() for line in file.readlines()]
    return program

def Fetch(program):
    global pc, next_pc
    instruction_index = pc // 4
    if instruction_index < len(program):
        instruction = program[instruction_index]
    else:
        instruction = None
    next_pc = pc + 4
    pc = next_pc
    return instruction

def sign_extend(imm, bits=12):
    if imm & (1 << (bits - 1)):
        imm = imm | (-1 << bits)
    return imm

def Decode(instruction):
    global ALUOp, ALUSrc, MemRead, MemWrite, Branch, MemtoReg, RegWrite
    opcode = int(instruction[25:], 2)
    rd = int(instruction[20:25], 2)
    funct3 = int(instruction[17:20], 2)
    rs1 = int(instruction[12:17], 2)
    rs2 = int(instruction[7:12], 2)
    imm_i = sign_extend(int(instruction[:12], 2))
    imm_s = sign_extend(int(instruction[:7] + instruction[20:25], 2))
    imm_b = sign_extend(int(instruction[0] + instruction[24] + instruction[1:7] + instruction[20:24], 2), 13)
    ControlUnit(opcode)
    return {'opcode': opcode, 'rd': rd, 'funct3': funct3, 'rs1': rs1, 'rs2': rs2, 'imm_i': imm_i, 'imm_s': imm_s, 'imm_b': imm_b, 'rs1_value': rf[rs1], 'rs2_value': rf[rs2]}

def ControlUnit(opcode):
    global RegWrite, Branch, MemRead, MemtoReg, ALUOp, MemWrite, ALUSrc
    # Reset control signals
    RegWrite = Branch = MemRead = MemtoReg = MemWrite = ALUSrc = 0
    ALUOp = "00"
    
    # R-type
    if opcode == 0b0110011:
        RegWrite = 1
        ALUOp = "10"
    # I-type (LW)
    elif opcode == 0b0000011:
        RegWrite = MemRead = MemtoReg = ALUSrc = 1
        ALUOp = "00"
    # S-type (SW)
    elif opcode == 0b0100011:
        MemWrite = ALUSrc = 1
        ALUOp = "00"
    # B-type (BEQ)
    elif opcode == 0b1100011:
        Branch = 1
        ALUOp = "01"
    # I-type (ADDI, ANDI, ORI)
    elif opcode == 0b0010011:
        RegWrite = ALUSrc = 1
        ALUOp = "10"

def ALUControl(funct3, ALUOp):
    if ALUOp == "00":  # LW or SW
        return "add"
    elif ALUOp == "01":  # BEQ
        return "sub"
    elif ALUOp == "10":
        if funct3 == 0b000:
            return "add"  # ADD or ADDI
        elif funct3 == 0b010:  # This case wasn't originally covered but is important for SUB
            return "sub"
        elif funct3 == 0b111:
            return "and"  # AND or ANDI
        elif funct3 == 0b110:
            return "or"   # OR or ORI
    return None

def Execute(decoded_instruction):
    global alu_zero, branch_target, next_pc
    alu_op = ALUControl(decoded_instruction['funct3'], ALUOp)
    result = None
    if alu_op == "add":
        result = decoded_instruction['rs1_value'] + (decoded_instruction['rs2_value'] if ALUSrc == 0 else decoded_instruction['imm_i'])
    elif alu_op == "sub":
        result = decoded_instruction['rs1_value'] - (decoded_instruction['rs2_value'] if ALUSrc == 0 else decoded_instruction['imm_i'])
        alu_zero = int(result == 0)
    elif alu_op == "and":
        result = decoded_instruction['rs1_value'] & (decoded_instruction['rs2_value'] if ALUSrc == 0 else decoded_instruction['imm_i'])
    elif alu_op == "or":
        result = decoded_instruction['rs1_value'] | (decoded_instruction['rs2_value'] if ALUSrc == 0 else decoded_instruction['imm_i'])
    if Branch and alu_zero:
        branch_target = pc - 4 + decoded_instruction['imm_b']
    else:
        branch_target = next_pc
    return result

def Mem(address, data=None):
    global pc
    index = address // 4
    if MemRead:
        return d_mem[index]
    elif MemWrite and data is not None:
        print(f"memory {hex(address)} is modified to {hex(data)}")
        d_mem[index] = data
    pc = branch_target

def Writeback(rd, result):
    global total_clock_cycles
    if RegWrite:
        print(f"x{rd} is modified to {hex(result)}")
        rf[rd] = result
    total_clock_cycles += 1

def run_program(file_path):
    global pc, next_pc, total_clock_cycles
    program = load_program_from_file(file_path)
    pc = 0
    while True:
        instruction = Fetch(program)
        if instruction is None:  # End of program
            break
        print(f"total_clock_cycles: {total_clock_cycles + 1}")
        decoded_instruction = Decode(instruction)
        result = Execute(decoded_instruction)
        if MemRead or MemWrite:
            mem_result = Mem(result) if MemRead else Mem(result, decoded_instruction['rs2_value'])
            if MemtoReg:
                result = mem_result

        Writeback(decoded_instruction['rd'], result)
        # Display changes after each instruction
        print(f"pc is modified to {hex(pc)}\n")
        pc = next_pc  # Update PC for the next instruction
    
    print(f"program terminated:\ntotal execution time is {total_clock_cycles} cycles")

# Main Program Execution
file_name = input("Enter the program file name to run:\n\n")
run_program(file_name)
