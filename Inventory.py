#MineBot
#GPL and all that
# - espes

from __future__ import division

import random
import logging
from collections import defaultdict

from Utility import *
from constants import *
from packets import *

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
        
        self.protocol.sendPacked(PACKET_WINDOWCLOSE, windowId)
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
            logging.info("fixme %d" % windowType)
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
        if windowId == -1 and slot == -1:
            self.currentWindow.inHand = item
            return
        
        if item is None:
            if slot in self.windows[windowId].items:
                del self.windows[windowId].items[slot]
            return
        
        self.windows[windowId].items[slot] = item
        logging.debug(" --> %r" % self.windows[windowId].items)
        
    

class Inventory(object):
    def __init__(self, handler, windowId, playerSlotsRange):
        self.handler = handler
        self.windowId = windowId
        self.playerSlotsRange = playerSlotsRange
        
        self.inHand = None
        self.items = {}
        
        self.transactionResult = defaultdict(lambda: None)
    def findPlayerItemId(self, itemId):
        for slot, item in self.items.items():
            if slot not in self.playerSlotsRange: continue
            if item.itemId == itemId:
                return slot
        return None
    def countPlayerItemId(self, itemId):
        count = 0
        for slot, item in self.items.items():
            if slot not in self.playerSlotsRange: continue
            if item.itemId == itemId:
                count += item.count
        return count
    def findPlayerEmptySlot(self):
        for i in self.playerSlotsRange:
            if self.items.get(i) is None:
                return i
        return None
    
    def command_click(self, slot, rightClick=0, shiftClick=0):
        assert self.handler.currentWindowId == self.windowId
        
        transactionId = random.randrange(1, 0x7fff)

        logging.debug("click %r %r %r %r %r" % (slot, rightClick,
            self.windowId, transactionId, self.items.get(slot)))

        self.handler.protocol.sendPacked(PACKET_WINDOWCLICK, self.windowId, slot,
            rightClick, transactionId, shiftClick, self.items.get(slot))
        
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
                        maxStack = gamelogic.maxStack(self.inHand.itemId)
                        placeAmount = max(maxStack-self.items[slot].count, 0)
                        if rightClick:
                            placeAmount = min(placeAmount, 1)
                        placeAmount = min(placeAmount, self.inHand.count)
                        self.inHand.count -= placeAmount
                        self.items[slot].count += placeAmount
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
            logging.error("transaction failed")
        yield result
    def command_swapSlots(self, src, dst):
        assert self.handler.currentWindowId == self.windowId
        
        for v in self.command_click(src): yield v
        for v in self.command_click(dst): yield v
        if self.inHand is not None:
            for v in self.command_click(src): yield v
    def command_fillSlotsWithPlayerItem(self, itemId, targetSlots):
        #print bool(targetSlots)
        while targetSlots:
            srcSlot = self.findPlayerItemId(itemId)
            if srcSlot is None:
                raise Exception, "insuffient items to fill"
            for v in self.command_click(srcSlot): yield v
            
            logging.debug("fill item %r" % self.inHand)
            for i in xrange(min(self.inHand.count, len(targetSlots))):
                slot = targetSlots.pop(0)
                assert slot not in self.items
                
                for v in self.command_click(slot, True): yield v
            
            if self.inHand is not None:
                #put it back
                for v in self.command_click(srcSlot): yield v

    def command_purge(self):
        for slot, item in self.items.items():
            for v in self.command_click(slot): yield v
            for v in self.command_click(-999): yield v
    def command_drop(self, itemId, count=1, dropAll=False):
        while count > 0 or dropAll:
            srcSlot = self.findPlayerItemId(itemId)
            if srcSlot is None: return
            if self.items[srcSlot].count <= count or dropAll:
                count -= self.items[srcSlot].count
                for v in self.command_click(srcSlot): yield v
                for v in self.command_click(-999): yield v
            else:
                for i in xrange(count):
                    count -= 1
                    for v in self.command_click(srcSlot, True): yield v
                    for v in self.command_click(-999): yield v
                    
    def command_moveToPlayerInventory(self, sourceSlot):
        for v in self.command_click(sourceSlot): yield v
        
        while self.inHand is not None:
            
            for slot, item in self.items.items():
                if slot not in self.playerSlotsRange:
                    continue
                if self.inHand.itemId == item.itemId:
                    for v in self.command_click(slot): yield v
                    break
            else:
                emptySlot = self.findPlayerEmptySlot()
                if emptySlot is None:
                    raise Exception, "no empty slot for item"
                for v in self.command_click(emptySlot): yield v
                assert self.inHand is None
        
    def onTransaction(self, actionNumber, accepted):
        self.transactionResult[actionNumber] = accepted

class CraftingInventory(Inventory):
    def __init__(self, handler, windowId, playerSlotsRange,
                 craftSlotsRange, craftOutSlot, craftDim):
        Inventory.__init__(self, handler, windowId, playerSlotsRange)
        self.craftItemsRange = craftSlotsRange
        self.craftOutSlot = craftOutSlot
        self.craftW, self.craftH = craftDim
    def command_fillRecipe(self, recipe):
        for i in self.craftItemsRange:
            if i in self.items:
                for v in self.command_moveToPlayerInventory(i): yield v
        
        recipeW, recipeH = recipe.dimensions
        craftSlots = defaultdict(list)
        for i, r in enumerate(recipe.recipe):
            if r is None: continue
            (itemId, _), count = r
            cx, cy = i%recipeW, i//recipeW
            craftSlots[itemId].append(self.craftItemsRange[cy*self.craftW+cx])
        
        for itemId, slots in craftSlots.iteritems():
            logging.debug("fill %r %r" % (itemId, slots))
            for v in self.command_fillSlotsWithPlayerItem(itemId, slots):
                yield v
        
        (producedItemId, _), producedCount = recipe.provides
        
        self.items[self.craftOutSlot] = Item(producedItemId, producedCount, 0)
        for i in self.craftItemsRange:
            if i in self.items:
                self.items[i].count -= 1
                if self.items[i].count <= 0:
                    del self.items[i]
                else:
                    for v in self.command_moveToPlayerInventory(i): yield v
        
        yield True


class WorkBenchInventory(CraftingInventory):
    def __init__(self, handler, windowId):
        CraftingInventory.__init__(self, handler, windowId, range(10, 46), range(1, 10), 0, (3, 3))

class PlayerInventory(CraftingInventory):
    def __init__(self, handler, windowId):
        CraftingInventory.__init__(self, handler, windowId, range(9, 45), range(1, 5), 0, (2, 2))
        
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
                    self.handler.protocol.sendPacked(PACKET_ITEMSWITCH, self.equippableSlots.index(slot))
                    self.equippedSlot = slot
                else:
                    for v in self.command_swapSlots(slot, self.equippableSlots[0]): yield v
                    self.handler.protocol.sendPacked(PACKET_ITEMSWITCH, 0)
                    self.equippedSlot = self.equippableSlots[0]
                return
        raise Exception, "No item %d" % itemId



