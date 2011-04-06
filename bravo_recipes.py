#stolen from the awesome server Bravo (http://github.com/MostAwesomeDude/bravo)
#insert MIT attribution and copyright here

from bravo_blocks import blocks, items

class Recipe(object):
    pass

#Basics
class OneBlock(Recipe):
    #first used in basics, but also usable in Misc. Recipes

    dimensions = (1, 1)

    def __init__(self, material, provides, amount, name=None):
        self.name = name
        self.recipe = (
            (material.key, 1),
        )
        self.provides = (provides.key, amount)

class OneByTwo(Recipe):

    dimensions = (1, 2)

    def __init__(self, topMat, btmMat, provides, amount, name=None):
        self.name = name
        self.recipe = (
            (topMat.key, 1),
            (btmMat.key, 1),
        )
        self.provides = (provides.key, amount)

class TwoByTwo(Recipe):

    dimensions = (2, 2)

    def __init__(self, material, provides, name=None):
        self.name = name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
        )
        self.provides = (provides.key, 1)

class ChestFurnace(Recipe):

    dimensions = (3, 3)

    def __init__(self, material, provides, name=None):
        self.name = name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            None,
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
        )
        self.provides = (provides.key, 1)


class ThreeByThree(Recipe):
    #Not all 3x3s fit here, this is only center changable 3x3s.

    dimensions = (3, 3)

    def __init__(self, material, center, provides, name=None):
        self.name = name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (center.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
        )
        self.provides = (provides.key, 1)

#Block
class TNT(Recipe):

    dimensions = (3, 3)

    name = "tnt"

    recipe = (
        (items["sulphur"].key, 1),
        (blocks["sand"].key, 1),
        (items["sulphur"].key, 1),
        (blocks["sand"].key, 1),
        (items["sulphur"].key, 1),
        (blocks["sand"].key, 1),
        (items["sulphur"].key, 1),
        (blocks["sand"].key, 1),
    )
    provides = (blocks["tnt"].key, 1)

class ThreeByOne(Recipe):

    dimensions = (3, 1)

    def __init__(self, material, provides, amount, name=None):
        self.name = name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
        )
        self.provides = (provides.key, amount)

class Stairs(Recipe):

    dimensions = (3, 3)

    def __init__(self, material, provides, name=None):
        self.name = "%s-name" % name
        self.recipe = (
            (material.key, 1),
            None,
            None,
            (material.key, 1),
            (material.key, 1),
            None,
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
        )
        self.provides = (provides.key, 1)

class Bookshelf(Recipe):

    dimensions = (3, 3)

    name = "bookshelf"

    recipe = (
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (items["book"].key, 1),
        (items["book"].key, 1),
        (items["book"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
    )
    provides = (blocks["bookshelf"].key, 1)

#Armor
class Helmet(Recipe):

    dimensions = (3, 2)

    def __init__(self, material, provides, name=None):
        self.name = "%s-helmet" % name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            None,
            (material.key, 1),
        )
        self.provides = (provides.key, 1)

class Chestplate(Recipe):

    dimensions = (3, 3)

    def __init__(self, material, provides, name=None):
        self.name = "%s-chestplate" % name
        self.recipe = (
            (material.key, 1),
            None,
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
        )
        self.provides = (provides.key, 1)

class Leggings(Recipe):

    dimensions = (3, 3)

    def __init__(self, material, provides, name=None):
        self.name = "%s-leggings" % name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            None,
            (material.key, 1),
            (material.key, 1),
            None,
            (material.key, 1),
        )
        self.provides = (provides.key, 1)

class Boots(Recipe):

    dimensions = (3, 2)

    def __init__(self, material, provides, name=None):
        self.name = "%s-boots" % name
        self.recipe = (
            (material.key, 1),
            None,
            (material.key, 1),
            (material.key, 1),
            None,
            (material.key, 1),
        )
        self.provides = (provides.key, 1)

#Tools
class Axe(Recipe):

    dimensions = (2, 3)

    def __init__(self, material, provides, name=None):
        self.name = "%s-axe" % name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (items["stick"].key, 1),
            None,
            (items["stick"].key, 1),
        )
        self.provides = (provides.key, 1)

class Pickaxe(Recipe):

    dimensions = (3, 3)

    def __init__(self, material, provides, name=None):
        self.name = "%s-pickaxe" % name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            None,
            (items["stick"].key, 1),
            None,
            None,
            (items["stick"].key, 1),
            None,
        )
        self.provides = (provides.key, 1)

class Shovel(Recipe):

    dimensions = (3, 1)

    def __init__(self, material, provides, name=None):
        self.name = "%s-shovel" % name
        self.recipe = (
            (material.key, 1),
            None,
            (items["stick"].key, 1),
            None,
            None,
            (items["stick"].key, 1),
            None,
        )
        self.provides = (provides.key, 1)

