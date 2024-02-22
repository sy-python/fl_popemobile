import numbers
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve
from scipy.sparse import csc_matrix
from scipy.optimize import linprog
from enum import Enum, auto
from itertools import count

import numpy as np

'''
TODO
- electrostatic machine
- khan's heart stuff esp. ivory
'''

class Rarity(Enum):
    Rare = 10
    Unusual = 20
    VeryInfrequent = 50
    Infrequent = 80
    Standard = 100
    Frequent = 200
    Abundant = 500
    Ubiquitous = 1000

class Item(Enum):
    Echo = 0

    Action = 1
    CardDraws = 2 # Fake item
    # DayOfCardDraws = 3 # Fake item

    # Menaces
    Wounds = auto()
    Scandal = auto()
    Suspicion = auto()
    Nightmares = auto()
    SeeingBanditryInTheUpperRiver = auto()
    InCorporateDebt = auto()

    # Favours
    FavBohemians = auto()
    FavChurch = auto()
    FavConstables = auto()
    FavCriminals = auto()
    FavDocks = auto()
    FavGreatGame = auto()
    FavHell = auto()
    FavRevolutionaries = auto()
    FavRubberyMen = auto()
    FavSociety = auto()
    FavTombColonies = auto()
    FavUrchins = auto()

    # Connected
    ConnectedBenthic = auto()

    # Academic
    MemoryOfDistantShores = auto()
    IncisiveObservation = auto()
    UnprovenancedArtefact = auto()
    VolumeOfCollatedResearch = auto()
    LostResearchAssistant = auto()

    # Curiosity
    WhirringContraption = auto()
    OilOfCompanionship = auto()

    # Cartography
    ShardOfGlim = auto()
    MapScrap = auto()
    ZeeZtory = auto()

    # Currency
    HinterlandScrip = auto()
    RatShilling = auto()

    # Elder
    JadeFragment = auto()
    MysteryOfTheElderContinent = auto()
    AntiqueMystery = auto()

    # Goods
    CertifiableScrap = auto()
    NevercoldBrassSliver = auto()
    PreservedSurfaceBlooms = auto()
    KnobOfScintillack = auto()
    PieceOfRostygold = auto()

    # Great Game
    ViennaOpening = auto()
    FinalBreath = auto()
    QueenMate = auto()

    # Historical
    SilveredCatsClaw = auto()
    UnlawfulDevice = auto()

    # Infernal
    BrilliantSoul = auto()
    BrightBrassSkull = auto()
    QueerSoul = auto()

    # Influence
    CompromisingDocument = auto()
    FavourInHighPlaces = auto()

    # Legal
    SwornStatement = auto()
    CaveAgedCodeOfHonour = auto()
    LegalDocument = auto()

    # Luminosity
    LumpOfLamplighterBeeswax = auto()
    MemoryOfLight = auto()

    # Mysteries
    WhisperedHint = auto()
    CrypticClue = auto()
    AppallingSecret = auto()
    JournalOfInfamy = auto()
    TaleOfTerror = auto()
    ExtraordinaryImplication = auto()
    UncannyIncunabulum = auto()

    # Nostaliga
    RomanticNotion = auto()
    VisionOfTheSurface = auto()

    # Osteology
    AlbatrossWing = auto()
    AmberCrustedFin = auto()
    BoneFragments = auto()
    FemurOfAJurassicBeast = auto()
    FinBoneCollected = auto()
    FlourishingRibcage = auto()
    HolyRelicOfTheThighOfStFiacre = auto()
    HornedSkull = auto()
    HumanArm = auto()
    HumanRibcage = auto()
    JetBlackStinger = auto()
    MammothRibcage = auto()
    PlasterTailBones = auto()
    PrismaticFrame = auto()
    SabreToothedSkull = auto()
    SegmentedRibcage = auto()
    SkeletonWithSevenNecks = auto()
    SurveyOfTheNeathsBones = auto()
    ThornedRibcage = auto()
    UnidentifiedThighbone = auto()
    WingOfAYoungTerrorBird = auto()
    WitheredTentacle = auto()

    # Rag Trade
    WhisperSatinScrap = auto()
    ThirstyBombazineScrap = auto()

    # Ratness
    RatOnAString = auto()
    RattyReliquary = auto()

    # Rubbery
    NoduleOfDeepAmber = auto()
    NoduleOfWarmAmber = auto()
    UnearthlyFossil = auto()
    NoduleOfTremblingAmber = auto()
    NoduleOfPulsatingAmber = auto()

    # Rumour
    ScrapOfIncendiaryGossip = auto()
    NightOnTheTown = auto()
    RumourOfTheUpperRiver = auto()

    # Sustenance
    RemainsOfAPinewoodShark = auto()
    BasketOfRubberyPies = auto()
    JasmineLeaves = auto()
    TinnedHam = auto()

    # Theological
    ApostatesPsalm = auto()

    # Wines
    BottleOfStranglingWillowAbsinthe = auto()

    # Wild Words
    ManiacsPrayer = auto()
    CorrespondencePlaque = auto()
    AeolianScream = auto( )
    StormThrenody = auto()
    NightWhisper = auto()


    # Zee-Treasures
    MoonPearl = auto()
    DeepZeeCatch = auto()
    RoyalBlueFeather = auto()
    AmbiguousEolith = auto()
    CarvedBallOfStygianIvory = auto()
    LiveSpecimen = auto()
    MemoryOfAShadowInVarchas = auto()
    OneiricPearl = auto()

    # -----
    # Equipment
    # -----

    # Weapon
    ConsignmentOfScintillackSnuff = auto()

    # Companion
    SulkyBat = auto()

    # -----
    # Qualities
    # -----

    # BoardMemberTentacledEntrepreneur = auto()
    ResearchOnAMorbidFad = auto()
    
    # MakingWaves = auto()
    Tribute = auto()

    # ----- Psuedo Items
    PortCecilCycles = auto()
    TimeAtJerichoLocks = auto()
    TimeAtWakefulCourt  = auto() # tribute grind
    ZailingDraws = auto() # self-explanatory
    SlightedAcquaintance = auto() # newspaper

    # --- Bone Market Recipes
    ThreeLeggedMammoth = auto()
    MammothOfTheSky = auto()
    MammothOfTheDeep = auto()
    SpiderPope = auto()
    PrismaticWalrus = auto()
    MammothTheHedgehog = auto()
    WoolyGothmother = auto()

actions_per_day = 144.0
cards_seen_per_day = 96.0

def pyramid(n): return n * (n+1) / 2

def per_day(exchanges):
    n = next(counter)
    b[n] = 1
    for item, value in exchanges.items():
        A[n, item.value] = value

