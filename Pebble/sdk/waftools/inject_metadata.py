#!/usr/bin/env python

from __future__ import with_statement

import os
import os.path
import sys
from subprocess import Popen, PIPE
from pprint import pformat, pprint
from shutil import copy2
from binascii import crc32
from struct import pack

import stm32_crc

# Pebble App Metadata Struct
HEADER_ADDR = 0x0 		 # 8 bytes
STRUCT_VERSION_ADDR = 0x8        # 2 bytes
SDK_VERSION_ADDR = 0xa           # 2 bytes
APP_VERSION_ADDR = 0xc           # 2 bytes
SIZE_ADDR = 0xe                  # 2 bytes
OFFSET_ADDR = 0x10               # 4 bytes
CRC_ADDR = 0x14                  # 4 bytes
NAME_ADDR = 0x18                 # 32 bytes
COMPANY_ADDR = 0x38              # 32 bytes
ICON_RES_ID_ADDR = 0x58          # 4 bytes
JUMP_TABLE_ADDR = 0x5c   	 # 4 bytes
FLAGS_ADDR = 0x60 		 # 4 bytes
RELOC_LIST_START_ADDR = 0x64 	 # 4 bytes
NUM_RELOC_ENTRIES_ADDR = 0x68 	 # 4 bytes
UUID_ADDR = 0x6c                 # 16 bytes
STRUCT_SIZE_BYTES = 0x7c

# max app size, including the struct and reloc table
MAX_APP_BINARY_SIZE = 0x10000

ENTRY_PT_SYMBOL = 'pbl_main'
JUMP_TABLE_ADDR_SYMBOL = 'pbl_table_addr'
DEBUG = False

cached_nm_output = None

class InvalidBinaryError(Exception):
    pass


def inject_metadata(target_binary):

    if target_binary[-4:] != '.bin':
        raise InvalidBinaryError

    def get_symbol_addr(elf_file, symbol):
        global cached_nm_output

        if not cached_nm_output:
            nm_process = Popen(['arm-none-eabi-nm', elf_file], stdout=PIPE)
            # Popen.communicate returns a tuple of (stdout, stderr)
            nm_output = nm_process.communicate()[0]

            if not nm_output:
                raise InvalidBinaryError()

            cached_nm_output = nm_output
        else:
            nm_output = cached_nm_output

        for sym in nm_output.split('\n'):
            if symbol in sym:
                return int(sym.split()[0], 16)

        raise InvalidBinaryError()

    def get_relocate_entries(elf_file):
        """ returns a list of all the locations requiring an offset"""
        # TODO: insert link to the wiki page I'm about to write about PIC and relocatable values
        entries = []

        # get the .data locations
        readelf_relocs_process = Popen(['arm-none-eabi-readelf', '-r', elf_file], stdout=PIPE)
        readelf_relocs_output = readelf_relocs_process.communicate()[0]
        lines = readelf_relocs_output.split('\n')

        i = 0
        reading_section = False
        while i < len(lines):
            if not reading_section:
                # look for the next section
                if lines[i].find("Relocation section '.rel.data") == 0:
                    reading_section = True
                    i += 1 # skip the column title section
            else:
                if len(lines[i]) == 0:
                    # end of the section
                    reading_section = False
                else:
                    entries.append(int(lines[i].split(' ')[0], 16))
            i += 1

        # get any Global Offset Table (.got) entries
        readelf_relocs_process = Popen(['arm-none-eabi-readelf', '--sections', elf_file], stdout=PIPE)
        readelf_relocs_output = readelf_relocs_process.communicate()[0]
        lines = readelf_relocs_output.split('\n')
        for line in lines:
            # We shouldn't need to do anything with the Procedure Linkage Table since we don't actually export functions
            if '.got' in line and '.got.plt' not in line:
                words = line.split(' ')
                while '' in words:
                    words.remove('')
                section_label_idx = words.index('.got')
                addr = int(words[section_label_idx + 2], 16)
                length = int(words[section_label_idx + 4], 16)
                for i in range(addr, addr + length, 4):
                    entries.append(i)
                break

        return entries

    target_elf = '.'.join([os.path.splitext(target_binary)[0], 'elf'])
    app_entry_address = get_symbol_addr(target_elf, ENTRY_PT_SYMBOL)
    jump_table_address = get_symbol_addr(target_elf, JUMP_TABLE_ADDR_SYMBOL)


    reloc_entries = get_relocate_entries(target_elf)

    statinfo = os.stat(target_binary)
    app_size = statinfo.st_size

    if DEBUG:
        copy2(target_binary, target_binary + ".orig")

    with open(target_binary, 'r+b') as f:
        app_bin = f.read()
        compiled_bin_size = len(app_bin)

        if compiled_bin_size + len(reloc_entries)*4 > MAX_APP_BINARY_SIZE:
            raise "Appending the reloc table will make this app too large"

        app_crc = stm32_crc.crc32(app_bin[STRUCT_SIZE_BYTES:])

        struct_changes = {
            'size' : app_size,
            'entry_point' : "0x%08x" % app_entry_address,
            'symbol_table' : "0x%08x" % jump_table_address,
            'crc' : "0x%08x" % app_crc,
            'reloc_list_start': "0x%08x" % compiled_bin_size,
            'num_reloc_entries': "0x%08x" % len(reloc_entries)
            }


        f.seek(SIZE_ADDR)
        f.write(pack('<HLL', app_size, app_entry_address, app_crc))

        f.seek(JUMP_TABLE_ADDR)
        f.write(pack('<L', jump_table_address))

        f.seek(RELOC_LIST_START_ADDR)
        f.write(pack('<LL', compiled_bin_size, len(reloc_entries)))

        f.seek(compiled_bin_size)
        for entry in reloc_entries:
            f.write(pack('<L', entry))

        f.flush()

    return struct_changes

def do_inject(target):
    try:
        injected_data = inject_metadata(target)
        return 0
    except InvalidBinaryError:
        print "Failed to inject app metadata :("
        return -1


def inject(task):
    target = task.inputs[0].abspath()
    return do_inject(target)


if __name__ == '__main__':
    target = sys.argv[1]
    try:
        injected_data = inject_metadata(target)
        print "Injected app metadata :)"
        pprint(injected_data)
    except InvalidBinaryError:
        print "Failed to inject app metadata :("
        sys.exit(-1)
