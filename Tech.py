from __future__ import division

import copy
from collections import defaultdict

from Utility import *
from Inventory import *

class Tech(object):
    def __init__(self, depends, consumes, producesCount=1):
        self.depends = depends
        self.consumes = consumes
        
        self.produces = producesCount
    def clientHas(self, client, count=1):
        pass
    
    #Note: due to lazyness, asume any item's depends won't also be a consume somewhere
    def calcRequiredCounts(self, getCount=1, curGet=None, curHas=None, invHas=None):
        #print "%r %r" % (self, getCount)
        top = False
        if curHas is None:
            curHas = defaultdict(int)
            top = True
        if curGet is None:
            curGet = defaultdict(int)
        if invHas is None:
            invHas = defaultdict(int)
        for dep, count in self.depends:
            #handle when there are optional depends
            try:
                ndep = [TECH_MAP.get(d) or d for d in dep]
                
                dep = max(ndep, key=lambda d: curHas[d]+invHas[d])
            except TypeError: #not iterable
                if isinstance(dep, int): dep = TECH_MAP[dep]
            
            if count/dep.produces > curHas[dep]+invHas[dep]:
                get = max(0, count/dep.produces-(curHas[dep]+invHas[dep]))
                dep.calcRequiredCounts(get, curGet, curHas, invHas)
                curHas[dep] += get
            #for i in xrange(count-curHas[dep]):
            #    curHas[dep] += 1
            #    dep.evaluateDeps(curGet, curHas)
        for dep, count in self.consumes:
            get = getCount*count/dep.produces
            dep.calcRequiredCounts(get, curGet, curHas, invHas)
            curGet[dep] += get
            
            #curGet[dep] += count
            #for i in xrange(count):
            #    dep.evaluateDeps(curGet, curHas)
        #return curHas, curGet
        if top:
            
            #remove inventory things for gets
            for dep, count in invHas.iteritems():
                if curGet[dep] > 0:
                    dep.calcRequiredCounts(-min(invHas[dep], curGet[dep]), curGet, curHas, invHas)
                    #curGet[dep] -= invHas[dep]
                    curGet[dep] = max(0, curGet[dep]-invHas[dep])
            for dep, count in curGet.iteritems():
                if count <= 0:
                    curGet[dep] = 0
                    #del curGet[dep]
            
            #print curGet, curHas
            #fix so all the gets have been rounded up
            #evaluate them in tolological order so current adjustments won't affect past ones
            order = self.calcGetOrder()
            for dep in order[::-1]:
                if dep in curHas:
                    cget = curHas[dep]
                    get = iceil(cget)-cget
                    if get != 0:
                        dep.calcRequiredCounts(get, curGet, curHas, invHas)
                        curHas[dep] += get
                elif dep in curGet:
                    cget = curGet[dep]
                    get = iceil(cget)-cget
                    if get != 0:
                        dep.calcRequiredCounts(get, curGet, curHas, invHas)
                        curGet[dep] += get
                
            #print curGet, curHas
            #probable doesn't work optimally :\
            #while True:
            #    #print "has", curHas
            #    for dep, cget in curHas.iteritems():
            #        get = iceil(cget)-cget
            #        if get != 0:
            #            #print "ping"
            #            dep.calcRequiredCounts(get, curGet, curHas, invHas)
            #            curHas[dep] += get
            #            break
            #    else:
            #        break
            

            #won't affect curHas (hopefully)
            #while True:
            #    #print "get", curGet
            #    for dep, cget in curGet.iteritems():
            #        get = iceil(cget)-cget
            #        if get != 0:
            #            dep.calcRequiredCounts(get, curGet, curHas, invHas)
            #            curGet[dep] += get
            #            break
            #    else:
            #        break
            
            for dep, count in curHas.iteritems():
                curGet[dep] += count
            #for dep, count in invHas.iteritems():
            #    if dep not in curHas and curGet[dep] > 0:
            #        curGet[dep] = max(0, curGet[dep]-invHas[dep])
            
            curGet[self] += getCount
            for dep, count in curGet.items():
                if count <= 0:
                    del curGet[dep]
            return curGet
    def calcGetOrder(self, order=None, seen=None, validItems=None):
        #top-sort is fun
        
        if seen is None:
            seen = set([])
        top = False
        if order is None:
            top = True
            order = []
        for dep, count in self.depends+self.consumes:
            try:
                iter(dep)
            except TypeError:
                dep = [dep]
            for d in dep:
                d = TECH_MAP.get(d) or d
                if validItems is None or d in validItems:
                    if d not in seen:
                        d.calcGetOrder(order, seen, validItems)
                    break
        order.append(self)
        seen.add(self)
        if top:
            return order
    def calcGetWithInventory(self, inventory, getCount=1):
        invHas = defaultdict(int)
        for slot, item in inventory.items.items():
            if slot not in inventory.playerItemsRange: continue
            tech = TECH_MAP.get(item.itemId)
            if tech is None: continue
            invHas[tech] += item.count/tech.produces
        print invHas
        getCounts = self.calcRequiredCounts(getCount, invHas=invHas)
        order = self.calcGetOrder(validItems=set(getCounts.iterkeys()))
        return [(tech, getCounts[tech]) for tech in order]
    def command_getOrderly(self, client, getCount=1):
        orderGet = self.calcGetWithInventory(client.playerInventory, getCount)
        print orderGet
        for tech, evalCount in orderGet:
            print "evl %r %r" % (tech, evalCount) 
            for v in tech.command_get(client, evalCount):
                yield v
    def command_get(self, client, getCount=1):
        print "getting %r %r" % (self, getCount)
        
        if False: #make it a generator
            yield True
        #iterate over dependencies makeing sure we really do have requirements
        #done = False
        #while not done:
        #    done = True
        #    for dep, count in self.depends+self.consumes:
        #        print "dependency %d %r" % (count, dep)
        #        while not dep.clientHas(client, count):
        #            done = False
        #            for v in dep.command_get(client): #count/dep.produces
        #                yield v
        

