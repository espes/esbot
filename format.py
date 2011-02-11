#MineBot
#GPL and all that
# - espes

import struct
import zlib

from DataBuffer import *

def readStruct(formatString, dataBuffer):
    length = struct.calcsize(formatString)
    try:
        return struct.unpack(formatString, dataBuffer.read(length))
    except struct.error:
        raise IncompleteDataError

class Format(object):
    def __init__(self, format):
        self.format = format
    def decode(self, dataBuffer):
        for char in self.format:
            if char == "S": # minecraft string
                length, = readStruct("!h", dataBuffer)
                yield dataBuffer.read(length)
            elif char == "M":
                yield tuple(EntityMetadataFormat().decode(dataBuffer))
            else:
                res, = readStruct("!"+char, dataBuffer)
                yield res
    
    def encode(self, *args):
        assert len(self.format) == len(args)
        data = ""
        for char, arg in zip(self.format, args):
            if char == "S": # minecraft string
                data += struct.pack("!h", len(arg))
                data += arg
            elif char in ("b", "B") and isinstance(arg, str) and len(arg) == 1: # Byte as string
                data += arg
            else:
                data += struct.pack("!"+char, arg)

        return data

class MultiBlockChangeFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        x, z, size = readStruct("!iih", dataBuffer)
        yield x, z
        
        coords = readStruct("!%dh" % size, dataBuffer)
        types = readStruct("!%db" % size, dataBuffer)
        metadatas = readStruct("!%db" % size, dataBuffer)
        
        for coord, type, metadata in zip(coords, types, metadatas):
            bx = coord >> (8+4)
            bz = (coord >> 8) & 0b1111
            by = coord & 0xFF
            
            yield ((bx, by, bz), type, metadata)
        


class WindowItemsFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        type, count = readStruct("!bh", dataBuffer)
        
        yield type
        #yield count
        
        items = {}
        for i in xrange(count):
            itemId, = readStruct("!h", dataBuffer)
            if itemId == -1: continue
            
            count, health = readStruct("!bh", dataBuffer)
            items[i] = (itemId, count, health)
        yield items


class SetSlotFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        type, slot, itemId = readStruct("!bhh", dataBuffer)
        
        yield type
        yield slot
        
        if itemId >= 0:
            count, health = readStruct("!bh", dataBuffer)
            yield (itemId, count, health)
        else:
            yield None

class WindowClickFormat(Format):
    def __init__(self):
        pass
    def encode(self, windowId, slot, rightClick, actionNumber, item):
        if item is None:
            return struct.pack("!bhbhh", windowId, slot, rightClick, actionNumber, -1)
        else:
            itemId, count, uses = item
            return struct.pack("!bhbhhbh", windowId, slot, rightClick, actionNumber, itemId, count, uses)

class ExplosionFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        x, y, z, unk1, count = readStruct("!dddfi", dataBuffer)
        for i in xrange(count):
            dx, dy, dz = readStruct("!bbb", dataBuffer)

class BlockPlaceFormat(Format):
    def __init__(self):
        pass
    def encode(self, x, y, z, direction, item):
        if item is None:
            return struct.pack("!ibibh", x, y, z, direction, -1)
        else:
            itemId, count, uses = item
            return struct.pack("!ibibhbh", x, y, z, direction, itemId, count, uses)
    def decode(self, dataBuffer):
        x, y, z, face, itemId = readStruct("!ibibh", dataBuffer)
        if itemId >= 0:
            count, health = readStruct("!bb", dataBuffer)

class ChunkFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        x, y, z, sx, sy, sz, chunkSize = readStruct("!ihibbbi", dataBuffer)
        
        sx += 1
        sy += 1
        sz += 1
        
        yield (x, y, z)
        yield (sx, sy, sz)
        
        yield zlib.decompress(dataBuffer.read(chunkSize))
        
        #chunkData = zlib.decompress(data[:chunkSize])
        #yield chunkData[:sx*sy*sz] #block types
        #i = sx*sy*sz
        #metaData = []
        #for j in range(sx*sy*sz):
        #    metaData.append(chunkData[i+j/2] >> (4*(i%2)))
        


class EntityMetadataFormat(Format):
    def __init__(self):
        self.formatMap = {
            0: Format('b'),
            1: Format('h'),
            2: Format('i'),
            3: Format('f'),
            4: Format('S'),
            5: Format('hbh')
        }
    def decode(self, dataBuffer):
        while True:
            x, = readStruct("!b", dataBuffer)
            if x == 127: break
            yield tuple(self.formatMap[(x & 0xE0) >> 5].decode(dataBuffer))
        

