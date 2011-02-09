#MineBot
#GPL and all that
# - espes

from __future__ import division
import thread
from twisted.internet import reactor

from packets import *
from BotClient import *

from MCProtocol import MCBaseClientProtocol
class BotProtocol(MCBaseClientProtocol):
    def connectionMade(self):
        MCBaseClientProtocol.connectionMade(self)
        
        self.client = BotClient(self, self.factory.botname)
        
        if self.factory.clientsList is not None:
            self.factory.clientsList.append(self.client)
        
        #from SimpleXMLRPCServer import SimpleXMLRPCServer
        #rpcServer = SimpleXMLRPCServer(('', 1120), allow_none=True)
        #rpcServer.register_introspection_functions()
        #rpcServer.register_instance(self, allow_dotted_names=True)
        #thread.start_new_thread(rpcServer.serve_forever, ())
        
        
    #HACK for rpc debug purposes.
    #def tmpEvl(self, exp):
    #    return repr(eval(exp, globals(), locals()))
    #def tmpExc(self, exp):
    #    exec exp
    
    def _handleLogin(self, parts):
        MCBaseClientProtocol._handleLogin(self, parts)
        
        #Start main client "tick" loop
        reactor.callInThread(self.client.run)
        reactor.addSystemEventTrigger('before', 'shutdown', self.client.stop)
        

        