def trade(actionCost, exchanges):
    n = next(counter)
    b[n] = 0
    A[n, Item.Action.value] = -1 * actionCost
    for item, value in exchanges.items():
        A[n, item.value] = value

def card(name, freq, isGood, exchanges):
    # n = next(counter)
    # b[n] = 0
    # A[n, Item.Action.value] = -1
    # A[n, Item.CardDraw.value] = -1
    global LondonDeckSize
    global GoodCardsInDeck
    LondonDeckSize += freq.value
    if isGood:
        GoodCardsInDeck += freq.value
        for item, value in exchanges.items():
            # A[n, item.value] = value    
            LondonCardsByItem[item.value] += (value * freq.value)


var_buffer = 500
num_vars = max(Item, key=lambda x: x.value).value + 1 + var_buffer

A = lil_matrix((num_vars, num_vars))

b = [1]*num_vars
counter = count(start=-1)

bounds = [(0, None) for _ in range(num_vars)]

# bounds[Item.Action.value] = (0, actions_per_day)
# bounds[Item.CardDraws.value] = (0, cards_seen_per_day)

# actually a little higher since you can overflow
bounds[Item.Wounds.value] = (0, 36)
bounds[Item.Scandal.value] = (0, 36)
bounds[Item.Suspicion.value] = (0, 36)
bounds[Item.Nightmares.value] = (0, 36)
bounds[Item.SeeingBanditryInTheUpperRiver.value] = (0, 36)

bounds[Item.ConnectedBenthic.value] = (0, 800)

bounds[Item.Tribute.value] = (0, 260)
bounds[Item.TimeAtWakefulCourt.value] = (0, 13)
bounds[Item.TimeAtJerichoLocks.value] = (0, 5)

bounds[Item.NightWhisper.value] = (0, 300)

bounds[Item.FavBohemians.value] = (0, 7)

bounds[Item.ResearchOnAMorbidFad.value] = (0, 6)

# rare success rate
default_rsr = 0.05


# for card averages
LondonDeckSize = 0
GoodCardsInDeck = 0
LondonCardsByItem = [0] * num_vars

per_day({
    Item.Action: actions_per_day,
    Item.CardDraws: cards_seen_per_day
})


#  ██████╗ ██████╗ ██████╗     ██████╗ ███████╗ ██████╗██╗  ██╗
# ██╔═══██╗██╔══██╗██╔══██╗    ██╔══██╗██╔════╝██╔════╝██║ ██╔╝
# ██║   ██║██████╔╝██████╔╝    ██║  ██║█████╗  ██║     █████╔╝ 
# ██║   ██║██╔═══╝ ██╔═══╝     ██║  ██║██╔══╝  ██║     ██╔═██╗ 
# ╚██████╔╝██║     ██║         ██████╔╝███████╗╚██████╗██║  ██╗
#  ╚═════╝ ╚═╝     ╚═╝         ╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝


'''
TODO
- Lofty Tower with inculcating kraken
- Urchins with that one HOJOTOHO fate story 
- Check out Red (free) cards esp. Discordance stuff
- improve Aunt payout
    - can't do actions into more actions, will break everything
    - just add a bunch of echoes or sth
- check location-specific London cards
    - skin of the bazaar?
    - that university one?
'''

# ----------------------
# --- Cards: Lodgings
# ----------------------

# Lair in the Marshes
card("Lair in the Marshes", Rarity.Standard, True, {
    Item.FavSociety: 1,
    Item.CertifiableScrap: 1,
    Item.Nightmares: 1
})

# The Tower of Knives: Difficulties at a Smoky Flophouse
# The next victim?
card("The Tower of Knives", Rarity.Standard, True, {
    Item.FavCriminals: 0.5 - default_rsr / 2.0,
    Item.FavRevolutionaries: 0.5 - default_rsr / 2.0,
    Item.AeolianScream: default_rsr
})

# The Tower of Eyes: Behind Closed Doors at a Handsome Townhouse
# scandalous party
card("The Tower of Eyes", Rarity.Frequent, True, {
  Item.FavBohemians: 0.5,
  Item.FavSociety: 0.5,
  Item.Scandal: 2  
})

# The Tower of Sun and Moon: a Reservation at the Royal Bethlehem Hotel
card("Royal Beth lodings", Rarity.Frequent, False, {
    Item.CertifiableScrap: 3
})

# -----------------------------------------------------
# --- Cards: Companions
# ----------------------------------------------------

card("What will you do with your [connected pet]?", Rarity.Standard, True, {
    Item.FavBohemians: 1
})

# With Bewildering Procession
card("Attend to your spouses", Rarity.VeryInfrequent, True, {
    Item.FavBohemians: 1
})

# -----------------------------------------------------
# --- Cards: Other Equipment
# ----------------------------------------------------

# avoidable
card("A day out in your Clay Sedan Chair", Rarity.Standard, True, {
    Item.FavSociety: 1
})

# avoidable
card("Riding your Velocipede", Rarity.Standard, False, {
    Item.ManiacsPrayer: -5,
    Item.FavConstables: 1
})

# -----------------------------------------------------
# --- Cards: Clubs
# ----------------------------------------------------

# # Sophia's
# # Can also be Tomb-Colony favour, maybe 50/50?
# card("Club: Sophia's", Rarity.Standard, True, {
#     Item.RumourOfTheUpperRiver: -5,
#     Item.PieceOfRostygold: 1500,
#     Item.JetBlackStinger: 5
# })

card("More Larks with the Young Stags", Rarity.Standard, True, {
    # Item.PieceOfRostygold: -500,
    Item.Echo: -5, # everyone has rostygold
    Item.FavSociety: 2,
    Item.FavBohemians: 1
})

# -----------------------------------------------------
# --- Cards: Dreams
# ----------------------------------------------------

# Not sure how to model this? Can they be locked out of altogether?
# Or just have one card for each of the four
# Guessing at rarity for the red cards

# card("A dream about a clouded place", Rarity.Unusual, {
#     # TODO
# })

# assuming you end up with 5 and they are all Unusual
card("omni-Dreams placeholder card", Rarity.Standard, False, {
    # TODO
})

# -----------------------------------------------------
# --- Cards: Factions
# ----------------------------------------------------

# Bohemians
card("Bohemians Faction", Rarity.Standard, True, {
    Item.Echo: -1.2,
    Item.FavBohemians: 1
})

# Church
card("Church Faction", Rarity.Standard, True, {
    Item.Echo: -0.1,
    Item.FavChurch: 1
})

# Constables
card("Constables Faction", Rarity.Standard, False, {
    Item.Echo: -0.1,
    Item.FavConstables: 1
})

