#MineBot
#GPL and all that
# - espes

import heapq
import time

from constants import *
from Utility import *

class BlockNotLoadedError(Exception):
    pass
class SearchTimeoutError(Exception):
    pass

try:
    import numpy
except ImportError:
    import array
    class Chunk(object):
        def __init__(self, position, size, chunkData):
            self.pos = position
            self.size = size
            self.sizeX, self.sizeY, self.sizeZ = size
        
            #TODO: handle other chunk data
        
            self.blockData = array.array('B', chunkData[:self.sizeX*self.sizeY*self.sizeZ])
        def __getitem__(self, key):
            x, y, z = key
            return self.blockData[y + z*self.sizeY + x*self.sizeY*self.sizeZ]
        def __setitem__(self, key, value):
            x, y, z = key
            self.blockData[y + z*self.sizeY + x*self.sizeY*self.sizeZ] = value
        def getBlocks(self, value):
            for x in xrange(self.sizeX):
                for y in xrange(self.sizeY):
                    for z in xrange(self.sizeZ):
                        if self[x, y, z] == value:
                            yield x, y, z
else:
    class Chunk(object):
        def __init__(self, position, size, chunkData):
            self.pos = position
            self.size = size
            self.sizeX, self.sizeY, self.sizeZ = size
            
            d = numpy.fromstring(chunkData[:self.sizeX*self.sizeY*self.sizeZ], dtype=numpy.uint8)
            self.blockData = d.reshape(self.sizeX, self.sizeZ, self.sizeY).swapaxes(1, 2)
        def __getitem__(self, key):
            return self.blockData[tuple(key)]
        def __setitem__(self, key, value):
            self.blockData[tuple(key)] = value
        def getBlocks(self, value):
            return numpy.transpose(numpy.nonzero(self.blockData==value))



