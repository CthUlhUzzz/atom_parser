#!/usr/bin/env python3
import argparse
import struct

MEMORY_TYPES = {0x10: 'DDR',
                0x20: 'DDR2',
                0x30: 'GDDR3',
                0x40: 'GDDR4',
                0x50: 'GDDR5',
                0x60: 'HBM',
                0xB0: 'DDR3'}

MEMORY_VENDORS = {0x1: 'SAMSUNG',
                  0x2: 'INFINEON/QIMONDA/KRETON',
                  0x3: 'ELPIDA/MEZZA',
                  0x4: 'ETRON',
                  0x5: 'NANYA/ELIXIR',
                  0x6: 'HYNIX',
                  0x7: 'MOSEL/PROMOS',
                  0x8: 'WINBOND',
                  0x9: 'ESMT',
                  0xF: 'MICRON'}


class VRAMInfoTable:
    def __init__(self, fd, ptr):
        self.TableHeader = TableHeader(fd, ptr)
        self.VRAMInfoHeader = VRAMInfoHeader(fd, ptr + 4)


def read_cstr(fd, ptr=None):
    print(ptr)
    if ptr:
        fd.seek(ptr)
    cstr = b''
    while True:
        symbol = fd.read(1)
        if symbol == b'\0':
            break
        cstr += symbol
    return cstr.decode()


class AtomINITRegIndexFormat:
    def __init__(self, fd, ptr):
        fd.seek(ptr)
        self.RegIndex, \
        self.PreRegDataLength = struct.unpack('<HB', fd.read(3))


class AtomMemorySettingIDConfig:
    def __init__(self, data):
        self.MemClockRange = struct.unpack('<I', data[:3] + b'\0')[0]
        self.MemBlkId = data[3]


class AtomMemorySettingIDConfigAccess:
    def __init__(self, data):
        self.AccessID = AtomMemorySettingIDConfig(data[:4])
        self.Access = struct.unpack('<I', data[4:])[0]


