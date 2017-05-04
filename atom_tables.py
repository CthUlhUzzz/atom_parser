#!/usr/bin/env python3
import struct
from hexdump import hexdump
import argparse

ATOM_BIOS_MAGIC = b'\x55\xAA'  # Первые 2 байта прошивки
ATOM_ATI_MAGIC_OFFSET = 0x30  # Смещение относительно начала прошивки
ATOM_ATI_MAGIC = b' 761295520'
ATOM_ROM_TABLE_PTR_OFFSET = 0x48  # Смещение относительно начала прошивки
ATOM_ROM_MAGIC_OFFSET = 0x4  # Смещение относительно ATOM_ROM_TABLE
ATOM_ROM_MAGIC = b'ATOM\0'
ATOM_ROM_DATA_PTR_OFFSET = 0x20  # Смещение относительно ATOM_ROM_TABLE

# class AtomROMHeader:
#     def __init__(self):
#         self.FirmWareSignature[4]
#         self.BiosRuntimeSegmentAddress
#         self.ProtectedModeInfoOffset
#         self.ConfigFilenameOffset
#         self.CRC_BlockOffset
#         self.BIOS_BootupMessageOffset
#         self.Int10Offset
#         self.PciBusDevInitCode
#         self.IoBaseAddress
#         self.SubsystemVendorID
#         self.SubsystemID
#         self.PCI_InfoOffset
#         self.MasterCommandTableOffset
#         self.MasterDataTableOffset
#         self.ExtendedFunctionCode
#         self.Reserved

LIST_OF_DATA_TABLES = ['UtilityPipeLine',
                       'MultimediaCapabilityInfo',
                       'MultimediaConfigInfo',
                       'StandardVESA_Timing',
                       'FirmwareInfo',
                       'PaletteData',
                       'LCD_Info',
                       'DIGTransmitterInfo',
                       'SMU_Info',
                       'SupportedDevicesInfo',
                       'GPIO_I2C_Info',
                       'VRAM_UsageByFirmware',
                       'GPIO_Pin_LUT',
                       'VESA_ToInternalModeLUT',
                       'GFX_Info',
                       'PowerPlayInfo',
                       'GPUVirtualizationInfo',
                       'SaveRestoreInfo',
                       'PPLL_SS_Info',
                       'OemInfo',
                       'XTMDS_Info',
                       'MclkSS_Info',
                       'Object_Header',
                       'IndirectIOAccess',
                       'MC_InitParameter',
                       'ASIC_VDDC_Info',
                       'ASIC_InternalSS_Info',
                       'TV_VideoMode',
                       'VRAM_Info',
                       'MemoryTrainingInfo',
                       'IntegratedSystemInfo',
                       'ASIC_ProfilingInfo',
                       'VoltageObjectInfo',
                       'PowerSourceInfo',
                       'ServiceInfo']


def read_cstr(ptr, fp):
    fp.seek(ptr)
    cstr = b''
    while True:
        b = fp.read(1)
        cstr += b
        if b == b'\0':
            break
    return cstr


def parse_data_tables_list(rom_fp):
    bios_magic = rom_fp.read(len(ATOM_BIOS_MAGIC))
    if bios_magic != ATOM_BIOS_MAGIC:
        print('Invalid BIOS magic.')
        exit()
    rom_fp.seek(ATOM_ATI_MAGIC_OFFSET)
    ati_magic = rom_fp.read(len(ATOM_ATI_MAGIC))
    if ati_magic != ATOM_ATI_MAGIC:
        print('Invalid ATI magic.')
        exit()
    rom_fp.seek(ATOM_ROM_TABLE_PTR_OFFSET)
    rom_base = struct.unpack('<H', rom_fp.read(2))[0]
    rom_fp.seek(rom_base + ATOM_ROM_MAGIC_OFFSET)
    rom_magic = rom_fp.read(len(ATOM_ROM_MAGIC))
    if rom_magic != ATOM_ROM_MAGIC:
        print('Invalid ATOM magic.')
        exit()
    # rom_fp.seek(rom_base + ATOM_ROM_CMD_PTR_OFFSET)
    # rom_cmd_ptr = struct.unpack('<H', rom_fp.read(2))[0]
    rom_fp.seek(rom_base + ATOM_ROM_DATA_PTR_OFFSET)
    rom_data_ptr = struct.unpack('<H', rom_fp.read(2))[0]

    rom_fp.seek(rom_data_ptr + 4)
    data_tables_ptrs = []
    for i in range(len(LIST_OF_DATA_TABLES)):
        data_tables_ptrs.append(struct.unpack('<H', rom_fp.read(2))[0])

    for table in zip(LIST_OF_DATA_TABLES, data_tables_ptrs):
        if table[1] != 0:
            rom_fp.seek(table[1])
            length, v, subv = struct.unpack('<H2B', rom_fp.read(4))
            yield table[0], table[1], length, v, subv, rom_fp.read(length)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=str,
                        help="path to rom file")
    parser.add_argument("--hexdump", help="print hex dump of tables",action="store_true")
    args = parser.parse_args()
    with open(args.rom, 'rb') as rom:
        for table in parse_data_tables_list(rom):
            print('Name: %s' % table[0])
            print('Offset: 0x%02x' % table[1])
            print('Length: %d' % table[2])
            print('Version: %d.%d' % (table[3], table[4]))
            if args.hexdump:
                print()
                hexdump(table[5])
            print()
