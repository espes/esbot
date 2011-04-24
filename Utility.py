#MineBot
#GPL and all that
# - espes

from __future__ import division

import logging
from math import floor, ceil

from constants import *


def ifloor(n):
    return int(floor(n))
def iceil(n):
    return int(ceil(n))

inf = float("inf")

class Point(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z
    def mag(self):
        try:
            return (self.x**2+self.y**2+self.z**2)**0.5
        except OverflowError:
            return inf
    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z
    def __repr__(self):
        return "Point(x=%r, y=%r, z=%r)" % tuple(self)
    def __add__(self, other):
        try: ox, oy, oz = other
        except TypeError: ox, oy, oz = other, other, other
        return Point(self.x+ox, self.y+oy, self.z+oz)
    def __iadd__(self, other):
        try: ox, oy, oz = other
        except TypeError: ox, oy, oz = other, other, other
        self.x += ox
        self.y += oy
        self.z += oz
    def __sub__(self, other):
        try: ox, oy, oz = other
        except TypeError: ox, oy, oz = other, other, other
        return Point(self.x-ox, self.y-oy, self.z-oz)
    def __isub__(self, other):
        try: ox, oy, oz = other
        except TypeError: ox, oy, oz = other, other, other
        self.x -= ox
        self.y -= oy
        self.z -= oz
    def __mul__(self, other):
        try: ox, oy, oz = other
        except TypeError: ox, oy, oz = other, other, other
        return Point(self.x*ox, self.y*oy, self.z*oz)
    def __imul__(self, other):
        try: ox, oy, oz = other
        except TypeError: ox, oy, oz = other, other, other
        self.x *= ox
        self.y *= oy
        self.z *= oz
    def __div__(self, other):
        try: ox, oy, oz = other
        except TypeError: ox, oy, oz = other, other, other
        return Point(self.x/ox, self.y/oy, self.z/oz)
    def __idiv__(self, other):
        try: ox, oy, oz = other
        except TypeError: ox, oy, oz = other, other, other
        self.x /= ox
        self.y /= oy
        self.z /= oz
    def __abs__(self):
        return Point(abs(self.x), abs(self.y), abs(self.z))
    
    #fail :\
    def __cmp__(self, other):
        return tuple(self).__cmp__(tuple(other))
    def __lt__(self, other):
        return tuple(self).__lt__(tuple(other))
    def __le__(self, other):
        return tuple(self).__le__(tuple(other))
    def __eq__(self, other):
        return tuple(self).__eq__(tuple(other))
    def __ne__(self, other):
        return tuple(self).__ne__(tuple(other))
    def __gt__(self, other):
        return tuple(self).__gt__(tuple(other))
    def __ge__(self, other):
        return tuple(self).__ge__(tuple(other))
    
    #only use if you're sure it's not going to be modified
    def __hash__(self):
        return tuple(self).__hash__()
    


class Entity(object):
    def __init__(self, id, pos):
        self.id, self.pos = id, pos
    def __repr__(self):
        return "Entity(id=%r, pos=%r)" % (self.id, self.pos)
class Mob(Entity):
    def __init__(self, id, pos, type):
        Entity.__init__(self, id, pos)
        self.type = type
    def __repr__(self):
        return "Mob(id=%r, pos=%r, type=%r)" % (self.id, self.pos, self.type)
class Player(Entity):
    def __init__(self, id, pos, name):
        Entity.__init__(self, id, pos)
        self.name = name
    def __repr__(self):
        return "Player(id=%r, pos=%r, name=%r)" % (self.id, self.pos, self.name)
class Pickup(Entity):
    def __init__(self, id, pos, item):
        Entity.__init__(self, id, pos)
        self.item = item
    def __repr__(self):
        return "Pickup(id=%r, pos=%r, item=%r)" % (self.id, self.pos, self.item)
class WorldObject(Entity):
    def __init__(self, id, pos, type):
        Entity.__init__(self, id, pos)
        self.type = type
    def __repr__(self):
        return "WorldObject(id=%r, pos=%r, type=%r)" % (self.id, self.pos, self.type)

class Item(object):
    def __init__(self, itemId, count, health):
        self.itemId, self.count, self.health = itemId, count, health
    def __iter__(self):
        yield self.itemId
        yield self.count
        yield self.health
    def __repr__(self):
        return "Item(itemId=%r, count=%r, health=%r)" % (self.itemId, self.count, self.health)

class MapPlayer(object):
    def __init__(self, name, pos):
        self.name, self.pos = name, pos
    def __repr__(self):
        return "MapPlayer(name=%r, pos=%r)" % (self.name, self.pos)
                    
class GameLogic(object):
    def getFace(self, dx, dy, dz):
        #Assumes facing at center of the block
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
            logging.error("wtf face")
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
            if block in (
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
                BLOCK_BRIMSTONE): return (level+1)*2
        
        return 1
    
    def calcHitsToBreakBlock(self, client, block, item=None):
        if item is None:
            item = client.playerInventory.equippedItem or -1
        
        #since items are not fully implemented
        item = -1
        
        if block in BLOCKS_HARDNESS:
            hardness = BLOCKS_HARDNESS[block]
        else:
            hardness = 1
        
        if hardness == 0: return 1
        
        if self.itemCanHarvestBlock(item, block):
            strength = self.itemStrVsBlock(item, block)
            if client.map[client.pos + (0, 1, 0)] in (BLOCKS_WATER, BLOCKS_STATIONARYWATER):
                strength /= 5
            damagePerHit = strength / hardness / 30
        else:
            damagePerHit = 1 / hardness / 100
        
        
        return int(1/damagePerHit + 2) #Add 2 to be safe
    
    def maxStack(self, itemId):
        if itemId in ITEMS_UNSTACKABLE:
            return 1
        if itemId in ITEMS_SPECIALSTACKS:
            return ITEMS_SPECIALSTACKS[itemId]
        return 64

gamelogic = GameLogic()