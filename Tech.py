from collections import defaultdict

from Inventory import *

class Tech(object):
    def __init__(self, depends):
        self.depends = depends
    def clientHas(self, client):
        return True
    def command_get(self, client):
        for dep, count in self.depends:
            while not dep.clientHas(client, count):
                for v in dep.command_get(client):
                    yield v
        

#item representable in inventory
class TechItem(Tech):
    def __init__(self, depends, itemId):
        Tech.__init__(self, depends)
        self.itemId = itemId
    def clientHas(self, client, count=1):
        for slot, item in client.inventoryHandler.currentWindow.items():
            if slot in client.inventoryHandler.currentWindow.playerItemsRange and \
                    item.itemId == self.itemId and item.count >= count:
                return True
        return False

#item that can just be mined somewhere
class TechMineItem(TechItem):
    def __init__(self, itemId, mineTool=None):
        if mineTool is None:
            TechItem.__init__(self, [], itemId)
        else:
            TechItem.__init__(self, [(mineTool, 1)], itemId)
        
        self.mineTool = mineTool
    def command_get(self, client):
        for v in TechItem.command_get(self, client):
            yield v
        
        if self.mineTool is not None:
            #equipt the tool of choice (by now should have it in inventory)
            for v in client.command_equipItem(self.mineTool):
                yield v
        
        #try 20 times
        for count in xrange(20):
            if self.clientHas(client):
                return
            
            blockPos = client.map.searchForBlock(client.pos, self.itemId)
            #TODO: Look for items on the ground
            
            if not blockPos:
                break

            for v in client.map.command_walkPathToPoint(blockPos,
                destructive=True, blockBreakPenalty=100):
                yield v
        
        print "mining item %d failed" % self.itemId
        yield False
        return

class TechCraftItem(TechItem):
    def __init__(self, itemId, recipe, producedItem):
        depends = defaultdict(int)
        for tech in recipe:
            if not isinstance(tech, Tech):
                tech = TECH_MAP[tech]
            depends[tech] += 1
        depends = [(TECH_MAP[BLOCK_CRAFTINGTABLE], 1)] + depends.items()
        TechItem.__init__(self, depends, itemId)
        
        self.recipe = recipe
        self.produced = producedItem
    def command_get(self, client):
        for v in TechItem.command_get(self, client):
            yield v
        
        #Move up one block
        placePos = client.pos
        for v in client.command_walkPathToPoint(client.pos + (0, 1, 0), destructive=True):
            yield v
        
        #equipt crafting table
        for v in client.playerInventory.command_equipItem(BLOCK_CRAFTINGTABLE):
            yield v
        
        #place crafting table
        if not client.placeBlock(placePos + (0, -1, 0)): 
            print "failed placing crafting table"
            yield False
            return
        yield True
        
        if not client.map[placePos] == BLOCK_CRAFTINGTABLE:
            print "failed placing crafting table"
            yield False
            return
        
        """
        
        #Hack for inner function shit
        state = [False, None, None, None] #done, id, title, numSlots
        def callback(windowId, windowTitle, numSlots):
            state[0] = True
            state[1] = windowId
            state[2] = windowTitle
            state[3] = numSlots
        client.windowOpenCallbacks[INVENTORYTYPE_WORKBENCH] = callback
        
        """
        
        #hit it
        if not client.placeBlock(placePos):
            print "failed hitting crafing table"
            yield False
            return
        yield True
        
        #Wait for window to come up
        while not isinstance(client.inventoryHandler.currentWindow, WorkBenchInventory):
            yield True
        
        craftingWindow = client.inventoryHandler.currentWindow
        
        #print "wait for open"
        #while not state[0]: #while window hasn't been displayed
        #    yield True
        #
        #_, windowId, windowTitle, numSlots = state
        
        print "place items"
        
        for i, itemId in enumerate(self.recipe):
            if itemId is None: continue
            
            #srcSlot = client.findInventoryItemId(itemId, windowId)
            srcSlot = craftingWindow.findPlayerItemId(itemId)
            if srcSlot is None:
                print "required crafting item %d not in inventory" % itemId
                yield False
                return
            for v in craftingWindow.command_swapSlots(srcSlot, i+1):
                yield v
        yield True
        
        #TODO: Handle recipes better
        craftingWindow.items[0] = self.produced
        
        #client.inventories[windowId][0] = self.produced
        #while client.inventories[windowId].get(0) is None:
        #    print "item was not crafted for some reason"
        #    yield False
        #    return
        
        print "retrieve"
        
        emptySlot = craftingWindow.findPlayerEmptySlot()
        if emptySlot is None:
            print "no empty slot to store item"
        for v in craftingWindow.command_swapSlots(0, emptySlot):
            yield v
        
        #no need to other items because they'll pop out when closing window
        #client.protocol.sendPacked(TYPE_WINDOWCLOSE, windowId)
        client.inventoryHandler.closeWindow(craftingWindow)
        
        #walk back down destroying the crafting table
        for v in client.command_walkPathToPoint(placePos, destructive=True):
            yield v
        
        
        


TECH_MAP = {}

    #BLOCK_STONE: TechMineItem(BLOCK_STONE, )
}