# Criminals
card("Criminals Faction", Rarity.Standard, False, {
    Item.Suspicion: 1,
    Item.FavCriminals: 1,
})

# Docks
card("Docks Faction", Rarity.Standard, True, {
    Item.Echo: -0.1,
    Item.FavDocks: 1
})

# GreatGame
card("Great Game Faction", Rarity.Standard, False, {
    Item.Wounds: 1,
    Item.FavGreatGame: 1
})

# Hell
card("Burning Shadows: the Devils of London", Rarity.Standard, False, {
    Item.Scandal: 1,
    Item.FavHell: 1
})

# Revolutionaries
card("Rev Faction", Rarity.Standard, False, {
    Item.Echo: -0.5,
    Item.FavRevolutionaries: 1 
})

# RubberyMen
card("Rubbery Faction", Rarity.Standard, False, {
    Item.Echo: -0.1,
    Item.FavRubberyMen: 1
})

# Society
card("Society Faction", Rarity.Standard, True, {
    Item.Echo: -0.5,
    Item.FavSociety: 1
})

# Tomb-Colonies
card("Tomb Colonies Faction", Rarity.Standard, True, {
    Item.FavTombColonies: 1
})

# Urchins
card("Urchins Faction", Rarity.Standard, False, {
    Item.Echo: -0.1,
    Item.FavUrchins: 1
})

# ----------------------
# --- Cards: General London
# ----------------------

# A tournament of weasels
card("A tournament of weasels", Rarity.Unusual, False, {
    # TODO
})

# Nightmares >= 1
card("Orthographic Infection", Rarity.Standard, False, {
    # TODO
})

# FavBohe >= 1
card("City Vices: A rather decadent evening", Rarity.Standard, False, {
    # TODO
})

# Wounds >= 2
card("A Restorative", Rarity.Standard, False, {
    # TODO
})

# Scandal >= 2
# > an afternoon of mischief
card("An Afternoon of Good Deeds", Rarity.Standard, False, {
    Item.FavHell: 1,
    ## TODO
    # Item.ConfidentSmile: 1,
    # Item.JadeFragment: 10
})

# Nightmares >= 3
card("A Moment's Peace", Rarity.VeryInfrequent, False, {
    # TODO
})

# Nightmares >= 3
# Publish => War-games
# With testing, slightly lowers EPA
card("The interpreter of dreams", Rarity.Unusual, False, {
    # Success
    Item.Nightmares: -5 * 0.6,
    Item.FavGreatGame: 1 * 0.6,

    # Failure
    Item.Scandal: 1 * 0.4
})

card("An implausible penance", Rarity.Standard, False, {
    # TODO
})

# > Rependant forger
card("A visit", Rarity.Standard, True, {
    Item.CrypticClue: 230, # base shadowy,
    Item.FavBohemians: 1,
    Item.FavCriminals: 1
})

# > Entertain a curious crowd
card("The seekers of the garden", Rarity.Standard, False, {
    Item.ZeeZtory: -7,
    Item.FavBohemians: 1,
    Item.FavDocks: 0.5,
    Item.FavSociety: 0.5
})

card("devices and desires", Rarity.Standard, False, {
    # TODO
})


card("A Polite Invitation", Rarity.Standard, False, {
    # TODO: Separate entry for party carousel
})

card("Give a Gift!", Rarity.Standard, False, {
    # TODO
})

# > A disgraceful spectacle
card("A day at the races", Rarity.Standard, True, {
    Item.FavChurch: 1
})

# Avoidable!
# Sulky Bat >= 1
card("A parliament of bats", Rarity.Standard, False, {
    Item.VisionOfTheSurface: -1,
    Item.FavGreatGame: 1
})

card("One's public", Rarity.Standard, False, {
    # TODO    
})

card("A Day with God's Editors", Rarity.Standard, False, {
    Item.TaleOfTerror: -1,
    Item.FavChurch: 1
})

# Avoidable? unsure
card("Bringing the revolution", Rarity.Standard, False, {
    Item.CompromisingDocument: -1,
    Item.FavRevolutionaries: 1
})

# Time limited, also lots of good options?
# Maybe just leave it out?
card("The Calendrical Confusion of 1899", Rarity.Standard, True, {
    Item.ScrapOfIncendiaryGossip: 14
})

card("Mirrors and Clay", Rarity.Standard, False, {
    # TODO
})

card("The Cities that Fell", Rarity.Standard, False, {
    # TODO
})

card("The Soft-Hearted Widow", Rarity.Standard, False, {
    # TODO
})

card("All fear the overgoat!", Rarity.Standard, False, {
    # TODO
})

card("The Northbound Parliamentarian", Rarity.Standard, False, {
    # TODO
})

card("A Dream of Roses", Rarity.Standard, False, {
    # TODO
})

card("Weather at last", Rarity.Standard, False, {
    # TODO
})

card("An unusual wager", Rarity.Standard, False, {
    # TODO
})

card("Mr Wines is holding a sale!", Rarity.Standard, False, {
    # TODO
})

card("The awful temptation of money", Rarity.Standard, False, {
    # TODO
})

# not sure if this can be avoided
card("Investigation the Affluent Photographer", Rarity.Standard, False, {
    # TODO
})

card("The Geology of Winewound", Rarity.Standard, False, {
    # TODO
})

# > Ask her about the sudden influx of bones
# Debatable whether this one is "good"
card("A Public Lecture", Rarity.Standard, False, {
    Item.CrypticClue: 100
    # also RoaMF for newspaper grind
})

# # avoidable with no Favours: Hell
# card("A consideration for services rendered", Rarity.Standard, {
#     # TODO
# })

card("Wanted: Reminders of Brighter Days", Rarity.Standard, False, {
    # TODO
})

# notability >= 1
card("An Unsigned Message", Rarity.VeryInfrequent, False, {
    # TODO
})

card("A Presumptuous Little Opportunity", Rarity.VeryInfrequent, False, {
    # TODO
})

card("A visit from slowcake's amanuensis", Rarity.Infrequent, False, {
    # TODO
})

# Shadowy >= 69, Renown Crims >= 20
card("A merry sort of crime", Rarity.VeryInfrequent, True, {
    Item.FavCriminals: 1
})

card("A dusty bookshop", Rarity.Rare, False, {
    # TODO
})

card("A little omen", Rarity.Rare, False, {
    # TODO
})

card("A disgraceful spectacle", Rarity.Rare, True, {
    Item.Echo: 12.5
})

card("A voice from a well", Rarity.Rare, False, {
    # TODO
})

card("A fine day in the flit", Rarity.Unusual, False, {
    # TODO
})

card("The Paranomastic Newshound", Rarity.Unusual, False, {
    # TODO
})

# ----------------------
# --- Cards: Relickers
# ----------------------

