#Minebot
#GPL and all that
# - espes

import urllib
from twisted.internet.protocol import Protocol

from constants import *

class MCBaseClientProtocol(Protocol):
    def sendPacked(self, mtype, *args):
        fmt = TYPE_FORMATS[mtype]
        self.transport.write(chr(mtype) + fmt.encode(*args))
    
    def connectionMade(self):
        self.buffer = ""
        self.counter = 0
        
        self.packetHandlers = {
            TYPE_LOGIN: self._handleLogin,
            TYPE_HANDSHAKE: self._handleHandshake,
            TYPE_CHAT: self._handleChat,
            TYPE_DISCONNECT: self._handleDisconnect
        }
        
        self.otype = None
        
        self.sendPacked(TYPE_HANDSHAKE, self.factory.username)

    def connectionLost(self, reason):
        pass
        
    def dataReceived(self, data):
        self.buffer += data
        while self.buffer:
            type = ord(self.buffer[0])
            print hex(type)
            try:
                format = TYPE_FORMATS[type]
            except KeyError:
                print "invalid packet type"
                print hex(type), len(self.buffer), repr(self.buffer)
                print "last", self.otype
                
                self.transport.loseConnection()
                return
            
            try:
                parts = list(format.decode(self.buffer[1:]))
            except IncompleteDataError:
                break
            dataLength = parts.pop()
            self.buffer = self.buffer[dataLength+1:]
            
            #debug
            self.otype = type
            
            self.counter += 1
            if self.counter % 300 == 0:
                self.sendPacked(TYPE_KEEPALIVE)
            
            if type in self.packetHandlers:
                ret = self.packetHandlers[type](parts)
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
        f = urllib.urlopen("http://www.minecraft.net/game/joinserver.jsp", params)
        f.read()
        print "Done"

        self.sendPacked(TYPE_LOGIN, 8, self.factory.username, "Password", 0, 0)
    def _handleChat(self, parts):
        message, = parts
        #print
        print "Chat", repr(message)
    def _handleDisconnect(self, parts):
        reason, = parts
        print "Disconnect!", reason

        self.transport.loseConnection()
        return False