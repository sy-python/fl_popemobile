import numbers
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve
from scipy.sparse import csc_matrix
from scipy.optimize import linprog
from enum import Enum, auto
from itertools import count

from enums import *

import numpy as np
import pprint

'''
TODO
- cut up the monolith somehow
- don't think this is properly penalizing menace accumulations
    - maybe need to just convert those directly to action penalties.
    - or invert it somehow? treat it as an actual cost both ways
- add railway stuff before more london stuff bc it's prob more relevant

London
- location-specific opp deck cards
- all the chimes & chimes-tier carousels
    - brawling with dockers
    - sunken embassy
    - spider debates
    - whatever other crap i forgot
- remaining hearts' game payouts
- all the MYN locations
- forgotten quarter expeditions
- model Airs somehow

Laboratory
- model the actual deck & bonus payoffs
- highly dependent on exclusive character choices?
    - ambition, profession, etc.
- sounds like a lot of work payoff so putting this off unless something looks esp. promising

Parabola
- parabolan war
- most parabolan hunts
- waswood shores?
    - figure out the odds
- basically everything else

Zailing
- godfall
- polythreme
- irem
- other port cecil options
- hunting the beasts
- random smaller islands
- better model of the deck

Khanate
- model the round-trip costs
- smuggling
- intrigues

Railway
- TONS of shit
- opportunity deck
- TRACKLAYER CITY

short term
- parabola stuff?
- Lofty Tower with inculcating kraken
- Check out Red (free) cards esp. Discordance stuff
- check location-specific London cards
    - skin of the bazaar?
    - that university one for TC favours
- bone market exhaustion
    - model it as just 4/7ths of a point per day?
    - fuck maybe we have to move to a per-week basis blergh

medium term
- option to optimize for hinterland scrip instead of echoes
    - fuck it optimize for any item
    - it already does this, just the option for the terminal output
    
long term
- incorporate a given character's capabilities
    - what are your stats, what various options do you have unlocked
    - in general more fine-grained control over the various base assumptions
'''

# Important Parameters
# actions doesn't matter on its own until I add some weekly+ stuff
# but it does matter relative to cards seen per day
actions_per_day = 120.0
cards_seen_per_day = 40

# placeholder for upconversions and stuff
# if anyone knows the real values please share
default_rare_success_rate = 0.05

# maybe improve slightly with EPA
zailing_epa = 3.2

# lab research per action
# somewhat optimistic
lab_rpa = 33

# for modeling actions that can grant more actions
# eg. the 30% success on the aunt card
replacement_epa = 6.5

# for modeling time spent outside london
replacement_good_card_density = 0.33

# 0.85, 0.74, 0.65
wounds_multiplier = 1.0
scandal_multiplier = 1.0
suspicion_multiplier = 1.0
nightmares_multiplier = 1.0

# --------------------------------------------
# -------------- Player Config ---------------
# --------------------------------------------    
# TODO: separate class?

player_profession = Profession.NoProfession
player_treasure = Treasure.NoTreasure
player_location = Location.NoLocation
player_ambition = Ambition.BagALegend

player_stats = {
    Stat.Watchful: 315,
    Stat.Shadowy: 315,
    Stat.Dangerous: 315,
    Stat.Persuasive: 315,
    Stat.KatalepticToxicology: 15,
    Stat.MonstrousAnatomy: 15,
    Stat.APlayerOfChess: 15,
    Stat.Glasswork: 15,
    Stat.ShapelingArts: 15,
    Stat.ArtisanOfTheRedScience: 15,
    Stat.Mithridacy: 15,
    Stat.StewardOfTheDiscordance: 8,
    Stat.Zeefaring: 15
}


# --------------------------------------------
# -------------- Player Config ---------------
# --------------------------------------------  

def pyramid(n): return n * (n+1) / 2
def clamp(n, floor, ceiling): return min(ceiling, max(floor, n))

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
    global LondonDeckSize
    global GoodCardsInDeck
    LondonDeckSize += freq.value
    if isGood:
        GoodCardsInDeck += freq.value
        for item, value in exchanges.items():
            LondonCardsByItem[item.value] += (value * freq.value)

def railway_card(name, freq, isGood, exchanges):
    # dummy alias for now
    trade(1, exchanges)

def broad_challenge_success_rate(stat, difficulty): return clamp(0.6 * stat/difficulty, 0.0, 1.0)

def narrow_challenge_success_rate(stat, difficulty): return clamp(0.5 + (stat - difficulty)/10, 0.1, 1.0)

def expected_failures(success_rate): return 1.0/success_rate - 1 if success_rate < 1.0 else 0

def challenge_ev(player_stat, difficulty, success, failure):
    success_rate = broad_challenge_success_rate(player_stat, difficulty)
    return success_rate * success + (1.0 - success_rate) * failure

def skelly_value_in_items(skelly_value, item_value, zoo_bonus_active):
    zoo_multiplier = 1.1 if zoo_bonus_active else 1.0
    return skelly_value * zoo_multiplier / item_value
    

# hack
var_buffer = 3000
num_items = max(Item, key=lambda x: x.value).value
num_vars = num_items + 1 + var_buffer

A = lil_matrix((num_vars, num_vars))

b = [1]*num_vars
counter = count(start=-1)

bounds = [(0, None) for _ in range(num_vars)]

# in practice it seems this rarely affects the output, but it makes me feel better
# I don't know if this even works the way I think it does as far as modeling long-term stockpiling
# but if you set it too low, you will lock out certain trades
# eg setting the upper bound of Bohemian favours to 3 will lock out the Jericho option
# so really it's a source of bugs more than anything else
# still keeping it in

# menace bounds actually a little higher since you can overflow
# also should maybe have negative bound, since menace reduction is usually a side-effect rather than a cost
# tried setting it to (-100, 36) and EPA went down slightly so who the heck knows
bounds[Item.WoundsCredit.value] = (0, 36)
bounds[Item.ScandalCredit.value] = (0, 36)
bounds[Item.SuspicionCredit.value] = (0, 36)
bounds[Item.NightmaresCredit.value] = (0, 36)
bounds[Item.Hedonist.value] = (0, 55)

bounds[Item.SeeingBanditryInTheUpperRiver.value] = (0, 36)

bounds[Item.ConnectedBenthic.value] = (0, 800)

bounds[Item.Tribute.value] = (0, 260)
bounds[Item.TimeAtWakefulCourt.value] = (0, 13)
bounds[Item.TimeAtJerichoLocks.value] = (0, 5)

bounds[Item.FavBohemians.value] = (0, 7)
bounds[Item.FavChurch.value] = (0, 7)
bounds[Item.FavConstables.value] = (0, 7)
bounds[Item.FavCriminals.value] = (0, 7)
bounds[Item.FavDocks.value] = (0, 7)
bounds[Item.FavGreatGame.value] = (0, 7)
bounds[Item.FavHell.value] = (0, 7)
bounds[Item.FavRevolutionaries.value] = (0, 7)
bounds[Item.FavRubberyMen.value] = (0, 7)
bounds[Item.FavSociety.value] = (0, 7)
bounds[Item.FavTombColonies.value] = (0, 7)
bounds[Item.FavUrchins.value] = (0, 7)

bounds[Item.ResearchOnAMorbidFad.value] = (0, 6)

# for card averages
LondonDeckSize = 0
GoodCardsInDeck = 0
LondonCardsByItem = [0] * num_vars

# ---------------- Trades ----------------------------

# Plug in the basic economic contraints

per_day({
    Item.Action: actions_per_day,
    Item.CardDraws: cards_seen_per_day,
    Item.VisitFromTimeTheHealer: 1/7
})


# Time-gated stuff
# Lots missing

# # Just gonna comment this out for now
# # it will only confuse things until the non-exlusive options are settled

# def rewards_of_ambition(treasure):
#     if treasure == Treasure.NoTreasure:
#         return {}
#     # Bag a Legend
#     elif treasure == Treasure.VastNetworkOfConnections:
#         return {
#             Item.ParabolaLinenScrap: 1,
#             Item.HinterlandScrip: 5,
#             Item.Nightmares: -5,
#             Item.BraggingRightsAtTheMedusasHead: 5
#         }
#     elif treasure == Treasure.SocietyOfTheThreeFingeredHand:
#         return {
#             Item.SearingEnigma: 1,
#             Item.Nightmares: -5,
#             Item.BraggingRightsAtTheMedusasHead: 5
#         }
#     elif treasure == Treasure.WingedAndTalonedSteed:
#         return {
#             Item.NightWhisper: 1,
#             Item.Wounds: -5,
#             Item.BraggingRightsAtTheMedusasHead: 5
#         }
#     elif treasure == Treasure.LongDeadPriestsOfTheRedBird:
#         return {
#             Item.PrimaevalHint: 1,
#             Item.Wounds: -5,
#             Item.BraggingRightsAtTheMedusasHead: 5
#         }
#     # Hearts Desire
#     elif treasure == Treasure.TheRobeOfMrCards:
#         return {
#             Item.FragmentOfTheTragedyProcedures: 1,
#             Item.Suspicion: -5
#         }
#     elif treasure == Treasure.NewlyCastCrownOfTheCityOfLondon:
#         return {
#             Item.BottleOfFourthCityAirag: 1,
#             Item.Scandal: -5
#         }
#     elif treasure == Treasure.LeaseholdOnAllOfLondon:
#         return {
#             Item.SearingEnigma: 1,
#             Item.Wounds: -5
#         }    
#     elif treasure == Treasure.PalatialHomeInTheArcticCircle:
#         return {
#             Item.NightWhisper: 1,
#             Item.Nightmares: -5
#         }
#     elif treasure == Treasure.TheRobeOfMrCards:
#         return {
#             Item.PrimaevalHint: 1,
#             Item.Nightmares: -5
#         }
#     elif treasure == Treasure.FalseStartOfYourOwn:
#         return {
#             Item.SearingEnigma: 1,
#             Item.Nightmares: -5
#         }
#     elif treasure == Treasure.KittenSizedDiamond:
#         return {
#             Item.PrimaevalHint: 1,
#             Item.Wounds: -5,
#             # ???
#             Item.OstentatiousDiamond: -1,
#             Item.MagnificentDiamond: 1
#         }
#     elif treasure == Treasure.BloodiedTravellingCoatOfMrCups:
#         return {
#             Item.BlackmailMaterial: 1,
#             Item.Nightmares: -5
#         }
#     elif treasure == Treasure.YourLovedOneReturned:
#         return {
#             Item.PrimaevalHint: 1,
#             Item.Nightmares: -5
#         }


