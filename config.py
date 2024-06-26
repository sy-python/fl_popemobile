import numbers
import player as Player
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve
from scipy.sparse import csc_matrix
from scipy.optimize import linprog
from enum import Enum, auto
from itertools import count

from enums import *
import utils as utils

class Config:
    player: Player.Player

    def __init__(self, num_vars, player):
        self.player = player
        self.A = lil_matrix((num_vars, num_vars))
        self.b = [1]*num_vars
        
        self.counter = count(start=-1)

        self.bounds = [(0, None) for _ in range(num_vars)]

        # in practice it seems this rarely affects the output, but it makes me feel better
        # I don't know if this even works the way I think it does as far as modeling long-term stockpiling
        # but if you set it too low, you will lock out certain trades
        # eg setting the upper bound of Bohemian favours to 3 will lock out the Jericho option
        # so really it's a source of bugs more than anything else
        # still keeping it in

        # important that menace is capped at 0
        # ensures any gains are pre-paid for
        self.bounds[Item.Wounds.value] = (None, 0)
        self.bounds[Item.Scandal.value] = (None, 0)
        self.bounds[Item.Suspicion.value] = (None, 0)
        self.bounds[Item.Nightmares.value] = (None, 0)

        self.bounds[Item.TroubledWaters.value] = (None, 35)

        self.bounds[Item.BoneMarketExhaustion.value] = (-4, 0)

        self.bounds[Item.Hedonist.value] = (0, 55)

        self.bounds[Item.InCorporateDebt.value] = (None, 15)
        self.bounds[Item.SeeingBanditryInTheUpperRiver.value] = (0, 36)

        self.bounds[Item.ConnectedBenthic.value] = (0, 800)

        self.bounds[Item.Tribute.value] = (0, 260)
        self.bounds[Item.TimeAtWakefulCourt.value] = (0, 13)
        self.bounds[Item.TimeAtJerichoLocks.value] = (0, 5)

        self.bounds[Item.FavBohemians.value] = (0, 7)
        self.bounds[Item.FavChurch.value] = (0, 7)
        self.bounds[Item.FavConstables.value] = (0, 7)
        self.bounds[Item.FavCriminals.value] = (0, 7)
        self.bounds[Item.FavDocks.value] = (0, 7)
        self.bounds[Item.FavGreatGame.value] = (0, 7)
        self.bounds[Item.FavHell.value] = (0, 7)
        self.bounds[Item.FavRevolutionaries.value] = (0, 7)
        self.bounds[Item.FavRubberyMen.value] = (0, 7)
        self.bounds[Item.FavSociety.value] = (0, 7)
        self.bounds[Item.FavTombColonies.value] = (0, 7)
        self.bounds[Item.FavUrchins.value] = (0, 7)

        self.bounds[Item.ResearchOnAMorbidFad.value] = (0, 6)

        self.bounds[Item.RecentParticipantInAStarvedCulturalExchange.value] = (-1, 0)

        self.bounds[Item.DelayUntilTheNextBoardMeeting.value] = (-1, 0)

        self.bounds[Item.CoverTiesGeneric.value] = (0, 1)
        self.bounds[Item.CoverTiesSurface.value] = (0, 1)
        self.bounds[Item.CoverTiesBazaar.value] = (0, 1)
        self.bounds[Item.CoverTiesDispossessed.value] = (0, 1)

        self.bounds[Item.RatMarketExhaustion.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek1ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek2ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek3ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek4ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek5ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek6ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek7ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek8ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek9ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek10ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek11ExhaustionStage1.value] = (-50_000, 0)
        self.bounds[Item.RatMarketWeek12ExhaustionStage1.value] = (-50_000, 0)

        self.bounds[Item.RatMarketWeek1ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek2ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek3ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek4ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek5ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek6ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek7ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek8ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek9ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek10ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek11ExhaustionStage2.value] = (-30_000, 0)
        self.bounds[Item.RatMarketWeek12ExhaustionStage2.value] = (-30_000, 0)

        self.bounds[Item.RatMarketWeek1ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek2ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek3ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek4ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek5ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek6ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek7ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek8ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek9ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek10ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek11ExhaustionStage3.value] = (-90_000, 0)
        self.bounds[Item.RatMarketWeek12ExhaustionStage3.value] = (-90_000, 0)      

        self.bounds[Item.WhiskerwaysSecondaryPayout.value] = (None, 0)  

        self.enable_all_rat_market_moons = True

    def add(self, exchanges: dict):
        n = next(self.counter)
        self.b[n] = exchanges.get(Item.Constraint, 0)
        for key, value in exchanges.items():
            if key != Item.Constraint:
                self.A[n, key.value] = value

    # def per_day(self, exchanges):
    #     n = next(self.counter)
    #     self.b[n] = 1
    #     for item, value in exchanges.items():
    #         self.A[n, item.value] = value

    def trade(self, actionCost, exchanges):
        n = next(self.counter)
        self.b[n] = 0
        self.A[n, Item.Action.value] = -1 * actionCost
        for item, value in exchanges.items():
            self.A[n, item.value] = value

    def railway_card(self, name, freq, location, isGood, exchanges):
        # dummy alias for now
        self.trade(1, exchanges)

    def add_weighted_trade(self, actions, *weighted_trades):
        net_trade = {}

        for weight, trade in weighted_trades:
            for key, val in trade.items():
                net_trade[key] = net_trade.get(key, 0) + val * weight

        self.trade(actions, net_trade)

    def uniform_random_trade(self, input, outputs):
        net_output = {}
        num = len(outputs)

        for i in outputs:
            for key, val in i.items():
                net_output[key] = net_output.get(key, 0) + (val / num)

        net_trade = utils.sum_dicts(input, net_output)
        self.trade(0, net_trade)        
    
    def weighted_trade(self, cost, *weighted_trades):
        weighted_outcome = {}

        for weight, trade in weighted_trades:
            for key, val in trade.items():
                weighted_outcome[key] = weighted_outcome.get(key, 0) + val * weight

        net_trade = utils.sum_dicts(cost, weighted_outcome)
        self.trade(0, net_trade)

    def challenge_ev(self, stat: Stat, dc: int, on_pass: dict, on_fail: dict):
        pass_rate = self.player.pass_rate(stat, dc)

        return utils.weighted_exchange(
            (pass_rate, on_pass),
            (1.0 - pass_rate, on_fail)
        )
    
    def challenge_trade(self, stat: Stat, dc: int, cost, on_pass, on_fail):
        pass_rate = self.player.pass_rate(stat, dc)

        self.weighted_trade(
            cost,
            (pass_rate, on_pass),
            (1.0 - pass_rate, on_fail)
        )