card("The curt relicker and montgomery are moving quietly past",
     Rarity.VeryInfrequent, False, {
         # TODO
     })

card("The Capering Relicker and Gulliver are outside in the street",
     Rarity.VeryInfrequent, False, {
         # TODO
     })

card("The Shivering Relicker and Pinnock are trundling by",
     Rarity.VeryInfrequent, False, {
         # TODO
     })

card("The Coquettish Relicker and Mathilde are making the rounds",
     Rarity.VeryInfrequent, False, {
         # TODO
     })

# ----------------------
# --- Cards: FATE-locked
# ----------------------

card("A Trade in Souls card", Rarity.Standard, True, {
    Item.Echo: -4, # 50 souls + 5 contracts
    Item.FavConstables: 1,
    Item.FavChurch: 1,
    Item.FavSociety: 1
})

# Society ending
# TODO: Check rarity
# TODO: add chance of action refresh. think it won't work w current impl
# currently assumes 100% failure rate
card("The OP Aunt card", Rarity.Standard, True, {
    Item.Echo: -2, # 50x bottle of greyfields 1882
    Item.FavSociety: 1,
    Item.ScrapOfIncendiaryGossip: 3,
    # Item.InklingOfIdentity: 5,
    Item.Scandal: -2,
})



#  ██████╗ ███████╗███╗   ██╗███████╗██████╗  █████╗ ██╗     
# ██╔════╝ ██╔════╝████╗  ██║██╔════╝██╔══██╗██╔══██╗██║     
# ██║  ███╗█████╗  ██╔██╗ ██║█████╗  ██████╔╝███████║██║     
# ██║   ██║██╔══╝  ██║╚██╗██║██╔══╝  ██╔══██╗██╔══██║██║     
# ╚██████╔╝███████╗██║ ╚████║███████╗██║  ██║██║  ██║███████╗
#  ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
                                                           

## ------------
## Social Menace Clears
## ------------

trade(1, {
    Item.Wounds: -6
})

trade(1, {
    Item.Scandal: -5
})

trade(1, {
    Item.Suspicion: -5
})

trade(1, {
    Item.Nightmares: -6
})

trade(1, {
    Item.Scandal: -5
})

# Banditry

# Sets to 3
# In practice probably slightly better w overcap
trade(1, {
    Item.SeeingBanditryInTheUpperRiver: - (pyramid(8) - pyramid(3)),
    Item.Scandal: 12
})

# Card: Intervene in an Attack
trade(1, {
    Item.SeeingBanditryInTheUpperRiver: -1,
    Item.InCorporateDebt: -1 * default_rsr,
    Item.PieceOfRostygold: 400
})

trade(1, {

})

# -----
# Board Member Stuff
# -----

# Tentacled Entrepreneur rotation
trade(7, {
    Item.InCorporateDebt: -15,
    Item.HinterlandScrip: 10
})
# trade(1, {
#     Item.BoardMemberTentacledEntrepreneur: 1,
#     Item.InCorporateDebt: -15,
#     Item.HinterlandScrip: 10
# })

# # double check action cost
# # start vote + collect votes + declare victory?
# trade(6, {
#     Item.BoardMemberTentacledEntrepreneur: -1
# })

## -----------------------
## --- Selling to Bazaar
## ----------------------

# Academic
trade(0, {
    Item.UnprovenancedArtefact: -1,
    Item.Echo: 2.5
})

# Cartography ------

trade(0, {
    Item.ShardOfGlim: -1,
    Item.Echo: 0.01
})

trade(0, {
    Item.MapScrap: -1,
    Item.Echo: 0.10
})

# Currency ------
trade(0, {
    Item.HinterlandScrip: -1,
    Item.Echo: 0.5
})

# Elder ---------
trade(0, {
    Item.AntiqueMystery: -1,
    Item.Echo: 12.5
})

# Goods ----------

trade(0, {
    Item.NevercoldBrassSliver: -1,
    Item.Echo: 0.01
})

trade(0, {
    Item.PieceOfRostygold: -1,
    Item.Echo: 0.01
})

trade(0, {
    Item.PreservedSurfaceBlooms: -1,
    Item.Echo: 2.5
})

trade(0, {
    Item.KnobOfScintillack: -1,
    Item.Echo: 2.5
})

# ----- Great Game
trade(0, {
    Item.FinalBreath: -1,
    Item.HinterlandScrip: 1
})

trade(0, {
    Item.ViennaOpening: -1,
    Item.HinterlandScrip: 5
})

trade(0, {
    Item.QueenMate: -1,
    Item.HinterlandScrip: 50
})


# Historical -----

trade(0, {
    Item.SilveredCatsClaw: -1,
    Item.Echo: 0.10
})

trade(0, {
    Item.UnlawfulDevice: -1,
    Item.Echo: 12.5
})

trade(0, {
    Item.UnlawfulDevice: -1,
    Item.HinterlandScrip: 25
})

# Infernal
trade(0, {
    Item.QueerSoul: -1,
    Item.Echo: 2.5
})

# Influence
trade(0, {
    Item.CompromisingDocument: -1,
    Item.Echo: 0.5
})

trade(0, {
    Item.FavourInHighPlaces: -1,
    Item.Echo: 1
})

# Legal
trade(0, {
    Item.CaveAgedCodeOfHonour: -1,
    Item.LegalDocument: 1,
})

trade(0, {
    Item.LegalDocument: -1,
    Item.Echo: 12.5
})

# Mysteries ---------

trade(0, {
    Item.JournalOfInfamy: -1,
    Item.Echo: 0.5
})

trade(0, {
    Item.ExtraordinaryImplication: -1,
    Item.Echo: 2.5
})

trade(0, {
    Item.UncannyIncunabulum: -1,
    Item.Echo: 12.50
})


# Nostalgia

trade(0, {
    Item.RomanticNotion: -1,
    Item.Echo: 0.10
})

# Osteology

trade(0, {
    Item.CarvedBallOfStygianIvory: -1,
    Item.Echo: 2.5
})

# Rag Trade
trade(0, {
    Item.ThirstyBombazineScrap: -1,
    Item.RatShilling: 2.5
})

# Ratness
trade(1, {
    Item.RattyReliquary: -5,
    Item.RatShilling: 850
})

# Rumour ---------------------

trade(0, {
    Item.ScrapOfIncendiaryGossip: -1,
    Item.Echo: 0.5
})

trade(0, {
    Item.RumourOfTheUpperRiver: -1,
    Item.Echo: 2.5
})

trade(0, {
    Item.NightOnTheTown: -1,
    Item.Echo: 2.5
})

# Sustenance ----------------
trade(0, {
    Item.JasmineLeaves: -1,
    Item.Echo: 0.1
})

