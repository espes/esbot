#Minebot
#GPL and all that
# - espes

from __future__ import division

import time
import urllib
import logging
from collections import defaultdict
from twisted.internet import reactor, protocol
from twisted.python import log

from packets import *

from DataBuffer import DataBuffer

from settings import *

class MCBaseClientProtocol(protocol.Protocol):
    def sendPacked(self, mtype, *args):
        fmt = PACKET_FORMATS[mtype]
        
        #self.transport.write(chr(mtype) + fmt.encode(*args))
        reactor.callFromThread(self.transport.write, chr(mtype) + fmt.encode(*args))
    
    def addPacketHandlers(self, handlers):
        for packetType, func in handlers.iteritems():
            self.packetHandlers[packetType].append(func)
    
    def connectionMade(self):
        self.buffer = ""
        
        self.packetHandlers = defaultdict(list)
        self.addPacketHandlers({
           PACKET_KEEPALIVE: self._handleKeepAlive,
           PACKET_LOGIN: self._handleLogin,
           PACKET_HANDSHAKE: self._handleHandshake,
           PACKET_CHAT: self._handleChat,
           PACKET_DISCONNECT: self._handleDisconnect
        })
        
        self.sendPacked(PACKET_HANDSHAKE, self.factory.username)
        
        #interesting benchmark stuffs
        self.counter = 0
        self.lastCountTime = time.time()
        self.totalData = 0
        from collections import Counter
        self.packetCounts = Counter()

    def connectionLost(self, reason):
        pass
        
    def dataReceived(self, data):
        self.buffer += data
        self.totalData += len(data)
        
        parseBuffer = DataBuffer(self.buffer)
        while parseBuffer.lenLeft() > 0:
            packetType = ord(parseBuffer.read(1))
            
            #logging.debug("packet 0x%x" % (packetType,))
            try:
                format = PACKET_FORMATS[packetType]
            except KeyError:
                logging.error("invalid packet type - 0x%x %r %r" % (packetType,
                    len(self.buffer), self.buffer))
                logging.error("last 0x%x" % (self.lastPacket,))
                self.transport.loseConnection()
                return
            
            try:
                parts = list(format.decode(parseBuffer) or [])
            except IncompleteDataError:
                break
            self.buffer = parseBuffer.peek()
            
            
            #interesting benchmark stuffs
            self.packetCounts[packetType] += 1
            self.counter += 1
            if self.counter % 1000 == 0:
                d = time.time()-self.lastCountTime
                logging.debug("1000 in %r - %r packets/s - %r kB/s" % (d, 1000/d, self.totalData/1000/d))
                logging.debug(repr(self.packetCounts.most_common(5)))
                self.lastCountTime = time.time()
                self.totalData = 0
                self.packetCounts.clear()
            
            self.lastPacket = packetType
            
            for handler in self.packetHandlers[packetType]:
                try:
                    ret = handler(parts)
                    if ret == False:
                        return
                except Exception as ex:
                    logging.error("Exception in handling packet 0x%02x:" % (packetType,))
                    logging.exception(ex)
    def _handleKeepAlive(self, parts):
        id, = parts
        self.sendPacked(PACKET_KEEPALIVE, id)
    def _handleLogin(self, parts):
        id, name, mapSeed, mode, dimension, unk, height, plaers = parts
        logging.info("Server login %r" % (parts,))
    def _handleHandshake(self, parts):
        serverId, = parts

        logging.info("Handshake: %r" % serverId)
        if ENABLE_AUTH:
            logging.info("Authing...")
            params = urllib.urlencode({
                'user': self.factory.username,
                'sessionId': self.factory.sessionId,
                'serverId': serverId
            })
        
            f = urllib.urlopen("http://www.minecraft.net/game/joinserver.jsp?%s" % params)
            ret = f.read()
            if ret == "Bad login":
                logging.error(ret)
                self.transport.loseConnection()
                return False
            
            logging.debug(repr(ret))
        
            logging.info("Done")

        self.sendPacked(PACKET_LOGIN, 17, self.factory.username, 0, 0, 0, 0, 0, 0)
    def _handleChat(self, parts):
        message, = parts
        logging.info("Chat\t%r" % message)
    def _handleDisconnect(self, parts):
        reason, = parts
        logging.info("Disconnect! - %r" % reason)

        self.transport.loseConnection()
        return False