#MineBot
#GPL and all that
# - espes

from __future__ import division

import re
import time
import math
import urllib

from twisted.internet import task, threads
from twisted.python import log, failure

from packets import *

from Tech import *
from Utility import *
from Inventory import *
from Map import *


class BotClient(object):
    def __init__(self, protocol, botname):
        self.protocol = protocol
        self.botname = botname
        
        protocol.addPacketHandlers({
            PACKET_CHAT: self._handleChat,
            
            PACKET_SPAWNPOSITION: self._handleSpawnPosition,
            PACKET_PLAYERHEALTH: self._handlePlayerHealth,
            PACKET_PLAYERPOSITION: self._handlePlayerPosition,
            PACKET_PLAYERPOSITIONLOOK: self._handlePlayerPositionLook,

            PACKET_MOBSPAWN: self._handleMobSpawn,
            PACKET_NAMEDENTITYSPAWN: self._handleNamedEntitySpawn,
            PACKET_PICKUPSPAWN: self._handlePickupSpawn,
            PACKET_ENTITYMOVE: self._handleEntityMove,
            PACKET_ENTITYMOVELOOK: self._handleEntityMoveLook,
            PACKET_ENTITYTELEPORT: self._handleEntityTeleport,
            PACKET_DESTROYENTITY: self._handleDestroyEntity,

            PACKET_PRECHUNK: self._handlePreChunk,
            PACKET_CHUNK: self._handleChunk,
            PACKET_BLOCKCHANGE: self._handleBlockChange,
            PACKET_MULTIBLOCKCHANGE: self._handleMultiBlockChange,

            PACKET_SETSLOT: self._handleSetSlot,
            PACKET_WINDOWOPEN: self._handleWindowOpen,
            PACKET_WINDOWCLOSE: self._handleWindowClose,
            PACKET_WINDOWITEMS: self._handleWindowItems,
            PACKET_TRANSACTION: self._handleTransaction,
        })
        
        self.entities = {}
        #redundant entity dicts for convenience 
        self.players = {}
        self.pickups = {}
        self.entityDicts = [self.entities, self.players, self.pickups]
        
        self.spawnPos = Point(-1, -1, -1)
        self.pos = Point(-1, -1, -1)
        self.headY = -1
        self.hp = -1
        
        self.lookTarget = None
        
        self.map = Map()
        
        self.inventoryHandler = InventoryHandler(self.protocol)
        self.playerInventory = self.inventoryHandler.windows[0]
        
        self.speed = 6#block/s
        self.targetTick = 0.2
        
        self.runTask = None
        #self.running = False
        self.commandQueue = []
    
    def command_gotoEntity(self, entityId, threshold=2):
        while True:
            try:
                pos = self.entities[entityId].pos
            except KeyError:
                raise Exception, "No entity %d" % entityId
            if (pos-self.pos).mag() <= threshold: break
            for v in self.command_walkPathTo(pos, targetThreshold=threshold): yield v
    def command_followEntity(self, entityId):
        while True:
            try:
                pos = self.entities[entityId].pos
            except KeyError:
                raise Exception, "No entity %d" % entityId
            try:
                for v in self.command_walkPathTo(pos, targetThreshold=4): yield v
            except Exception:
                pass
    def command_walkPathTo(self, targetPoint,
                targetThreshold=None,
                destructive=False, blockBreakPenalty=None,
                lookTowardsWalk=False):
        walkableBlocks = BLOCKS_WALKABLE
        if destructive:
            walkableBlocks |= BLOCKS_BREAKABLE
        
        setLook = False
        if (not lookTowardsWalk) and self.lookTarget is None:
            self.lookTarget = targetPoint
            self.lookAt(self.lookTarget)
            setLook = True
        
        try:
            targetPoint = Point(*targetPoint) #Make a copy
            while True:
                found = True
                #print "finding path"
            
                deferred = threads.deferToThread(self.map.findPath,
                                self.pos, targetPoint, True, targetThreshold,
                                destructive=destructive, blockBreakPenalty=blockBreakPenalty,
                                forClient=self)
                #hack
                while not hasattr(deferred, 'result'):
                    yield True
            
                if isinstance(deferred.result, failure.Failure):
                    logging.error("findpath failed:")
                    log.err(deferred.result)
                    raise Exception, "findpath failed"
            
                path, complete = deferred.result
                if path is None:
                    raise Exception, "findpath failed"
                
                for i, point in enumerate(path):
                    #This shouldn't fail, as points in the path should be close enough to the player
                    #But sometimes it does.
                    try:
                        if self.map[point] not in walkableBlocks:
                            found = False
                            break
                    except BlockNotLoadedError:
                        #Find a new path and hope it doesn't happen again
                        found = False
                        break
                    
                    #if we can get to the next block in the path without hitting something,
                    #skip the current block.
                    if 0<=i<len(path)-1:
                        for offset in [
                                (0, 0, 0),
                                (-0.5, 0, -0.5),  (-0.5, 0, 0.5), (0.5, 0, 0.5), (0.5, 0, -0.5),
                                (-0.5, 2, -0.5),  (-0.5, 2, 0.5), (0.5, 2, 0.5), (0.5, 2, -0.5),]:
                            if self.map.blockInLine(self.pos+offset, path[i+1]+offset, BLOCKS_UNWALKABLE):
                                #logging.debug("broke %r" % (offset,))
                                break
                        else:
                            #make sure we don't float for too long
                            c = 0
                            for pos in self.map.raycast(self.pos, path[i+1]):
                                if self.map[pos+(0, -1, 0)] in BLOCKS_WALKABLE:
                                    c += 1
                                else:
                                    c = 0
                                if c >= 3:
                                    break
                            else:
                                #logging.debug("skip")
                                continue
                    
                    for v in self.command_moveTowards(point,
                        lookTowardsWalk=lookTowardsWalk,
                        destructive=destructive): yield v
            
                if found and complete:
                    return
        finally:
            if setLook:
                self.lookTarget = None

    def command_moveTowards(self, position, lookTowardsWalk=False, threshold=0.1, speed=None, destructive=False):
        if speed is None:
            speed = self.speed
        
        while (position - self.pos).mag() > threshold:
            
            dx, dy, dz = position - self.pos
            
            highest = max(map(abs, (dx, dy, dz)))
            dmx = (dx/highest)*speed*self.targetTick
            dmy = (dy/highest)*speed*self.targetTick
            dmz = (dz/highest)*speed*self.targetTick
            if abs(dx) < abs(dmx): dmx = dx
            if abs(dy) < abs(dmy): dmy = dy
            if abs(dz) < abs(dmz): dmz = dz
            
            target = self.pos + (dmx, dmy, dmz)
            #target = Point(self.pos.x+dmx, self.pos.y+dmy, self.pos.z+dmz)
            
            if destructive:
                #Assume there are no blocks between cur pos and target.
                #i.e. axis aligned path
                #TODO: raycast to destroy blocks
                if dy >= 0:
                    for v in self.command_breakBlock(target): yield v
                    for v in self.command_breakBlock(target+(0, 1, 0)): yield v
                else:
                    for v in self.command_breakBlock(target+(0, 1, 0)): yield v
                    for v in self.command_breakBlock(target): yield v
                    
            
            self.pos = target
            self.headY = self.pos.y+PLAYER_HEIGHT
            
            lookTarget = self.lookTarget or (lookTowardsWalk and position)
            if lookTarget:
                horizontalDistance = ((lookTarget.x-self.pos.x)**2+(lookTarget.z-self.pos.z)**2)**0.5
                direction = math.degrees(math.atan2(lookTarget.z-self.pos.z, lookTarget.x-self.pos.x))-90
                pitch = -math.degrees(math.atan2(lookTarget.y-self.headY, horizontalDistance))
                
                self.protocol.sendPacked(PACKET_PLAYERPOSITIONLOOK,
                    self.pos.x, self.pos.y, self.headY, self.pos.z, direction, pitch, 1)
            else:
                self.protocol.sendPacked(PACKET_PLAYERPOSITION,
                    self.pos.x, self.pos.y, self.headY, self.pos.z, 1)
            
            self.movedThisTick = True
            
            yield True
    
    def lookAt(self, position):
        dx = position.x - self.pos.x
        dy = position.y - self.headY
        dz = position.z - self.pos.z
        horizontalDistance = (dx**2+dz**2)**0.5
        direction = math.degrees(math.atan2(dz, dx))-90
        pitch = -math.degrees(math.atan2(dy, horizontalDistance))
        
        self.protocol.sendPacked(PACKET_PLAYERLOOK, direction, pitch, 1)
    
    #must have line-of-sight to center of block
    def command_breakBlock(self, position, hits=None, destroyWalkable=False):
        position = Point(*map(ifloor, position))
        positionCenter = position + (0.5, 0.5, 0.5)
        
        block = self.map[position]
        
        if block in BLOCKS_UNBREAKABLE: return
        if (not destroyWalkable) and block in BLOCKS_WALKABLE: return
        
        self.lookAt(positionCenter)
        
        if hits is None:
            hits = gamelogic.calcHitsToBreakBlock(self, block)
        
        dx, dy, dz = Point(self.pos.x, self.headY, self.pos.z) - positionCenter
        face = gamelogic.getFace(dx, dy, dz)
        
        self.protocol.sendPacked(PACKET_PLAYERBLOCKDIG, 0, position.x, position.y, position.z, face)
        startTime = time.time()
        for i in xrange(hits):
            self.protocol.sendPacked(PACKET_PLAYERBLOCKDIG, 1, position.x, position.y, position.z, face)
            if i%10:
                self.protocol.sendPacked(PACKET_ANIMATION, 0, 1)
            while time.time()-startTime < i/20: yield True
        
        self.protocol.sendPacked(PACKET_PLAYERBLOCKDIG, 3, position.x, position.y, position.z, face)
        self.protocol.sendPacked(PACKET_PLAYERBLOCKDIG, 2, position.x, position.y, position.z, face)
        
        self.map[position] = BLOCK_AIR
        
    def placeBlock(self, againstBlock):
        position = Point(*map(ifloor, againstBlock))
        positionCenter = position + (0.5, 0.5, 0.5)
        self.lookAt(positionCenter)
        
        face = gamelogic.getFace(*(self.pos-positionCenter))
        facesPos = [ #TODO: Put into constants
            (0, -1, 0),
            (0, 1, 0),
            (0, 0, -1),
            (0, 0, 1),
            (-1, 0, 0),
            (1, 0, 0)
        ]
        
        #assert self.inventoryHandler.currentWindow == self.playerInventory
        if self.inventoryHandler.currentWindow is not self.playerInventory:
            self.inventoryHandler.closeWindow()
        
        item = self.playerInventory.equippedItem
        
        logging.debug("place %r %r %r" % (position, face, item))
        
        self.protocol.sendPacked(PACKET_PLAYERBLOCKPLACE, position.x, position.y, position.z, face, item)
        
        if self.map[position] in (BLOCK_CHEST, BLOCK_FURNACE, BLOCK_BURNINGFURNACE, BLOCK_WORKBENCH):
            #activating, not placing
            return True
        
        if item is not None and item.itemId in BLOCKS:
            targetPos = position + facesPos[face]
            targetBlock = self.map[targetPos]
            self.map[targetPos] = item.itemId
        
        return True
    
    def getPlayerByName(self, name, fuzzy=False):
        for player in self.players.itervalues():
            if (fuzzy and player.name.lower() == name.lower()) or player.name == name:
                return player
        return None
    
    def queueCommand(self, command):
        self.commandQueue.append(command)
    def cancelCommand(self):
        if len(self.commandQueue) > 0:
            self.commandQueue.pop(0)
    def currentCommand(self):
        if len(self.commandQueue) > 0:
            return self.commandQueue[0]
        return None
    
    def parseCommand(self, name, command):
        logging.debug("Command - %r" % command)

        warpMatch = re.match(r"warp\s+(.*)\s*", command, re.IGNORECASE)
        if warpMatch:
            self.say("/warp %s" % warpMatch.group(1))
        followMatch = re.match(r"follow\s+([a-zA-Z0-9]+)\s*", command, re.IGNORECASE)
        if followMatch:
            followName = followMatch.group(1).strip().lower()
            if followName == "me":
                followName = name.lower()

            player = self.getPlayerByName(followName, True)
            if player:
                #remove existing follow commands
                for c in self.commandQueue:
                    if c.__name__ == self.command_followEntity.__name__:
                        self.commandQueue.remove(c)
                self.commandQueue.append(self.command_followEntity(player.id))
            else:
                logging.error("couldn't find %r" % followName)
                #self.say("I'm afraid I cannot do that, %s" % name)
        fetchMatch = re.match(r"(?:gimm?eh?|get meh?)\s+(?:(?:a|(?P<count>\d+))\s+)?(?P<item>[a-zA-Z0-9]+)\s*", command,
            re.IGNORECASE)
        if fetchMatch:
            player = self.getPlayerByName(name)
            itemName = fetchMatch.groupdict()['item']
            count = fetchMatch.groupdict()['count']
            if count is None: count = 1
            else: count = int(count)
            
            if itemName not in BLOCKITEM_LOOKUP:
                logging.error("no item %r" % (fetchMatch.group(1),))
            elif player:
                def fetchItemCommand(itemId, entityId):
                    if itemId not in TECH_MAP:
                        raise Exception, "%r not in tech tree" % (BLOCKITEM_NAMES[itemId],)
                    if self.playerInventory.countPlayerItemId(itemId) < count:
                        evalCount = (count-self.playerInventory.countPlayerItemId(itemId))/TECH_MAP[itemId].produces
                        for v in TECH_MAP[itemId].command_getOrderly(self, iceil(evalCount)): yield v
                    for v in self.command_gotoEntity(entityId): yield v
                    for v in self.playerInventory.command_drop(itemId, count): yield v

                self.queueCommand(fetchItemCommand(BLOCKITEM_LOOKUP[itemName], player.id))
        elif command.lower().startswith("quit following"):
            logging.info("quit following")
            for c in self.commandQueue:
                if c.__name__ == self.command_followEntity.__name__:
                    self.commandQueue.remove(c)
        elif command.lower() == "come here":
            player = self.getPlayerByName(name)
            if player:
                def walkCommand(pos, name):
                    try:
                        for v in self.command_walkPathTo(pos): yield v
                    except Exception:
                        logging.error("I'm afraid I cannot do that, %s" % (name,))
                        #self.say("I'm afraid I cannot do that, %s" % name)
                        raise
                logging.info("going to %r" % name)
                self.queueCommand(walkCommand(player.pos, name))
        elif command.lower() == "respawn" or command.lower() == "spawn":
            self.commandQueue = []
            self.protocol.sendPacked(PACKET_RESPAWN)
        elif command.lower() == "purge inventory":
            self.queueCommand(self.playerInventory.command_purge())
    
    def say(self, stuff):
        self.protocol.sendPacked(PACKET_CHAT, stuff)
    
    def stop(self):
        self.runTask.stop()
    def start(self):
        self.runTask = task.LoopingCall(self.tick)
        self.runTask.start(self.targetTick)
    def tick(self):
        self.movedThisTick = False
        
        #not done init
        if self.pos == (-1, -1, -1):
            return
        
        if len(self.commandQueue) > 0:
            try:
                v = self.commandQueue[0].next()
                if v == False: #Something broke
                    self.commandQueue.pop(0)
            except Exception as ex:
                if isinstance(ex, StopIteration):
                    self.commandQueue.pop(0)
                else:
                    logging.error("Exception in command %r:" % self.commandQueue[0])
                    logging.exception(ex)
                    self.commandQueue.pop(0)
        else:
        #if not self.movedThisTick:
            self.lookAt(self.lookTarget or (self.players and (min(self.players.values(),
                            key=lambda p: (p.pos-self.pos).mag()).pos + (0, PLAYER_HEIGHT, 0))) or Point(0, 70, 0))
            
            try:
                #fall
                if self.map[self.pos + (0, -1, 0)] in BLOCKS_WALKABLE or (self.pos.y % 1) > 0.1:
                    logging.info("falling...")
                    y=0
                    for y in xrange(self.pos.y, -1, -1):
                        if self.map[self.pos.x, y, self.pos.z] not in BLOCKS_WALKABLE:
                            break
                    self.queueCommand(self.command_moveTowards(Point(self.pos.x, y+1, self.pos.z)))
            except BlockNotLoadedError:
                pass
        if not self.movedThisTick:
            pass
            #self.protocol.sendPacked(PACKET_PLAYERONGROUND, 1)
    
    
    
    def _handleChat(self, parts):
        message, = parts

        #Baconbot
        commandMatch = re.match("<?(?:\xC2\xA7.)*(.*?):?(?:\xC2\xA7.)*>?\\s*%s[,.:\\s]\\s*(.*)\\s*" %
                                    self.botname, message, re.IGNORECASE)
        if commandMatch:
            name = commandMatch.group(1)
            #if name != "espes":
            #    return
            command = commandMatch.group(2)
            
            self.parseCommand(name, command)


    def _handleSpawnPosition(self, parts):
        self.spawnPos = Point(*parts)

    def _handlePlayerHealth(self, parts):
        hp, = parts
        logging.info("hp: %r" % hp)
        self.hp = hp

    def _handlePlayerPosition(self, parts):
        #is the stance and y meant to be backwards?
        x, stance, y, z, onGround = parts
        self.pos = Point(x, y, z)
        self.headY = stance

        self.protocol.sendPacked(PACKET_PLAYERPOSITION, x, y, stance, z, 1)

    def _handlePlayerPositionLook(self, parts):
        x, stance, y, z, rotation, pitch, onGround = parts
        self.pos = Point(x, y, z)
        self.headY = stance

        self.protocol.sendPacked(PACKET_PLAYERPOSITIONLOOK, x, y, stance, z, rotation, pitch, 1)

    def _handleMobSpawn(self, parts):
        entityId, type, x, y, z, rotation, pitch, metaData = parts
        self.entities[entityId] = Mob(entityId, Point(x/32, y/32, z/32), type)
    def _handleNamedEntitySpawn(self, parts):
        entityId, name, x, y, z, rotation, pitch, item = parts
        self.entities[entityId] = Player(entityId, Point(x/32, y/32, z/32), name)
        self.players[entityId] = self.entities[entityId]
    def _handlePickupSpawn(self, parts):
        entityId, itemId, count, health, x, y, z, rotation, pitch, roll = parts
        item = Item(itemId, count, health)
        self.entities[entityId] = Pickup(entityId, Point(x/32, y/32, z/32), item)
        self.pickups[entityId] = self.entities[entityId]
    def _handleEntityMove(self, parts):
        entityId, dx, dy, dz = parts
        if entityId in self.entities:
            self.entities[entityId].pos.x += dx / 32
            self.entities[entityId].pos.y += dy / 32
            self.entities[entityId].pos.z += dz / 32
    def _handleEntityMoveLook(self, parts):
        entityId, dx, dy, dz, rotation, pitch = parts

        if entityId in self.entities:
            self.entities[entityId].pos.x += dx / 32
            self.entities[entityId].pos.y += dy / 32
            self.entities[entityId].pos.z += dz / 32
    def _handleEntityTeleport(self, parts):
        entityId, x, y, z, rotation, pitch = parts
        if entityId in self.entities:
            self.entities[entityId].pos = Point(x/32, y/32, z/32)
    def _handleDestroyEntity(self, parts):
        entityId, = parts
        for dct in self.entityDicts:
            if entityId in dct:
                del dct[entityId]
    def _handleChunk(self, parts):
        (x, y, z), (sizeX, sizeY, sizeZ), blockTypes = parts
        #print "chunk", x, y, z, " - ", sizeX, sizeY, sizeZ
        self.map.addChunk(Chunk(Point(x, y, z), (sizeX, sizeY, sizeZ), blockTypes))

        #print x, y, z, sizeX, sizeY, sizeZ, repr(data[:20])
    def _handlePreChunk(self, parts):
        x, z, mode = parts
        if mode == 0 and (x, 0, z) in self.map.chunks:
            #pass
            del self.map.chunks[x, 0, z]
    def _handleBlockChange(self, parts):
        x, y, z, type, metaData = parts
        #print "change", x, y, z, type, metaData
        try:
            self.map[x, y, z] = type
        except BlockNotLoadedError:
            pass
    def _handleMultiBlockChange(self, parts):
        parts = list(parts)
        chunkX, chunkZ = parts.pop(0)
        blocks = parts
        if (chunkX, 0, chunkZ) in self.map.chunks:
            chunk = self.map.chunks[chunkX, 0, chunkZ]
            for place, type, metadata in blocks:
                chunk[place] = type

    def _handleSetSlot(self, parts):
        windowId, slot, item = parts
        logging.debug("Slot %r %r %r" % (windowId, slot, item))

        if item is not None:
            item = Item(*item)
        self.inventoryHandler.onSetSlot(windowId, slot, item)
    def _handleWindowOpen(self, parts):
        windowId, windowType, windowTitle, numSlots = parts
        logging.debug("window open %r" % parts)
        self.inventoryHandler.onWindowOpen(
            windowId, windowType, windowTitle, numSlots)
    def _handleWindowClose(self, parts):
        windowId, = parts
        self.inventoryHandler.onWindowClose(windowId)
    def _handleWindowItems(self, parts):
        windowId, items = parts
        logging.debug("Items %r %r" % (windowId, items))

        for slot, (itemId, count, health) in items.iteritems():
            items[slot] = Item(itemId, count, health)

        self.inventoryHandler.onWindowItems(windowId, items)

        #self.inventories[windowId] = items
    def _handleTransaction(self, parts):
        windowId, actionNumber, accepted = parts
        logging.debug("transaction %r %r %r" % (windowId, actionNumber, accepted))

        self.inventoryHandler.onTransaction(
            windowId, actionNumber, accepted)
