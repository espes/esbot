#MineBot
#GPL and all that
# - espes

from __future__ import division

import re
import time
import math
import urllib

from packets import *

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
            PACKET_COMPLEXENTITY: self._handleComplexEntity,
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
        
        #self.mapPlayers = {}
        #self._mapPlayersUpdate()
        
        self.map = Map()
        
        self.inventoryHandler = InventoryHandler(self.protocol)
        self.playerInventory = self.inventoryHandler.windows[0]
        
        self.speed = 6#block/s
        self.targetTick = 0.2
        
        self.running = False
        self.commandQueue = []
    
    #def _mapPlayersUpdate(self):
    #    import json
    #    try:
    #        h = urllib.urlopen("http://maps.mcau.org/markers")
    #        self.mapPlayers = {}
    #        for item in json.loads(h.read()):
    #            if item['id'] == 4:
    #                self.mapPlayers[item['msg']] = MapPlayer(item['msg'],
    #                    Point(item['x'], item['y'], item['z']))
    #    except:
    #        pass
    #    self.mapPlayersUpdateTimer = threading.Timer(6, self._mapPlayersUpdate)
    #    self.mapPlayersUpdateTimer.start()
        
    def command_followEntity(self, entityId):
        while True:
            try:
                pos = self.entities[entityId].pos
            except KeyError:
                logging.error("No entity %d" % entityId)
                yield False
                return
            
            for v in self.command_walkPathToPoint(pos, targetThreshold=4):
                yield v
    def command_walkPathToPoint(self, targetPoint,
                targetThreshold=None,
                destructive=False, blockBreakPenalty=None,
                lookTowardsWalk=False):
        walkableBlocks = BLOCKS_WALKABLE
        if destructive:
            walkableBlocks |= BLOCKS_BREAKABLE
        
        #if (not lookTowardsWalk) and self.lookTarget is None:
        self.lookTarget = targetPoint
        #    self.lookAt(self.lookTarget)
        
        targetPoint = Point(*targetPoint) #Make a copy
        while True:
            found = True
            #print "finding path"
            try:
                #TODO: pathfind in a seperate thread so the main loop isn't blocked
                path, complete = self.map.findPath(self.pos, targetPoint, True, targetThreshold,
                                    destructive=destructive, blockBreakPenalty=None)
                if path is None:
                    logging.error("findpath failed")
                    yield False
                    return
            except (AssertionError, TimeoutError):
                logging.error("findpath failed")
                yield False
                return
            
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
                
                if (not destructive) and 0<i<len(path)-1 and ( \
                    (path[i-1].x==point.x==path[i+1].x and path[i-1].y==point.y==path[i+1].y) or \
                    (path[i-1].x==point.x==path[i+1].x and path[i-1].z==point.z==path[i+1].z) or \
                    (path[i-1].y==point.y==path[i+1].y and path[i-1].z==point.z==path[i+1].z) ):
                    continue
                for v in self.command_moveTowards(point,
                    lookTowardsWalk=lookTowardsWalk,
                    destructive=destructive): yield v
            
            if found and complete:
                return

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
                    self.breakBlock(target)
                    self.breakBlock(target+(0, 1, 0))
                else:
                    self.breakBlock(target+(0, 1, 0))
                    self.breakBlock(target)
                yield True
                    
            
            self.pos = target
            self.headY = self.pos.y+1.62
            
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
    def breakBlock(self, position, hits=None, destroyWalkable=False):
        position = Point(*map(ifloor, position))
        positionCenter = position + (0.5, 0.5, 0.5)
        
        block = self.map[position]
        
        #print "prebreak", position, block
        
        if block in BLOCKS_UNBREAKABLE: return
        if (not destroyWalkable) and block in BLOCKS_WALKABLE: return
        
        self.lookAt(positionCenter)
        
        if hits is None:
            hits = gamelogic.calcHitsToBreakBlock(self, -1, block)
        
        dx, dy, dz = Point(self.pos.x, self.headY, self.pos.z) - positionCenter
        face = gamelogic.getFace(dx, dy, dz)
        
        for i in xrange(hits):
            self.protocol.sendPacked(PACKET_PLAYERBLOCKDIG, 1, position.x, position.y, position.z, face)
        
        self.protocol.sendPacked(PACKET_PLAYERBLOCKDIG, 3, position.x, position.y, position.z, face)
        self.protocol.sendPacked(PACKET_PLAYERBLOCKDIG, 2, position.x, position.y, position.z, face)
        
        self.map[tuple(position)] = BLOCK_AIR
        
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
        #item = self.inventories[0].get(self.equippedSlot)
        
        logging.debug("place %r %r %r" % (position, face, item))
        
        self.protocol.sendPacked(PACKET_PLAYERBLOCKPLACE, position.x, position.y, position.z, face, item)
        
        if self.map[position] in (BLOCK_CHEST, BLOCK_FURNACE, BLOCK_LITFURNACE, BLOCK_CRAFTINGTABLE):
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
    
    def stop(self):
        self.running = False
    def run(self):
        self.running = True
        while self.running:
            startTime = time.time()
            
            self.movedThisTick = False
            
            if len(self.commandQueue) > 0:
                try:
                    v = self.commandQueue[0].next()
                    if v == False: #Something broke
                        self.commandQueue.pop(0)
                except Exception as ex:
                    if isinstance(ex, StopIteration):
                        self.commandQueue.pop(0)
                    else:
                        logging.error("Command Error: command %r raised %r" % (self.commandQueue[0], ex))
                        self.commandQueue.pop(0)
            
            if not self.movedThisTick:
                self.lookAt(self.lookTarget or (self.players and (min(self.players.values(),
                                key=lambda p: (p.pos-self.pos).mag()).pos + (0, 1, 0))) or Point(0, 70, 0))
                #self.protocol.sendPacked(PACKET_PLAYERONGROUND, 1)
            
            endTime = time.time()
            timeDiff = endTime-startTime
            if timeDiff < self.targetTick:
                time.sleep(self.targetTick-timeDiff)
            else:
                logging.info("too slow! O.o")
    
    
    
    def _handleChat(self, parts):
        message, = parts

        #Baconbot
        commandMatch = re.match("<?(?:\xC2\xA7.)*(.*?):?(?:\xC2\xA7.)*>?\\s*%s[,.:\\s]\\s*(.*)\\s*" %
                                    self.botname, message)
        if commandMatch:
            name = commandMatch.group(1)
            #if name != "espes":
            #    return
            command = commandMatch.group(2)

            logging.debug("Command - %r" % command)

            #Disabled because dropping is broken
            """
            matchBacon = re.match(r"gimm?eh? (fried )?bacon", command)
            if matchBacon:
                print "Giving bacon"
                if matchBacon.group(1) is not None:
                    item = ITEM_COOKEDMEAT
                else:
                    item = ITEM_MEAT

                player = None
                for player_ in self.players.itervalues():
                    if player_.name == name:
                        player = player_
                        break
                else:
                    if name in self.mapPlayers:
                        player = self.mapPlayers[name]

                if player:
                    x, y, z = player.pos
                    self.protocol.sendPacked(PACKET_PICKUPSPAWN, 0, item, 1, 400, x*32, y*32, z*32, 0, 0, 0)
            """
            warpMatch = re.match(r"warp\s+(.*)\s*", command)
            if warpMatch:
                self.protocol.sendPacked(PACKET_CHAT, "/warp %s" % warpMatch.group(1))
            followMatch = re.match(r"follow\s+([a-zA-Z0-9]+)\s*", command)
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
                    #self.protocol.sendPacked(PACKET_CHAT, "I'm afraid I cannot do that, %s" % name)
            elif command.lower().startswith("quit following"):
                logging.info("quit following")
                for c in self.commandQueue:
                    if c.__name__ == self.command_followEntity.__name__:
                        self.commandQueue.remove(c)
            elif command.lower() == "come here":
                player = self.getPlayerByName(name)
                if player:
                    def walkCommand(pos, name):
                        for v in self.command_walkPathToPoint(pos):
                            if v == False:
                                logging.error("I'm afraid I cannot do that, %s" % name)
                                #self.protocol.sendPacked(PACKET_CHAT, "I'm afraid I cannot do that, %s" % name)
                                return
                            yield v
                    logging.info("adding follow %r" % name)
                    self.commandQueue.append(walkCommand(player.pos, name))
            elif command.lower() == "spawn":
                self.commandQueue = []
                self.protocol.sendPacked(PACKET_CHAT, "/spawn")
            elif command.lower() == "purge inventory":
                self.commandQueue.append(self.playerInventory.command_purge())



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
    def _handleComplexEntity(self, parts):
        x, y, z, payload = parts

        from pymclevel import nbt
        import gzip, StringIO

        stringFile = StringIO.StringIO(payload)
        gzipFile = gzip.GzipFile(fileobj = stringFile, mode = 'rb')
        data = gzipFile.read()
        gzipFile.close()
        stringFile.close()

        tag = nbt.load(buf=data)
        #print "Complex Entity", x, y, z, tag['id']

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