class Hoe(Recipe):

    dimensions = (3, 2)

    def __init__(self, material, provides, name=None):
        self.name = "%s-hoe" % name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            None,
            (items["stick"].key, 1),
            None,
            (items["stick"].key, 1),
        )
        self.provides = (provides.key, 1)

class ClockCompass(Recipe):

    dimensions = (3, 3)

    def __init__(self, material, provides, name=None):
        self.name = name
        self.recipe = (
            None,
            (material.key, 1),
            None,
            (material.key, 1),
            (items["redstone"].key, 1),
            (material.key, 1),
            None,
            (material.key, 1),
            None,
        )
        self.provides = (provides.key, 1)

class FlintAndSteel(Recipe):

    name = "flint-and-steel"

    dimensions = (2, 2)

    recipe = (
        (items["iron-ingot"].key, 1),
        None,
        None,
        (items["flint"].key, 1)
    )
    provides = (items["flint-and-steel"].key, 1)

class FishingRod(Recipe):

    name = "fishing-rod"

    dimensions = (3, 3)

    recipe = (
        None,
        None,
        (items["stick"].key, 1),
        None,
        (items["stick"].key, 1),
        (items["string"].key, 1),
        None,
        (items["stick"].key, 1),
        None,
        (items["string"].key, 1),
    )
    provides = (items["fishing-rod"].key, 1)

class BowlBucket(Recipe):

    dimensions = (2, 3)

    def __init__(self, material, provides, amount, name=None):
        self.name = name
        self.recipe = (
            (material.key, 1),
            None,
            (material.key, 1),
            None,
            (material.key, 1),
            None,
        )
        self.provides = (provides.key, amount)

#Weapons
class Sword(Recipe):

    dimensions = (1, 3)

    def __init__(self, material, provides, name=None):
        self.name = "%s-sword" % name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            (items["stick"].key, 1),
        )
        self.provides = (provides.key, 1)

class Bow(Recipe):

    dimensions = (3, 3)

    name = "bow"

    recipe = (
        (items["string"].key, 1),
        (items["stick"].key, 1),
        None,
        (items["string"].key, 1),
        None,
        (items["stick"].key, 1),
        (items["string"].key, 1),
        (items["stick"].key, 1),
        None,
    )
    provides = (items["bow"].key, 1)

class Arrow(Recipe):

    dimensions = (1, 3)

    name = "arrow"

    recipe = (
        (items["coal"].key, 1),
        (items["stick"].key, 1),
        (items["feather"].key, 1),
    )
    provides = (items["arrow"].key, 4)

#Transportation
class CartBoat(Recipe):
    #at the time of creation, this only the cart and boat had this shape

    dimensions = (3, 2)

    def __init__(self, material, provides, name=None):
        self.name = name
        self.recipe = (
            (material.key, 1),
            None,
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
        )
        self.provides = (provides.key, 1)

class Track(Recipe):

    dimensions = (3, 3)

    name = "track"

    recipe = (
        (items["iron-ingot"].key, 1),
        None,
        (items["iron-ingot"].key, 1),
        (items["iron-ingot"].key, 1),
        (items["stick"].key, 1),
        (items["iron-ingot"].key, 1),
        (items["iron-ingot"].key, 1),
        None,
        (items["iron-ingot"].key, 1),
    )
    provides = (blocks["tracks"].key, 16)

#Mechanism
class Door(Recipe):

    dimensions = (2, 3)

    def __init__(self, material, provides, name=None):
        self.name = "%s-door" % name
        self.recipe = (
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
            (material.key, 1),
        )
        self.provides = (provides.key, 1)

class Dispenser(Recipe):

    dimensions = (3, 3)

    name = "dispenser"

    recipe = (
        (blocks["cobblestone"].key, 1),
        (blocks["cobblestone"].key, 1),
        (blocks["cobblestone"].key, 1),
        (blocks["cobblestone"].key, 1),
        (items["bow"].key, 1),
        (blocks["cobblestone"].key, 1),
        (items["redstone"].key, 1),
        (blocks["cobblestone"].key, 1),
    )
    provides = (blocks["dispenser"].key, 1)

#Food
class MushroomSoup(Recipe):

    dimensions = (1, 3)

    name = "shroomstew"

    recipe = (
        (blocks["red-mushroom"].key, 1),
        (blocks["brown-mushroom"].key, 1),
        (items["bowl"].key, 1),
    )
    provides = (items["mushroom-soup"].key, 1)

