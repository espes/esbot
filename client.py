#!/usr/bin/env python2.6

#MineBot
#GPL and all that
# - espes


import urllib
import logging

from twisted.internet import reactor
from twisted.python import log

from BotProtocol import BotFactory
from Interface import CommandLineBotInterface, runReactorWithTerminal


#twisted idiom fail, yeah
def main():
    logging.basicConfig(filename="client.log", level=logging.DEBUG)
    observer = log.PythonLoggingObserver()
    observer.start()
    
    from sys import argv
    from getpass import getpass
    
    loginname = argv[1]
    
    botname = None
    if len(argv) >= 3:
        botname = argv[2]
    
    password = getpass()
    
    logging.info("Logging in")
    params = urllib.urlencode({'user': loginname, 'password': password, 'version': 9001})
    handler = urllib.urlopen("http://www.minecraft.net/game/getversion.jsp", params)
    ret = handler.read()
    if ret == "Bad login":
        logging.error(ret)
        return -1
    
    version, downloadTicket, username, sessionId, _ = ret.split(":")
    logging.info("Got %r %r %r %r" % (version, downloadTicket, username, sessionId))
    
    interfaceNamespace = {}
    
    f = BotFactory(username, sessionId, botname, interfaceNamespace)
    reactor.connectTCP("127.0.0.1", 25565, f)
    
    #start with a null oberserver to remove DefaultObserver
    #because we can't stderr in a terminal
    log.startLoggingWithObserver(lambda a: '')
    runReactorWithTerminal(CommandLineBotInterface, interfaceNamespace)
    
    

if __name__ == '__main__':
    main()
