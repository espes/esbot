import copy
from collections import defaultdict

from Utility import *
from Inventory import *

class Tech(object):
    def __init__(self, depends):
        self.depends = depends
    def clientHas(self, client):
        return True
    def command_get(self, client):
        print "getting %r" % self
        #TODO: dependency evaluation is really inefficient
        done = False
        while not done:
            done = True
            for dep, count in self.depends:
                print "dependency %d %r" % (count, dep)
                while not dep.clientHas(client, count):
                    done = False
                    for v in dep.command_get(client):
                        yield v
        

#item representable in inventory
class TechItem(Tech):
    def __init__(self, depends, itemId):
        Tech.__init__(self, depends)
        self.itemId = itemId
    def __repr__(self):
        if self.itemId in BLOCKITEM_NAMES:
            return "TechItem(%r)" % BLOCKITEM_NAMES[self.itemId]
        return "TechItem(%r)" % self.itemId
    def clientHas(self, client, count=1):
        return client.inventoryHandler.currentWindow.countPlayerItemId(self.itemId) >= count
    def command_get(self, client):
        for v in Tech.command_get(self, client):
            yield v
        
        #try to grab any pickups < 5 blocks away
        #(Because sometimes we are so clumsy and drop things)
        for pickup in client.pickups.values():
            if pickup.item.itemId == self.itemId and (client.pos-pickup.pos).mag() < 5:
                for v in client.command_walkPathToPoint(pickup.pos):
                    if v == False: break
                    yield v

#item that can just be mined somewhere
class TechMineItem(TechItem):
    def __init__(self, itemId, mineTool=None, mineItem=None):
        if mineTool is None:
            TechItem.__init__(self, [], itemId)
        else:
            if isinstance(mineTool, int):
                mineTool = TECH_MAP[mineTool]
            TechItem.__init__(self, [(mineTool, 1)], itemId)
        
        self.mineTool = mineTool
        self.mineItemId = mineItem or self.itemId
    def command_get(self, client):
        for v in TechItem.command_get(self, client):
            yield v
        print "mineping"
        if self.mineTool is not None:
            #equipt the tool of choice (by now should have it in inventory)
            for v in client.playerInventory.command_equipItem(self.mineTool.itemId):
                yield v
        
        try:
            print "finding block"
            blockPos = client.map.searchForBlock(client.pos, self.mineItemId)
        except TimeoutError:
            print "timeout! block too far away!"
            yield False
            return
        #TODO: Look for items on the ground
        
        if not blockPos:
            print "block not found"
            yield False
            return

        for v in client.command_walkPathToPoint(blockPos,
            destructive=True, blockBreakPenalty=5):
            yield v

def buildDependsFromRecipe(recipe):
    depends = defaultdict(int)
    for tech in recipe:
        if tech is None: continue
        if isinstance(tech, int):
            tech = TECH_MAP[tech]
        depends[tech] += 1
    return depends.items()
def buildSlotsFromRecipe(recipe):
    slots = defaultdict(list)
    for i, item in enumerate(recipe):
        if item is None: continue
        
        if isinstance(item, TechItem):
            item = tech.itemId
        elif not isinstance(item, int):
            print "recipe must be items"
        
        slots[item].append(i+1)
    return slots

#Tech made with the inventory crafting thing
class TechAssembleItem(TechItem):
    def __init__(self, itemId, recipe, producedItem):
        depends = buildDependsFromRecipe(recipe)
        TechItem.__init__(self, depends, itemId)
        
        self.recipe = recipe
        self.produced = producedItem
    def command_get(self, client):
        for v in TechItem.command_get(self, client):
            yield v
        
        print "assembly get"
        print "place items"
        craftSlots = buildSlotsFromRecipe(self.recipe)
        for itemId, slots in craftSlots.iteritems():
            print itemId, slots
            for v in client.playerInventory.command_fillSlotsWithPlayerItem(itemId, slots):
                yield v
        
        client.playerInventory.items[0] = copy.copy(self.produced)
        for i in xrange(1, 5):
            if i in client.playerInventory.items:
                del client.playerInventory.items[i]
        
        print "retrieve"
        emptySlot = client.playerInventory.findPlayerEmptySlot()
        if emptySlot is None:
            print "no empty slot to store item"
            yield False
            return
        for v in client.playerInventory.command_swapSlots(0, emptySlot):
            yield v
        
        #close the window (throwing everything out)
        client.inventoryHandler.closeWindow(client.playerInventory)
        yield True

