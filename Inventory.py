import random

from collections import defaultdict

from Utility import *
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
        if windowId == 0:
            #these items will be dropped
            for i in range(5):
                if i in self.windows[0].items:
                    del self.windows[0].items[i]
            
            return
        
        if windowId in self.windows:
            del self.windows[windowId]
        if self.currentWindowId == windowId:
            self.currentWindowId = 0
    def onWindowItems(self, windowId, items):
        self.windows[windowId].items = items
    def onSetSlot(self, windowId, slot, item):
        if windowId < 0: return
        if item is None:
            if slot in self.windows[windowId].items:
                del self.windows[windowId].items[slot]
            return
        
        self.windows[windowId].items[slot] = item
        print " -->", self.windows[windowId].items
        
    
#TODO: Make commands modify the inventory themselves
class Inventory(object):
    def __init__(self, handler, windowId, playerItemsRange):
        self.handler = handler
        self.windowId = windowId
        self.playerItemsRange = playerItemsRange
        
        self.inHand = None
        self.items = {}
        
        self.transactionResult = defaultdict(lambda: None)
    def findPlayerItemId(self, itemId):
        for slot, item in self.items.items():
            if slot not in self.playerItemsRange: continue
            if item.itemId == itemId:
                return slot
        return None
    def countPlayerItemId(self, itemId):
        count = 0
        for slot, item in self.items.items():
            if slot not in self.playerItemsRange: continue
            if item.itemId == itemId:
                count += item.count
        return count
    def findPlayerEmptySlot(self):
        for i in self.playerItemsRange:
            if self.items.get(i) is None:
                return i
        return None
    
    def command_click(self, slot, rightClick=0):
        assert self.handler.currentWindowId == self.windowId
        
        transactionId = random.randrange(1, 0x7fff)

        print "click", slot, rightClick, self.windowId, transactionId, self.items.get(slot)

        self.handler.protocol.sendPacked(TYPE_WINDOWCLICK, self.windowId, slot,
            rightClick, transactionId, self.items.get(slot))
        
        while self.transactionResult[transactionId] is None:
            yield True
        result = self.transactionResult[transactionId]
        del self.transactionResult[transactionId]
        
        if result:
            if slot == -999:
                #drop
                self.inHand = None
            else:
                #update inventory
                if self.inHand is not None and slot in self.items:
                    if self.inHand.itemId == self.items[slot].itemId:
                        placeAmount = max(64-self.items[slot].count, 0)
                        if rightClick:
                            placeAmount = min(placeAmount, 1)
                        placeAmount = min(placeAmount, inHand.count)
                        self.inHand.count -= placeAmount
                        self.items[slot] += placeAmount
                    else:
                        #swap them
                        self.inHand, self.items[slot] = self.items[slot], self.inHand
                elif self.inHand is not None:
                    #in hand but empty slot
                    if rightClick and self.inHand.count > 1:
                        self.items[slot] = Item(self.inHand.itemId, 1, 0)
                        self.inHand.count -= 1
                    else:
                        self.items[slot] = self.inHand
                        self.inHand = None
                elif slot in self.items:
                    if rightClick and self.items[slot].count > 1:
                        takeCount = int((self.items[slot].count+1)/2)
                        self.items[slot].count -= takeCount
                        self.inHand = Item(self.items[slot].itemId, takeCount, 0)
                    else:
                        self.inHand = self.items[slot]
                        del self.items[slot]
                else:
                    #both are empty, don't need to do anything
                    pass
                if self.inHand is not None and self.inHand.count == 0:
                    self.inHand = None
        else:
            print "transaction failed"
        yield result
    def command_swapSlots(self, src, dst):
        assert self.handler.currentWindowId == self.windowId
        
        for v in self.command_click(src): yield v
        for v in self.command_click(dst): yield v
        if self.inHand is not None:
            for v in self.command_click(src): yield v
        
        """
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
        """
    def command_fillSlotsWithPlayerItem(self, itemId, targetSlots):
        #print bool(targetSlots)
        while targetSlots:
            srcSlot = self.findPlayerItemId(itemId)
            if srcSlot is None:
                print "insuffient items to fill"
                yield False
                return
            for v in self.command_click(srcSlot): yield v
            #inHand = self.items[srcSlot]
            #del self.items[srcSlot]
            
            print "fill item", self.inHand
            for i in xrange(min(self.inHand.count, len(targetSlots))):
                slot = targetSlots.pop(0)
                assert slot not in self.items
                
                for v in self.command_click(slot, True): yield v
                #inHand.count -= 1
                
                #self.items[slot] = Item(inHand.itemId, 1, 0)
            
            if self.inHand is not None and self.inHand.count > 0:
                #put it back
                for v in self.command_click(srcSlot): yield v
                #self.items[srcSlot] = inHand
    def command_purge(self):
        for slot, item in self.items.items():
            for v in self.command_click(slot): yield v
            for v in self.command_click(-999): yield v
            
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
        Inventory.__init__(self, handler, windowId, range(10, 46))
