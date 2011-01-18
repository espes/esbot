#MineBot
#GPL and all that
# - espes

from __future__ import division

import re
import time
import math
import thread, threading

import urllib
import json

from SimpleXMLRPCServer import SimpleXMLRPCServer

from pymclevel import nbt
import gzip, StringIO

from constants import *
from Utility import *

#unneeded
from Builder import Builder


class MCFancyClient(object):
    def __init__(self, protocol):
        self.protocol = protocol
        
        self.players = {}
        self.spawnPos = Point(-1, -1, -1)
        self.pos = Point(-1, -1, -1)
        self.headY = -1
        self.hp = -1
        
        self.lookTarget = None
        
        self.mapPlayers = {}
        #self._mapPlayersUpdate()
        
        self.map = Map()
        
        self.speed = 6#block/s
        self.targetTick = 0.2
        
        self.commandQueue = []
    def _mapPlayersUpdate(self):
        try:
            h = urllib.urlopen("http://maps.mcau.org/markers")
            self.mapPlayers = {}
            for item in json.loads(h.read()):
                if item['id'] == 4:
                    self.mapPlayers[item['msg']] = MapPlayer(item['msg'],
                        Point(item['x'], item['y'], item['z']))
        except:
            pass
        self.mapPlayersUpdateTimer = threading.Timer(6, self._mapPlayersUpdate)
        self.mapPlayersUpdateTimer.start()
        
    def command_followEntity(self, entityId): #Only works on players ATM
        while True:
            try:
                pos = self.players[entityId].pos
            except KeyError:
                yield False
                return
            
            for v in self.command_walkPathToPoint(pos, True, 4):
                yield v
                #if v == False:
                #    return
    def command_walkPathToPoint(self, targetPoint, lookTowardsWalk=False, threshhold=None):
        while True:
            found = True
            #print "finding path"
            try:
                path, complete = self.map.findPath(self.pos, targetPoint, True, threshhold)
                if path is None:
                    print "findpath failed"
                    yield False
                    return
            except (AssertionError, TimeoutError):
                print "findpath failed"
                yield False
                return
            
            for i, point in enumerate(path):
                #This shouldn't fail, as points in the path should be close enough to the player
                #But sometimes it does.
                try:
                    if self.map[point] not in BLOCKS_WALKABLE:
                        found = False
                        break
                except BlockNotLoadedError:
                    #Find a new path and hope it doesn't happen again
                    found = False
                    break
                
                #if 0<i<len(path)-1 and ( \
                #    (path[i-1].x==point.x==path[i+1].x and path[i-1].y==point.y==path[i+1].y) or \
                #    (path[i-1].x==point.x==path[i+1].x and path[i-1].z==point.z==path[i+1].z) or \
                #    (path[i-1].y==point.y==path[i+1].y and path[i-1].z==point.z==path[i+1].z) ):
                #    continue
                for v in self.command_moveTowards(point, lookTowardsWalk): yield v
            
            if found and complete:
                return

    def command_moveTowards(self, position, lookTowardsWalk=False, threshold=0.1, speed=None):
        
        if speed is None:
            speed = self.speed
        
        while ((position.x-self.pos.x)**2+\
                (position.y-self.pos.y)**2+\
                (position.z-self.pos.z)**2)**0.5 > threshold:
            
            dx = position.x - self.pos.x
            dy = position.y - self.pos.y
            dz = position.z - self.pos.z
            
            highest = max(map(abs, (dx, dy, dz)))
            dmx = (dx/highest)*speed*self.targetTick
            dmy = (dy/highest)*speed*self.targetTick
            dmz = (dz/highest)*speed*self.targetTick
            if abs(dx) < abs(dmx): dmx = dx
            if abs(dy) < abs(dmy): dmy = dy
            if abs(dz) < abs(dmz): dmz = dz
            self.pos = Point(self.pos.x+dmx, self.pos.y+dmy, self.pos.z+dmz)
            self.headY = self.pos.y+1.62
            
            lookTarget = self.lookTarget or (lookTowardsWalk and position)
            if lookTarget:
                horizontalDistance = ((lookTarget.x-self.pos.x)**2+(lookTarget.z-self.pos.z)**2)**0.5
                direction = math.degrees(math.atan2(lookTarget.z-self.pos.z, lookTarget.x-self.pos.x))-90
                pitch = -math.degrees(math.atan2(lookTarget.y-self.headY, horizontalDistance))
                
                self.protocol.sendPacked(TYPE_PLAYERPOSITIONLOOK, self.pos.x, self.pos.y, self.headY, self.pos.z, direction, pitch, 1)
            else:
                self.protocol.sendPacked(TYPE_PLAYERPOSITION, self.pos.x, self.pos.y, self.headY, self.pos.z, 1)
            
            yield True
    
    def lookAt(self, position):
        dx = position.x - self.pos.x
        dy = position.y - self.headY
        dz = position.z - self.pos.z
        horizontalDistance = (dx**2+dz**2)**0.5
        direction = math.degrees(math.atan2(dz, dx))-90
        pitch = -math.degrees(math.atan2(dy, horizontalDistance))
        
        self.protocol.sendPacked(TYPE_PLAYERLOOK, direction, pitch, 1)
    
    def breakBlock(self, position):
        position = Point(*map(ifloor, position))
        self.lookAt(Point(position.x+0.5, position.y+0.5, position.z+0.5))
        
        block = self.map[position]
        if block in BLOCKS_UNBREAKABLE: return
        hits = gamelogic.calcHitsToBreakBlock(-1, block)
        
        dx, dy, dz = self.pos - position
        face = gamelogic.getFace(dx, dy, dz)
        
        print "break", hits, face
        
        for i in xrange(hits):
            self.protocol.sendPacked(TYPE_PLAYERBLOCKDIG, 1, position.x, position.y, position.z, face)
        
        self.protocol.sendPacked(TYPE_PLAYERBLOCKDIG, 3, position.x, position.y, position.z, face)
        self.protocol.sendPacked(TYPE_PLAYERBLOCKDIG, 2, position.x, position.y, position.z, face)
        
        self.map[tuple(position)] = BLOCK_AIR
        
    def placeBlock(self, position, type):
        position = Point(*map(ifloor, position))
        self.lookAt(Point(position.x+0.5, position.y+0.5, position.z+0.5))
        
        #TODO: Fix
        #self.protocol.sendPacked(TYPE_PLAYERBLOCKPLACE, type, position.x, position.y-1, position.z, 1)
        try:
            self.map[position.x, position.y, position.z] = type
        except BlockNotLoadedError:
            print "wtf"
    def run(self):
        while True:
            startTime = time.time()
            
            #self.protocol.sendPacked(TYPE_PLAYERONGROUND, 1)
            
            if len(self.commandQueue) > 0:
                try:
                    self.commandQueue[0].next()
                except StopIteration:
                    self.commandQueue.pop(0)
            
            endTime = time.time()
            timeDiff = endTime-startTime
            if timeDiff < self.targetTick:
                time.sleep(self.targetTick-timeDiff)
            else:
                print "too slow! O.o"