class Cake(Recipe):

    dimensions = (3, 3)

    name = "cake"

    recipe = (
        (items["milk"].key, 1),
        (items["milk"].key, 1),
        (items["milk"].key, 1),
        (items["egg"].key, 1),
        (items["sugar"].key, 1),
        (items["egg"].key, 1),
        (items["wheat"].key, 1),
        (items["wheat"].key, 1),
        (items["wheat"].key, 1),
    )
    provides = (items["cake"].key, 1)

class Sign(Recipe):

    dimensions = (3, 3)

    name = "sign"

    recipe = (
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        None,
        (items["stick"].key, 1),
        None,
    )
    provides = (items["sign"].key, 1)

class Ladder(Recipe):

    dimensions = (3, 3)

    name = "ladder"

    recipe = (
        (items["stick"].key, 1),
        None,
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        None,
        (items["stick"].key, 1),
    )
    provides = (blocks["ladder"].key, 1)

class Book(Recipe):

    dimensions = (1, 3)

    name = "book"

    recipe = (
        (items["paper"].key, 1),
        (items["paper"].key, 1),
        (items["paper"].key, 1),
    )
    provides = (items["book"].key, 1)

class Fence(Recipe):

    name = "fence"

    dimensions = (3, 2)

    recipe = (
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
    )
    provides = (blocks["fence"].key, 2)

