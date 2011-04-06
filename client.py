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

from settings import *

#twisted idiom fail, yeah
def main():
    logging.basicConfig(filename="client.log", level=logging.DEBUG)
    observer = log.PythonLoggingObserver()
    observer.start()
    
    from sys import argv
    from getpass import getpass
    
    loginname = argv[1]
    server = argv[2]
    port = int(argv[3])
    
    botname = None
    if len(argv) >= 5:
        botname = argv[4]
    
    if ENABLE_AUTH:
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
    else:
        sessionId = 0
        username = botname
    interfaceNamespace = {}
    
    f = BotFactory(username, sessionId, botname, interfaceNamespace)
    reactor.connectTCP(server, port, f)
    
    #start with a null oberserver to remove DefaultObserver
    #because we can't stderr in a terminal
    log.startLoggingWithObserver(lambda a: '')
    runReactorWithTerminal(CommandLineBotInterface, interfaceNamespace)
    
    

if __name__ == '__main__':
    main()
