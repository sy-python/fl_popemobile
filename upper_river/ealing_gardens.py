from enums import *
from utils import *
from player import *
from config import *

def add_trades(active_player: Player, config):
    trade = config.trade
    # ---- Helicon House

    '''
    Progress: mostly done
    - butcher: done
    - helicon house: major grinds done
    - spa: done
    - digs: done

    - deck: TODO
    
    there's gonna be some weird-looking stuff in this section
    these are hacks to accomodate:
    - zeroing out unspent qualities when you leave
    - certain options only being available at specific "times"
    - other things I don't know how to cleanly model
    '''

    initial_fitting_in = 3

    # action costs paid upfront to prevent dipping in and out
    trade(6, {
        Item.TimeRemainingAtHeliconHouseTwoThruFive: 4,
        Item.TimeRemainingAtHeliconHouseExactlyOne: 1,

        # with spouse & FATE pendant
        Item.FittingInAtHeliconHouse: initial_fitting_in,
        Item.IntriguingSnippet: 3
    })

    trade(5, {
        Item.TimeRemainingAtHeliconHouseTwoThruFive: 3,
        Item.TimeRemainingAtHeliconHouseExactlyOne: 1,

        # with spouse & FATE pendant
        Item.FittingInAtHeliconHouse: initial_fitting_in,
    })

    # Entrance Hall
    trade(0, {
        Item.TimeRemainingAtHeliconHouseTwoThruFive: -1,
        Item.HandPickedPeppercaps: -1,
        Item.FittingInAtHeliconHouse: 2,
        Item.Investigating: 20
    })

    trade(0, {
        Item.TimeRemainingAtHeliconHouseExactlyOne: -1,
        # stop FittingIn from carrying over 
        Item.FittingInAtHeliconHouse: -1 * initial_fitting_in,
        Item.CrateOfIncorruptibleBiscuits: 4,
        Item.PotOfVenisonMarrow: 5.5
    })

    for i in range(0, 5):
        fitting_in = initial_fitting_in + i * 2
        trade(0, {
            Item.TimeRemainingAtHeliconHouseExactlyOne: -1,
            Item.FittingInAtHeliconHouse: -1 * fitting_in,
            Item.HandPickedPeppercaps: fitting_in,
            Item.SolaceFruit: 20
        })

        trade(0, {
            Item.TimeRemainingAtHeliconHouseExactlyOne: -1,
            Item.FittingInAtHeliconHouse: -1 * fitting_in,
            Item.HandPickedPeppercaps: 15 + fitting_in,
            Item.ThirstyBombazineScrap: 1
        })

    # The Upstairs Honey Den
    # more variable but not gonna bother rn
    trade(0, {
        Item.TimeRemainingAtHeliconHouseExactlyOne: -1,
        Item.Casing: -15,
        Item.FittingInAtHeliconHouse: -3,
        Item.HinterlandScrip: 26,
        Item.DropOfPrisonersHoney: 10.5,
        Item.MoonPearl: 25.5,
    })

    trade(0, {
        Item.TimeRemainingAtHeliconHouseTwoThruFive: -1,
        Item.FittingInAtHeliconHouse:
            2 if active_player.profession == Profession.Silverer else 1,
        Item.Inspired: 6
    })

    # Bellow Stairs

    # actually requires 4+ fitting in
    trade(0, {
        Item.TimeRemainingAtHeliconHouseTwoThruFive: -1,
        Item.NoduleOfWarmAmber: -5,
        Item.WitheredTentacle: 3,
        Item.FittingInAtHeliconHouse: 2
    })

    trade(0, {
        Item.TimeRemainingAtHeliconHouseTwoThruFive: -1,
        Item.FinBonesCollected: -10,
        Item.AmberCrustedFin: 1
    })

    trade(0, {
        Item.TimeRemainingAtHeliconHouseExactlyOne: -1,
        Item.FinBonesCollected: -10,
        Item.AmberCrustedFin: 1
    })

    trade(0, {
        Item.TimeRemainingAtHeliconHouseTwoThruFive: -1,
        Item.HumanRibcage: -1,
        Item.ThornedRibcage: -1,
        Item.FlourishingRibcage: 1
    })

    trade(0, {
        Item.TimeRemainingAtHeliconHouseExactlyOne: -1,
        Item.HumanRibcage: -1,
        Item.ThornedRibcage: -1,
        Item.FlourishingRibcage: 1
    })

    trade(0, {
        Item.TimeRemainingAtHeliconHouseTwoThruFive: -1,
        Item.ThornedRibcage: -1,
        Item.SkeletonWithSevenNecks: -1,
        Item.NoduleOfTremblingAmber: -3,
        Item.SearingEnigma: -3,
        Item.RibcageWithABoutiqueOfEightSpines: 1
    })

    trade(0, {
        Item.TimeRemainingAtHeliconHouseExactlyOne: -1,
        Item.ThornedRibcage: -1,
        Item.SkeletonWithSevenNecks: -1,
        Item.NoduleOfTremblingAmber: -3,
        Item.SearingEnigma: -3,
        Item.RibcageWithABoutiqueOfEightSpines: 1
    })

    '''
    spouse options of interest
    - +5 fascinating
    - +5 investigating
    - +5 inspired
    - +2 each of casing, investigating, fascinating (PC spouse)
    - Nemesis "Returned" treasures give -6 CP of menaces but obv are incompatible
    '''

    # full carousel
    # how to model the variable time cost?
    # priests option needs 5 fitting in
    # not sure what the best way is to get the remaining 2
    # trades below consider various ways to do so

    # if it turns out the best filler source is one that gives 3 or more
    # then you can use a different spouse for entry

    # example:
    # if you happen to be a Silverer with LDPotRB
    # 1) Enter with pendant
    # 2) Offer yourself as escort and guide
    # 3) nightmare on elm street
    # how much do you need to get from the lesser self + discordance?
    # if getting inspired from the palace, like 30 echoes
    # if social action, only 19. that might be doable?

    # TODO: implement "Entry" token for one of:
    # 3x Intriguing Snippet
    # 5x Romantic Notion
    # 5x Warm Amber

    if (active_player.treasure == Treasure.LongDeadPriestsOfTheRedBird):
        trade(3, {
            Item.IntriguingSnippet: 3,

            Item.Inspired: -55 + 6,
            Item.MemoryOfLight: 6,
            Item.MemoryOfDistantShores: 6,
            Item.MemoryOfALesserSelf: 1,
            Item.MemoryOfDiscordance: 1
        })

        # Master Jewel Thief
        trade(3, {
            Item.IntriguingSnippet: 3,

            Item.Inspired: -55,
            Item.Casing: -3,
            Item.Echo: 3.36,
            Item.MemoryOfLight: 6,
            Item.MemoryOfDistantShores: 6,
            Item.MemoryOfALesserSelf: 1,
            Item.MemoryOfDiscordance: 1
        })

        # Rubbery Cat
        trade(3, {
            Item.IntriguingSnippet: 3,

            Item.Inspired: -55,
            Item.Casing: 6,
            Item.HandPickedPeppercaps: 3,
            Item.MemoryOfLight: 6,
            Item.MemoryOfDistantShores: 6,
            Item.MemoryOfALesserSelf: 1,
            Item.MemoryOfDiscordance: 1
        })

        # enter with secular missionary or firebrand
        trade(3, {
            Item.IntriguingSnippet: 3,

            Item.Inspired: -55 + 5,
            Item.CulinaryTributeToTheSeaOfSpines: -1,

            Item.HinterlandScrip: 56,
            Item.MemoryOfLight: 6,
            Item.MemoryOfDistantShores: 6,
            Item.MemoryOfALesserSelf: 1,
            Item.MemoryOfDiscordance: 1
        })

        if (active_player.profession == Profession.Silverer):
            # 1) Enter with pendant & firebrand or missionary
            #   +3 snippets, +3 Fitting In, +5 Inspired
            # 2) Offer yourself as escort and guide
            #   +2 Fitting In, +6 Inspired
            # 3) Spooky scary skeletons

            # counting one action to make up difference in inspired
            # (end up with +2 Inspired per loop, so every 23rd loop is only 3 actions)
            # gives 0.6 + 3 + 3 + 2.5 + 12.5 = 21.6 echoes
            # about 5.46 EPA selling at price
            # still not worth it
            # maybe use the 2nd action to sell paintings instead
            
            trade(3, {
                Item.IntriguingSnippet: 3,

                Item.Inspired: -55 + 5 + 6,
                Item.MemoryOfLight: 6,
                Item.MemoryOfDistantShores: 6,
                Item.MemoryOfALesserSelf: 1,
                Item.MemoryOfDiscordance: 1
            })

    # placeholder
    # trade(0, {
    #     Item.MemoryOfALesserSelf: -1,
    #     # Item.MemoryOfDiscordance: -1,
    #     Item.Echo: 2.5
    # })

    # TODO: display your painting option

    # ----- Butcher

    trade(1, {
        Item.FemurOfASurfaceDeer: -5,
        Item.PotOfVenisonMarrow: 5
    })

    trade(1, {
        Item.RatOnAString: -1000,
        Item.SausageAboutWhichNoOneComplains: 1
    })

    trade(1, {
        Item.DeepZeeCatch: -1,
        Item.CrustaceanPincer: 2
    })

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
        Item.RustedStirrup: 63
    })

    # --- Spa
    
    # wild guess
    spa_rare_success_rate = 0.1
    spa_normal_success_rate = 1 - spa_rare_success_rate

    trade(1, {
        Item.BrilliantSoul: 1.5 * spa_normal_success_rate,
        Item.Soul: 100 * spa_normal_success_rate,
        Item.CompromisingDocument: 6 * spa_rare_success_rate
    })

    trade(1, {
        Item.BrilliantSoul: 5 * spa_normal_success_rate,
        Item.SilentSoul: 1 * spa_rare_success_rate,
        Item.FavHell: 1 * spa_rare_success_rate
    })

    # --- Rubbery Pie Stand
    
    trade(1, {
        Item.BasketOfRubberyPies: -5,
        Item.InCorporateDebt: -3
    })

    trade(1, {
        Item.BasketOfRubberyPies: -5,
        Item.HinterlandScrip: 32
    })