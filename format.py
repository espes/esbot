#GPL and all that
# - espes

import struct
import zlib

class IncompleteDataError(Exception):
    pass

def unpackStructBuffer(formatString, data):
    length = struct.calcsize(formatString)
    if len(data) < length: raise IncompleteDataError
    return struct.unpack(formatString, data[:length]), length

class Format(object):
    def __init__(self, format):
        self.format = format
    def decode(self, data):
        dataLen = 0
        for char in self.format:
            if char == "s":
                (length,), ll = unpackStructBuffer("!h", data)
                length += ll
                if len(data) < length: raise IncompleteDataError
                yield data[2:length]
            else:
                (res,), length = unpackStructBuffer("!"+char, data)
                yield res
            
            data = data[length:]
            dataLen += length
        yield dataLen
    
    def encode(self, *args):
        assert len(self.format) == len(args)
        data = ""
        for char, arg in zip(self.format, args):
            if char == "s": # String
                data += struct.pack("!h", len(arg))
                data += arg
            elif char == "b": # Byte
                if isinstance(arg, int):
                    data += struct.pack("!b", arg)
                elif isinstance(arg, str) and len(arg) == 1:
                    data += arg
                else:
                    raise ValueError("Invalid value for byte: %r" % arg)
            elif char == "h": # Short
                data += struct.pack("!h", arg)
            elif char == "i": # Integer
                data += struct.pack("!i", arg)
            elif char == "q": # Long (long)
                data += struct.pack("!q", arg)
            elif char == "f": # Float
                data += struct.pack("!f", arg)
            elif char == "d": # Double
                data += struct.pack("!d", arg)

        return data

class MultiBlockChangeFormat(Format):
    def __init__(self):
        pass
    def decode(self, data):
        length = 0
        (x, z, size), usedData = unpackStructBuffer("!iih", data)
        data = data[usedData:]
        length += usedData
        yield x, z
        
        coords, usedData = unpackStructBuffer("!%dh" % size, data)
        data = data[usedData:]
        length += usedData
        types, usedData = unpackStructBuffer("!%db" % size, data)
        data = data[usedData:]
        length += usedData
        metadatas, usedData = unpackStructBuffer("!%db" % size, data)
        data = data[usedData:]
        length += usedData
        
        
        for coord, type, metadata in zip(coords, types, metadatas):
            bx = coord >> (8+4)
            bz = (coord >> 8) & 0b1111
            by = coord & 0xFF
            
            yield (bx, by, bz), type, metadata
        
        yield length
        


class InventoryFormat(Format):
    def __init__(self):
        pass
    def decode(self, data):
        length = 0
        (type, count), usedData = unpackStructBuffer("!bh", data)
        data = data[usedData:]
        length += usedData
        
        yield type
        yield count
        
        for i in xrange(count):
            (itemId,), usedData = unpackStructBuffer("!h", data)
            data = data[usedData:]
            length += usedData
            
            if itemId < 0:
                continue
            
            (count, health), usedData = unpackStructBuffer("!bh", data)
            data = data[usedData:]
            length += usedData
            
            yield itemId, count, health
        
        yield length


class SetSlotFormat(Format):
    def __init__(self):
        pass
    def decode(self, data):
        length = 0
        (type, slot, itemId), usedData = unpackStructBuffer("!bhh", data)
        data = data[usedData:]
        length += usedData
        
        if itemId >= 0:
            (count, health), usedData = unpackStructBuffer("!bh", data)
            data = data[usedData:]
            length += usedData
        
        yield length

class ExplosionFormat(Format):
    def __init__(self):
        pass
    def decode(self, data):
        #print "explosion format"
        length = 0
        (x, y, z, unk1, count), usedData = unpackStructBuffer("!dddfi", data)
        data = data[usedData:]
        length += usedData
        
        for i in xrange(count):
            (dx, dy, dz), usedData = unpackStructBuffer("!bbb", data)
            data = data[usedData:]
            length += usedData
        
        yield length

class BlockPlaceFormat(Format):
    def __init__(self):
        pass
    def decode(self, data):
        length = 0
        (x, y, z, face, itemId), usedData = unpackStructBuffer("!ibibh", data)
        data = data[usedData:]
        length += usedData
        
        if itemId >= 0:
            (count, health), usedData = unpackStructBuffer("!bb", data)
            data = data[usedData:]
            length += usedData

        yield length

class ChunkFormat(Format):
    def __init__(self):
        pass
    def decode(self, data):
        length = 0
        (x, y, z, sx, sy, sz, chunkSize), usedData = unpackStructBuffer("!ihibbbi", data)
        data = data[usedData:]
        length += usedData
        
        sx += 1
        sy += 1
        sz += 1
        
        for v in (x, y, z, sx, sy, sz): yield v
        
        if len(data) < chunkSize: raise IncompleteDataError
        yield zlib.decompress(data[:chunkSize])
        #chunkData = zlib.decompress(data[:chunkSize])
        #yield chunkData[:sx*sy*sz] #block types
        #i = sx*sy*sz
        #metaData = []
        #for j in range(sx*sy*sz):
        #    metaData.append(chunkData[i+j/2] >> (4*(i%2)))
        
        
        length += chunkSize
        
        yield length
        


class EntityMetadataFormat(Format):
    def __init__(self):
        self.formatMap = {
            0: Format('b'),
            1: Format('h'),
            2: Format('i'),
            4: Format('s'),
            5: Format('hbh')
        }
    def decode(self, data):
        length = 0
        
        while True:
            (x,), usedData = unpackStructBuffer("!b", data)
            data = data[usedData:]
            length += usedData
            
            if x == 127: break
            
            values = self.formatMap[x >> 5].decode(data)
            usedData = values.pop()
            data = data[usedData:]
            length += usedData
        yield length