trade(0, {
    Item.BasketOfRubberyPies: -1,
    Item.Echo: 2.5
})

trade(0, {
    Item.HinterlandScrip: -125,
    Item.TinnedHam: 1
})

trade(0, {
    Item.TinnedHam: -1,
    Item.Echo: 63.5
})

# Theological
trade(0, {
    Item.ApostatesPsalm: -1,
    Item.Echo: 2.5
})

# Wild Words ----------

trade(0, {
    Item.AeolianScream: -1,
    Item.Echo: 2.5
})

trade(0, {
    Item.StormThrenody: -1,
    Item.Echo: 12.50
})

trade(0, {
    Item.NightWhisper: -1,
    Item.Echo: 62.5
})


# Equipment
trade(0, {
    Item.SulkyBat: -1,
    Item.Echo: 0.2
})

## --------------------------------------
## ----------- Connected
## --------------------------------------

# Benthic
trade(3, {
    Item.Echo: -3,
    Item.ConnectedBenthic: 75
})


## --------------------------------------
## ----------- Favour Cards
## --------------------------------------

# Bundle of all favour cards
# minus hell which lacks good trades?
# card(11, {
#     Item.Echo: -2.7,
#     Item.Suspicion: 1,
#     Item.Wounds: 1,

#     Item.FavBohemians: 1,
#     Item.FavChurch: 1,
#     Item.FavConstables: 1,
#     Item.FavCriminals: 1,
#     Item.FavDocks: 1,
#     Item.FavGreatGame: 1,
#     Item.FavRevolutionaries: 1,
#     Item.FavRubberyMen: 1,
#     Item.FavSociety: 1,
#     Item.FavTombColonies: 1,
#     Item.FavUrchins: 1
# })

# TODO: upper river cards
# card("UR Respectable passengers", Rarity.Standard, {
#     Item.FavCriminals: 1,
#     Item.SeeingBanditryInTheUpperRiver: 2
# })

# -----------------------------------
# ---- Calling in Favours in Jericho
# -----------------------------------

# how to model cost of actually going to jericho
# just bundle all the favours together?

# trade(1, {
#     Item.TimeAtJerichoLocks: 5,
#     Item.RumourOfTheUpperRiver: 1
# })

# def trade(actionCost, exchanges):
#     n = next(counter)
#     b[n] = actionCost
#     for item, value in exchanges.items():
#         A[n, item.value] = value

# hack
jericho_add = 0.0

# hack
def jericho_trade(exchange):
    exchange[Item.RumourOfTheUpperRiver] = jericho_add
    trade(1 + jericho_add, exchange)

# currently putting all the weight of getting to/from Jericho on bohemians
# other factions are modeled as always-availabel trade since it's assumed
# you won't overcap on them by the next time you have at least 4 bohe to trade

trade(3, {
    Item.FavBohemians: -4,
    Item.HolyRelicOfTheThighOfStFiacre: 2,
    Item.WingOfAYoungTerrorBird: 1,
    Item.RumourOfTheUpperRiver: 2
})

trade(1 + jericho_add, {
    Item.FavChurch: -4,
    Item.RattyReliquary: 2,
    Item.ApostatesPsalm: 1,
})

trade(1 + jericho_add, {
    Item.FavConstables: -4,
    Item.CaveAgedCodeOfHonour: 2,
    Item.SwornStatement: 1
})

trade(1 + jericho_add, {
    Item.FavCriminals: -4,
    Item.HumanRibcage: 2,
    Item.HumanArm: 1
})

trade(1 + jericho_add, {
    Item.FavDocks: -4,
    Item.UncannyIncunabulum: 2,
    Item.KnobOfScintillack: 1
})

trade(1 + jericho_add, {
    Item.FavGreatGame: -4,
    Item.ViennaOpening: 1,
    Item.QueenMate: 1
})

trade(1 + jericho_add, {
    Item.FavHell: -4,
    Item.ThornedRibcage: 2,
    Item.QueerSoul: 1
})

trade(1 + jericho_add, {
    Item.FavRevolutionaries: -4,
    Item.UnlawfulDevice: 2,
    Item.ThirstyBombazineScrap: 1
})

trade(1 + jericho_add, {
    Item.FavRubberyMen: -4,
    Item.FlourishingRibcage: 2,
    Item.BasketOfRubberyPies: 1,
})

trade(1 + jericho_add, {
    Item.FavSociety: -4,
    Item.FavourInHighPlaces: 2,
    Item.NightOnTheTown: 1
})

trade(1 + jericho_add, {
    Item.FavTombColonies: -4,
    Item.AntiqueMystery: 2,
    Item.UnprovenancedArtefact: 1,
})

trade(1 + jericho_add, {
    Item.FavUrchins: -4,
    Item.StormThrenody: 2,
    Item.AeolianScream: 1
})


# # All favours in one visit?
# trade(12, {
#     Item.FavBohemians: -4,
#     Item.HolyRelicOfTheThighOfStFiacre: 2,
#     Item.WingOfAYoungTerrorBird: 1,

#     Item.FavChurch: -4,
#     Item.RattyReliquary: 2,
#     Item.ApostatesPsalm: 1,

#     Item.FavConstables: -4,
#     Item.CaveAgedCodeOfHonour: 2,
#     Item.SwornStatement: 1,

#     Item.FavCriminals: -4,
#     Item.HumanRibcage: 2,
#     Item.HumanArm: 1,
    
#     Item.FavDocks: -4,
#     Item.UncannyIncunabulum: 2,
#     Item.KnobOfScintillack: 1,

#     Item.FavGreatGame: -4,
#     Item.ViennaOpening: 1,
#     Item.QueenMate: 1,

#     Item.FavHell: -4,
#     Item.ThornedRibcage: 2,
#     Item.QueerSoul: 1,

#     Item.FavRevolutionaries: -4,
#     Item.UnlawfulDevice: 2,
#     Item.ThirstyBombazineScrap: 1,

#     Item.FavRubberyMen: -4,
#     Item.FlourishingRibcage: 2,
#     Item.BasketOfRubberyPies: 1,

#     Item.FavSociety: -4,
#     Item.FavourInHighPlaces: 2,
#     Item.NightOnTheTown: 1,

#     Item.FavTombColonies: -4,
#     Item.AntiqueMystery: 2,
#     Item.UnprovenancedArtefact: 1,

#     Item.FavUrchins: -4,
#     Item.StormThrenody: 2,
#     Item.AeolianScream: 1
# })

## ------------
## Zailing
## ------------

# ballparking EPA for zailing with piracy
trade(0, {
    Item.ZailingDraws: -1,
    Item.Echo: 3
})