trade(0, {
    Item.VisitFromTimeTheHealer: -1,
    # Item.AConsequenceOfYourAmbition: 1
})

# ambition_reward = rewards_of_ambition(treasure)
# ambition_reward[Item.AConsequenceOfYourAmbition] = -4
# trade(1, ambition_reward)

#  ██████╗ ██████╗ ██████╗     ██████╗ ███████╗ ██████╗██╗  ██╗
# ██╔═══██╗██╔══██╗██╔══██╗    ██╔══██╗██╔════╝██╔════╝██║ ██╔╝
# ██║   ██║██████╔╝██████╔╝    ██║  ██║█████╗  ██║     █████╔╝ 
# ██║   ██║██╔═══╝ ██╔═══╝     ██║  ██║██╔══╝  ██║     ██╔═██╗ 
# ╚██████╔╝██║     ██║         ██████╔╝███████╗╚██████╗██║  ██╗
#  ╚═════╝ ╚═╝     ╚═╝         ╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝

# ----------------------
# --- Cards: Lodgings
# ----------------------

# Lair in the Marshes
card("Lair in the Marshes", Rarity.Standard, True, {
    Item.FavSociety: 1,
    Item.CertifiableScrap: 1,
    Item.NightmaresCredit: -1 * nightmares_multiplier
})

# The Tower of Knives: Difficulties at a Smoky Flophouse
# The next victim?
card("The Tower of Knives", Rarity.Standard, True, {
    Item.FavCriminals: 0.5 - default_rare_success_rate / 2.0,
    Item.FavRevolutionaries: 0.5 - default_rare_success_rate / 2.0,
    Item.AeolianScream: default_rare_success_rate
})

# The Tower of Eyes: Behind Closed Doors at a Handsome Townhouse
# scandalous party
card("The Tower of Eyes", Rarity.Frequent, True, {
  Item.FavBohemians: 0.5,
  Item.FavSociety: 0.5,
  Item.Hedonist: 3,
  Item.ScandalCredit: -2 * scandal_multiplier
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
    Item.FavSociety: 1,
    Item.Hedonist: -3
})

# # avoidable? A: yes, with watchful gains
# card("Riding your Velocipede", Rarity.Standard, False, {
#     Item.ManiacsPrayer: -5,
#     Item.FavConstables: 1
# })

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
card("Criminals Faction", Rarity.Standard, True, {
    Item.SuspicionCredit: -1 * suspicion_multiplier,
    Item.FavCriminals: 1,
})

# Docks
card("Docks Faction", Rarity.Standard, True, {
    Item.Echo: -0.1,
    Item.FavDocks: 1
})

# GreatGame
card("Great Game Faction", Rarity.Standard, False, {
    Item.WoundsCredit: -1 * wounds_multiplier,
    Item.FavGreatGame: 1
})

