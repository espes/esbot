#Minebot
#GPL and all that
# - espes

from __future__ import division

import urllib
from collections import defaultdict
from twisted.internet import reactor, protocol

from packets import *

from DataBuffer import DataBuffer

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
        self.counter = 0
        
        self.packetHandlers = defaultdict(list)
        self.addPacketHandlers({
           PACKET_LOGIN: self._handleLogin,
           PACKET_HANDSHAKE: self._handleHandshake,
           PACKET_CHAT: self._handleChat,
           PACKET_DISCONNECT: self._handleDisconnect
        })
        
        self.sendPacked(PACKET_HANDSHAKE, self.factory.username)

    def connectionLost(self, reason):
        pass
        
    def dataReceived(self, data):
        self.buffer += data
        
        parseBuffer = DataBuffer(self.buffer)
        while parseBuffer.lenLeft() > 0:
            packetType = ord(parseBuffer.read(1))
            
            #print "packet", hex(packetType)
            try:
                format = PACKET_FORMATS[packetType]
            except KeyError:
                print "invalid packet type"
                print hex(packetType), len(self.buffer), repr(self.buffer)
                print "last", self.otype
                
                self.transport.loseConnection()
                return
            
            try:
                parts = list(format.decode(parseBuffer) or [])
            except IncompleteDataError:
                break
            self.buffer = parseBuffer.peek()
            
            self.counter += 1
            
            #TODO: send the keepalive at some set interval
            if self.counter % 300 == 0:
                self.sendPacked(PACKET_KEEPALIVE)
            
            for handler in self.packetHandlers[packetType]:
                ret = handler(parts)
                if ret == False:
                    return
    
    def _handleLogin(self, parts):
        id, name, motd, mapSeed, dimension = parts
        print "Server login", id, name, motd, mapSeed, dimension
    def _handleHandshake(self, parts):
        serverId, = parts

        print "Handshake", serverId

        print "Authing..."
        params = urllib.urlencode({
            'user': self.factory.username,
            'sessionId': self.factory.sessionId,
            'serverId': serverId
        })
        f = urllib.urlopen("http://www.minecraft.net/game/joinserver.jsp?%s" % params)
        print repr(f.read())
        
        print "Done"

        self.sendPacked(PACKET_LOGIN, 8, self.factory.username, "Password", 0, 0)
    def _handleChat(self, parts):
        message, = parts
        print "Chat", repr(message)
    def _handleDisconnect(self, parts):
        reason, = parts
        print "Disconnect!", reason

        self.transport.loseConnection()
        return False