## ------------
## Court of the Wakeful Eye Grind
## ------------

# Round trip between London and CotWE
# with zub or yacht
trade(14, {
    Item.ZailingDraws: 12,
    # Psuedo item represents tribute cap of 260
    Item.TimeAtWakefulCourt: 13
})

trade(4, {
    Item.Tribute: -20,
    Item.TimeAtWakefulCourt: -1,
    Item.NightWhisper: 1
})

trade(1, {
    Item.FavBohemians: -7,
    Item.Tribute: 23
})

trade(1, {
    Item.FavChurch: -7,
    Item.Tribute: 23
})

trade(1, {
    Item.FavCriminals: -7,
    Item.Tribute: 23
})

trade(1, {
    Item.FavDocks: -7,
    Item.Tribute: 23
})

trade(1, {
    Item.FavSociety: -7,
    Item.Tribute: 23
})

## -------------------------
## Innate Item Conversions
## -------------------------

# ----- Academic
trade(1, {
    Item.MemoryOfDistantShores: -50,
    Item.VolumeOfCollatedResearch: 10,
    Item.CrypticClue: 50 * (0.6 - default_rsr),
    Item.UncannyIncunabulum: 2 * default_rsr
})

# requires urchin war active
# also other items hard to model
trade(1, {
    Item.LostResearchAssistant: -1,
    Item.Echo: 12.5 # blackmail material x1
})

# ----- Mysteries
# Journals to Implications @ 50:10
trade(1,{
    Item.JournalOfInfamy: -50,
    Item.ConnectedBenthic: -5,
    Item.ExtraordinaryImplication: 10,
    Item.ShardOfGlim: 100 * (0.6 - default_rsr),
    Item.StormThrenody: 2 * default_rsr
})

# # Implications to Incunabula @ 25:5
trade(1, {
    Item.ExtraordinaryImplication: -25,
    Item.ConnectedBenthic: -20,
    Item.UncannyIncunabulum: 5,
    Item.NevercoldBrassSliver: 200 * (0.6 - default_rsr),
    Item.Echo: 62.5 * default_rsr # Nodule of Pulsating Amber
})

## ------------
## Rat Market
## ------------

trade(0, {
    Item.RatShilling: -10,
    Item.Echo: 1
})

trade(0, {
    Item.RatShilling: -7,
    Item.CompromisingDocument: 1
})

trade(0, {
    Item.RatShilling: -1,
    Item.ManiacsPrayer: 1
})

trade(1, {
    Item.UncannyIncunabulum: -5,
    Item.RatShilling: 850
})

trade(1, {
    Item.StormThrenody: -5,
    Item.RatShilling: 850
})

trade(1, {
    Item.NightWhisper: -1,
    Item.RatShilling: 850
})

## ------------
## Various London Carousels?
## ------------

# optimistic size
trade(20, {
    Item.ApostatesPsalm: 3,
    Item.NevercoldBrassSliver: ((38 * 20) - 50) * 10
})


# Hearts' Game
trade(6, {
    Item.Echo: 12.5,
    Item.WhirringContraption: 1
})


# 50:51 Cross-Conversion Carousel
trade(1, {
    Item.JournalOfInfamy: -50,
    Item.CorrespondencePlaque: 51
})

trade(1, {
    Item.CorrespondencePlaque: -50,
    Item.VisionOfTheSurface: 51
})

trade(1, {
    Item.VisionOfTheSurface: -50,
    Item.MysteryOfTheElderContinent: 51
})

trade(1, {
    Item.MysteryOfTheElderContinent: -50,
    Item.ScrapOfIncendiaryGossip: 51
})

trade(1, {
    Item.ScrapOfIncendiaryGossip: -50,
    Item.MemoryOfDistantShores: 51
})

trade(1, {
    Item.MemoryOfDistantShores: -50,
    Item.BrilliantSoul: 51
})

trade(1, {
    Item.BrilliantSoul: -50,
    Item.TaleOfTerror: 51
})

trade(1, {
    Item.TaleOfTerror: -50,
    Item.CompromisingDocument: 51
})

trade(1, {
    Item.CompromisingDocument: -50,
    Item.MemoryOfLight: 51
})

trade(1, {
    Item.MemoryOfLight: -50,
    Item.ZeeZtory: 51
})

trade(1, {
    Item.ZeeZtory: -50,
    Item.BottleOfStranglingWillowAbsinthe: 51
})

trade(1, {
    Item.BottleOfStranglingWillowAbsinthe: -50,
    Item.WhisperSatinScrap: 51
})

trade(1, {
    Item.WhisperSatinScrap: -50,
    Item.JournalOfInfamy: 51
})

## ------------
## Newspaper
## ------------

# Gossipy edition with maximum Salacious
trade(13, {
    Item.WhirringContraption: -1,
    Item.ScrapOfIncendiaryGossip: -5,

    Item.JournalOfInfamy: 148,
    Item.SlightedAcquaintance: 1,
    Item.SulkyBat: 2
})

# Tawdry secrets without slighted 
trade(13, {
    Item.WhirringContraption: -1,
    Item.JournalOfInfamy: 118,
    Item.SulkyBat: 2,
    Item.Echo: 10 # 4 broken giant
})

# Outlandish edition
trade(13, {
    Item.WhirringContraption: -1,
    Item.JournalOfInfamy: 118,
    Item.ExtraordinaryImplication: 4
    # Item.Echo: 7.9 # 0.4 bats, 10 wine, -2.5 gossip
})

# Expose of Palaeontology
# - 6 actions to get max RoaMF
# - 13 actions base
trade(6, {
    Item.CrypticClue: 100, # carpenter's granddaughter
    Item.FinBoneCollected: 3, # palaeo companion
    Item.WitheredTentacle: 3, # carnival
    Item.UnidentifiedThighbone: 2, # university
    Item.JetBlackStinger: 3, # ??? can also be tentacles?
    Item.PlasterTailBones: 1, # stalls
    Item.ResearchOnAMorbidFad: 6
})

trade(13, {
    Item.WhirringContraption: -1,
    Item.ResearchOnAMorbidFad: -6,

    Item.PieceOfRostygold: 500,
    Item.SurveyOfTheNeathsBones: 20 + 13 * 6,
    Item.HolyRelicOfTheThighOfStFiacre: 2
})

# Revenge card, ignoring Opp Deck cost
# various actual cards, ignores cost to acquaintance
trade(1, {
    Item.SlightedAcquaintance: -1,
    Item.Echo: 12.5
})

# --------------
# Port Cecil
# -------------

# 7? actions to zail from london? 4 + 2 + 1
# TODO: check round trip length
trade(14, {
    Item.PortCecilCycles: 4, # arbitrary, how many times thru before home
    Item.ZailingDraws: 12
})

