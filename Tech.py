#MineBot
#GPL and all that
# - espes

#Everyone loves really bad code

from __future__ import division
from time import sleep
from collections import defaultdict

from twisted.internet import threads
from twisted.python import log, failure

from Utility import *
from Inventory import *

from bravo_recipes import recipes

#should only be called after TECH_MAP construction
def makeTech(d):
    if isinstance(d, Tech):
        return d
    elif isinstance(d, int):
        return TECH_MAP.get(d)
    elif isinstance(d, Item):
        return TECH_MAP.get(d.itemId)
    else:
        raise ValueError, "%r can not be made into tech" % (d,)

class Tech(object):
    def __init__(self, depends, consumes, producesCount=1):
        self.depends = depends
        self.consumes = consumes
        
        self.produces = producesCount
    def clientHas(self, client, count=1):
        pass
    
    #Note: due to lazyness, asume any item's depends won't also be a consume somewhere
    def calcRequiredCounts(self, getCount=1, curGet=None,
                           hasReq=None, invHas=None):
        #print "%r %r" % (self, getCount)
        top = False
        if curGet is None:
            curGet = defaultdict(int)
            top = True
        if hasReq is None:
            hasReq = defaultdict(int)
        if invHas is None:
            invHas = defaultdict(int)
        
        for dep, count in self.depends:
            #handle when there are optional depends
            # - This is broken
            try:
                ndep = map(makeTech, dep)
                
                dep = max(ndep, key=lambda d: curGet[d]+invHas[d])
            except TypeError: #not iterable
                dep = makeTech(dep)
            
            get = (getCount/abs(getCount))*(count/dep.produces)
            hasReq[dep] = max(get, hasReq[dep])
            dep.calcRequiredCounts(get, curGet, hasReq, invHas)

        for dep, count in self.consumes:
            dep = makeTech(dep)
            
            get = getCount*count/dep.produces
            dep.calcRequiredCounts(get, curGet, hasReq, invHas) 
        
        curGet[self] += getCount
        
        if top:
            #negate inventory item values
            for dep, count in invHas.iteritems():
                dep = makeTech(dep)
                
                if dep is not self and count > 0 and curGet[dep] > 0:
                    dep.calcRequiredCounts(-min(count, curGet[dep]), curGet, hasReq, invHas)
            
            #fix so dependency items have at most min required
            for dep, count in hasReq.iteritems():
                if curGet[dep] > count:
                    dep.calcRequiredCounts(count-curGet[dep], curGet, hasReq, invHas)
            
            for dep, count in curGet.items():
                if count <= 0:
                    del curGet[dep]
            
            #fix so all the gets have been rounded up
            #evaluate them in tolological order so current adjustments won't affect past ones
            order = self.calcGetOrder()
            for dep in order[::-1]:
                if dep in curGet:
                    cget = curGet[dep]
                    get = iceil(cget)-cget
                    if get != 0:
                        dep.calcRequiredCounts(get, curGet, hasReq, invHas)
            
            for dep, count in curGet.items():
                if count <= 0:
                    del curGet[dep]
            return curGet
    def calcGetOrder(self, order=None, seen=None, validItems=None):
        #top-sort is fun
        top = False
        if order is None:
            top = True
            order = []
        if seen is None:
            seen = set([])
        
        for dep, count in self.depends+self.consumes:
            try:
                iter(dep)
            except TypeError:
                dep = [dep]
            for d in dep:
                d = makeTech(d)
                
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
            if slot not in inventory.playerSlotsRange: continue
            tech = makeTech(item)
            if tech is None: continue
            
            invHas[tech] += item.count/tech.produces
        
        logging.debug("invHas: %r" % invHas)
        
        getCounts = self.calcRequiredCounts(getCount, invHas=invHas)
        logging.debug("getCounts: %r" % invHas)
        
        order = self.calcGetOrder(validItems=set(getCounts.iterkeys()))
        logging.debug("order: %r" % invHas)
        
        return [(tech, getCounts[tech]) for tech in order]
    def command_getOrderly(self, client, getCount=1):
        orderGet = self.calcGetWithInventory(client.playerInventory, getCount)
        logging.debug("orderGet: %r" % orderGet)
        
        for tech, evalCount in orderGet:
            logging.debug("evl %r %r" % (tech, evalCount))
            for v in tech.command_get(client, evalCount):
                yield v
    def command_get(self, client, getCount=1):
        logging.info("getting %r %r" % (self, getCount))
        
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
            return "%s(%r)" % (self.__class__.__name__, BLOCKITEM_NAMES[self.itemId])
        return "%s(%r)" % (self.__class__.__name__, self.itemId)
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
                try:
                    for v in client.command_walkPathTo(pickup.pos): yield v
                except Exception:
                    pass
                else:
                    return

