#!/usr/bin/env python3

from sys import path as sys_path
from ctypes import create_string_buffer
from os import unlink
from os.path import exists
from unittest import TestCase
from io import BytesIO
from tempfile import NamedTemporaryFile

from stage0dir import get_stage0_dir, get_stage0_file
from knightvm_minimal import load_program
from knightdecode import (
    create_vm, grow_memory, read_instruction, eval_instruction,
    MIN_INSTRUCTION_LEN,
    )
from constants import (
    IP, REG, MEM, HALTED, PERF_COUNT, # vm tuple indexes
    RAW, HAL_CODE, # intruction tuple indexes
    HALT_OP, HAL_CODE_OP, HAL_CODE_FGETC, HAL_CODE_FPUTC,
    HAL_IO_DATA_REGISTER, HAL_IO_DEVICE_REGISTER, HAL_IO_DEVICE_STDIO,
    )
from hex0tobin import write_binary_filefd_from_hex0_filefd


LILITH_TAPE_NAME_01, LILITH_TAPE_NAME_02 = ("tape_01", "tape_02")
LILITH_IP_REGISTER_INDEX, LILITH_PERF_COUNT_REGISTER_INDEX = (16, 17)
LILITH_REGISTER_SIZE = 32

def get_hal_code_from_raw(py_instruction):
    hal_code = ( (py_instruction[RAW][1]<<16) |
                 (py_instruction[RAW][2]<<8) |
                 (py_instruction[RAW][3]) )
    return hal_code

def get_closed_named_temp_file():
    return_file = NamedTemporaryFile(delete=False)
    return_file.close()
    return return_file.name

