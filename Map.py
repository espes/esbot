#MineBot
#GPL and all that
# - espes

import heapq
from collections import deque
import time

from constants import *
from Utility import *

class BlockNotLoadedError(Exception):
    pass
class TimeoutError(Exception):
    pass
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
    def searchForBlock(self, source, targetBlock, timeout=10, maxDist=None):
        source = Point(*map(ifloor, source))
        
        startTime = time.time()
        
        visited = {}
        visited[tuple(source)] = True
        q = deque([source])
        while q:
            pos = q.popleft()
            if time.time()-startTime > timeout:
                logging.debug("last dis: %r" % (pos-source).mag())
                raise TimeoutError
            for dx, dy, dz in zip(self.adjX, self.adjY, self.adjZ):
                npos = pos + (dx, dy, dz)
                if maxDist is not None and npos.mag() > maxDist: continue
                if tuple(npos) in visited: continue
                try:
                    if self[npos] == targetBlock:
                        return npos
                except BlockNotLoadedError:
                    continue
                
                q.append(npos)
                visited[tuple(npos)] = True
        
        return None
        
    def findPath(self, start, end,
            acceptIncomplete=False,
            threshold=None, 
            destructive=False,
            blockBreakPenalty=None,
            forClient=None):
        walkableBlocks = BLOCKS_WALKABLE
        if destructive:
            walkableBlocks |= BLOCKS_BREAKABLE
        
        #A* FTW
        try:
            assert self[end] in walkableBlocks and self[end.x,end.y+1,end.z] in walkableBlocks
        except BlockNotLoadedError, e:
            if not acceptIncomplete:
                raise e
        assert self[start] in BLOCKS_WALKABLE
        
        adjX = self.adjX
        adjY = self.adjY
        adjZ = self.adjZ
        
        pq = []
        heapq.heapify(pq)
        
        visited = {}
        backTrack = {}
        found = None
        
        mapInstance = self
        class AStarNode(Point):
            def __init__(self, *args):
                Point.__init__(self, *args)
                self.dist = (end-self).mag()
                
                try:
                    self.blockId = mapInstance[self]
                    self.available = True
                except BlockNotLoadedError:
                    self.blockId = None
                    self.available = False
                
                if destructive and self.blockId in BLOCKS_BREAKABLE:
                    if blockBreakPenalty is not None:
                        self.dist += blockBreakPenalty
                    elif forClient:
                        #TODO: estimate using number of hits
                    
                        #takes about 3? game ticks to clear the blocks
                        mineTime = forClient.targetTick*3
                        mineDistance = forClient.speed*mineTime
                        self.dist += mineDistance
                
        
        startNode = AStarNode(*map(ifloor, start))
        endNode = AStarNode(*map(ifloor, end))
        
        startTime = time.time()
        
        heapq.heappush(pq, startNode)
        while len(pq) > 0 and found is None:
            if time.time()-startTime > 10:
                raise TimeoutError
            
            node = heapq.heappop(pq)
            if tuple(node) in visited:
                continue
            if tuple(node) == tuple(endNode) or \
                    ((not node.available) and acceptIncomplete) or \
                    (threshold is not None and node.dist <= threshold):
                
                found = node
                break
            
            visited[tuple(node)] = True
            for dx, dy, dz in zip(adjX, adjY, adjZ):
                newNode = AStarNode(node.x+dx, node.y+dy, node.z+dz)
                
                if (not newNode.available) and (not acceptIncomplete):
                    continue
                if newNode.available and (newNode.blockId not in walkableBlocks):
                    continue
                
                #Make sure the player can get through, player is 2 blocks vertically
                try:
                    if self[newNode.x, newNode.y+1, newNode.z] not in walkableBlocks:
                        continue
                except BlockNotLoadedError:
                    pass
                
                #Make sure the block below is not a fence
                try:
                    if self[newNode.x, newNode.y-1, newNode.z] == BLOCK_FENCE:
                        continue
                except BlockNotLoadedError:
                    pass
                
                #don't destroy blocks when things will fall on you
                try:
                    if destructive and self[newNode.x, newNode.y+2, newNode.z] in (
                            BLOCK_GRAVEL,
                            BLOCK_SAND,
                            BLOCK_WATER,
                            BLOCK_STATIONARYWATER,
                            BLOCK_LAVA,
                            BLOCK_STATIONARYLAVA):
                        continue
                except BlockNotLoadedError:
                    pass
                
                backTrack[newNode] = node
                heapq.heappush(pq, newNode)
                pq.sort(lambda a,b: cmp(a.dist, b.dist))
        
        if found is not None:
            path = []
            cur = found
            while cur != startNode:
                path.append(Point(cur.x+0.5, cur.y, cur.z+0.5))
                cur = backTrack[cur]
            path.append(Point(cur.x+0.5, cur.y, cur.z+0.5)) #append the start node too
            
            path.reverse()
            if acceptIncomplete:
                return path, found.available
            else:
                return path
        
        if acceptIncomplete:
            return None, False
        else:
            return None