class AtomMemorySettingDataBlock:
    def __init__(self, data):
        self.offset = None
        self.MemoryID = AtomMemorySettingIDConfigAccess(data[:8])
        self.MemData = []
        for i in range(len(data[8:]) // 4):
            self.MemData.append(struct.unpack('<I', data[8 + (4 * i):8 + (4 * i) + 4])[0])


class AtomINITRegBlock:
    def __init__(self, fd, ptr):
        fd.seek(ptr)
        self.RegIndexTblSize, \
        self.RegDataBlkSize = struct.unpack('<HH', fd.read(4))
        self.RegIndexBuf = []
        for i in range((self.RegIndexTblSize // 3) - 1):
            self.RegIndexBuf.append(AtomINITRegIndexFormat(fd, ptr + 4 + i * 3))
        if fd.read(3) != b'\xff\xff\x00':
            print('Parsing error!')
            exit()
        self.RegDataBuf = []
        while True:
            line = rom.read(self.RegDataBlkSize)
            if line[:4] == b'\0\0\0\0':
                break
            self.RegDataBuf.append(AtomMemorySettingDataBlock(line))
            self.RegDataBuf[-1].offset = fd.tell() - self.RegDataBlkSize


class TableHeader:
    def __init__(self, fd, ptr):
        fd.seek(ptr)
        self.StructureSize, \
        self.TableFormatRevision, \
        self.TableContentRevision = struct.unpack('<HBB', fd.read(4))


class VRAMModule:
    def __init__(self, fd, ptr):
        self.start = ptr

        fd.seek(ptr)
        self.ChannelMapCfg, \
        self.ModuleSize, \
        self.McRamCfg, \
        self.EnableChannels, \
        self.ExtMemoryID, \
        self.MemoryType, \
        self.ChannelNum, \
        self.ChannelWidth, \
        self.Density, \
        self.BankCol, \
        self.Misc, \
        self.VREFI, \
        self.Reserved1, \
        self.MemorySize, \
        self.McTunningSetId, \
        self.RowNum, \
        self.EMRS2Value, \
        self.EMRS3Value, \
        self.MemoryVenderID, \
        self.RefreshRateFactor, \
        self.FIFODepth, \
        self.CDR_Bandwidth, \
        self.ChannelMapCfg1, \
        self.BankMapCfg, \
        self.Reserved1 = struct.unpack('<I3H8B2H2B2H4B3I', fd.read(44))
        self.MemPNString = b''
        while True:
            symbol = fd.read(1)
            self.MemPNString += symbol
            if symbol == b'\0':
                break
        self.length = 44 + len(self.MemPNString)
        self.MemPNString = self.MemPNString[:-1].decode()


class VRAMInfoHeader:
    def __init__(self, fd, ptr):
        fd.seek(ptr)
        self.MemAdjustTblOffset, \
        self.MemClkPatchTblOffset, \
        self.McAdjustPerTileTblOffset, \
        self.McPhyInitTableOffset, \
        self.DramDataRemapTblOffset, \
        self.Reserved, \
        self.NumOfVRAMModule, \
        self.MemoryClkPatchTblVer, \
        self.VramModuleVer, \
        self.McPhyTileNum = struct.unpack('<6H4B', fd.read(16))
        self.VramInfo = []
        latest_ptr = fd.tell()
        if self.VramModuleVer == 8:
            for _ in range(self.NumOfVRAMModule):
                self.VramInfo.append(VRAMModule(fd, latest_ptr))
                latest_ptr = self.VramInfo[-1].start + self.VramInfo[-1].length


def parse_vram(fd, offset):
    vram_info_table = VRAMInfoTable(fd, offset)
    vram_clk_patch_tbl = AtomINITRegBlock(fd, offset + vram_info_table.VRAMInfoHeader.MemClkPatchTblOffset)
    return vram_info_table, vram_clk_patch_tbl


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--print_offsets", action="store_true", help="print offsets")
    parser.add_argument("rom", type=str,
                        help="path to rom file")
    parser.add_argument("offset", type=str, help='offset of table in hex notation')
    args = parser.parse_args()
    offset = int(args.offset, 16)
    with open(args.rom, 'rb') as rom:
        vram_info_table, vram_clk_patch_tbl = parse_vram(rom, offset)
    counter = 0
    for vram in vram_info_table.VRAMInfoHeader.VramInfo:
        print('ID: %d' % counter)
        if vram.MemPNString:
            print('Name: %s' % vram.MemPNString)
        if vram.MemoryType in MEMORY_TYPES:
            print('Type: %s' % MEMORY_TYPES[vram.MemoryType])
        print('Total size: %sMB' % vram.MemorySize)
        vend_rev = bin(vram.MemoryVenderID)[2:].zfill(8)
        vend, rev = int(vend_rev[4:], 2), int(vend_rev[:4], 2)
        if vend in MEMORY_VENDORS:
            print('Vendor: %s' % MEMORY_VENDORS[vend])
        print('Revision: %d' % rev)
        print()
        for timings in vram_clk_patch_tbl.RegDataBuf:
            if timings.MemoryID.AccessID.MemBlkId == counter:
                print(str(timings.MemoryID.AccessID.MemClockRange / 100) + '\t', end='')
                if args.print_offsets:
                    print(hex(timings.offset)[2:].zfill(8) + ': ', end='')
                print(' '.join((hex(i)[2:].zfill(8) for i in timings.MemData)))
        print()
        counter += 1

    pass

    # self.strMemPNString = read_cstr(fd, fd.tell())

    # MEMORY_RATES_FACTOR = {0b0: 8,
    #                        0b1: 16,
    #                        0b10: 32,
    #                        0b11: 64}


    # self.length = 44 + len(self.strMemPNString)
    # while True:
    #     symbol = fd.read(1)
    #     self.strMemPNString += symbol
    #     if symbol == b'\0':
    #         break
    # self.length = 44 + len(self.strMemPNString)


    # MEMORY_DENSITYS = {0x2: '4Mx16',
    #                    0x3: '4Mx32',
    #                    0x12: '8Mx16',
    #                    0x13: '8Mx32',
    #                    0x15: '8Mx128',
    #                    0x22: '16Mx16',
    #                    0x23: '16Mx32',
    #                    0x25: '16Mx128',
    #                    0x32: '32Mx16',
    #                    0x33: '32Mx32',
    #                    0x35: '32Mx128',
    #                    0x41: '64Mx8',
    #                    0x42: '64Mx16',
    #                    0x43: '64Mx32',
    #                    0x45: '64Mx128',
    #                    0x51: '128Mx8',
    #                    0x52: '128Mx16',
    #                    0x53: '128Mx32',
    #                    0x61: '256Mx8',
    #                    0x62: '256Mx16',
    #                    0x63: '256Mx32',
    #                    0x71: '512Mx8',
    #                    0x72: '512Mx16'}


    # if vram.ChannelNum in MEMORY_WIDTHS:
    # print('Channel width: %dbit' % 2 ** vram.ChannelWidth)
    # print('Channels count: %d' % vram.ChannelNum)
    # if vram.Density in MEMORY_DENSITYS:
    #     print('Density: %s' % MEMORY_DENSITYS[vram.Density])
    # if vram.RefreshRateFactor in MEMORY_RATES_FACTOR:
    #     print('Refresh rate factor: %dms' % MEMORY_RATES_FACTOR[vram.RefreshRateFactor])
    # print(bin(vram.EnableChannels)[2:].zfill(16))
