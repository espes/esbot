#MineBot
#GPL and all that
# - espes

from __future__ import division

import struct
from collections import defaultdict

from constants import *
from Utility import *


class Builder(object):
    def __init__(self, client):
        self.client = client
        
        #Excluding some that sholdn't be used on a specific server
        #Excluding blocks with gravity
        #TODO: Fix these
        self.blockColours = {
            BLOCK_STONE: (109, 111, 112),
            BLOCK_GRASS: (111, 174, 69),
            BLOCK_DIRT: (113, 84, 62),
            BLOCK_COBBLESTONE: (85, 85, 85),
            BLOCK_WOOD: (170, 138, 85),
            #BLOCK_GOLDORE: (179, 172, 109),
            BLOCK_IRONORE: (115, 115, 115),
            #BLOCK_COALORE: (95, 95, 95),
            BLOCK_LOG: (86, 68, 41),
            #BLOCK_LEAVES: (45, 145, 32),
            #BLOCK_GLASS: (212, 255, 255),
            BLOCK_GREYCLOTH: (229, 229, 229),
            BLOCK_GOLD: (223, 164, 43),
            BLOCK_IRON: (194, 194, 194),
            BLOCK_DIAMOND: (112, 222, 215),
            BLOCK_BRICK: (205, 120, 95),
            #BLOCK_BOOKCASE: (66, 62, 37),
            BLOCK_MOSSYCOBBLESTONE: (117, 133, 117),
            BLOCK_OBSIDIAN: (15, 15, 24),
            BLOCK_CLAY: (147, 153, 164),
            BLOCK_CHEST: (149, 127, 75),
            BLOCK_SNOWBLOCK: (246, 255, 255),
            BLOCK_WORKBENCH: (135, 77, 43),
            BLOCK_TNT: (219, 68, 26),
        }
        
    def command_buildBlocks(self, blocks):
        yPoints = defaultdict(list)
        for point, type in blocks:
            yPoints[point.y].append((point, type))
        
        for y in sorted(yPoints.keys()):
            points = yPoints[y]
            while len(points) > 0:
                buildPoint, type = min(points, key=
                    lambda p: ((p[0].x-self.client.pos.x)**2+\
                        (p[0].y-self.client.pos.y)**2+\
                        (p[0].z-self.client.pos.z)**2)**0.5
                )
                points.remove((buildPoint, type))
                
                try:
                    if self.client.map[buildPoint] != BLOCK_AIR:
                        continue
                except BlockNotLoadedError:
                    pass
                    
                logging.debug("build %r" % buildPoint)
                foundPath = True
                try:
                    for v in self.client.command_walkPathTo( \
                            Point(buildPoint.x, buildPoint.y, buildPoint.z), 3): yield v
                except Exception:
                    logging.error("skipping block")
                    continue
                    
                #Above it anyway, no need to check if it's not air
                self.client.placeBlock(buildPoint, type)
    
    def sphereBlocks(self, center, radius, type):
        center = Point(*map(ifloor, center))
        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):
                for dz in range(-radius, radius+1):
                    #print "ping"
                    x = center.x+dx
                    y = center.y+dy
                    z = center.z+dz
                    d = ifloor((dx**2+dy**2+dz**2)**0.5)
                    if d <= radius:
                        yield Point(x, y, z)
    
    def torisBlocks(self, center, radius, torRadius, type):
        center = Point(*map(ifloor, center))
        totalRadius = radius+torRadius
        for dx in xrange(-totalRadius, totalRadius+1):
            for dy in xrange(-totalRadius, totalRadius+1):
                for dz in xrange(-torRadius, torRadius+1):
                    if (radius-(dx**2+dy**2)**0.5)**2 + dz**2 - torRadius**2 <= 0:
                        yield Point(center.x+dx, center.y+dz, center.z+dy)
                        
    def getBlockForColour(self, colour):
        blockMatch, matchColour = min(self.blockColours.items(),
            key= lambda a: (3*(a[1][0]-colour[0])**2+\
                4*(a[1][1]-colour[1])**2+\
                2*(a[1][2]-colour[2])**2)**0.5
        )
        return blockMatch
    def voxModelBlocks(self, filename, startPos, typeMap=None):
        points = []
        colours = []
        with open(filename,"rb") as voxFile:
            xsiz, ysiz, zsiz = struct.unpack("iii", voxFile.read(4*3))
            for vx in xrange(xsiz):
                for vy in xrange(ysiz):
                    for vz in xrange(zsiz):
                        c, = struct.unpack("B", voxFile.read(1))
                        if c != 0xFF:
                            points.append((Point(startPos.x+vx, startPos.y-vz, startPos.z+vy), c))
            for i in xrange(255):
                r, g, b = struct.unpack("BBB", voxFile.read(3))
                colours.append((r<<2,g<<2,b<<2))
        
        if typeMap is None:
            typeMap = {}
            for i, colour in enumerate(colours):
                typeMap[i] = self.getBlockForColour(colour)
        
        for point, cid in points:
            yield point, typeMap[cid]
    def vxlNrrdModelBlocks(self, filename, startPos):
        import nrrd
        
        n = nrrd.Nrrd(filename)
        for z, zSlice in enumerate(n.data):
            for y, yRow in enumerate(zSlice):
                for x, data in numerate(yRow):
                    used, r, g, b, normal = data
                    if used != 0:
                        yield Point(startPos.x+x, startPos.y-z, startPos.z+y), \
                            self.getBlockForColour((r,g,b))
    
    def command_clearCuboid(self, startPos, dx, dy, dz):
        for x in xrange(startPos.x, startPos.x+dx, dx/abs(dx)):
            for z in xrange(startPos.z, startPos.z+dz, dz/abs(dz)):
                for y in xrange(max(startPos.y, startPos.y+dy), min(startPos.y, startPos.y+dy)-1, -1):
                    try:
                        if self.client.map[x, y, z] in BLOCKS_UNBREAKABLE:
                            continue
                    except BlockNotLoadedError:
                        pass
                    #print ">>", x, y, z
                    
                    try:
                        for v in self.client.command_walkPathTo(Point(x, y+1, z)): yield v
                    except Exception:
                        continue
                       
                    if self.client.map[x, y, z] not in BLOCKS_UNBREAKABLE:
                        for v in self.client.command_breakBlock(Point(x, y, z)): yield v
    def command_buildCuboid(self, startPos, dx, dy, dz, type):
        for x in xrange(startPos.x, startPos.x+dx, dx/abs(dx)):
            for z in xrange(startPos.z, sstartPos.z+dz, dz/abs(dz)):
                for y in xrange(min(startPos.y, startPos.y+dy), max(startPos.y, startPos.y+dy)):
                    try:
                        if self.client.map[x, y, z] != BLOCK_AIR:
                            continue
                    except BlockNotLoadedError:
                        pass
                    
                    foundPath = True
                    try:
                        for v in self.client.command_walkPathTo(Point(x, y+1, z)): yield v
                    except Exception:
                        continue
                    
                    if self.client.map[x, y, z] == BLOCK_AIR:
                        self.client.placeBlock(Point(x, y, z), type)
                        yield True
    def command_buildWall(self, startPos, dx, dz, height, type):
        for x in xrange(startPos.x,  startPos.x+dx, dx/abs(dx)):
            for z in xrange(startPos.z, startPos.z+dz, dz/abs(dz)):
                
                try:
                    #Fix: The may be out of bounds
                    for y in range(127, 0, -1):
                        if self.client.map[x, y, z] != BLOCK_AIR:
                            startY = y
                            break
                except BlockNotLoadedError:
                    #Fix: Make this less crappy
                    
                    try:
                        for v in self.client.command_walkPathTo(Point(x, 127, z)): yield v
                    except Exception:
                        continue
                    for y in range(127, 0, -1):
                         if self.client.map[x, y, z] != BLOCK_AIR:
                             startY = y
                             break
                
                for y in range(startY, height):
                    try:
                        for v in self.client.command_walkPathTo(Point(x, y+1, z)): yield v
                    except Exception:
                        continue
                    
                    self.client.placeBlock(Point(x, y, z), type)
                    yield True

        
    