# ideal cycle w/ maxed stats
# - 13 AotRS (reliable but less profitable w less)
# - 334 Watchful (required to guarantee 50/50 split)
# - 334 Persuasive  (required to guarantee 50/50 split)
# 5x (red science miners => 7x map scrap, 1x knob scintillack)
# 1x (instruct the cats => 5x scrap of i.g., 7x romantic notion)
# 5x (prey on miners concerns => 6x journal ofinf)
# 2x (deploy cat wrangling => 30x silvered cats claw)
#   OR (distact w wildlife => 4x withered tentacle)

trade(14, {
    Item.PortCecilCycles: -1,
    Item.MapScrap: 35,
    Item.KnobOfScintillack: 5,
    Item.ScrapOfIncendiaryGossip: 5,
    Item.RomanticNotion: 7,
    Item.JournalOfInfamy: 30,
    Item.WitheredTentacle: 8,
    Item.LostResearchAssistant: 1,
    Item.SegmentedRibcage: 3
})

# alternative in carousel
trade(0, {
    Item.WitheredTentacle: -4,
    Item.SilveredCatsClaw: 30
})

# slightly less profitable but more achievable grind
# 5x direct miners toward dig site
# - doesn't derail on failure
# - 90% success w 273 P, 100% w 300
# 1x instruct cats in calc
# 3x liberate raw scintillack
# 3x bring refreshments
# 1x distract cats w/ wildlife

trade (14, {
    Item.PortCecilCycles: -1,
    Item.ZeeZtory: 6 * 5,
    Item.ScrapOfIncendiaryGossip: 5,
    Item.RomanticNotion: 7,
    Item.KnobOfScintillack: 3,
    Item.MemoryOfDistantShores: 4 * 3,
    Item.WitheredTentacle: 4,
    Item.LostResearchAssistant: 1, 
    Item.SegmentedRibcage: 3
})

# --------------
# Ealing & Helicon
# -------------

# TODO: fix total carousel stuff here
trade(1, {
    Item.FinBoneCollected: -10,
    Item.AmberCrustedFin: 1
})


# --------------
# Balmoral
# -------------

# 2x (1 action, 4 research) to enter
# 1 action to go to glade
# 3x (1 action, 3 bombazine) to darken
# 1 action wander
# 1 action locate red deer
# 1 action cash out with keeper

# TODO: double check action counts for these
# Mammoth Ribcage
trade(9, {
    Item.VolumeOfCollatedResearch: -8,
    Item.ThirstyBombazineScrap: -9,

    Item.MammothRibcage: 1,
    Item.HolyRelicOfTheThighOfStFiacre: 1,
    Item.FemurOfAJurassicBeast: 2,
    Item.BoneFragments: 400
})

# Skeleton with 7 Necks
trade(7, {
    Item.VolumeOfCollatedResearch: -8,
    Item.UnprovenancedArtefact: -4,

    Item.SkeletonWithSevenNecks: 1
})

# --------------
# Station VIII
# -------------

trade(1, {
    Item.OilOfCompanionship: -1,
    Item.RumourOfTheUpperRiver: -98,

    Item.PrismaticFrame: 1
})

# guessing how this works, havent unlocked  yet
trade(2, {
    Item.AntiqueMystery: -2,
    Item.ConsignmentOfScintillackSnuff: -2,

    Item.OilOfCompanionship: 1
})

# --------------
# Laboratory
# -------------

trade(1, {
    Item.PreservedSurfaceBlooms: -1,
    Item.KnobOfScintillack: -8,
    Item.ConsignmentOfScintillackSnuff: 2
})

# estimated actions
trade(4, {
    Item.RemainsOfAPinewoodShark: -1,
    Item.FinBoneCollected: 38,
    Item.BoneFragments: 500,
    Item.IncisiveObservation: 2
})

# --------------
# Parabola
# -------------

# Hunting Pinewood Shark
# TODO: check actual length of carousel
trade(6, {
    Item.FinBoneCollected: 2,
    Item.FavDocks: 1,
    Item.RemainsOfAPinewoodShark: 1
})

# ----------
# Bone Market
# -----------

trade(0, {
    Item.HinterlandScrip: -2,
    Item.UnidentifiedThighbone: 1
})

trade(1, {
    Item.BoneFragments: -100,
    Item.NoduleOfWarmAmber: -25,
    Item.WingOfAYoungTerrorBird: 2
})

trade(0, {
    Item.Echo: -62.5,
    Item.BrightBrassSkull: 1
})


# Buy from patrons

trade(1, {
    Item.HinterlandScrip: -120,
    Item.SabreToothedSkull: 1
})

# 3 + parts actions?

# Three Legged Mammoth
# Sell as Lizard to Gothic Tales during Antiq/Menace Week
trade(9, {
    Item.MammothRibcage: -1,
    Item.SabreToothedSkull: -1,
    Item.FemurOfAJurassicBeast: -3,
    Item.UnidentifiedThighbone: -1,
    Item.JetBlackStinger: -1,
    Item.ThreeLeggedMammoth: 1
})

trade(1, {
    Item.ThreeLeggedMammoth: -1,
    Item.HinterlandScrip: 303,
    Item.CarvedBallOfStygianIvory: 21
})

# Mammoth of the Sky
# Sell to Gothic as Bird during A/M week
trade(9, {
    Item.MammothRibcage: -1,
    Item.SabreToothedSkull: -1,
    Item.WingOfAYoungTerrorBird: -2,
    Item.FemurOfAJurassicBeast: -2,
    Item.WitheredTentacle: -1,
})

trade(1, {
    Item.MammothOfTheSky: -1,
    Item.HinterlandScrip: 310,
    Item.CarvedBallOfStygianIvory: 21
})


# Mammoth of the Deep
# Fish, Gothic
trade(10, {
    Item.MammothRibcage: -1,
    Item.SabreToothedSkull: -1,
    Item.AmberCrustedFin: -3,
    Item.FinBoneCollected: -1,
    Item.JetBlackStinger: -1,
})

trade(1, {
    Item.MammothOfTheDeep: -1,
    Item.HinterlandScrip: 381,
    Item.CarvedBallOfStygianIvory: 20
})

# Spider Pope
trade(14, {
    Item.SegmentedRibcage: -3,
    Item.HolyRelicOfTheThighOfStFiacre: -8,
    Item.WitheredTentacle: -1,
    Item.SpiderPope: 1
})

trade(1, {
    Item.SpiderPope: -1,
    Item.PreservedSurfaceBlooms: 55,
    Item.RumourOfTheUpperRiver: 88
})

