#MineBot
#GPL and all that
# - espes

import struct
import zlib

from DataBuffer import *

class Format(object):
    def __init__(self, format):
        self.format = format
    def decode(self, dataBuffer):
        for char in self.format:
            if char == "S": # minecraft string
                length, = dataBuffer.readStruct("!h")
                yield unicode(dataBuffer.read(length*2), "utf_16_be")
            elif char == "8": # minecraft string8
                length, = dataBuffer.readStruct("!h")
                yield dataBuffer.read(length)
            elif char == "M": # hack
                yield tuple(EntityMetadataFormat().decode(dataBuffer))
            else:
                res, = dataBuffer.readStruct("!"+char)
                yield res
    
    def encode(self, *args):
        assert len(self.format) == len(args)
        data = ""
        for char, arg in zip(self.format, args):
            if char == "S": # minecraft string
                data += struct.pack("!h", len(arg))
                data += arg.encode("utf_16_be")
            elif char == "8":
                data += struct.pack("!h", len(arg))
                data += arg.encode("utf_8")
            elif char in ("b", "B") and isinstance(arg, str) and len(arg) == 1: # Byte as string
                data += arg
            else:
                data += struct.pack("!"+char, arg)

        return data

class MultiBlockChangeFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        x, z, size = dataBuffer.readStruct("!iih")
        yield x, z
        
        coords = dataBuffer.readStruct("!%dh" % size)
        types = dataBuffer.readStruct("!%db" % size)
        metadatas = dataBuffer.readStruct("!%db" % size)
        
        for coord, type, metadata in zip(coords, types, metadatas):
            bx = coord >> (8+4)
            bz = (coord >> 8) & 0b1111
            by = coord & 0xFF
            
            yield ((bx, by, bz), type, metadata)
        


class WindowItemsFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        type, count = dataBuffer.readStruct("!bh")
        
        yield type
        #yield count
        
        items = {}
        for i in xrange(count):
            itemId, = dataBuffer.readStruct("!h")
            if itemId == -1: continue
            
            count, health = dataBuffer.readStruct("!bh")
            items[i] = (itemId, count, health)
        yield items


class SetSlotFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        type, slot, itemId = dataBuffer.readStruct("!bhh")
        
        yield type
        yield slot
        
        if itemId >= 0:
            count, health = dataBuffer.readStruct("!bh")
            yield (itemId, count, health)
        else:
            yield None

class WindowClickFormat(Format):
    def __init__(self):
        pass
    def encode(self, windowId, slot, rightClick, actionNumber, shiftClick, item):
        if item is None:
            return struct.pack("!bhbhbh", windowId, slot, rightClick, actionNumber, shiftClick, -1)
        else:
            itemId, count, uses = item
            return struct.pack("!bhbhbhbh", windowId, slot, rightClick, actionNumber, shiftClick, itemId, count, uses)

class ExplosionFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        x, y, z, unk1, count = dataBuffer.readStruct("!dddfi")
        for i in xrange(count):
            dx, dy, dz = dataBuffer.readStruct("!bbb")

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
        x, y, z, face, itemId = dataBuffer.readStruct("!ibibh")
        if itemId >= 0:
            count, health = dataBuffer.readStruct("!bb")

class ChunkFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        x, y, z, sx, sy, sz, chunkSize = dataBuffer.readStruct("!ihibbbi")
        
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
            5: Format('hbh'),
            6: Format('iii')
        }
    def decode(self, dataBuffer):
        while True:
            x, = dataBuffer.readStruct("!B")
            if x == 127: break
            yield tuple(self.formatMap[x >> 5].decode(dataBuffer))
        
class ItemDataFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        itemId, damage, length = dataBuffer.readStruct("!hhb")
        yield itemId
        yield damage
        yield dataBuffer.read(length)

class AddObjectFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        id, type, x, y, z, fireballThrowerId = dataBuffer.readStruct("!ibiiii")
        for v in (id, type, x, y, z, fireballThrowerId):
            yield v
        if fireballThrowerId > 0:
            u1, u2, u3 = dataBuffer.readStruct("hhh")