#item representable in inventory
class TechItem(Tech):
    def __init__(self, depends, consumes, itemId, producesCount=1):
        Tech.__init__(self, depends, consumes, producesCount)
        self.itemId = itemId
    def __repr__(self):
        if self.itemId in BLOCKITEM_NAMES:
            return "TechItem(%r)" % BLOCKITEM_NAMES[self.itemId]
        return "TechItem(%r)" % self.itemId
    def clientHas(self, client, count=1):
        return client.inventoryHandler.currentWindow.countPlayerItemId(self.itemId) >= count
    def command_get(self, client, getCount=1):
        for v in Tech.command_get(self, client, getCount):
            yield v
        
        #try to grab any pickups < 5 blocks away
        #(Because sometimes we are so clumsy and drop things)
        for pickup in client.pickups.values():
            #if pickup.item.itemId == self.itemId and (client.pos-pickup.pos).mag() < 5:
            if (client.pos-pickup.pos).mag() < 5:
                for v in client.command_walkPathToPoint(pickup.pos):
                    if v == False: break
                    yield v
                else:
                    return

#item that can just be mined somewhere
class TechMineItem(TechItem):
    def __init__(self, itemId, mineTool=None, mineItem=None):
        if mineTool is None:
            TechItem.__init__(self, [], [], itemId)
        else:
            try:
                iter(mineTool)
            except TypeError:
                mineTool = [mineTool]
            
            #mineOptions = []
            #for v in mineTool:
            #    if isinstance(v, int):
            #        v = TECH_MAP[v]
            #    mineOptions.append(v)
            #if isinstance(mineTool, int): mineTool = TECH_MAP[mineTool]
            TechItem.__init__(self, [(mineTool, 1)], [], itemId)
            
        
        self.mineTool = mineTool
        self.mineItemId = mineItem or self.itemId
    def command_get(self, client, getCount=1):
        
        print "mineping"
        if self.mineTool is not None:
            #equipt the tool of choice (by now should have it in inventory)
            for tool in self.mineTool:
                tool = TECH_MAP.get(tool) or tool
                for v in client.playerInventory.command_equipItem(tool.itemId):
                    if v == False:
                        break
                    yield v
                else:
                    break
            else: #nothing was successfully equipped
                yield False
                return
        
        startCount = client.playerInventory.countPlayerItemId(self.itemId)
        
        while client.playerInventory.countPlayerItemId(self.itemId)-startCount < getCount*self.produces:
            for v in TechItem.command_get(self, client, getCount):
                yield v
            
            if client.playerInventory.countPlayerItemId(self.itemId)-startCount >= getCount*self.produces:
                break
            
            try:
                print "finding block %r" % self.mineItemId
                
                #done = [False]
                #result = [None]
                #def callBack(res):
                #    result[0] = res
                #    done[0] = True
                
                blockPos = client.map.searchForBlock(client.pos, self.mineItemId, timeout=60)
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

