#MineBot
#GPL and all that
# - espes

from __future__ import division
import thread
from twisted.internet import reactor, protocol

from packets import *
from BotClient import *

from MCProtocol import MCBaseClientProtocol
class BotProtocol(MCBaseClientProtocol):
    def connectionMade(self):
        MCBaseClientProtocol.connectionMade(self)
        
        self.client = BotClient(self, self.factory.botname)
        
        if self.factory.interfaceNamespace is not None:
            self.factory.interfaceNamespace[self.factory.botname] = self.client
    
    def _handleLogin(self, parts):
        MCBaseClientProtocol._handleLogin(self, parts)
        
        #Start main client "tick" loop
        reactor.callInThread(self.client.run)
        reactor.addSystemEventTrigger('before', 'shutdown', self.client.stop)

class BotFactory(protocol.ClientFactory):#ReconnectingClientFactory
    protocol = BotProtocol

    def __init__(self, username, sessionId, botname=None, interfaceNamespace=None):
        self.username = username
        self.sessionId = sessionId

        if botname is None:
            self.botname = username
        else:
            self.botname = botname

        self.interfaceNamespace = interfaceNamespace

    def clientConnectionFailed(self, connector, reason):
        logging.error("Connection failed.")
        if reactor.running: reactor.stop()

    def clientConnectionLost(self, connector, reason):
        logging.error("Connection terminated.")
        if reactor.running: reactor.stop()