class ParallelExecutionTests(TestCase):
    optimize = False
    
    def setUp(self):
        sys_path.append(get_stage0_dir())
        import User_Interface
        self.c_vm = User_Interface.vm

        self.vm_size = self.stack_start+self.stack_size
        self.c_vm.initialize_lilith(self.vm_size)
        self.output_mem_buffer = BytesIO()
        self.skipped_instructions = 0

        self.binary_rom = NamedTemporaryFile(delete=False)
        self.binary_rom_filename = self.binary_rom.name

        self.tape_01_filename = get_closed_named_temp_file()
        self.tape_02_filename = get_closed_named_temp_file()
        
    def tearDown(self):
        self.output_mem_buffer.close()
        self.binary_rom.close()
        unlink(self.binary_rom_filename)
        unlink(self.tape_01_filename)
        unlink(self.tape_02_filename)
        if exists(LILITH_TAPE_NAME_01):
            unlink(LILITH_TAPE_NAME_01)
        if exists(LILITH_TAPE_NAME_02):
            unlink(LILITH_TAPE_NAME_02)
        
        
    def check_memory_match(self, debug_tuple=None):
        py_memory = self.py_vm[MEM]
        # just check the stack
        for i in range(self.stack_start, self.vm_size):
            self.assertEqual(
                self.c_vm.get_byte(i),
                py_memory[i],
                "memory mismatch at 0x%s : %d" % (hex(i), i)
                )

    def check_register_match(self, debug_tuple=None):
        registerfile = self.py_vm[REG]
        num_registers = len(self.py_vm[REG])
        # after our regular registers (0..15) ,len()==16
        # the instruction pointer (16) should be next
        self.assertEqual(
            len(self.py_vm[REG]),
            LILITH_IP_REGISTER_INDEX )
        for i in range(num_registers): # 0...15
            self.assertEqual(
                self.c_vm.get_register(i),
                registerfile[i],
                "register %d mis-match address: 0x%.2X\n%s" % (
                    i, self.py_vm[IP], repr(debug_tuple))
                )

    def check_ip_match(self, debug_tuple=None):
        self.assertEqual(
            self.py_vm[IP],
            self.c_vm.get_register(LILITH_IP_REGISTER_INDEX), # IP
            "instruction pointers don't match %.2X\ninstruc: %s" % (
                self.c_vm.get_register(LILITH_IP_REGISTER_INDEX),
                repr(debug_tuple),
            ),
        ) # assertEqual

    def check_perf_count(self, debug_tuple=None):
        self.assertEqual(
            self.py_vm[PERF_COUNT],
            self.c_vm.get_register(LILITH_PERF_COUNT_REGISTER_INDEX) +
            self.skipped_instructions,
            "perf counters don't match %.2X\ninstruc: %s" % (
                self.c_vm.get_register(LILITH_PERF_COUNT_REGISTER_INDEX),
                repr(debug_tuple),
            ),
        ) # assertEqual        
        
    def do_state_checks(self, debug_tuple=None):
        self.check_memory_match(debug_tuple=debug_tuple)
        self.check_register_match(debug_tuple=debug_tuple)
        self.check_ip_match(debug_tuple=debug_tuple)

        # not necessary
        # self.check_perf_count(debug_tuple=debug_tuple)
        
    def halted(self):
        return self.py_vm[HALTED]

    def advance_both_vms(self):
        old_ip = self.py_vm[IP]
        
        py_instruction = read_instruction(self.py_vm)
        py_vm_new = eval_instruction(
            self.py_vm, py_instruction, optimize=self.optimize)

        self.assertTrue(
            0<= py_vm_new[IP] < self.program_size,
            "instruction at %.2X put us out of program %s" % (
                old_ip, repr(py_instruction) ) )
        
        # intercept io from stdin / to stdout and force emulation by
        # copying the result of our python interpreter doing the io
        # into the c based VM
        if (py_instruction[RAW][0] == HAL_CODE_OP and
            get_hal_code_from_raw(py_instruction) in 
            (HAL_CODE_FGETC, HAL_CODE_FPUTC) and
            self.c_vm.get_register(HAL_IO_DEVICE_REGISTER)
            ==HAL_IO_DEVICE_STDIO ):

            if get_hal_code_from_raw(py_instruction)==HAL_CODE_FGETC:
                    self.c_vm.set_register(
                        HAL_IO_DATA_REGISTER,
                        py_vm_new[REG][HAL_IO_DATA_REGISTER] )
            # no need to simulate FPUTC, just do nothing
            # else: # HAL_CODE_FPUTC
            #    self.assertEqual(py_instruction[HAL_CODE],
            #                     HAL_CODE_FPUTC)
                        
            new_c_vm_ip = py_vm_new[IP] # our python code went here
            # presumably that's 4 bytes after the c VM's current IP
            self.assertEqual(
                new_c_vm_ip,
                self.c_vm.get_register(LILITH_IP_REGISTER_INDEX) +
                MIN_INSTRUCTION_LEN
            ) # assertEqual
            # force the instruction pointer of the c implementation to go
            # where our python code went, which we know from the above
            # assert would have been where the c code would have gone
            self.c_vm.set_register(LILITH_IP_REGISTER_INDEX, new_c_vm_ip)

            self.skipped_instructions+=1
        elif py_instruction[RAW][0] == HALT_OP:
            # skip halt to avoid print output
            self.skipped_instructions+=1
        else: # read and execute all other instructions
            self.c_vm.step_lilith()

        debug_tuple = old_ip, py_instruction, self.py_vm[PERF_COUNT]
        self.py_vm = py_vm_new
        return debug_tuple

    def finish_setup(self, input_file_fd):
        self.py_vm = create_vm(
            size=0, registersize=LILITH_REGISTER_SIZE,
            tapefile1=self.tape_01_filename,
            tapefile2=self.tape_02_filename,
            stdin=input_file_fd,
            stdout=self.output_mem_buffer,
        )
        load_program(self.py_vm, self.binary_rom_filename)
        self.program_size = len(self.py_vm[MEM])
        grow_memory(self.py_vm, self.vm_size)
        
        self.rom_name_string_buffer = create_string_buffer(
            self.binary_rom_filename.encode('ascii') )
        self.c_vm.load_lilith(self.rom_name_string_buffer)

    def run_execution_test(self, romfilename_hex, stdin_filename):
        with open(romfilename_hex, 'r') as romfile_hex:
                write_binary_filefd_from_hex0_filefd(
                    romfile_hex, self.binary_rom)
        self.binary_rom.close()
        
        with open(stdin_filename, 'rb') as input_file_fd:
            self.finish_setup(input_file_fd)

            self.do_state_checks()
            while True:
                debug_tuple = self.advance_both_vms()
                if self.halted():
                    break # don't bother with state checks after HALT
                self.do_state_checks(debug_tuple)

class Stage0MonitorTests(ParallelExecutionTests):
    stack_start = 0x600
    stack_size = 8
        
    def test_stage0_monitor_encoding_self(self):
        self.run_execution_test(
            get_stage0_file("stage0/stage0_monitor.hex0"),
            get_stage0_file("stage0/stage0_monitor.hex0") )

class Stage0MonitorTestsOptimise(Stage0MonitorTests):
    optimise = True