# Hell
card("Burning Shadows: the Devils of London", Rarity.Standard, False, {
    Item.ScandalCredit: -1 * scandal_multiplier,
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
card("Tomb Colonies Faction", Rarity.Standard, False, {
    Item.FavTombColonies: 1
})

# # Urchins
# card("Urchins Faction", Rarity.Standard, False, {
#     Item.Echo: -0.4, # 1x lucky weasel
#     Item.FavUrchins: 1
# })

# With HOJOTOHO ending
card("Urchins Faction", Rarity.Standard, True, {
    Item.FavUrchins: 1,
    Item.NightmaresCredit: 2
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
    Item.NightmaresCredit: 5 * 0.6,
    Item.FavGreatGame: 1 * 0.6,

    # Failure
    Item.ScandalCredit: -1 * 0.4 * scandal_multiplier
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
# card("The Calendrical Confusion of 1899", Rarity.Standard, True, {
#     Item.ScrapOfIncendiaryGossip: 14
# })

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

# Society ending since that's what I have
# probably the best of the aunt-bitions anyway
card("The OP Aunt card", Rarity.Standard, True, {
    Item.BottleOfGreyfields1882: -50,

    # 0.7 Failure
    Item.FavSociety: 1 * 0.7,
    Item.ScrapOfIncendiaryGossip: 3 * 0.7,
    Item.InklingOfIdentity: 5 * 0.7,
    Item.ScandalCredit: 2 * 0.7,
    
    # 0.3 success
    Item.Echo: 10 * replacement_epa * 0.3
})


# ----------------------
# --- Cards: Location-specific
# ----------------------

# so far no special location is positive EPA
# but these have potential 

# if (player_location == Location.BazaarSideStreet):
#     card("The Skin of the Bazaar", Rarity.Rare, False, {

#     })

if (player_location == Location.LadybonesRoad):
    card("1000 Nevercold Brass Silver Wanted!", Rarity.Standard, True, {
        Item.NevercoldBrassSliver: -1000,
        Item.CrypticClue: 500,
        Item.AppallingSecret: 10,
        Item.FavGreatGame: 1
    })

if (player_location == Location.Spite):
    card("2000 Foxfire Candles Wanted!", Rarity.Standard, True, {
        Item.FoxfireCandleStub: -2000,
        Item.PieceOfRostygold: 2000,
        Item.MysteryOfTheElderContinent: 1,
        Item.FavChurch: 1
    })

if (player_location == Location.TheUniversity):
    card("A peculiar practice", Rarity.Standard, True, {
        # Item.ConnectedSummerset: -5 # ignoring for now
        Item.FavTombColonies: 1,
        Item.Echo: 0.6 # bundle of oddities
    })

    card("Stone by stone", Rarity.Standard, False, {

    })

if (player_location == Location.YourLodgings):
    card("A commotion above", Rarity.Rare, False, {
        
    })    

    card("The Neath's Mysteries", Rarity.Standard, False, {
        
    })

    card("The Urchin and the Monkey", Rarity.VeryInfrequent, True, {
        Item.CompromisingDocument: -2,
        Item.FavUrchins: 1
    })

    card("Your Grubby Urchin is becoming troublesome", Rarity.VeryInfrequent, True, {
        Item.TaleOfTerror: -2,
        Item.FavUrchins: 1
    })    



# # TODO: check the actual rarity of this
# # also it adds that other rare card to the deck that clears all wounds
# card("Slavering Dream Hound", Rarity.Unusual, True, {
#     Item.DropOfPrisonersHoney: 200
# })


#  ██████╗ ███████╗███╗   ██╗███████╗██████╗  █████╗ ██╗     
# ██╔════╝ ██╔════╝████╗  ██║██╔════╝██╔══██╗██╔══██╗██║     
# ██║  ███╗█████╗  ██╔██╗ ██║█████╗  ██████╔╝███████║██║     
# ██║   ██║██╔══╝  ██║╚██╗██║██╔══╝  ██╔══██╗██╔══██║██║     
# ╚██████╔╝███████╗██║ ╚████║███████╗██║  ██║██║  ██║███████╗
#  ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
                                                           

## ------------------------------
## -------- Menace Stuff --------
## ------------------------------

# Social Actions, ignoring the cost to the other party
# Better options for Scandal and Suspicion exist @ -6 (dupe/betrayal) but those have a weekly limit

trade(1, {
    Item.WoundsCredit: 6
})

trade(1, {
    Item.ScandalCredit: 5
})

trade(1, {
    Item.SuspicionCredit: 5
})

trade(1, {
    Item.NightmaresCredit: 6
})

# Not a real action, represents the fact that menace reduction is a side effect rather than a cost
# otherwise we might miss a grind that's net negative on a given menace

trade(1, {
    Item.WoundsCredit: -10
})

trade(1, {
    Item.ScandalCredit: -10
})

trade(1, {
    Item.SuspicionCredit: -10
})

trade(1, {
    Item.NightmaresCredit: -10
})

# --------------------------
# --- Buying from Bazaar ---
# --------------------------

trade(0, {
    Item.Echo: -64.80,
    Item.WinsomeDispossessedOrphan: 1
})

## -----------------------
## --- Selling to Bazaar
## ----------------------

# # # Test
# trade(0, {
#     Item.HumanRibcage: -1,
#     Item.Echo: 50
# })

# Academic
trade(0, {
    Item.MemoryOfDistantShores: -1,
    Item.Echo: 0.5
})

trade(0, {
    Item.IncisiveObservation: -1,
    Item.Echo: 0.5
})

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

trade(0, {
    Item.ZeeZtory: -1,
    Item.Echo: 0.5
})

trade(0, {
    Item.PartialMap: -1,
    Item.Echo: 2.5
})

trade(0, {
    Item.PuzzlingMap: -1,
    Item.Echo: 12.5
})

trade(0, {
    Item.SaltSteppeAtlas: -1,
    Item.Echo: 62.5
})

trade(0, {
    Item.RelativelySafeZeeLane: -1,
    Item.Echo: 62.5
})

trade(0, {
    Item.SightingOfAParabolanLandmark: -1,
    Item.Echo: 0.1
})

trade(0, {
    Item.VitreousAlmanac: -1,
    Item.Echo: 12.5
})

trade(0, {
    Item.OneiromanticRevelation: -1,
    Item.Echo: 62.5
})

trade(0, {
    Item.ParabolanParable: -1,
    Item.Echo: 312.5
})

trade(0, {
    Item.CartographersHoard: -1,
    Item.Echo: 312.5
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

# Luminosity ---------

trade(0, {
    Item.LumpOfLamplighterBeeswax: -1,
    Item.Echo: 0.01
})

trade(0, {
    Item.PhosphorescentScarab: -1,
    Item.Echo: 0.10
})

trade(0, {
    Item.MemoryOfLight: -1,
    Item.CrypticClue: 25
})

trade(0, {
    Item.LumpOfLamplighterBeeswax: -1,
    Item.Echo: 0.01
})

trade(0, {
    Item.MourningCandle: -1,
    Item.Echo: 2.5
})

# Mysteries ---------

trade(0, {
    Item.WhisperedHint: -1,
    Item.Echo: 0.01
})

trade(0, {
    Item.CrypticClue: -1,
    Item.Echo: 0.02
})

trade(0, {
    Item.CrypticClue: -1,
    Item.AppallingSecret: 0.02
})

trade(0, {
    Item.JournalOfInfamy: -1,
    Item.Echo: 0.5
})

trade(0, {
    Item.TaleOfTerror: -1,
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
    Item.Echo: -0.04,
    Item.DropOfPrisonersHoney: 1
})

trade(0, {
    Item.RomanticNotion: -1,
    Item.Echo: 0.10
})

# Osteology

# worth ~3.05 echoes with horsebitrage
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

# Wines
trade(0, {
    Item.Echo: -0.04,
    Item.BottleOfGreyfields1882: 1
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

## -------------------------
## Innate Item Conversions
## -------------------------

# ----- Academic
trade(1, {
    Item.MemoryOfDistantShores: -50,
    Item.ConnectedBenthic: -5,
    Item.VolumeOfCollatedResearch: 10,
    Item.CrypticClue: 50 * (0.6 - default_rare_success_rate),
    Item.UncannyIncunabulum: 2 * default_rare_success_rate
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
    Item.ShardOfGlim: 100 * (0.6 - default_rare_success_rate),
    Item.StormThrenody: 2 * default_rare_success_rate
})

# # Implications to Incunabula @ 25:5
trade(1, {
    Item.ExtraordinaryImplication: -25,
    Item.ConnectedBenthic: -20,
    Item.UncannyIncunabulum: 5,
    Item.NevercoldBrassSliver: 200 * (0.6 - default_rare_success_rate),
    Item.Echo: 62.5 * default_rare_success_rate # Nodule of Pulsating Amber
})

# -----------------
# --- Underclay
# ----------------


trade(2+20+1, {
    Item.MountainSherd: 1,
})
# # with FATE clay arm, 19 * 33 => 627 confessions
trade(2+19+1, {
    Item.MountainSherd: 1,
    Item.ShardOfGlim: 270
})

# with SotD 13, not currently achievable, 16 * 38 => 608 confessions
trade(2+16+1, {
    Item.MountainSherd: 1,
    Item.ShardOfGlim: 80
})

## ------------
## Rat Market
## ------------

trade(0, {
    Item.RatShilling: -10,
    Item.Echo: 1
})


# Crow-Crease Cryptics

trade(0, {
    Item.RatShilling: -1,
    Item.InklingOfIdentity: 1
})

trade(0, {
    Item.RatShilling: -1,
    Item.ManiacsPrayer: 1
})

trade(0, {
    Item.RatShilling: -2,
    Item.AppallingSecret: 1
})

trade(0, {
    Item.RatShilling: -7,
    Item.CompromisingDocument: 1
})

trade(0, {
    Item.RatShilling: -7,
    Item.CorrespondencePlaque: 1
})

trade(0, {
    Item.RatShilling: -7,
    Item.JournalOfInfamy: 1
})

trade(0, {
    Item.RatShilling: -7,
    Item.TaleOfTerror: 1
})

trade(0, {
    Item.RatShilling: -50,
    Item.TouchingLoveStory: 1
})

trade(0, {
    Item.RatShilling: -1000,
    Item.BlackmailMaterial: 1
})

# Tier 4

trade(0, {
    Item.FourthCityEcho: -1,
    Item.RatShilling: 125
})

# Tier 5

trade(1, {
    Item.UncannyIncunabulum: -5,
    Item.RatShilling: 850
})

trade(1, {
    Item.StormThrenody: -5,
    Item.RatShilling: 850
})

trade(1, {
    Item.RattyReliquary: -5,
    Item.RatShilling: 850
})

trade(1, {
    Item.UnlawfulDevice: -5,
    Item.RatShilling: 850
})

# Tier 6

trade(1, {
    Item.NightWhisper: -1,
    Item.RatShilling: 850
})

trade(1, {
    Item.ParabolaLinenScrap: -1,
    Item.RatShilling: 850
})

trade(1, {
    Item.CracklingDevice: -1,
    Item.RatShilling: 850
})

trade(1, {
    Item.CaptivatingBallad: -1,
    Item.RatShilling: 850
})

# Tier 7

trade(1, {
    Item.CorrespondingSounder: -1,
    Item.RatShilling: 4000
})

trade(1, {
    Item.ScrapOfIvoryOrganza: -1,
    Item.RatShilling: 4000
})

trade(1, {
    Item.CartographersHoard: -1,
    Item.RatShilling: 4000
})

trade(1, {
    Item.ParabolanParable: -1,
    Item.RatShilling: 4000
})

## ------------
## Various London Carousels?
## ------------

# overnight trip
trade(40, {
    Item.ApostatesPsalm: 3,
    Item.NevercoldBrassSliver: ((38 * 40) - 50) * 10
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

    Item.Hedonist: 1,
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
    Item.FinBonesCollected: 3, # palaeo companion
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

# Revenge cards -----------
# Ignores cost to acquaintance
trade(1, {
    Item.CardDraws: -1,
    Item.SlightedAcquaintance: -1,
    Item.PuzzleDamaskScrap: 1
})

trade(1, {
    Item.CardDraws: -1,
    Item.SlightedAcquaintance: -1,
    Item.NoduleOfTremblingAmber: 1
})

trade(1, {
    Item.CardDraws: -1,
    Item.SlightedAcquaintance: -1,
    Item.MagnificentDiamond: 1
})

# FATE Johnny Croak
trade(1, {
    Item.CardDraws: -1,
    Item.SlightedAcquaintance: -1,
    Item.PuzzlingMap: 1
})

# FATE Johnny Croak
trade(1, {
    Item.CardDraws: -1,
    Item.SlightedAcquaintance: -1,
    Item.AntiqueMystery: 1
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
    Item.FinBonesCollected: 38,
    Item.BoneFragments: 500,
    Item.IncisiveObservation: 2
})

# ██████╗  █████╗ ██████╗  █████╗ ██████╗  ██████╗ ██╗      █████╗ 
# ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔═══██╗██║     ██╔══██╗
# ██████╔╝███████║██████╔╝███████║██████╔╝██║   ██║██║     ███████║
# ██╔═══╝ ██╔══██║██╔══██╗██╔══██║██╔══██╗██║   ██║██║     ██╔══██║
# ██║     ██║  ██║██║  ██║██║  ██║██████╔╝╚██████╔╝███████╗██║  ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝                                           
# Parabola

trade(1, {
    Item.DropOfPrisonersHoney: 0 if player_profession == Profession.Silverer else -100,
    Item.ParabolaRoundTrip: 1
})

trade(2, {
    Item.BoneFragments: -1100,
    Item.ParabolanOrangeApple: 1
})

# with specific BaL ending
# trade(2, {
#     Item.BoneFragments: -500,
#     Item.ParabolanOrangeApple: 1
# })

trade(2, {
    Item.BoneFragments: -100,
    Item.Hedonist: -21,
    Item.ParabolanOrangeApple: 2
})

# Hunting Pinewood Shark
# TODO: check actual length of carousel

# just stay there, ignore travel cost
trade(6, {
    Item.CardDraws: -6,
    Item.FinBonesCollected: 2,
    Item.FavDocks: 1,
    Item.RemainsOfAPinewoodShark: 1
})

# short trip, no cards missed
trade(6, {
    Item.ParabolaRoundTrip: -1,
    Item.FinBonesCollected: 2,
    Item.FavDocks: 1,
    Item.RemainsOfAPinewoodShark: 1
})

# ------------------
# Parabolan War
# ------------------

# Ballparked via wiki calculator @ 320 base stats and default values

trade(72, {
    Item.ParabolanParable: 1
})

trade(72, {
    Item.RayDrenchedCinder: 1
})

trade(72, {
    Item.EdictsOfTheFirstCity: 1
})

trade(72, {
    Item.WaswoodAlmanac: 1
})

trade(72, {
    Item.ConcentrateOfSelf: 1
})

# # ----------
# ██████╗  ██████╗ ███╗   ██╗███████╗    ███╗   ███╗ █████╗ ██████╗ ██╗  ██╗███████╗████████╗
# ██╔══██╗██╔═══██╗████╗  ██║██╔════╝    ████╗ ████║██╔══██╗██╔══██╗██║ ██╔╝██╔════╝╚══██╔══╝
# ██████╔╝██║   ██║██╔██╗ ██║█████╗      ██╔████╔██║███████║██████╔╝█████╔╝ █████╗     ██║   
# ██╔══██╗██║   ██║██║╚██╗██║██╔══╝      ██║╚██╔╝██║██╔══██║██╔══██╗██╔═██╗ ██╔══╝     ██║   
# ██████╔╝╚██████╔╝██║ ╚████║███████╗    ██║ ╚═╝ ██║██║  ██║██║  ██║██║  ██╗███████╗   ██║   
# ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝    ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   
#                                                                                            

def actions_to_sell_skelly(shadowy, implausibility):
    if (implausibility < 1): return 1
    difficulty = 75 * implausibility
    success_rate = min(0.6 * shadowy/difficulty, 1.0)
    expected_failures = 1.0/success_rate - 1

    # assumes 5 clear per action
    suspicion_penalty = 0.2 * expected_failures
    return 1 + expected_failures + suspicion_penalty

chimera_success_rate = narrow_challenge_success_rate(player_stats[Stat.Mithridacy], 10)
actions_on_success = actions_to_sell_skelly(player_stats[Stat.Shadowy], 3)
actions_on_failure = actions_to_sell_skelly(player_stats[Stat.Shadowy], 6)
actions_to_sell_chimera = (actions_on_success * chimera_success_rate) + (actions_on_failure * (1.0 - chimera_success_rate))

# out of curiosity, what happens if we could cash out everything for free
# Suggests the following items can be acquired profitably:
# - AmberCrustedFin
# - Thigh of saint fiacre
# - Skull in coral
# - wing of a young terror bird
# - skeleton with seven necks

# trade(0, {
#     Item.AlbatrossWing: -1, 
#     Item.Echo: 12.50
# })

# trade(0, {
#     Item.AmberCrustedFin: -1, 
#     Item.Echo: 12.50
# })

# # counterfeit head of john the baptist
# trade(0, {
#     Item.BoneFragments: -500,
#     Item.HandPickedPeppercaps: -10, 
#     Item.Echo: 12.50
# })

# trade(0, {
#     Item.DoubledSkull: -1,
#     Item.Echo: 62.5
# })

# trade(0, {
#     Item.EyelessSkull: -1, 
#     Item.Echo: 30
# })


# trade(0, {
#     Item.FemurOfAJurassicBeast: -1, 
#     Item.Echo: 3
# })

# trade(0, {
#     Item.FinBonesCollected: -1, 
#     Item.Echo: 0.5
# })

# trade(0, {
#     Item.FivePointedRibcage: -1, 
#     Item.Echo: 312.5
# })

# trade(0, {
#     Item.FlourishingRibcage: -1, 
#     Item.Echo: 12.50
# })

# trade(0, {
#     Item.FossilisedForelimb: -1, 
#     Item.Echo: 27.50
# })

# trade(0, {
#     Item.HeadlessSkeleton: -1, 
#     Item.Echo: 2.50
# })

# trade(0, {
#     Item.HelicalThighbone: -1, 
#     Item.Echo: 3
# })

# trade(0, {
#     Item.HolyRelicOfTheThighOfStFiacre: -1, 
#     Item.Echo: 12.50
# })

# trade(0, {
#     Item.HornedSkull: -1, 
#     Item.Echo: 12.50
# })

# trade(0, {
#     Item.HumanArm: -1, 
#     Item.Echo: 2.50
# })

# trade(0, {
#     Item.HumanRibcage: -1, 
#     Item.Echo: 12.50
# })

# trade(0, {
#     Item.IvoryFemur: -1, 
#     Item.Echo: 65
# })

# trade(0, {
#     Item.IvoryHumerus: -1, 
#     Item.Echo: 15
# })

# trade(0, {
#     Item.JetBlackStinger: -1, 
#     Item.Echo: 0.5
# })

# trade(0, {
#     Item.KnottedHumerus: -1, 
#     Item.Echo: 3
# })

# trade(0, {
#     Item.LeviathanFrame: -1, 
#     Item.Echo: 312.50
# })

# trade(0, {
#     Item.MammothRibcage: -1, 
#     Item.Echo: 62.50
# })

# # vake skull
# trade(0, {
#     Item.BoneFragments: -6000,
#     Item.Echo: 65
# })

# trade(0, {
#     Item.PlatedSkull: -1,
#     Item.Echo: 62.50
# })

# trade(0, {
#     Item.PrismaticFrame: -1, 
#     Item.Echo: 312.50
# })

# trade(0, {
#     Item.RibcageWithABoutiqueOfEightSpines: -1, 
#     Item.Echo: 312.50
# })

# trade(0, {
#     Item.RubberySkull: -1,
#     Item.Echo: 6
# })

# trade(0, {
#     Item.SabreToothedSkull: -1, 
#     Item.Echo: 62.50
# })

# trade(0, {
#     Item.SegmentedRibcage: -1, 
#     Item.Echo: 2.50
# })

# trade(0, {
#     Item.SkeletonWithSevenNecks: -1, 
#     Item.Echo: 62.50
# })

# trade(0, {
#     Item.SkullInCoral: -1, 
#     Item.Echo: 17.50
# })

# trade(0, {
#     Item.ThornedRibcage: -1, 
#     Item.Echo: 12.50
# })

# trade(0, {
#     Item.WingOfAYoungTerrorBird: -1, 
#     Item.Echo: 2.50
# })

# Bone Market
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
    Item.HinterlandScrip: challenge_ev(player_stats[Stat.Persuasive], 200, success= -120, failure= -125),
    Item.SabreToothedSkull: 1
})

trade(1 + expected_failures(broad_challenge_success_rate(player_stats[Stat.Persuasive], 210)), {
    Item.ParabolanOrangeApple: -1,
    Item.IvoryHumerus: 1
})


# -----------------
# Sell To Patrons
# ----------------

trade(1, {
    Item.HumanRibcage: -1,
    Item.IncisiveObservation: 30
})

# -------------------------
# ------- Recipes ---------
# -------------------------
# TODO: Verify all outputs

'''
6000 fragment recipes require:
- BaL for the vake skull
- AotRS 10 to 100% the check
'''

if (player_ambition == Ambition.BagALegend):
    # min 1 action is baked into recipes, this only adds for failure
    # ignores other failure costs bc lazy
    success_rate = narrow_challenge_success_rate(player_stats[Stat.ArtisanOfTheRedScience], 5)
    expected_failures = 1.0/success_rate - 1 if success_rate < 1.0 else 0
    trade(expected_failures, {
        Item.BoneFragments: -6000,
        Item.DuplicatedVakeSkull: 1
    })

# -------------------------------
# ------ Leviathan Frame

# 3/0/6/0/3 chimera => gothic
trade(5 + actions_to_sell_chimera, {
    Item.LeviathanFrame: -1,
    Item.DuplicatedVakeSkull: -1,
    Item.WingOfAYoungTerrorBird: -2,
    Item.HinterlandScrip: 885,
    Item.CarvedBallOfStygianIvory: 21
})

# 1/2/6 fish => gothic
trade(6, {
    Item.LeviathanFrame: -1,
    Item.DuplicatedVakeSkull: -1,
    Item.AmberCrustedFin: -2,
    Item.HinterlandScrip: 942,
    Item.CarvedBallOfStygianIvory: 9
})

# 2/2/4 fish => gothic
trade(6, {
    Item.LeviathanFrame: -1,
    Item.SabreToothedSkull: -1,
    Item.AmberCrustedFin: -2,
    Item.HinterlandScrip: 937,
    Item.CarvedBallOfStygianIvory: 10
})

# 1/2/3 fish => gothic
trade(5 + actions_to_sell_skelly(player_stats[Stat.Shadowy], 2), {
    Item.LeviathanFrame: -1,
    Item.BrightBrassSkull: -1,
    Item.AmberCrustedFin: -2,
    Item.HinterlandScrip: 948,
    Item.CarvedBallOfStygianIvory: 5
})

# -------------------------------
# ----- Human Ribcage

# 0/6/3 humanoid
trade(8, {
    Item.HumanRibcage: -1,
    Item.DuplicatedVakeSkull: -1,
    Item.KnottedHumerus: -2,
    Item.HelicalThighbone: -2,
    Item.NightsoilOfTheBazaar: 184,
    Item.BasketOfRubberyPies: 21,
})

trade(8, {
    Item.HumanRibcage: -1,
    Item.DuplicatedVakeSkull: -1,
    Item.FossilisedForelimb: -2,
    Item.FemurOfAJurassicBeast: -2,
    Item.NightsoilOfTheBazaar: skelly_value_in_items(12.5 + 65 + (27.5 * 2) + (3 * 2), 0.5, False),
    Item.CarvedBallOfStygianIvory: 21,
})

'''
"Biblically Inaccurate Angel"
AKA the reject ribcage recycler

the filler limb can be any limb with 0 antiquity & menace
'''

filler_limb = Item.UnidentifiedThighbone
filler_limb_echo_value = -1 # net -1 scrip buying it from

# 3/?/6
trade(7 + actions_to_sell_chimera, {
    Item.HumanRibcage: -1,
    Item.DuplicatedVakeSkull: -1,
    Item.WingOfAYoungTerrorBird: -3,
    filler_limb: -1,
    Item.HinterlandScrip: skelly_value_in_items(12.5 + 65 + (3 * 2.5) + filler_limb_echo_value, 0.5, False),
    Item.CarvedBallOfStygianIvory: 21, # 20/18/21
})

# 3/1/6
trade(7 + actions_to_sell_chimera, {
    Item.HumanRibcage: -1,
    Item.DuplicatedVakeSkull: -1,
    Item.FemurOfAJurassicBeast: -1,
    Item.WingOfAYoungTerrorBird: -2,
    Item.AmberCrustedFin: -1,
    Item.HinterlandScrip: skelly_value_in_items(12.5 + 65 + 3 + (2 * 2.5) + 15, 0.5, False),
    Item.CarvedBallOfStygianIvory: 21, # 20/18/21
})

# 4/?/4
trade(7 + actions_to_sell_chimera, {
    Item.HumanRibcage: -1,
    Item.SabreToothedSkull: -1,
    Item.WingOfAYoungTerrorBird: -3,
    filler_limb: -1,
    Item.HinterlandScrip: skelly_value_in_items(12.5 + 62.5 + (3 * 2.5) + filler_limb_echo_value, 0.5, False),
    Item.CarvedBallOfStygianIvory: 18, # 18/16/18
})

# 3/2/6
trade(7 + actions_to_sell_chimera, {
    Item.HumanRibcage: -1,
    Item.HornedSkull: -1,
    Item.WingOfAYoungTerrorBird: -2,
    Item.AmberCrustedFin: -2,
    Item.HinterlandScrip: skelly_value_in_items(12.5 + 12.5 + (2 * 2.5) + (2 * 15), 0.5, False),
    Item.CarvedBallOfStygianIvory: 21 # 20/18/21,
})

# 4/0/4
trade(7 + actions_to_sell_chimera, {
    Item.HumanRibcage: -1,
    Item.HornedSkull: -1,
    Item.WingOfAYoungTerrorBird: -3,
    Item.HumanArm: -1,
    Item.HinterlandScrip: skelly_value_in_items(12.5 + 12.5 + (3 * 2.5) + 2.5, 0.5, False),
    Item.CarvedBallOfStygianIvory: 18 # 18/16/18,
})

# Generator Skeleton, various
# testing various balances of brass vs. sabre-toothed skull

for i in range(0, 4):
    zoo_bonus = 0.1

    brass_skulls = i
    sabre_toothed_skulls = 7 - i

    penny_value = 6250 + 2500
    penny_value += 6500 * brass_skulls
    penny_value += 6250 * sabre_toothed_skulls

    trade(11 + actions_to_sell_skelly(player_stats[Stat.Shadowy], brass_skulls * 2), {
        Item.SkeletonWithSevenNecks: -1,
        Item.BrightBrassSkull: -1 * brass_skulls,
        Item.NevercoldBrassSliver: -200 * brass_skulls,
        Item.SabreToothedSkull: -1 * sabre_toothed_skulls,
        Item.AlbatrossWing: -2,
        Item.MemoryOfDistantShores: 5 + (penny_value * (1 + zoo_bonus)/50),
        Item.FinalBreath: 74
    })

# same as above but with 1x skull in coral and different wings
for i in range(0, 4):
    brass_skulls = i
    sabre_toothed_skulls = 6 - i

    penny_value = 6250 + 1750 + 500
    penny_value += 6500 * brass_skulls
    penny_value += 6250 * sabre_toothed_skulls

    zoo_bonus = 0.1

    trade(11 + actions_to_sell_skelly(player_stats[Stat.Shadowy], brass_skulls * 2), {
        Item.SkeletonWithSevenNecks: -1,
        Item.BrightBrassSkull: -1 * brass_skulls,
        Item.NevercoldBrassSliver: -200 * brass_skulls,
        Item.SabreToothedSkull: -1 * sabre_toothed_skulls,
        Item.SkullInCoral: -1,
        Item.KnobOfScintillack: -1,
        Item.WingOfAYoungTerrorBird: -2,
        Item.MemoryOfDistantShores: 5 + (penny_value * (1 + zoo_bonus)/50),
        # amalgamy week
        Item.FinalBreath: 74
    })

# Hoarding Palaeo
for i in range(0, 4):
    zoo_bonus = 0.1

    brass_skulls = i
    sabre_toothed_skulls = 7 - i

    penny_value = 0
    penny_value += 6250 # skelly
    penny_value += 6500 * brass_skulls
    penny_value += 6250 * sabre_toothed_skulls
    penny_value += 250 * 2 # wings

    trade(11 + actions_to_sell_skelly(player_stats[Stat.Shadowy], brass_skulls * 2), {
        Item.SkeletonWithSevenNecks: -1,
        Item.BrightBrassSkull: -1 * brass_skulls,
        Item.NevercoldBrassSliver: -200 * brass_skulls,
        Item.SabreToothedSkull: -1 * sabre_toothed_skulls,
        Item.WingOfAYoungTerrorBird: -2,
        Item.BoneFragments: penny_value * (1 + zoo_bonus),
        Item.UnearthlyFossil: 2
    })

# Zailor Particular
for i in range(0, 4):
    zoo_bonus = 0.1
    antiquity_bonus = 0.5
    amalgamy_bonus  = 0

    brass_skulls = i
    sabre_toothed_skulls = 7 - i

    penny_value = 0
    penny_value += 6250 # skelly
    penny_value += 6500 * brass_skulls
    penny_value += 6250 * sabre_toothed_skulls
    penny_value += 250 * 2 # wings

    antiquity = sabre_toothed_skulls + 2
    amalgamy = 2

    trade(11 + actions_to_sell_skelly(player_stats[Stat.Shadowy], brass_skulls * 2), {
        Item.SkeletonWithSevenNecks: -1,
        Item.BrightBrassSkull: -1 * brass_skulls,
        Item.NevercoldBrassSliver: -200 * brass_skulls,
        Item.SabreToothedSkull: -1 * sabre_toothed_skulls,
        Item.WingOfAYoungTerrorBird: -2,
        Item.NoduleOfWarmAmber: 25 + (penny_value * (1 + zoo_bonus))/10,
        Item.KnobOfScintillack: ((antiquity + amalgamy_bonus) * (amalgamy + antiquity_bonus))
    })    
    

# ██╗  ██╗███████╗ █████╗ ██████╗ ████████╗███████╗     ██████╗  █████╗ ███╗   ███╗███████╗
# ██║  ██║██╔════╝██╔══██╗██╔══██╗╚══██╔══╝██╔════╝    ██╔════╝ ██╔══██╗████╗ ████║██╔════╝
# ███████║█████╗  ███████║██████╔╝   ██║   ███████╗    ██║  ███╗███████║██╔████╔██║█████╗  
# ██╔══██║██╔══╝  ██╔══██║██╔══██╗   ██║   ╚════██║    ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝  
# ██║  ██║███████╗██║  ██║██║  ██║   ██║   ███████║    ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗
# ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝     ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝
# Hearts' Game

trade(1, {
    Item.HeartsGameExploits: 1
})

trade(1, {
    Item.HeartsGameExploits: -5,
    Item.Echo: 12.5,
    Item.WhirringContraption: 1
})

trade(1, {
    Item.HeartsGameExploits: -14,
    Item.BessemerSteelIngot: 100
})

trade(1, {
    Item.HeartsGameExploits: -18,
    Item.MortificationOfAGreatPower: 1
})

trade(1, {
    Item.HeartsGameExploits: -25,
    Item.SaltSteppeAtlas: 1,
    Item.PuzzlingMap: 4,
    Item.PartialMap: 4,
    Item.MapScrap: 5
})

trade(1, {
    Item.HeartsGameExploits: -65,
    Item.IntriguersCompendium: 1
})

trade(1, {
    Item.HeartsGameExploits: -65,
    Item.LeviathanFrame: 1
})

trade(1, {
    Item.HeartsGameExploits: -65,
    Item.ElementalSecret: 1
})

trade(1, {
    Item.HeartsGameExploits: -65,
    Item.StarstoneDemark: 1
})

trade(1, {
    Item.HeartsGameExploits: -80,
    Item.ScrapOfIvoryOrganza: 1
})

# ██╗      █████╗ ██████╗  ██████╗ ██████╗  █████╗ ████████╗ ██████╗ ██████╗ ██╗   ██╗
# ██║     ██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗╚██╗ ██╔╝
# ██║     ███████║██████╔╝██║   ██║██████╔╝███████║   ██║   ██║   ██║██████╔╝ ╚████╔╝ 
# ██║     ██╔══██║██╔══██╗██║   ██║██╔══██╗██╔══██║   ██║   ██║   ██║██╔══██╗  ╚██╔╝  
# ███████╗██║  ██║██████╔╝╚██████╔╝██║  ██║██║  ██║   ██║   ╚██████╔╝██║  ██║   ██║   
# ╚══════╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ╚═╝   
# Laboratory

trade(1, {
    Item.LaboratoryResearch: lab_rpa
})

# TODO better estimate
trade(1, {
    Item.ParabolanResearch: 12
})

# Cartographic Projects -----------

trade(2, {
    Item.LaboratoryResearch: -2700,
    Item.CartographersHoard: 1
})

# Small Gazette
trade(2, {
    Item.LaboratoryResearch: -60,
    Item.GlassGazette: 5
})

# Big Gazette
trade(2, {
    Item.LaboratoryResearch: -2500,
    Item.GlassGazette: 125
})

# Biological Projects ------------

# False Snake
trade(2, {
    Item.LaboratoryResearch: -100,
    Item.MemoryOfDistantShores: 20,
    Item.UnearthlyFossil: 1
})

# Dissect the Pinewood Shark
trade(2, {
    Item.RemainsOfAPinewoodShark: -1,
    Item.LaboratoryResearch: -100,
    Item.IncisiveObservation: 2,
    Item.FinBonesCollected: 38,
    Item.BoneFragments: 500
})

# Geology Projects --------------

trade(2, {
    Item.LaboratoryResearch: -100,
    Item.SurveyOfTheNeathsBones: 25
})

trade(2, {
    Item.LaboratoryResearch: -2700,
    Item.SurveyOfTheNeathsBones: 125
})

# Mathematical Projects ------------

trade(2, {
    Item.LaboratoryResearch: -13000,
    Item.ImpossibleTheorem: 1,
})

# ██╗  ██╗██╗  ██╗ █████╗ ███╗   ██╗ █████╗ ████████╗███████╗
# ██║ ██╔╝██║  ██║██╔══██╗████╗  ██║██╔══██╗╚══██╔══╝██╔════╝
# █████╔╝ ███████║███████║██╔██╗ ██║███████║   ██║   █████╗  
# ██╔═██╗ ██╔══██║██╔══██║██║╚██╗██║██╔══██║   ██║   ██╔══╝  
# ██║  ██╗██║  ██║██║  ██║██║ ╚████║██║  ██║   ██║   ███████╗
# ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

# -------------
# Khaganian Markets
# -------------

# selling
trade(0, {
    Item.DeepZeeCatch: -1,
    Item.AssortmentOfKhaganianCoinage: 1
})

trade(0, {
    Item.CarvedBallOfStygianIvory: -1,
    Item.AssortmentOfKhaganianCoinage: 5
})

trade(0, {
    Item.JasmineLeaves: -1,
    Item.MoonPearl: 10
})

trade(0, {
    Item.BottleOfFourthCityAirag: -1,
    Item.AssortmentOfKhaganianCoinage: 125
})

trade(0, {
    Item.CaptivatingBallad: -1,
    Item.AssortmentOfKhaganianCoinage: 125
})

trade(0, {
    Item.CracklingDevice: -1,
    Item.AssortmentOfKhaganianCoinage: 125
})

trade(0, {
    Item.MuchNeededGap: -1,
    Item.AssortmentOfKhaganianCoinage: 125
})

trade(0, {
    Item.OneiricPearl: -1,
    Item.AssortmentOfKhaganianCoinage: 125
})

trade(0, {
    Item.SaltSteppeAtlas: -1,
    Item.AssortmentOfKhaganianCoinage: 125
})

# -------------
# Mightnight Market
# -------------

trade(0, {
    Item.AssortmentOfKhaganianCoinage: -2,
    Item.DeepZeeCatch: 1
})

trade(0, {
    Item.AssortmentOfKhaganianCoinage: -10,
    Item.CarvedBallOfStygianIvory: 1
})

trade(0, {
    Item.TouchingLoveStory: -10,
    Item.TouchingLoveStory: 1
})

trade(0, {
    Item.MoonPearl: -20,
    Item.JasmineLeaves: 1
})

trade(0, {
    Item.MoonPearl: -20,
    Item.KhaganianLightbulb: 1
})

trade(0, {
    Item.AssortmentOfKhaganianCoinage: -130,
    Item.CracklingDevice: 1
})



# -------------
# Intrigues
# -------------

# Intercept a cablegram
trade(2, {
    Item.Infiltrating: -20,
    Item.InterceptedCablegram: 5,
    Item.VitalIntelligence: 1
})




# ███████╗ █████╗ ██╗██╗     ██╗███╗   ██╗ ██████╗ 
# ╚══███╔╝██╔══██╗██║██║     ██║████╗  ██║██╔════╝ 
#   ███╔╝ ███████║██║██║     ██║██╔██╗ ██║██║  ███╗
#  ███╔╝  ██╔══██║██║██║     ██║██║╚██╗██║██║   ██║
# ███████╗██║  ██║██║███████╗██║██║ ╚████║╚██████╔╝
# ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝ 
    
# ballparking EPA for zailing with piracy
trade(0, {
    Item.ZailingDraws: -1,
    Item.Echo: zailing_epa
})

# rounding up for overflow
trade(2, {
    Item.ChasingDownYourBounty: -120,
    Item.StashedTreasure: 5500
})

# amortizing travel cost
trade(0, {
    Item.StashedTreasure: -1250,
    Item.MourningCandle: 5
})

trade(0, {
    Item.StashedTreasure: -1250,
    Item.CaveAgedCodeOfHonour: 1
})

trade(0, {
    Item.StashedTreasure: -6250,
    Item.RelativelySafeZeeLane: 1
})

trade(0, {
    Item.StashedTreasure: -6250,
    Item.SaltSteppeAtlas: 1
})

trade(0, {
    Item.StashedTreasure: -31250,
    Item.FabulousDiamond: 1
})

# optimistic 100% draw rate of chasing cards
# pessimistic no rare success
trade(0, {
    Item.HomeWatersZeeDraw: -1,
    Item.ChasingDownYourBounty: 8
})

trade(0, {
    Item.ShephersWashZeeDraw: -1,
    Item.ChasingDownYourBounty: 8.5
})

trade(0, {
    Item.StormbonesZeeDraw: -1,
    Item.ChasingDownYourBounty: 8.5
})

trade(0, {
    Item.SeaOfVoicesZeeDraw: -1,
    Item.ChasingDownYourBounty: 9
})

trade(0, {
    Item.SaltSteppesZeeDraw: -1,
    Item.ChasingDownYourBounty: 13.5
})

trade(0, {
    Item.PillaredSeaZeeDraw: -1,
    Item.ChasingDownYourBounty: 14.5
})

trade(0, {
    Item.StormbonesZeeDraw: -1,
    Item.ChasingDownYourBounty: 15.5
})


## ------------
## Court of the Wakeful Eye Grind
## ------------

# Just make it one big blob
# Can't be arsed to figure out the 240/260 leftovers thing
# 14 actions = 2x the following
# - 1 action to dock
# - 2 actions in home waters
# - 4 actions in shephers wash

trade(14 + 50.6, {
    Item.HomeWatersZeeDraw: 4,
    Item.ShephersWashZeeDraw: 8,
    # Psuedo item represents tribute cap of 260
    Item.Tribute: -253,
    Item.NightWhisper: 12.65
})

# Gaining tribute

trade(1, {
    Item.Echo: -25,
    Item.Tribute: 10
})

trade(1, {
    Item.MagnificentDiamond: -1,
    Item.Tribute: 5
})

trade(1, {
    Item.PuzzleDamaskScrap: -1,
    Item.Tribute: 5
})

trade(1, {
    Item.CellarOfWine: -1,
    Item.Tribute: 5
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

trade(1, {
    Item.MemoryOfLight: -50,
    Item.Tribute: 10
})

trade(1, {
    Item.MountainSherd: -1,
    Item.Tribute: 35
})

trade(1, {
    Item.RoyalBlueFeather: -16,
    Item.Tribute: 4
})

trade(1, {
    Item.CorrespondencePlaque: -50,
    Item.Tribute: 10
})

trade(1, {
    Item.StrongBackedLabour: -1,
    Item.Tribute: 2
})

# trade(1, {
#     # throwing this random penalty in there arbitrarily
#     # to represent the fact that you're no longer bounded by cards
#     Item.CardDraws: -1,
#     Item.WinsomeDispossessedOrphan: -1,
#     Item.Tribute: 25
# })

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

# ███████╗ █████╗ ████████╗███████╗
# ██╔════╝██╔══██╗╚══██╔══╝██╔════╝
# █████╗  ███████║   ██║   █████╗  
# ██╔══╝  ██╔══██║   ██║   ██╔══╝  
# ██║     ██║  ██║   ██║   ███████╗
# ╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚══════╝

# -------------------
# --- Upwards
# ------------------

# TODO: confirm all of this

trade(9, {
    Item.CartographersHoard: -1,
    Item.FivePointedRibcage: 1
})

trade(7, {
    Item.FavourInHighPlaces: -1,
    Item.CartographersHoard: -1,
    Item.FivePointedRibcage: 1
})

trade(9, {
    Item.PentagrammicSkull: 1,
    Item.BoneFragments: 1900
})

trade(7, {
    Item.FavourInHighPlaces: -1,
    Item.PentagrammicSkull: 1,
    Item.BoneFragments: 1900
})

# -------------------
# --- Philosofruits
# -------------------

# TODO: travel cost estimate
# using wiki values

trade(5, {
    Item.CardDraws: -5,
    Item.BlackmailMaterial: 1,
    Item.AnIdentityUncovered: 3
})

trade(5, {
    Item.CardDraws: -5,
    Item.AntiqueMystery: 1,
    Item.PresbyteratePassphrase: 3
})

trade(5, {
    Item.CardDraws: -5,
    Item.UncannyIncunabulum: 1,
    Item.ExtraordinaryImplication: 3
})

trade(13, {
    Item.CardDraws: -13,
    Item.ComprehensiveBribe: 4,
})

trade(10, {
    Item.CardDraws: -10,
    Item.CorrespondencePlaque: 90,
})

trade(20, {
    Item.CardDraws: -20,
    Item.BottleOfFourthCityAirag: 1,
    Item.CellarOfWine: 2
})

trade(11, {
    Item.CardDraws: -11,
    Item.StormThrenody: 4
})

#  █████╗  █████╗ ██╗██╗     ██╗    ██╗ █████╗ ██╗   ██╗
# ██╔══██╗██╔══██╗██║██║     ██║    ██║██╔══██╗╚██╗ ██╔╝
# ██████╔╝███████║██║██║     ██║ █╗ ██║███████║ ╚████╔╝ 
# ██╔══██╗██╔══██║██║██║     ██║███╗██║██╔══██║  ╚██╔╝  
# ██║  ██║██║  ██║██║███████╗╚███╔███╔╝██║  ██║   ██║   
# ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝   

# Sets to 3
# In practice probably slightly better w overcap
trade(1, {
    Item.SeeingBanditryInTheUpperRiver: - (pyramid(8) - pyramid(3)),
    Item.ScandalCredit: -12
})

# Card: Intervene in an Attack
trade(1, {
    Item.SeeingBanditryInTheUpperRiver: -1,
    Item.InCorporateDebt: -1 * default_rare_success_rate,
    Item.PieceOfRostygold: 400
})

# -----
# Board Member Stuff
# -----

# Tentacled Entrepreneur rotation
trade(7, {
    Item.InCorporateDebt: -15,
    Item.HinterlandScrip: 10
})

# --------------
# Shops
# -------------

trade(0, {
    Item.HinterlandScrip: -2,
    Item.UnidentifiedThighbone: 1,
})

trade(0, {
    Item.HinterlandScrip: -85,
    Item.FossilisedForelimb: 1
})

# ----- Selling
trade(0, {
    Item.AmbiguousEolith: -1,
    Item.HinterlandScrip: 1
})

trade(0, {
    Item.FinalBreath: -1,
    Item.HinterlandScrip: 1
})

trade(0, {
    Item.HandPickedPeppercaps: -1,
    Item.HinterlandScrip: 1
})

trade(0, {
    Item.MovesInTheGreatGame: -1,
    Item.HinterlandScrip: 1
})

trade(0, {
    Item.NightsoilOfTheBazaar: -1,
    Item.HinterlandScrip: 1
})


trade(0, {
    Item.PotOfVenisonMarrow: -1,
    Item.HinterlandScrip: 1
})

trade(0, {
    Item.RoyalBlueFeather: -1,
    Item.HinterlandScrip: 1
})

trade(0, {
    Item.SolaceFruit: -1,
    Item.HinterlandScrip: 1
})

trade(0, {
    Item.SurveyOfTheNeathsBones: -1,
    Item.HinterlandScrip: 1
})

trade(0, {
    Item.UnidentifiedThighbone: -1,
    Item.HinterlandScrip: 1
})

trade(0, {
    Item.PreservedSurfaceBlooms: -1,
    Item.HinterlandScrip: 3
})

trade(0, {
    Item.CarvedBallOfStygianIvory: -1,
    Item.HinterlandScrip: 5
})

trade(0, {
    Item.CrateOfIncorruptibleBiscuits: -1,
    Item.HinterlandScrip: 5
})

trade(0, {
    Item.KnobOfScintillack: -1,
    Item.HinterlandScrip: 5
})

trade(0, {
    Item.NicatoreanRelic: -1,
    Item.HinterlandScrip: 5
})

trade(0, {
    Item.TailfeatherBrilliantAsFlame: -1,
    Item.HinterlandScrip: 5
})

trade(0, {
    Item.ViennaOpening: -1,
    Item.HinterlandScrip: 5
})

trade(0, {
    Item.UnlawfulDevice: -1,
    Item.HinterlandScrip: 25
})

trade(0, {
    Item.VitalIntelligence: -1,
    Item.HinterlandScrip: 25
})

trade(0, {
    Item.QueenMate: -1,
    Item.HinterlandScrip: 50
})


trade(0, {
    Item.EpauletteMate: -1,
    Item.HinterlandScrip: 50
})

trade(0, {
    Item.SapOfTheCedarAtTheCrossroads: -1,
    Item.HinterlandScrip: 125
})

trade(0, {
    Item.Stalemate: -1,
    Item.HinterlandScrip: 125
})

trade(0, {
    Item.CartographersHoard: -1,
    Item.HinterlandScrip: 625
})


# --------------
# Ealing
# -------------

# Helicon House
# TODO: fix total carousel stuff here
trade(1.2, {
    Item.FinBonesCollected: -10,
    Item.AmberCrustedFin: 1
})

# -- Butcher
trade(1, {
    Item.BoneFragments: -130,
    Item.NoduleOfWarmAmber: -2,
    Item.WarblerSkeleton: 2
})

trade(1, {
    Item.BoneFragments: -100,
    Item.NoduleOfWarmAmber: -2,
    Item.BatWing: 2
})

trade(1, {
    Item.BoneFragments: -2000,
    Item.NoduleOfWarmAmber: -25,
    Item.AlbatrossWing: 2
})

trade(1, {
    Item.BoneFragments: -4900,
    Item.NoduleOfWarmAmber: -125,
    Item.SabreToothedSkull: 1,
    Item.FemurOfASurfaceDeer: 0.5,
    Item.UnidentifiedThighbone: 0.5
})

trade(1, {
    Item.BoneFragments: -1000,
    Item.NoduleOfWarmAmber: -5,
    Item.HornedSkull: 1
})

trade(1, {
    Item.BoneFragments: -200,
    Item.NoduleOfWarmAmber: -2,
    Item.TombLionsTail: 2
})

trade(1, {
    Item.BoneFragments: -100,
    Item.NoduleOfWarmAmber: -25,
    Item.WingOfAYoungTerrorBird: 2
})

trade(1, {
    Item.BoneFragments: -1750,
    Item.NoduleOfWarmAmber: -25,
    Item.CrateOfIncorruptibleBiscuits: -1,
    Item.PlatedSkull: 1
})

# --- Sponsor a Dig
# NB: Wiki is uncertain about some ranges

trade(1, {
    Item.StrongBackedLabour: -1,
    Item.SurveyOfTheNeathsBones: -50,
    Item.HelicalThighbone: 3,
    Item.KnottedHumerus: 2.5,
    Item.HumanRibcage: 1,
    Item.BoneFragments: 385.5
})

trade(1, {
    Item.StrongBackedLabour: -1,
    Item.SurveyOfTheNeathsBones: -75,
    Item.ThornedRibcage: 1,
    Item.HornedSkull: 1,
    Item.FemurOfAJurassicBeast: 4,
    Item.JetBlackStinger: 4,
    Item.FinBonesCollected: 12.5
})


trade(1, {
    Item.StrongBackedLabour: -1,
    Item.SurveyOfTheNeathsBones: -163,
    Item.PalaeontologicalDiscovery: 7
})


trade(1, {
    Item.StrongBackedLabour: -1,
    Item.SurveyOfTheNeathsBones: 175,
    Item.MagisterialLager: -10,
    Item.PalaeontologicalDiscovery: 7,
    Item.Echo: 6.3 # estimated Rusted Stirrup value
})

trade(0, {
    Item.PalaeontologicalDiscovery: -25,
    Item.LeviathanFrame: 1
})

trade(0, {
    Item.PalaeontologicalDiscovery: -5,
    Item.MammothRibcage: 1
})

trade(0, {
    Item.PalaeontologicalDiscovery: -5,
    Item.SabreToothedSkull: 1
})

trade(0, {
    Item.PalaeontologicalDiscovery: -4,
    Item.FossilisedForelimb: 2
})

trade(0, {
    Item.PalaeontologicalDiscovery: -3,
    Item.HumanRibcage: 2,
    Item.HumanArm: 4
    # Item.TraceOfTheFirstCity: 5
})

trade(0, {
    Item.PalaeontologicalDiscovery: -2,
    Item.HelicalThighbone: 6,
    Item.KnottedHumerus: 4
})

trade(0, {
    Item.PalaeontologicalDiscovery: -2,
    Item.ThornedRibcage: 2,
})

trade(0, {
    Item.PalaeontologicalDiscovery: -1,
    Item.HornedSkull: 1
})

trade(0, {
    Item.PalaeontologicalDiscovery: -1,
    Item.FemurOfAJurassicBeast: 6,
})

trade(0, {
    Item.PalaeontologicalDiscovery: -1,
    Item.BoneFragments: 1250,
})


# -----------------------------------
# ---- Jericho
# -----------------------------------

# --------- Canal Cruising

if player_profession == Profession.CrookedCross:
    trade(1, {
        Item.UnprovenancedArtefact: -4,
        Item.EsteemOfTheGuild: 1
    })

trade(1, {
    Item.VolumeOfCollatedResearch: -10,
    Item.EsteemOfTheGuild: 2
})

trade(1, {
    Item.PartialMap: -6,
    Item.AnIdentityUncovered: -4,
    Item.EsteemOfTheGuild: 2
})

# trade(1, {
#     Item.MemoryOfDistantShores: -40,
#     Item.SwornStatement: -2,
#     Item.EsteemOfTheGuild: 2
# })

trade(1, {
    Item.NightOnTheTown: -1,
    Item.ScrapOfIncendiaryGossip: -45,
    Item.EsteemOfTheGuild: 2
})

trade(1, {
    Item.FavDocks: -5,
    Item.EsteemOfTheGuild: 2
})

# assume ranges are evenly distributed
trade(2, {
    Item.EsteemOfTheGuild: -3,
    Item.VitalIntelligence: 2.5,
    Item.ViennaOpening: 6.5
})

trade(2, {
    Item.EsteemOfTheGuild: -3,
    Item.MirrorcatchBox: 1
})

trade(2, {
    Item.EsteemOfTheGuild: -3,
    Item.MoonlightScales: 50,
    Item.FinBonesCollected: 5,
    Item.SkullInCoral: 1.5,
    Item.UnprovenancedArtefact: 8.5
})

# upper river destinations

trade(2, {
    Item.EsteemOfTheGuild: -6,
    Item.BrightBrassSkull: 1,
    Item.ExtraordinaryImplication: 5.5,
    Item.VerseOfCounterCreed: 2.5
})

trade(2, {
    Item.EsteemOfTheGuild: -6,
    Item.MovesInTheGreatGame: 18.5,
    Item.PrimaevalHint: 1,
    Item.UncannyIncunabulum: 2.5
})

trade(2, {
    Item.EsteemOfTheGuild: -6,
    Item.NightWhisper: 1,
    Item.TaleOfTerror: 3.5,
    Item.FinalBreath: 12,
    Item.HumanRibcage: 2
})


# --------- Calling in Favours
# hack to model dipping into jericho to trade favours
# when you would otherwise not go there

jericho_add = 0.0
def jericho_trade(exchange):
    exchange[Item.RumourOfTheUpperRiver] = jericho_add
    trade(1 + jericho_add, exchange)

jericho_trade({
    Item.FavBohemians: -4,
    Item.HolyRelicOfTheThighOfStFiacre: 2,
    Item.WingOfAYoungTerrorBird: 1,
})

jericho_trade({
    Item.FavChurch: -4,
    Item.RattyReliquary: 2,
    Item.ApostatesPsalm: 1,
})

jericho_trade({
    Item.FavConstables: -4,
    Item.CaveAgedCodeOfHonour: 2,
    Item.SwornStatement: 1
})

jericho_trade({
    Item.FavCriminals: -4,
    Item.HumanRibcage: 2,
    Item.HumanArm: 1
})

jericho_trade({
    Item.FavDocks: -4,
    Item.UncannyIncunabulum: 2,
    Item.KnobOfScintillack: 1
})

jericho_trade({
    Item.FavGreatGame: -4,
    Item.ViennaOpening: 1,
    Item.QueenMate: 1
})

jericho_trade({
    Item.FavHell: -4,
    Item.ThornedRibcage: 2,
    Item.QueerSoul: 1
})

jericho_trade({
    Item.FavRevolutionaries: -4,
    Item.UnlawfulDevice: 2,
    Item.ThirstyBombazineScrap: 1
})

jericho_trade({
    Item.FavRubberyMen: -4,
    Item.FlourishingRibcage: 2,
    Item.BasketOfRubberyPies: 1,
})

jericho_trade({
    Item.FavSociety: -4,
    Item.FavourInHighPlaces: 2,
    Item.NightOnTheTown: 1
})

jericho_trade({
    Item.FavTombColonies: -4,
    Item.AntiqueMystery: 2,
    Item.UnprovenancedArtefact: 1,
})

jericho_trade({
    Item.FavUrchins: -4,
    Item.StormThrenody: 2,
    Item.AeolianScream: 1
})

# --------------
# Evenlode
# -------------


railway_card("Digs in the Magistracy of the Evenlode", Rarity.Standard, True, {
    Item.DigsInEvenlode: 1
})

trade(0, {
    Item.DigsInEvenlode: -1,
    Item.SurveyOfTheNeathsBones: -120,
    Item.PalaeontologicalDiscovery: 5
})


trade(0, {
    Item.DigsInEvenlode: -1,
    Item.SurveyOfTheNeathsBones: -140,
    Item.PalaeontologicalDiscovery: 6
})

# specific treasure only
trade(0, {
    Item.DigsInEvenlode: -1,
    Item.SurveyOfTheNeathsBones: -240,
    Item.PalaeontologicalDiscovery: 10
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

    Item.SkeletonWithSevenNecks: 1,
    Item.WingOfAYoungTerrorBird: 3,
    Item.BoneFragments: 200
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


# ----------------
# --- The Hurlers
# ----------------


# Licensed by Mr Stones

trade(1, {
    Item.FlawedDiamond: -100,
    Item.HinterlandScrip: 30
})

trade(1, {
    Item.OstentatiousDiamond: -25,
    Item.CrateOfIncorruptibleBiscuits: 6
})

trade(1, {
    Item.MagnificentDiamond: -1,
    Item.TouchingLoveStory: 5.5 # assumes uniform 5 or 6
})

trade(1, {
    Item.FabulousDiamond: -1,
    Item.HinterlandScrip: 625,
    Item.StolenKiss: 2
})


# -------------------------------
# ---- Opportunity Deck Math ----
# -------------------------------

# London Deck
# subtract 400 for holding 4 bad standard freq cards in hand
deck_size = LondonDeckSize - 400;
good_card_density = GoodCardsInDeck / deck_size
card_exchange = {}

for item in Item:
    if LondonCardsByItem[item.value] != 0:
        card_exchange[item] = (LondonCardsByItem[item.value] / deck_size)

card_exchange[Item.CardDraws] = -1

# print(card_exchange)
trade(good_card_density, card_exchange)
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

optimize_for = Item.Echo

c = np.zeros(num_vars)
c[optimize_for.value] = -1

opt_result = linprog(c, A_ub=A.toarray(), b_ub=b, bounds=bounds, method='highs')
print(opt_result)

# print("Opp Deck")

# print(f"{'Item Name':^30}")
# # for item, quantity in zip(Item, opt_result.x):
# #     item_name = f"{item.name:30}"
# #     per_action = f"{(1.0/(quantity * actions_per_day) if quantity != 0 else 0.0):10.3f}"
# #     per_card = LondonCardsByItem[item.value] / LondonDeckSize
# #     per_day_of_draws = per_card * cards_seen_per_day
# #     print(item_name + per_action + ((f"{per_card:10.2f}" + f"{per_day_of_draws:10.2f}") if per_card != 0 else ""))


results = sorted(zip(Item, opt_result.x), key=lambda x: x[1])
for item, quantity in results:
    item_name = f"{item.name:40}"
    if quantity > 0:
        print(item_name
        + f"{1/(quantity * actions_per_day):10.5}")
    else:
        print(item_name + f"{'unsourced':10}")
    
pp = pprint.PrettyPrinter(indent=4)


print("------Assumptions-------")
print(f"Total Actions per Day:            {actions_per_day:10}")
print(f"Cards Drawn per Day:              {cards_seen_per_day:10}")
print(f"Good Card Density:                {good_card_density:10.3f}")

print(f"Optimize For:                     {optimize_for}")
print(f"-Player Stats-")
pp.pprint(player_stats)

print("------Summary-------")
print(f"{str(optimize_for) + ' Per Day:':34}{-1.0/(opt_result.fun):10.3f}")
print(f"{str(optimize_for) + ' Per Action':34}{-1.0/(opt_result.fun * actions_per_day):10.3f}")

# pp = pprint.PrettyPrinter(indent=4)
# pp.pprint(A)
# pp.pprint(A[0])
# pp.pprint(A[100, 0])

# print("-----Trades NOT USED-------")
# for i in range(0, len(opt_result.slack)):
#     slack = opt_result.slack[i]
#     marginal = opt_result.ineqlin.marginals[i]
#     if (slack != 1.0 and (slack > 1.0 or  marginal == 0)):
#         trade_items = ""
#         for ii in range(0, num_items):
#             if A[i, ii] != 0:
#                 trade_items += str(Item(ii)) + ":" + str(A[i, ii]) + "; "
#         print(f"Slack: {slack:3.3} " + trade_items)


print("-----Trades In Grind-------")
for i in range(0, len(opt_result.slack)):
    slack = opt_result.slack[i]
    marginal = opt_result.ineqlin.marginals[i]
    if (slack < 1.0 and marginal != 0):
        lose_items = ""
        gain_items = ""
        for ii in range(0, num_items):
            quantity = round(A[i, ii],2)
            if int(quantity) == quantity:
                quantity = int(quantity)
            if quantity < 0:
                lose_items += str(Item(ii)) + ":" + str(quantity) + "; "
            if quantity > 0:
                gain_items += str(Item(ii)) + ":" + str(quantity) + "; "
        trade_items = lose_items + " => " + gain_items            
        trade_items = trade_items.replace("Item.","");
        # print("* " + trade_items)
        print(f"{marginal:.3}       " + trade_items)

print(f"{str(optimize_for) + ' Per Action':34}{-1.0/(opt_result.fun * actions_per_day):10.5f}")