#item that can just be mined somewhere
class TechMineItem(TechItem):
    def __init__(self, itemId, mineTool=None, mineItem=None):
        if mineTool is None:
            TechItem.__init__(self, [], [], itemId)
        else:
            #make mineTool iterable for convenience later
            try:
                iter(mineTool)
            except TypeError:
                mineTool = [mineTool]
            TechItem.__init__(self, [(mineTool, 1)], [], itemId)
            
        
        self.mineTool = mineTool
        self.mineItemId = mineItem or self.itemId
    def command_get(self, client, getCount=1):
        
        logging.debug("mineping")
        if self.mineTool is not None:
            #equipt the tool of choice (by now should have it in inventory)
            for tool in self.mineTool:
                tool = TECH_MAP.get(tool) or tool
                try:
                    for v in client.playerInventory.command_equipItem(tool.itemId): yield v
                except Exception:
                    pass
                else:
                    break
            else:
                raise Exception, "couldn't equipt required tool"
        
        startCount = client.playerInventory.countPlayerItemId(self.itemId)
        
        while client.playerInventory.countPlayerItemId(self.itemId)-startCount < getCount*self.produces:
            for v in TechItem.command_get(self, client, getCount): yield v
            
            if client.playerInventory.countPlayerItemId(self.itemId)-startCount >= getCount*self.produces:
                break
            
            logging.info("finding block %r" % (self.mineItemId,))
            
            deferred = threads.deferToThread(client.map.searchForBlock,
                            client.pos, self.mineItemId)
            while not hasattr(deferred, 'result'): #hack
                yield True
            if not isinstance(deferred.result, Point):
                logging.error("couldn't find block!")
                if isinstance(deferred.result, failure.Failure):
                    log.err(deferred.result)
                raise Exception, "couldn't find block!"
            blockPos = deferred.result
            logging.debug("found at %r" % (blockPos,))
            
            try:
                for v in client.command_walkPathTo(blockPos,
                    destructive=True, blockBreakPenalty=10):
                    yield v
            except Exception as ex:
                logging.exception(ex)
                continue

def buildConsumesFromRecipe(recipe):
    depends = defaultdict(int)
    for r in recipe.recipe:
        if r is None: continue
        (itemId, _), count = r
        
        assert isinstance(itemId, int)
        
        depends[itemId] += count
    return depends.items()

class TechFromRecipe(TechItem):
    def __init__(self, depends, recipe):
        consumes = buildConsumesFromRecipe(recipe)
        (producedItemId, _), producedCount = recipe.provides
        TechItem.__init__(self, depends, consumes, producedItemId, producedCount)
        
        self.recipe = recipe

#Tech made with the inventory crafting thing
class TechAssembleItem(TechFromRecipe):
    def __init__(self, recipe):
        TechFromRecipe.__init__(self, [], recipe)
    def command_get(self, client, getCount=1):
        for v in TechFromRecipe.command_get(self, client, getCount):
            yield v
        try:
            for i in xrange(iceil(getCount)):
                logging.debug("assembly get")
                logging.debug("place items")
            
                for v in client.playerInventory.command_fillRecipe(self.recipe):
                    yield v
            
                logging.debug("retrieve")
                for v in client.playerInventory.command_moveToPlayerInventory(0):
                    yield v
            yield True
        finally:
            client.inventoryHandler.closeWindow(client.playerInventory)