from MCProtocol import MCBaseClientProtocol
class MCFancyClientProtocol(MCBaseClientProtocol):
    def connectionMade(self):
        MCBaseClientProtocol.connectionMade(self)
        
        self.packetHandlers.update({
            TYPE_SPAWNPOSITION: self._handleSpawnPosition,
            TYPE_PLAYERHEALTH: self._handlePlayerHealth,
            TYPE_PLAYERPOSITION: self._handlePlayerPosition,
            TYPE_PLAYERPOSITIONLOOK: self._handlePlayerPositionLook,
            
            TYPE_NAMEDENTITYSPAWN: self._handleNamedEntitySpawn,
            TYPE_ENTITYMOVE: self._handleEntityMove,
            TYPE_ENTITYMOVELOOK: self._handleEntityMoveLook,
            TYPE_ENTITYTELEPORT: self._handleEntityTeleport,
            TYPE_DESTROYENTITY: self._handleDestroyEntity,
            
            TYPE_PRECHUNK: self._handlePreChunk,
            TYPE_CHUNK: self._handleChunk,
            TYPE_BLOCKCHANGE: self._handleBlockChange,
            TYPE_COMPLEXENTITY: self._handleComplexEntity,
            TYPE_MULTIBLOCKCHANGE: self._handleMultiBlockChange,
        })
        
        self.client = MCFancyClient(self)
        
        rpcServer = SimpleXMLRPCServer(('', 1120), allow_none=True)
        rpcServer.register_introspection_functions()
        rpcServer.register_instance(self, allow_dotted_names=True)
        thread.start_new_thread(rpcServer.serve_forever, ())
    
    #for rpc debug purposes.
    def tmpEvl(self, exp):
        return repr(eval(exp, globals(), locals()))
    def tmpExc(self, exp):
        exec exp
    
    def _handleLogin(self, parts):
        MCBaseClientProtocol._handleLogin(self, parts)
        
        #baconbot
        #self.sendPacked(TYPE_ITEMSWITCH, ITEM_COOKEDMEAT)
        
        #
        thread.start_new_thread(self.client.run, ())
        
    def _handleChat(self, parts):
        MCBaseClientProtocol._handleChat(self, parts)
        
        message, = parts
        
        #Baconbot
        commandMatch = re.match("<?(?:\xC2\xA7.)*(.*?):?(?:\xC2\xA7.)*>?\\s*"+self.factory.botname+"[,.:\\s]\\s*(.*)\\s*", message)
        if commandMatch:
            name = commandMatch.group(1)
            #if name != "espes":
            #    return
            command = commandMatch.group(2)
            
            print "Command", repr(command)
            matchBacon = re.match(r"gimm?eh? (fried )?bacon", command)
            if matchBacon:
                print "Giving bacon"
                if matchBacon.group(1) is not None:
                    item = ITEM_COOKEDMEAT
                else:
                    item = ITEM_MEAT
                
                player = None
                for player_ in self.client.players.itervalues():
                    if player_.name == name:
                        player = player_
                        break
                else:
                    if name in self.client.mapPlayers:
                        player = self.client.mapPlayers[name]
                
                if player:
                    x, y, z = player.pos
                    self.sendPacked(TYPE_PICKUPSPAWN, 0, item, 1, 400, x*32, y*32, z*32, 0, 0, 0)
            
            warpMatch = re.match(r"warp\s+(.*)\s*", command)
            if warpMatch:
                self.sendPacked(TYPE_CHAT, "/warp %s" % warpMatch.group(1))
            followMatch = re.match(r"follow\s+([a-zA-Z0-9]+)\s*", command)
            if followMatch:
                followName = followMatch.group(1).strip().lower()
                if followName == "me":
                    followName = name.lower()
                
                for player in self.client.players.itervalues():
                    if player.name.lower() == followName:
                        print "following", followName
                        for c in self.client.commandQueue:
                            if c.__name__ == self.client.command_followEntity.__name__:
                                self.client.commandQueue.remove(c)
                        self.client.commandQueue.append(self.client.command_followEntity(player.id))
                        break
                else:
                    print "couldn't find", followName
                    self.sendPacked(TYPE_CHAT, "I'm afraid I cannot do that, %s" % name)
            elif command == "quit following":
                print "quit following"
                for c in self.client.commandQueue:
                    if c.__name__ == self.client.command_followEntity.__name__:
                        self.client.commandQueue.remove(c)
            elif command == "come here":
                for player in self.client.players.itervalues():
                    if player.name == name:
                    #if player.name in name:
                        def walkCommand(pos, name):
                            for v in self.client.command_walkPathToPoint(pos):
                                yield v
                                if v == False:
                                    #print "I'm afraid I cannot do that, %s" % name
                                    self.sendPacked(TYPE_CHAT, "I'm afraid I cannot do that, %s" % name)
                                    return
                        print "adding", name
                        self.client.commandQueue.append(walkCommand(player.pos, name))
            elif command == "spawn":
                self.commandQueue = []
                self.followingEntityId = None
                self.sendPacked(TYPE_CHAT, "/spawn")
            
    
    
    def _handleSpawnPosition(self, parts):
        self.client.spawnPos = Point(*parts)
    
    def _handlePlayerHealth(self, parts):
        hp, = parts
        self.client.hp = hp
    
    def _handlePlayerPosition(self, parts):
        #is the stance and y meant to be backwards?
        x, stance, y, z, onGround = parts
        self.client.pos = Point(x, y, z)
        self.client.headY = stance
        
        self.sendPacked(TYPE_PLAYERPOSITION, x, y, stance, z, 1)
        
    def _handlePlayerPositionLook(self, parts):
        x, stance, y, z, rotation, pitch, onGround = parts
        self.client.pos = Point(x, y, z)
        self.client.headY = stance
        
        self.sendPacked(TYPE_PLAYERPOSITIONLOOK, x, y, stance, z, rotation, pitch, 1)
        
        
    def _handleNamedEntitySpawn(self, parts):
        entityId, name, x, y, z, rotation, pitch, item = parts
        self.client.players[entityId] = Player(entityId, name, Point(x/32, y/32, z/32))
    def _handleEntityMove(self, parts):
        entityId, dx, dy, dz = parts
        if entityId in self.client.players:
            self.client.players[entityId].pos.x += dx / 32
            self.client.players[entityId].pos.y += dy / 32
            self.client.players[entityId].pos.z += dz / 32
    def _handleEntityMoveLook(self, parts):
        entityId, dx, dy, dz, rotation, pitch = parts
        
        if entityId in self.client.players:
            #print "a", rotation
            
            self.client.players[entityId].pos.x += dx / 32
            self.client.players[entityId].pos.y += dy / 32
            self.client.players[entityId].pos.z += dz / 32
    def _handleEntityTeleport(self, parts):
        entityId, x, y, z, rotation, pitch = parts
        if entityId in self.client.players:
            self.client.players[entityId].pos = Point(x/32, y/32, z/32)
    def _handleDestroyEntity(self, parts):
        entityId, = parts
        if entityId in self.client.players:
            del self.client.players[entityId]
    def _handleChunk(self, parts):
        x, y, z, sizeX, sizeY, sizeZ, blockTypes = parts
        #print "chunk", x, y, z, " - ", sizeX, sizeY, sizeZ
        self.client.map.addChunk(Chunk(Point(x, y, z), (sizeX, sizeY, sizeZ), blockTypes))
        
        #print x, y, z, sizeX, sizeY, sizeZ, repr(data[:20])
    def _handlePreChunk(self, parts):
        x, z, mode = parts
        if mode == 0 and (x, 0, z) in self.client.map.chunks:
            #pass
            del self.client.map.chunks[x, 0, z]
    def _handleBlockChange(self, parts):
        x, y, z, type, metaData = parts
        #print "change", x, y, z, type, metaData
        try:
            self.client.map[x, y, z] = type
        except BlockNotLoadedError:
            pass
    def _handleMultiBlockChange(self, parts):
        parts = list(parts)
        chunkX, chunkZ = parts.pop(0)
        blocks = parts
        if (chunkX, 0, chunkZ) in self.client.map.chunks:
            chunk = self.client.map.chunks[chunkX, 0, chunkZ]
            for place, type, metadata in blocks:
                chunk[place] = type
    def _handleComplexEntity(self, parts):
        x, y, z, payload = parts
        
        stringFile = StringIO.StringIO(payload)
        gzipFile = gzip.GzipFile(fileobj = stringFile, mode = 'rb')
        data = gzipFile.read()
        gzipFile.close()
        stringFile.close()
        
        tag = nbt.load(buf=data)
        #print "Complex Entity", x, y, z, tag['id']