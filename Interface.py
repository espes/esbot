#MineBot
#GPL and all that
# - espes

import io
import logging
from textwrap import wrap

from signal import signal, SIGWINCH
from fcntl import ioctl
from tty import TIOCGWINSZ
from struct import unpack

from twisted.python import log
from twisted.internet import reactor, protocol, task

from twisted.conch.manhole import Manhole

from twisted.conch.insults.insults import TerminalProtocol, privateModes, _KEY_NAMES, FUNCTION_KEYS
from twisted.conch.insults.helper import TerminalBuffer
from twisted.conch.insults.window import Widget, TopWindow, TextOutput, VBox, YieldFocus, horizontalLine, cursor


class FixedTerminalBuffer(TerminalBuffer):
    lastWrite = ''
    def write(self, bytes):
        TerminalBuffer.write(self, bytes)
        lastWrite = bytes
#make key ids the same as ServerProtocol
for name, const in zip(_KEY_NAMES, FUNCTION_KEYS):
    setattr(FixedTerminalBuffer, name, const)

#a list that calls a callback when it's modified
class AnnouncingList(list):
    def __init__(self, callback, *args, **kargs):
        list.__init__(self, *args, **kargs)
        self.callback = callback
    for m in ['__delattr__', '__delitem__', '__delslice__', 
              '__setattr__', '__setitem__', '__setslice__',
              '__iadd__', '__imul__',
              'append', 'extend', 'insert', 'pop', 'remove', 
              'reverse', 'sort']:
        exec """\
def %s(self, *args, **kargs):
    r = list.%s(self, *args, **kargs)
    self.callback()
    return r
""" % (m, m)

class AnnouncingTerminalBuffer(FixedTerminalBuffer):
    def __init__(self, modifyCallback):
        self.modifyCallback = modifyCallback
    def _emptyLine(self, width):
        res = FixedTerminalBuffer._emptyLine(self, width)
        return AnnouncingList(self.modifyCallback, res)
    def eraseDisplay(self):
        FixedTerminalBuffer.eraseDisplay(self)
        self.lines = AnnouncingList(self.modifyCallback, self.lines)


class TerminalProtocolWidget(Widget):
    width = 80
    height = 24
    
    def __init__(self, tp):
        Widget.__init__(self)
        self.tp = tp
        
        self._buf = AnnouncingTerminalBuffer(self.repaint)
        
        self._buf.width = self.width
        self._buf.height = self.height
        
        self._buf.connectionMade()
        self.tp.makeConnection(self._buf)
        
    def keystrokeReceived(self, keyID, modifier):
        self.tp.keystrokeReceived(keyID, modifier)
    
    def draw(self, width, height, terminal):
        if width != self.width or height != self.height:
            self.resizeTerminal(width, height)
        Widget.draw(self, width, height, terminal)
    
    def resizeTerminal(self, width, height):
        self._buf.width = width
        self._buf.height = height
        self._buf.eraseDisplay()
        
        self.tp.terminalSize(width, height)
        self.repaint()
    
    def render(self, width, height, terminal):
        for y, line in enumerate(self._buf.lines[:height]):
            terminal.cursorPosition(0, y)
            n = 0
            for n, (ch, attr) in enumerate(line[:width]):
                if ch is self._buf.void:
                    ch = ' '
                if y == self._buf.y and n == self._buf.x:
                    cursor(terminal, ch)
                else:
                    terminal.write(ch)
            if n < width:
                terminal.write(' ' * (width - n - 1))

#adapted from invective (http://twistedmatrix.com/trac/browser/sandbox/exarkun/invective)
class OutputWidget(TextOutput):
    def __init__(self, size=None):
        TextOutput.__init__(self, size)
        self.messages = []

    def formatMessage(self, s, width):
        return wrap(s, width=width, subsequent_indent="  ")

    def addMessage(self, message):
        self.messages.append(message)
        self.repaint()

    def render(self, width, height, terminal):
        output = []
        for i in xrange(len(self.messages) - 1, -1, -1):
            output[:0] = self.formatMessage(self.messages[i], width - 2)
            if len(output) >= height:
                break
        if len(output) < height:
            output[:0] = [''] * (height - len(output))
        for n, L in enumerate(output[-height:]):
            terminal.cursorPosition(0, n)
            terminal.write(L + ' ' * (width - len(L)))