#Tech made with crafting table
class TechCraftItem(TechFromRecipe):
    def __init__(self, recipe):
        TechFromRecipe.__init__(self, [(BLOCK_WORKBENCH, 1)], recipe)
    def command_get(self, client, getCount=1):
        for v in TechFromRecipe.command_get(self, client, getCount):
            yield v
        
        #Move up one block
        placePos = client.pos
        for v in client.command_walkPathTo(client.pos + (0, 1, 0), destructive=True):
            yield v
        
        logging.debug("equip crafting table")
        for v in client.playerInventory.command_equipItem(BLOCK_WORKBENCH):
            yield v
        
        logging.debug("place crafting table")
        if not client.placeBlock(placePos + (0, -1, 0)):
            raise Exception, "failed placing crafting table"
        yield True
        
        if not client.map[placePos] == BLOCK_WORKBENCH:
            raise Exception, "failed placing crafting table"

        #hit it
        if not client.placeBlock(placePos):
            raise Exception, "failed hitting crafing table"
        yield True
        
        logging.debug("wait for crafting window open")
        #Wait for window to come up
        while not isinstance(client.inventoryHandler.currentWindow, WorkBenchInventory):
            yield True
        
        craftingWindow = client.inventoryHandler.currentWindow
        
        
        for i in xrange(iceil(getCount)):
            logging.debug("place items")
            for v in craftingWindow.command_fillRecipe(self.recipe):
                yield v
            logging.debug("retrieve")
            for v in craftingWindow.command_moveToPlayerInventory(0):
                yield v
            
        
        client.inventoryHandler.closeWindow(craftingWindow)
        
        #walk back down destroying the crafting table
        for v in client.command_walkPathTo(placePos, destructive=True, blockBreakPenalty=0):
            yield v

TECH_MAP = {
    
    #Also, breaking saplings :\
    BLOCK_SAPLING: TechMineItem(BLOCK_SAPLING, mineItem=BLOCK_LEAVES),
    #Also, breaking grass :\
    BLOCK_DIRT: TechMineItem(BLOCK_DIRT),
    ITEM_FLINT: TechMineItem(ITEM_FLINT, mineItem=BLOCK_GRAVEL),
    BLOCK_SAND: TechMineItem(BLOCK_SAND),
    BLOCK_LOG: TechMineItem(BLOCK_LOG),
    
    BLOCK_COBBLESTONE: TechMineItem(BLOCK_COBBLESTONE,
        (ITEM_WOODENPICKAXE, ITEM_STONEPICKAXE, ITEM_IRONPICKAXE, ITEM_GOLDPICKAXE, ITEM_DIAMONDPICKAXE),
        BLOCK_STONE),
    
    ITEM_COAL: TechMineItem(ITEM_COAL,
            (ITEM_WOODENPICKAXE, ITEM_STONEPICKAXE, ITEM_IRONPICKAXE, ITEM_GOLDPICKAXE, ITEM_DIAMONDPICKAXE),
            BLOCK_COALORE),
    
    BLOCK_IRONORE: TechMineItem(BLOCK_IRONORE,
                (ITEM_STONEPICKAXE, ITEM_IRONPICKAXE, ITEM_DIAMONDPICKAXE)),
    
    ITEM_DIAMOND: TechMineItem(ITEM_DIAMOND,
                (ITEM_IRONPICKAXE, ITEM_DIAMONDPICKAXE),
                BLOCK_DIAMONDORE)
}
for recipe in recipes:
    (producesItemId, _), producesCount = recipe.provides
    craftW, craftH = recipe.dimensions
    if producesItemId in TECH_MAP:
        continue
    
    if craftW <= 2 and craftH <= 2:
        TECH_MAP[producesItemId] = TechAssembleItem(recipe)
    elif craftW <= 3 and craftH <= 3:
        TECH_MAP[producesItemId] = TechCraftItem(recipe)
