#MineBot
#GPL and all that
# - espes

import struct
from StringIO import StringIO

class IncompleteDataError(Exception):
    pass

class DataBuffer(StringIO):
    def lenLeft(self):
        return len(self.getvalue())-self.tell()
    def read(self, size=None):
        if size is None:
            return StringIO.read(self)
        
        if self.lenLeft() < size:
            raise IncompleteDataError
        return StringIO.read(self, size)
    def readStruct(self, formatString):
        length = struct.calcsize(formatString)
        try:
            return struct.unpack(formatString, self.read(length))
        except struct.error:
            raise IncompleteDataError
    def peek(self, size=None):
        if size is None:
            return self.getvalue()[self.tell():]
        
        if self.lenLeft() < size:
            raise IncompleteDataError
        return self.getvalue()[self.tell():self.tell()+size]