class SeperatorWidget(Widget):
    def sizeHint(self):
        return (None, 1)
    def focusReceived(self):
        raise YieldFocus()
    
    def render(self, width, height, terminal):
        horizontalLine(terminal, 0, 0, width)


class OutputLogStream(io.BufferedIOBase):
    def __init__(self, logWidget):
        self.logWidget = logWidget
        self.buffer = ""
    def write(self, b):
        self.buffer += b
        if "\n" in b:
            self.flush()
    def flush(self):
        lines = self.buffer.split("\n")
        self.buffer = lines[-1]
        for line in lines[:-1]:
            self.logWidget.addMessage(line)

class BotInterface(TerminalProtocol):
    width = 80
    height = 24
    
    def __init__(self, manholeNamespace = None):
        self.manholeNamespace = manholeNamespace
    
    def _draw(self):
        self.window.draw(self.width, self.height, self.terminal)
    def _schedule(self, f):
        reactor.callLater(0, f)
    
    def connectionMade(self):
        TerminalProtocol.connectionMade(self)
        self.terminal.eraseDisplay()
        self.terminal.resetPrivateModes([privateModes.CURSOR_MODE])
        
        self.window = TopWindow(self._draw, self._schedule)
        vbox = VBox()
        
        self.logWidget = OutputWidget()
        vbox.addChild(self.logWidget)
        
        logHandler = logging.StreamHandler(OutputLogStream(self.logWidget))
        #make it use the default formatter
        logHandler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        logging.getLogger().addHandler(logHandler)
        
        vbox.addChild(SeperatorWidget())
        
        #TODO: factory stuff
        self.manhole = Manhole()
        self.manholeView = TerminalProtocolWidget(self.manhole)
        #set the namespace directly so it's mutable
        self.manhole.interpreter.locals = self.manholeNamespace
        vbox.addChild(self.manholeView)
        
        self.window.addChild(vbox)
    
    def keystrokeReceived(self, keyID, modifier):
        self.window.keystrokeReceived(keyID, modifier)
    
    def terminalSize(self, width, height):
        self.width = width
        self.height = height
        self._draw()

#because twisted is too fail to have an interface
#from invective (http://twistedmatrix.com/trac/browser/sandbox/exarkun/invective)
class CommandLineBotInterface(BotInterface):
    def connectionMade(self):
        signal(SIGWINCH, self.windowChanged)
        winSize = self.getWindowSize()
        self.width = winSize[0]
        self.height = winSize[1]
        BotInterface.connectionMade(self)

    def connectionLost(self, reason):
        if reactor.running: reactor.stop()

    # XXX Should be part of runWithProtocol
    def getWindowSize(self):
        winsz = ioctl(0, TIOCGWINSZ, '12345678')
        winSize = unpack('4H', winsz)
        newSize = winSize[1], winSize[0], winSize[3], winSize[2]
        return newSize

    def windowChanged(self, signum, frame):
        winSize = self.getWindowSize()
        self.terminalSize(winSize[0], winSize[1])

#better version of twisted.conch.stdio.runWithProtocol
def runReactorWithTerminal(terminalProtocol, *args):
    import os, tty, sys, termios
    from twisted.internet import stdio
    from twisted.conch.insults.insults import ServerProtocol

    fd = sys.__stdin__.fileno()
    oldSettings = termios.tcgetattr(fd)
    tty.setraw(fd)
    try:
        p = ServerProtocol(terminalProtocol, *args)
        stdio.StandardIO(p)
        reactor.run()
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, oldSettings)
        os.write(fd, "\r\x1bc\r")