#--Recipies--
recipes = [
    #Basics
    OneBlock(blocks["log"], blocks["wood"], 4, "wood"),
    OneByTwo(blocks["wood"], blocks["wood"], items["stick"], 4, "sticks"),
    OneByTwo(items["coal"], items["stick"], blocks["torch"], 4, "torches"),
    TwoByTwo(blocks["wood"], blocks["workbench"], "workbench"),
    ChestFurnace(blocks["cobblestone"], blocks["furnace"], "furnace"),
    ChestFurnace(blocks["wood"], blocks["chest"], "chest"),
    
    #Block
    ThreeByThree(items["iron-ingot"], items["iron-ingot"], blocks["iron"], "iron-block"),
    ThreeByThree(items["gold-ingot"], items["gold-ingot"], blocks["gold"], "gold-block"),
    ThreeByThree(items["diamond"], items["diamond"], blocks["diamond"], "diamond-block"),
    ThreeByThree(items["glowstone-dust"], items["glowstone-dust"], blocks["lightstone"], "lightstone"),
    ThreeByThree(items["string"], items["string"], blocks["wool"], "wool"),
    TNT(),
    ThreeByOne(blocks["cobblestone"], blocks["step"], 1, "step"),
    Stairs(blocks["wood"], blocks["wooden-stairs"], "wood"),
    Stairs(blocks["cobblestone"], blocks["stone-stairs"], "stone"),
    TwoByTwo(items["snowball"], blocks["snow-block"], "snow-block"),
    TwoByTwo(items["clay-balls"], blocks["clay"], "clay-block"),
    TwoByTwo(items["clay-brick"], blocks["brick"], "brick"),
    Bookshelf(),
    TwoByTwo(blocks["sand"], blocks["sandstone"], "sandstone"),
    OneByTwo(blocks["pumpkin"], items["stick"], blocks["jack-o-lantern"], 1, "jack-o-lantern"),
    
    #Tools
    Axe(blocks["wood"], items["wooden-axe"], "wood"),
    Axe(blocks["cobblestone"], items["stone-axe"], "stone"),
    Axe(items["iron-ingot"], items["iron-axe"], "iron"),
    Axe(items["gold-ingot"], items["gold-axe"], "gold"),
    Axe(items["diamond"], items["diamond-axe"], "diamond"),
    Pickaxe(blocks["wood"], items["wooden-pickaxe"], "wood"),
    Pickaxe(blocks["cobblestone"], items["stone-pickaxe"], "stone"),
    Pickaxe(items["iron-ingot"], items["iron-pickaxe"], "iron"),
    Pickaxe(items["gold-ingot"], items["gold-pickaxe"], "gold"),
    Pickaxe(items["diamond"], items["diamond-pickaxe"], "diamond"),
    Shovel(blocks["wood"], items["wooden-shovel"], "wood"),
    Shovel(blocks["cobblestone"], items["stone-shovel"], "stone"),
    Shovel(items["iron-ingot"], items["iron-shovel"], "iron"),
    Shovel(items["gold-ingot"], items["gold-shovel"], "gold"),
    Shovel(items["diamond"], items["diamond-shovel"], "diamond"),
    Hoe(blocks["wood"], items["wooden-hoe"], "wood"),
    Hoe(blocks["cobblestone"], items["stone-hoe"], "stone"),
    Hoe(items["iron-ingot"], items["iron-hoe"], "iron"),
    Hoe(items["gold-ingot"], items["gold-hoe"], "gold"),
    Hoe(items["diamond"], items["diamond-hoe"], "diamond"),
    ClockCompass(items["iron-ingot"], items["clock"], "clock"),
    ClockCompass(items["gold-ingot"], items["compass"], "compass"),
    FlintAndSteel(),
    FishingRod(),
    BowlBucket(items["iron-ingot"], items["bucket"], 1, "bucket"),
    
    #Weapon,
    Sword(blocks["wood"], items["wooden-sword"], "wood"),
    Sword(blocks["cobblestone"], items["stone-sword"], "stone"),
    Sword(items["iron-ingot"], items["iron-sword"], "iron"),
    Sword(items["gold-ingot"], items["gold-sword"], "gold"),
    Sword(items["diamond"], items["diamond-sword"], "diamond"),
    Bow(),
    Arrow(),
    
    #Armor,
    Helmet(items["leather"], items["leather-helmet"], "leather"),
    Helmet(items["gold-ingot"], items["gold-helmet"], "gold"),
    Helmet(items["iron-ingot"], items["iron-helmet"], "iron"),
    Helmet(items["diamond"], items["diamond-helmet"], "diamond"),
    Helmet(blocks["fire"], items["chainmail-helmet"], "chainmail"),
    Chestplate(items["leather"], items["leather-chestplate"], "leather"),
    Chestplate(items["gold-ingot"], items["gold-chestplate"], "gold"),
    Chestplate(items["iron-ingot"], items["iron-chestplate"], "iron"),
    Chestplate(items["diamond"], items["diamond-chestplate"], "diamond"),
    Chestplate(blocks["fire"], items["chainmail-chestplate"], "chainmail"),
    Leggings(items["leather"], items["leather-leggings"], "leather"),
    Leggings(items["gold-ingot"], items["gold-leggings"], "gold"),
    Leggings(items["iron-ingot"], items["iron-leggings"], "iron"),
    Leggings(items["diamond"], items["diamond-leggings"], "diamond"),
    Leggings(blocks["fire"], items["chainmail-leggings"], "chainmail"),
    Boots(items["leather"], items["leather-boots"], "leather"),
    Boots(items["gold-ingot"], items["gold-boots"], "gold"),
    Boots(items["iron-ingot"], items["iron-boots"], "iron"),
    Boots(items["diamond"], items["diamond-boots"], "diamond"),
    Boots(blocks["fire"], items["chainmail-boots"], "chainmail"),
    
    #Transportation,
    CartBoat(items["iron-ingot"], items["mine-cart"], "minecart"),
    OneByTwo(blocks["furnace"], items["mine-cart"], items["powered-minecart"], 1, "poweredmc"),
    OneByTwo(blocks["chest"], items["mine-cart"], items["storage-minecart"], 1, "storagemc"),
    Track(),
    CartBoat(blocks["wood"], items["boat"], "boat"),
    
    #Mechanism,
    Door(blocks["wood"], blocks["wooden-door"], "wood"),
    Door(items["iron-ingot"], blocks["iron-door"], "iron"),
    ThreeByOne(blocks["wood"], blocks["wooden-plate"], 1, "wood-plate"),
    ThreeByOne(blocks["stone"], blocks["stone-plate"], 1, "stone-plate"),
    OneByTwo(blocks["stone"], blocks["stone"], blocks["stone-button"], 1, "stone-btn"),
    OneByTwo(items["redstone"], items["stick"], blocks["redstone-torch"], 1, "redstone-torch"),
    OneByTwo(items["stick"], blocks["cobblestone"], blocks["lever"], 1, "lever"),
    ThreeByThree(blocks["wood"], items["redstone"], blocks["note-block"], "noteblock"),
    ThreeByThree(blocks["wood"], items["diamond"], blocks["jukebox"], "jukebox"),
    Dispenser(),
    
    #Food
    BowlBucket(blocks["wood"], items["bowl"], 4, "bowl"),
    MushroomSoup(),
    ThreeByOne(items["wheat"], items["bread"], 1, "bread"),
    OneBlock(blocks["sugar-cane"], items["sugar"], 1, "sugar"),
    Cake(),
    ThreeByThree(blocks["gold"], items["apple"], items["golden-apple"], "goldapple"),
    
    #Misc.
    OneBlock(blocks["iron"], items["iron-ingot"], 9, "iron-ingots"),
    OneBlock(blocks["gold"], items["gold-ingot"], 9, "gold-ingots"),
    OneBlock(blocks["diamond"], items["diamond"], 9, "diamonds"),
    ThreeByThree(items["stick"], blocks["wool"], items["paintings"], "paintings"),
    Sign(),
    Ladder(),
    ThreeByOne(blocks["sugar-cane"], items["paper"], 3, "paper"),
    Book(),
    Fence()
]

recipesByName = dict((recipe.name, recipe) for recipe in recipes)
