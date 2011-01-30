import random

from collections import defaultdict

from constants import *

class InventoryHandler(object):
    def __init__(self, protocol):
        self.protocol = protocol
        
        self.currentWindowId = 0
        self.windows = {0: PlayerInventory(self, 0)}
    
    def closeWindow(self, window=None):
        if window is None:
            windowId = self.currentWindowId
        else:
            windowId = window.windowId
            assert windowId == self.currentWindowId
        
        if windowId != 0:
            self.protocol.sendPacked(TYPE_WINDOWCLOSE, windowId)
            self.onWindowClose(windowId)
    
    @property
    def currentWindow(self):
        return self.windows.get(self.currentWindowId)
    
    #These will be called from reactor thread, so it's ok to block untill
    #one of these fires
    def onTransaction(self, windowId, actionNumber, accepted):
        if windowId not in self.windows:
            return
        self.windows[windowId].onTransaction(actionNumber, accepted)
    def onWindowOpen(self, windowId, windowType, windowTitle, numSlots):
        if windowType == INVENTORYTYPE_WORKBENCH:
            inventory = WorkBenchInventory(self, windowId)
        else:
            print "fixme %d" % windowType
            return
        
        self.windows[windowId] = inventory
        self.currentWindowId = windowId
    def onWindowClose(self, windowId):
        if windowId in self.windows:
            del self.windows[windowId]
        if self.currentWindowId == windowId:
            self.currentWindowId = 0
    def onWindowItems(self, windowId, items):
        self.windows[windowId].items = items
    def onSetSlot(self, windowId, slot, item):
        if windowId < 0: return
        if item is None and slot in self.windows[windowId].items:
            del self.windows[windowId].items[slot]
        self.windows[windowId].items[slot] = item
        print " -->", self.windows[windowId].items
        
    
    
class Inventory(object):
    def __init__(self, handler, windowId, playerItemsRange):
        self.handler = handler
        self.windowId = windowId
        self.playerItemsRange = playerItemsRange
        
        self.items = {}
        
        self.transactionResult = defaultdict(lambda: None)
    def findPlayerItemId(self, itemId):
        for slot, item in self.items.items():
            if slot not in self.playerItemsRange: continue
            if item.itemId == itemId:
                return slot
        return None
    def findPlayerEmptySlot(self):
        for i in self.playerItemsRange:
            if self.items.get(i) is None:
                return i
        return None
    
    def command_click(self, slot, rightClick=0):
        assert self.handler.currentWindowId == self.windowId
        
        transactionId = random.randrange(1, 0x7fff)

        print "click", slot, self.windowId, transactionId, self.items.get(slot)

        self.handler.protocol.sendPacked(TYPE_WINDOWCLICK, self.windowId, slot,
            rightClick, transactionId, self.items.get(slot))
        
        while self.transactionResult[transactionId] is None:
            yield True
        result = self.transactionResult[transactionId]
        del self.transactionResult[transactionId]
        
        if result == False:
            print "transaction failed"
        yield result
    def command_swapSlots(self, src, dst):
        assert self.handler.currentWindowId == self.windowId
        
        inHand = None
        if src in self.items:
            for v in self.command_click(src): yield v
            inHand = self.items[src]
            del self.items[src]
        for v in self.command_click(dst): yield v
        if dst in self.items:
            if inHand is None:
                inHand = self.items[dst]
                del self.items[dst]
            else:
                inHand, self.items[dst] = self.items[dst], inHand

            for v in self.command_click(src): yield v
            self.items[src] = inHand
        elif inHand is not None:
            self.items[dst] = inHand
    
    def onTransaction(self, actionNumber, accepted):
        self.transactionResult[actionNumber] = accepted

class PlayerInventory(Inventory):
    def __init__(self, handler, windowId):
        Inventory.__init__(self, handler, windowId, range(9, 45))
        
        self.equippableSlots = range(36, 45)
        self.equippedSlot = None
    
    @property
    def equippedItem(self):
        return self.items.get(self.equippedSlot)
    def command_equipItem(self, itemId):
        assert self.handler.currentWindowId == self.windowId
        
        for slot, item in self.items.items():
            if item.itemId == itemId:
                if slot in self.equippableSlots:
                    self.handler.protocol.sendPacked(TYPE_ITEMSWITCH, self.equippableSlots.index(slot))
                    self.equippedSlot = slot
                else:
                    for v in self.command_swapSlots(slot, self.equippableSlots[0]): yield v
                    self.handler.protocol.sendPacked(TYPE_ITEMSWITCH, 0)
                    self.equippedSlot = self.equippableSlots[0]
                return
        print "No item %d" % itemId
        yield False

class WorkBenchInventory(Inventory):
    def __init__(self, handler, windowId):
        Inventory.__init__(self, handler, windowId, range(10, 56))
