#MineBot - random helper classes
#GPL and all that
# - espes

from __future__ import division

import heapq
from collections import deque
import time

from math import floor, ceil
import array
from constants import *

def ifloor(a):
    return int(floor(a))

class Point(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z
    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z
    def __repr__(self):
        return "Point(x=%r, y=%r, z=%r)" % tuple(self)
    
    def __sub__(self, other):
        return self.x-other.x, self.y-other.y, self.z-other.z
class Player(object):
    def __init__(self, id, name, pos):
        self.id, self.name, self.pos = id, name, pos
    def __repr__(self):
        return "Player(id=%r, name=%r, pos=%r)" % (self.id, self.name, self.pos)
class MapPlayer(object):
    def __init__(self, name, pos):
        self.name, self.pos = name, pos
    def __repr__(self):
        return "MapPlayer(name=%r, pos=%r)" % (self.name, self.pos)
class Chunk(object):
    def __init__(self, position, size, chunkData):
        self.pos = position
        self.size = size
        self.sizeX, self.sizeY, self.sizeZ = size
        
        self.blockData = array.array('B', chunkData[:self.sizeX*self.sizeY*self.sizeZ])
    def __getitem__(self, key):
        assert isinstance(key, Point) or isinstance(key, tuple)
        x, y, z = key
        return self.blockData[y + z*self.sizeY + x*self.sizeY*self.sizeZ]
    def __setitem__(self, key, value):
        x, y, z = key
        self.blockData[y + z*self.sizeY + x*self.sizeY*self.sizeZ] = value

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
    def searchForBlock(self, source, targetBlock):
        source = Point(*map(ifloor, source))
        
        startTime = time.time()
        
        visited = {}
        visited[tuple(source)] = True
        q = deque([source])
        while True:
            pos = q.popleft()
            if time.time()-startTime > 10:
                print ((pos.x-source.x)**2+(pos.y-source.y)**2+(pos.z-source.z)**2)**0.5
                raise TimeoutError
            for dx, dy, dz in zip(self.adjX, self.adjY, self.adjZ):
                npos = Point(pos.x+dx, pos.y+dy, pos.z+dz)
                if tuple(npos) in visited: continue
                try:
                    if self[npos] == targetBlock:
                        return npos
                except BlockNotLoadedError:
                    continue
                
                q.append(npos)
                visited[tuple(npos)] = True
        
        return None
        
    def findPath(self, start, end, acceptIncomplete=False, threshhold = None):
        #A* FTW
        try:
            assert self[end] in BLOCKS_WALKABLE and self[end.x,end.y+1,end.z] in BLOCKS_WALKABLE
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
        
        class AStarNode(Point):
            def __init__(self, *args):
                Point.__init__(self, *args)
                self.dist = ((end.x-self.x)**2+(end.y-self.y)**2+(end.z-self.z)**2)**0.5
                
                self.available = True
        
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
                    (threshhold is not None and \
                        ((node.x-end.x)**2+(node.y-end.y)**2+(node.z-end.z)**2)**0.5 <= threshhold):
                
                found = node
                break
            
            visited[tuple(node)] = True
            for dx, dy, dz in zip(adjX, adjY, adjZ):
                newNode = AStarNode(node.x+dx, node.y+dy, node.z+dz)
                #if tuple(newNode) in visited:
                #    continue
                
                
                try:
                    blockType = self[newNode]
                except BlockNotLoadedError:
                    newNode.available = False
                    if not acceptIncomplete:
                        continue
                else:
                    if blockType not in BLOCKS_WALKABLE:
                        continue
                
                #Make sure the player can get through, player is 2 blocks vertically
                try:
                    if self[newNode.x, newNode.y+1, newNode.z] not in BLOCKS_WALKABLE:
                        continue
                except BlockNotLoadedError:
                    pass
                
                #Make sure the block below is not a fence
                try:
                    if self[newNode.x, newNode.y-1, newNode.z] == BLOCK_FENCE:
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
                    
class GameLogic(object):
    def getFace(dx, dy, dz):
        if dy <= 0 and abs(dy) >= abs(dx) and abs(dy) >= abs(dz):
            face = 0
        elif dy >= 0 and abs(dy) >= abs(dx) and abs(dy) >= abs(dz):
            face = 1
        elif dz <= 0 and abs(dz) >= abs(dx) and abs(dz) >= abs(dy):
            face = 2
        elif dz >= 0 and abs(dz) >= abs(dx) and abs(dz) >= abs(dy):
            face = 3
        elif dx <= 0 and abs(dx) >= abs(dy) and abs(dx) >= abs(dz):
            face = 4
        elif dx >= 0 and abs(dx) >= abs(dy) and abs(dx) >= abs(dz):
            face = 5
        else:
            print "wtf face"
            face = 1
        return face
    
    def itemCanHarvestBlock(self, item, block):
        #TODO: Complete
        
        #if block not in MATERIAL_ROCK | MATERIAL_IRON | frozenset([BLOCK_SNOWBLOCK, BLOCK_SNOW]):
        #    return True
        if item in ITEMS_TOOLS:
            level = ITEMS_TOOLLEVEL[item]
        if item in ITEMS_PICKAXE:
            if block == BLOCK_OBSIDIAN: return level == 3
            if block in (BLOCK_DIAMONDBLOCK, BLOCK_DIAMONDORE): return level >= 2
            if block in (BLOCK_GOLDBLOCK, BLOCK_GOLDORE): return level >= 2
            if block in (BLOCK_IRONBLOCK, BLOCK_IRONORE): return level >= 1
            if block in (BLOCK_REDSTONEORE, BLOCK_REDSTONEORE2): return level >= 2
            return block in MATERIAL_ROCK | MATERIAL_IRON
        return False
    
    def itemStrVsBlock(self, item, block):
        #TODO: Complete
        
        if item in ITEMS_TOOLS:
            level = ITEMS_TOOLLEVEL[item]
        if item in ITEMS_PICKAXE:
            if block in frozenset([
                BLOCK_COBBLESTONE,
                BLOCK_STAIR,
                BLOCK_DOUBLESTAIR,
                BLOCK_STONE,
                BLOCK_MOSSYCOBBLESTONE,
                BLOCK_IRONORE,
                BLOCK_STEELBLOCK,
                BLOCK_COALORE,
                BLOCK_GOLDBLOCK,
                BLOCK_GOLDORE,
                BLOCK_DIAMONDORE,
                BLOCK_DIAMONDBLOCK,
                BLOCK_ICE,
                BLOCK_BLOODSTONE]): return (level+1)*2
        
        return 1
    
    def calcHitsToBreakBlock(self, item, block):
        if block in BLOCKS_HARDNESS:
            hardness = BLOCKS_HARDNESS[block]
        else:
            hardness = 1
        
        if hardness == 0: return 1
        
        if self.itemCanHarvestBlock(item, block):
            damagePerHit = self.itemStrVsBlock(item, block) / hardness / 30
        else:
            damagePerHit = 1 / hardness / 100
        
        return int(1/damagePerHit + 2)

gamelogic = GameLogic()