#Tech made with crafting table
class TechCraftItem(TechItem):
    def __init__(self, itemId, recipe, producedItem):
        depends = [(TECH_MAP[BLOCK_CRAFTINGTABLE], 1)] + buildDependsFromRecipe(recipe)
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
        
        #equip crafting table
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

        #hit it
        if not client.placeBlock(placePos):
            print "failed hitting crafing table"
            yield False
            return
        yield True
        
        print "wait for open"
        #Wait for window to come up
        while not isinstance(client.inventoryHandler.currentWindow, WorkBenchInventory):
            yield True
        
        craftingWindow = client.inventoryHandler.currentWindow
        
        print "place items"
        craftSlots = buildSlotsFromRecipe(self.recipe)
        for itemId, slots in craftSlots.iteritems():
            print itemId, slots
            for v in craftingWindow.command_fillSlotsWithPlayerItem(itemId, slots):
                yield v
        
        #for i, itemId in enumerate(self.recipe):
        #    if itemId is None: continue
        #    
        #    srcSlot = craftingWindow.findPlayerItemId(itemId)
        #    if srcSlot is None:
        #        print "required crafting item %d not in inventory" % itemId
        #        yield False
        #        return
        #    for v in craftingWindow.command_swapSlots(srcSlot, i+1):
        #        yield v
        yield True
        
        #TODO: Handle recipes better
        craftingWindow.items[0] = copy.copy(self.produced)
        #for i in xrange(1, 10):
        #    if i in craftingWindow.items:
        #        del craftingWindow.items[i]
        
        print "retrieve"
        
        emptySlot = craftingWindow.findPlayerEmptySlot()
        if emptySlot is None:
            print "no empty slot to store item"
            yield False
            return
        for v in craftingWindow.command_swapSlots(0, emptySlot):
            yield v
        
        #no need to other items because they'll pop out when closing window
        client.inventoryHandler.closeWindow(craftingWindow)
        
        #walk back down destroying the crafting table
        for v in client.command_walkPathToPoint(placePos, destructive=True):
            yield v

TECH_MAP = {}
TECH_MAP[BLOCK_DIRT] = TechMineItem(BLOCK_DIRT)
TECH_MAP[BLOCK_TREETRUNK] = TechMineItem(BLOCK_TREETRUNK)
TECH_MAP[BLOCK_WOOD] = TechAssembleItem(BLOCK_WOOD, [BLOCK_TREETRUNK], Item(BLOCK_WOOD, 4, 0))
TECH_MAP[ITEM_STICK] = TechAssembleItem(ITEM_STICK,
            [BLOCK_WOOD, None,
             BLOCK_WOOD, None], Item(ITEM_STICK, 4, 0))

TECH_MAP[BLOCK_CRAFTINGTABLE] = TechAssembleItem(BLOCK_CRAFTINGTABLE,
            [BLOCK_WOOD, BLOCK_WOOD,
             BLOCK_WOOD, BLOCK_WOOD], Item(BLOCK_CRAFTINGTABLE, 1, 0))

TECH_MAP[ITEM_BOAT] = TechCraftItem(ITEM_BOAT,
            [None,          None,           None,
             BLOCK_WOOD,    None,           BLOCK_WOOD,
             BLOCK_WOOD,    BLOCK_WOOD,     BLOCK_WOOD], Item(ITEM_BOAT, 1, 0))

TECH_MAP[ITEM_WOODPICKAXE] = TechCraftItem(ITEM_WOODPICKAXE,
            [BLOCK_WOOD,    BLOCK_WOOD,     BLOCK_WOOD,
             None,          ITEM_STICK,     None,
             None,          ITEM_STICK,     None], Item(ITEM_WOODPICKAXE, 1, 0))
TECH_MAP[ITEM_WOODSWORD] = TechCraftItem(ITEM_WOODSWORD,
            [None,  BLOCK_WOOD, None,
             None,  BLOCK_WOOD, None,
             None,  ITEM_STICK, None], Item(ITEM_WOODSWORD, 1, 0))

TECH_MAP[BLOCK_COBBLESTONE] = TechMineItem(BLOCK_COBBLESTONE, ITEM_WOODPICKAXE, BLOCK_STONE)
TECH_MAP[ITEM_COAL] = TechMineItem(ITEM_COAL, ITEM_WOODPICKAXE, BLOCK_COALORE)

TECH_MAP[ITEM_TORCH] = TechAssembleItem(ITEM_TORCH, 
            [ITEM_COAL,     None,
             ITEM_STICK,    None], Item(ITEM_TORCH, 4, 0))

TECH_MAP[BLOCK_FURNACE] = TechCraftItem(BLOCK_FURNACE,
            [BLOCK_COBBLESTONE, BLOCK_COBBLESTONE,  BLOCK_COBBLESTONE,
             BLOCK_COBBLESTONE, None,               BLOCK_COBBLESTONE,
             BLOCK_COBBLESTONE, BLOCK_COBBLESTONE,  BLOCK_COBBLESTONE], Item(BLOCK_FURNACE, 1, 0))

TECH_MAP[ITEM_STONEPICKAXE] = TechCraftItem(ITEM_STONEPICKAXE,
            [BLOCK_COBBLESTONE, BLOCK_COBBLESTONE,  BLOCK_COBBLESTONE,
             None,              ITEM_STICK,         None,
             None,              ITEM_STICK,         None], Item(ITEM_STONEPICKAXE, 1, 0))

TECH_MAP[BLOCK_IRONORE] = TechMineItem(BLOCK_IRONORE, ITEM_STONEPICKAXE)