def buildConsumesFromRecipe(recipe):
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
        consumes = buildConsumesFromRecipe(recipe)
        TechItem.__init__(self, [], consumes, itemId, producedItem.count)
        
        self.recipe = recipe
        self.produced = producedItem
    def command_get(self, client, getCount=1):
        for v in TechItem.command_get(self, client, getCount):
            yield v
        
        for i in xrange(iceil(getCount)):
            print "assembly get"
            print "place items"
            craftSlots = buildSlotsFromRecipe(self.recipe)
            for itemId, slots in craftSlots.iteritems():
                print itemId, slots
                for v in client.playerInventory.command_fillSlotsWithPlayerItem(itemId, slots):
                    yield v
        
            client.playerInventory.items[0] = copy.copy(self.produced)
        
            print "retrieve"
            emptySlot = client.playerInventory.findPlayerEmptySlot()
            if emptySlot is None:
                print "no empty slot to store item"
                yield False
                return
            for v in client.playerInventory.command_swapSlots(0, emptySlot):
                yield v
            
            #Destory recipe
            for i in xrange(1, 5):
                if i in client.playerInventory.items:
                    del client.playerInventory.items[i]
        
        #close the window (throwing everything out)
        client.inventoryHandler.closeWindow(client.playerInventory)
        yield True

#Tech made with crafting table
class TechCraftItem(TechItem):
    def __init__(self, itemId, recipe, producedItem):
        consumes = buildConsumesFromRecipe(recipe)
        TechItem.__init__(self, [(TECH_MAP[BLOCK_CRAFTINGTABLE], 1)], consumes, itemId, producedItem.count)
        
        self.recipe = recipe
        self.produced = producedItem
    def command_get(self, client, getCount=1):
        for v in TechItem.command_get(self, client, getCount):
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
        
        for i in xrange(iceil(getCount)):
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
        
            print "retrieve"
        
            emptySlot = craftingWindow.findPlayerEmptySlot()
            if emptySlot is None:
                print "no empty slot to store item"
                yield False
                return
            for v in craftingWindow.command_swapSlots(0, emptySlot):
                yield v
            
            #Destroy recipe
            for i in xrange(1, 10):
                if i in craftingWindow.items:
                    del craftingWindow.items[i]
            
        
        # NO - #no need to other items because they'll pop out when closing window
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

TECH_MAP[BLOCK_COBBLESTONE] = TechMineItem(BLOCK_COBBLESTONE,
    (ITEM_WOODPICKAXE, ITEM_STONEPICKAXE, ITEM_IRONPICKAXE, ITEM_GOLDPICKAXE, ITEM_DIAMONDPICKAXE), BLOCK_STONE)
TECH_MAP[ITEM_COAL] = TechMineItem(ITEM_COAL,
    (ITEM_WOODPICKAXE, ITEM_STONEPICKAXE, ITEM_IRONPICKAXE, ITEM_GOLDPICKAXE, ITEM_DIAMONDPICKAXE), BLOCK_COALORE)

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

TECH_MAP[BLOCK_IRONORE] = TechMineItem(BLOCK_IRONORE,
    (ITEM_STONEPICKAXE, ITEM_IRONPICKAXE, ITEM_DIAMONDPICKAXE))