class Map(object):
    def __init__(self):
        
        self.chunks = {}
        
        self.adjX = [0, -1, 0, 1, 0, 0]
        self.adjY = [0, 0, -1, 0, 1, 0]
        self.adjZ = [-1, 0, 0, 0, 0, 1]
    def addChunk(self, chunk):
        self.chunks[tuple(chunk.pos)] = chunk
    def findChunk(self, position):
        x, y, z = map(ifloor, position)
        #Try assuming chunks are 16-blocks alligned
        chunkPos = (x-x%16, 0, z-z%16)
        if chunkPos in self.chunks:
            chunk = self.chunks[chunkPos]
            cx, cy, cz = chunkPos
            if cx<=x<cx+chunk.sizeX and cy<=y<cy+chunk.sizeY and cz<=z<cz+chunk.sizeZ:
                return chunk
        
        #Do a search of all chunks
        for chunkPos, chunk in self.chunks.items():
            cx, cy, cz = chunkPos
            if cx<=x<cx+chunk.sizeX and cy<=y<cy+chunk.sizeY and cz<=z<cz+chunk.sizeZ:
                return chunk
        return None
        
        
    def __getitem__(self, key):
        assert isinstance(key, Point) or isinstance(key, tuple)
        x, y, z = map(ifloor, key)
        
        if y >= 128: #World top
            return BLOCK_AIR
        elif y <= 0:
            return BLOCK_BEDROCK
        
        chunk = self.findChunk((x, y, z))
        if chunk:
            cx, cy, cz = chunk.pos
            return chunk[x-cx, y-cy, z-cz]
        
        raise BlockNotLoadedError
    def __setitem__(self, key, value):
        assert isinstance(key, Point) or isinstance(key, tuple)
        x, y, z = map(ifloor, key)
        
        chunk = self.findChunk((x, y, z))
        if chunk:
            cx, cy, cz = chunk.pos
            chunk[x-cx, y-cy, z-cz] = value
        else:
            raise BlockNotLoadedError
        
    def searchForBlock(self, source, targetBlock, maxDist=None):
        source = Point(*map(ifloor, source))
        
        for i, chunk in enumerate(sorted(self.chunks.itervalues(), key=lambda c: (source-c.pos).mag())):
            r = None
            for cp in chunk.getBlocks(targetBlock):
                cp = Point(*cp)+chunk.pos
                if r is None or (source-cp).mag() < (source-r).mag():
                    r = cp
            if r is not None: return r
        return None
        
    def raycast(self, start, end, clip=True):
        start = Point(*start)
        end = Point(*end)
        
        d = end-start
        dis = (end-start).mag()
        
        try: xd = d/abs(d.x)
        except ZeroDivisionError: xd = Point(0, inf, inf)
        xc = start+xd*(start.x%1 if xd.x > 0 else 1-(start.x%1))
        xg = lambda: Point(ifloor(xc.x) if xd.x > 0 else ifloor(xc.x)-1, ifloor(xc.y), ifloor(xc.z))
        
        try: yd = d/abs(d.y)
        except ZeroDivisionError: yd = Point(inf, 0, inf)
        yc = start+yd*(start.y%1 if yd.y > 0 else 1-(start.y%1))
        yg = lambda: Point(ifloor(yc.x), ifloor(yc.y) if yd.y > 0 else ifloor(yc.y)-1, ifloor(yc.z))
        
        try: zd = d/abs(d.z)
        except ZeroDivisionError: zd = Point(inf, inf, 0)
        zc = start+zd*(start.z%1 if zd.z > 0 else 1-(start.z%1))
        zg = lambda: Point(ifloor(zc.x), ifloor(zc.y), ifloor(zc.z) if zd.z > 0 else ifloor(zc.z)-1)
        
        while True:
            cur, curd, curg = min(
                (xc, xd, xg), (yc, yd, yg), (zc, zd, zg),
                key=lambda p: (p[0]-start).mag())
            if clip and (cur-start).mag() > dis:
                return
            #print cur, curg()
            yield curg()
            
            cur += curd
    
    def blockInLine(self, start, end, cands):
        for p in self.raycast(start, end):
            if self[p] in cands:
                return True
        return False
        
        
    def findPath(self, start, end,
            acceptIncomplete=False,
            threshold=None,
            timeout=10,
            destructive=False,
            blockBreakPenalty=None,
            floatPenalty=10,
            forClient=None):
        walkableBlocks = BLOCKS_WALKABLE
        if destructive:
            walkableBlocks |= BLOCKS_BREAKABLE
        
        #Greedy BFS FTW
        #(I fail - A* slower in general case. Patches welcome)
        try:
            assert self[end] in walkableBlocks and self[end + (0, 1, 0)] in walkableBlocks
        except BlockNotLoadedError, e:
            if not acceptIncomplete:
                raise e
        assert self[start] in BLOCKS_WALKABLE
        
        adjX = self.adjX
        adjY = self.adjY
        adjZ = self.adjZ
        
        
        mapInstance = self
        class AStarNode(object):
            def __init__(self, pos):
                self.pos = pos
                self.dist = (end-self.pos).mag()
                
                try:
                    self.blockId = mapInstance[self.pos]
                    self.available = True
                except BlockNotLoadedError:
                    self.blockId = None
                    self.available = False
            def __cmp__(self, other):
                return cmp(self.dist, other.dist)
        
        pq = []
        heapq.heapify(pq)

        visited = set([])
        backTrack = {}
        found = None
        
        startNode = AStarNode(Point(*map(ifloor, start)))
        endPos = Point(*map(ifloor, end))
        
        startTime = time.time()
        
        visited.add(startNode.pos)
        heapq.heappush(pq, startNode)
        while pq and found is None:
            if time.time()-startTime > timeout:
                raise SearchTimeoutError
            
            node = heapq.heappop(pq)
            if (node.pos == endPos or 
                    ((not node.available) and acceptIncomplete) or 
                    (threshold is not None and node.dist <= threshold and
                        self[node.pos + (0, -1, 0)] not in BLOCKS_WALKABLE) ):
                
                found = node
                break
            
            
            for adj in zip(adjX, adjY, adjZ):
                newNode = AStarNode(node.pos + adj)
                if newNode.pos in visited:
                    continue
                
                if (not newNode.available) and (not acceptIncomplete):
                    continue
                if newNode.available and (newNode.blockId not in walkableBlocks):
                    continue
                
                #Make sure the player can get through, player is 2 blocks vertically
                try:
                    if self[newNode.pos + (0, 1, 0)] not in walkableBlocks:
                        continue
                except BlockNotLoadedError:
                    pass
                
                #Make sure the block below is not a fence
                try:
                    if self[newNode.pos + (0, -1, 0)] == BLOCK_FENCE:
                        continue
                except BlockNotLoadedError:
                    pass
                
                #don't destroy blocks when things will fall on you
                try:
                    if destructive and self[newNode.pos + (0, 2, 0)] in (
                            BLOCK_GRAVEL,
                            BLOCK_SAND,
                            BLOCK_WATER,
                            BLOCK_SPRING,
                            BLOCK_LAVA,
                            BLOCK_LAVASPRING):
                        continue
                except BlockNotLoadedError:
                    pass
                
                #don't destroy blocks when things will seep in
                if destructive:
                    abort = False
                    for offset in [ (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1),
                                    (1, 1, 0), (-1, 1, 0), (0, 1, 1), (0, 1, -1)]:
                        try:
                            if self[newNode.pos+offset] in (
                                    BLOCK_WATER,
                                    BLOCK_SPRING,
                                    BLOCK_LAVA,
                                    BLOCK_LAVASPRING):
                                abort = True
                                break
                        except BlockNotLoadedError:
                            pass
                    if abort: continue
                
                
                #walking ontop of lava hurts
                try:
                    if self[newNode.pos + (0, -1, 0)] in (BLOCK_LAVA, BLOCK_LAVASPRING):
                        continue
                except BlockNotLoadedError:
                    pass
                
                #Avoid breaking blocks
                if destructive:
                    for offset in [(0, 0, 0), (0, 1, 0)]:
                        try:
                            blockId = self[newNode.pos + offset]
                        except BlockNotLoadedError:
                            continue
                        if blockId in BLOCKS_BREAKABLE:
                            if blockBreakPenalty is not None:
                                newNode.dist += blockBreakPenalty
                            elif forClient:
                                #Assume not holding anything :\
                                #20 hits per sec
                                mineTime = gamelogic.calcHitsToBreakBlock(forClient, blockId, -1)/20

                                mineDistance = forClient.speed*mineTime
                                newNode.dist += mineDistance/2
                
                #Avoid floating
                try:
                    if (newNode.pos.y >= node.pos.y and
                            self[newNode.pos + (0, -1, 0)] in BLOCKS_WALKABLE and
                            self[node.pos + (0, -1, 0)] in BLOCKS_WALKABLE and
                            self[newNode.pos] != BLOCK_LADDER):
                        newNode.dist += floatPenalty
                except BlockNotLoadedError:
                    pass
                
                backTrack[newNode.pos] = node
                visited.add(newNode.pos)
                heapq.heappush(pq, newNode)
        
        if found is not None:
            #logging.debug("reconstruct")
            
            path = []
            cur = found
            while cur != startNode:
                path.append(cur.pos + (0.5, 0, 0.5))
                cur = backTrack[cur.pos]
            path.append(cur.pos + (0.5, 0, 0.5)) #append the start node too
            
            path.reverse()
            if acceptIncomplete:
                return path, found.available
            else:
                return path
        
        if acceptIncomplete:
            return None, False
        else:
            return None