# Prismatic Walrus
trade(9, {
    Item.PrismaticFrame: -1,
    Item.SabreToothedSkull: -1,
    Item.CarvedBallOfStygianIvory: -2,
    Item.AmberCrustedFin: -3,
    Item.JetBlackStinger: -1,
    Item.PrismaticWalrus: 1,
})

trade(1, {
    Item.PrismaticWalrus: -1,
    Item.HinterlandScrip: 908,
    Item.CarvedBallOfStygianIvory: 17
})

# Mammoth the Hedgehog
# Amphibian
trade(10, {
    Item.ThornedRibcage: -1,
    Item.HornedSkull: -1,
    Item.FemurOfAJurassicBeast: -4,
    Item.MammothTheHedgehog: 1
})

trade(1, {
    Item.MammothTheHedgehog: -1,
    Item.HinterlandScrip: 90,
    Item.CarvedBallOfStygianIvory: 18
})

# Wooly Gothmother
trade(9, {
    Item.ThornedRibcage: -1,
    Item.SabreToothedSkull: -1,
    Item.WingOfAYoungTerrorBird: -2,
    Item.UnidentifiedThighbone: -2,
    Item.JetBlackStinger: -1,
    Item.WoolyGothmother: 1
})

trade(1, {
    Item.WoolyGothmother: -1,
    Item.HinterlandScrip: 191,
    Item.CarvedBallOfStygianIvory: 9
})

# Generator Skeleton, various

# Sell to Tentacled Entrepreneur
# 64 vs 74 final breath if amalgamy week
trade(13, {
    Item.SkeletonWithSevenNecks: -1,
    Item.BrightBrassSkull: -2,
    Item.NevercoldBrassSliver: -400,
    Item.SabreToothedSkull: -5,
    Item.AlbatrossWing: -2,

    Item.MemoryOfDistantShores: 1171,
    Item.FinalBreath: 64
})

# Naive Collector
trade(13, {
    Item.SkeletonWithSevenNecks: -1,
    Item.BrightBrassSkull: -3,
    Item.NevercoldBrassSliver: -600,
    Item.SabreToothedSkull: -4,
    Item.WingOfAYoungTerrorBird: -2,

    Item.ThirstyBombazineScrap: 226,
})

# Hoarding Palaeo
trade(13, {
    Item.SkeletonWithSevenNecks: -1,
    Item.BrightBrassSkull: -2,
    Item.NevercoldBrassSliver: -400,
    Item.SabreToothedSkull: -5,
    Item.WingOfAYoungTerrorBird: -2,

    Item.BoneFragments: 56105,
    Item.UnearthlyFossil: 2
})

# Zailor Particular
trade(13, {
    Item.SkeletonWithSevenNecks: -1,
    Item.BrightBrassSkull: -2,
    Item.NevercoldBrassSliver: -400,
    Item.SabreToothedSkull: -5,
    Item.WingOfAYoungTerrorBird: -2,

    Item.NoduleOfWarmAmber: 5635,
    Item.KnobOfScintillack: 14
})

# -------------------------------
# ---- Opportunity Deck Math ----
# -------------------------------

# subtract 400 for holding 4 bad standard freq cards in hand
deck_size = LondonDeckSize - 400;
good_card_density = GoodCardsInDeck / deck_size
good_cards_per_day = good_card_density * cards_seen_per_day
card_exchange = {}

for item in Item:
    if LondonCardsByItem[item.value] != 0:
        card_exchange[item] = cards_seen_per_day * (LondonCardsByItem[item.value] / deck_size)

card_exchange[Item.CardDraws] = -1 * cards_seen_per_day
# card_exchange[Item.Action] = -1 * good_cards_per_day

print(card_exchange)
trade(good_cards_per_day, card_exchange)
# per_day(card_exchange)

# trade(20.42, {
#     Item.Echo: -1.05,
#     Item.Wounds: 0.84,
#     Item.Scandal: 3.43,
#     Item.Suspicion: 0.84,
#     Item.FavBohemians: 3.78,
#     Item.FavChurch: 2.52,
#     Item.FavCriminals: 2.5,
#     Item.FavDocks: 0.84,
#     Item.FavGreatGame: 1.78,
#     Item.FavRevolutionaries: 2.08,
#     Item.FavSociety: 3.36,
#     Item.FavTombColonies: 0.84,
#     Item.FavUrchins: 0.84,
#     Item.CertifiableScrap: 0.84,
#     Item.PieceOfRostygold: 1260.50,
#     Item.CompromisingDocument: -0.84,
#     Item.CrypticClue: 193.28,
#     Item.TaleOfTerror: -0.84,
#     Item.VisionOfTheSurface: -0.84,
#     Item.JetBlackStinger: 4.20,
#     Item.ScrapOfIncendiaryGossip: 11.76,
#     Item.RumourOfTheUpperRiver: -4.20,
#     Item.AeolianScream: 0.04
# })

# ------------------------------------------
# ---------------- Optimization ------------
# ------------------------------------------
# linear optimize
c = np.zeros(num_vars)
c[Item.Echo.value] = -1

opt_result = linprog(c, A_ub=A.toarray(), b_ub=b, bounds=bounds, method='highs')
print(opt_result)

print("Opp Deck")

# for item, quantity in zip(Item, opt_result.x):
#     if LondonCardsByItem[item.value] > 0:
#         cards = LondonCardsByItem[item.value]
#         print(f"{item.name}: 1 in {LondonDeckSize / LondonCardsByItem[item.value]:10.3f}")

print(f"{'Item Name':^30}")
for item, quantity in zip(Item, opt_result.x):
    item_name = f"{item.name:30}"
    per_action = f"{(1.0/(quantity * actions_per_day) if quantity != 0 else 0.0):10.2f}"
    per_card = LondonCardsByItem[item.value] / LondonDeckSize
    # per_card = f"{(LondonCardsByItem[item.value] / LondonDeckSize):10.2f}" if LondonCardsByItem[item.value] > 0 else f"{'n/a':^10}"
    per_day_of_draws = per_card * cards_seen_per_day
    print(item_name + per_action + ((f"{per_card:10.2f}" + f"{per_day_of_draws:10.2f}") if per_card != 0 else ""))

print("------Summary & Assumptions-------")
print(f"Total Actions per Day: {actions_per_day}")
print(f"Cards Drawn per Day: {cards_seen_per_day}")
print(f"Good Card Density: {good_card_density:.2}")
print(f"Actions spent on Cards per Day: {good_cards_per_day}")
print(f"Echoes per Day: {-1.0/(opt_result.fun):.7}")
print(f"EPA @ {actions_per_day} & {cards_seen_per_day}: {-1.0/(opt_result.fun * actions_per_day):.3}")

# print(bounds)