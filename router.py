#! python3
# coding: utf-8

import itertools

INF = float('inf')

class c_route:

    def __init__(self, path, grpkey, tired, profits, total_tired = None, total_profit = None):
        self.path = path
        self.plen = len(path)
        self.grpkey = grpkey
        self.tlst = tired
        if total_tired is None:
            total_tired = sum(tired)
        self.tired = total_tired
        if total_profit is None:
            total_profit = sum(p * n for _, p, n in profits.values())
        self.profits = profits
        self.total = total_profit
        self.benefit = total_profit / self.tired

    def new_profits(self, profits, total_profit = None):
        return c_route(
            self.path, self.grpkey, self.tlst,
            profits, self.tired, total_profit)

    def repr_path(self):
        return ' -> '.join((*self.path, self.path[0]))

    def __repr__(self):
        return f'<rt {len(self.path)}: {self.grpkey:X} {", ".join(self.path)} | {self.benefit:.2f}: {self.total:.2f}/{self.tired}>'

class c_router:

    def __init__(self, predictor):
        self.prd = predictor

    def update(self):
        return self.prd.update()

    def get_config(self):
        return self.prd.get_config()

    def _iter_tired(self, path):
        lp = len(path)
        for i in range(lp -1):
            yield self.prd.get_picker().get_tired(path[i], path[i + 1])
        yield self.prd.get_picker().get_tired(path[lp - 1], path[0])

    @staticmethod
    def _iter_idx(n):
        wk = set()
        for seq in itertools.permutations(range(n)):
            if seq in wk:
                continue
            dbseq = seq *2
            for i in range(n):
                wk.add(dbseq[i:i+n])
            yield seq

    def _iter_route(self, cgrp):
        assert len(cgrp) > 1
        for iseq in self._iter_idx(len(cgrp)):
            path = tuple(cgrp[i] for i in iseq)
            yield path, tuple(self._iter_tired(path))

    def _calc_profit(self, city_list, cgrp, time):
        profits = {}
        for src in cgrp:
            buy_list = {
                nm: self.prd.get_buy(nm, src, time)
                for nm in city_list[src]
            }
            for dst in cgrp:
                if src == dst:
                    continue
                for nm, buy_info in buy_list.items():
                    sell_info = self.prd.get_sell(nm, dst, time)
                    if sell_info is None:
                        assert self.prd.get_picker().get_buy(nm, dst)
                        continue
                    prf = sell_info['price'] - buy_info['price']
                    pkey = (nm, src)
                    if not pkey in profits or prf > profits[pkey][1]:
                        if prf > 0:
                            num = buy_info['number']
                        else:
                            num = 0
                        profits[pkey] = (dst, prf, num)
        total = sum(p * n for _, p, n in profits.values())
        return profits, total

    def _iter_group(self, n, time):
        cfg = self.get_config()
        city_list = self.prd.get_picker().get_city_list()
        ckeys = list(
            c for c in city_list.keys()
            if not cfg.get(['city block', c]))
        for igrp in itertools.combinations(range(len(ckeys)), n):
            cgrp = tuple(ckeys[i] for i in igrp)
            grpkey = sum(1 << i for i in igrp)
            profits, total = self._calc_profit(city_list, cgrp, time)
            yield cgrp, grpkey, total, profits

    def get_city_list(self):
        return self.prd.get_picker().get_city_list()

    def calc_market(self, time = None):
        city_list = self.prd.get_picker().get_city_list()
        cgrp = tuple(city_list.keys())
        profits, total = self._calc_profit(city_list, cgrp, time)
        return total, profits

    def calc_prd_market(self, time_seq):
        total = 0
        for time in time_seq:
            total += self.calc_market(time)[0]
        return total / len(time_seq)

    def iter_routes(self, mxn, time):
        for cgrp, grpkey, total, profits in (
                ginfo
                for n in range(2, mxn + 1)
                for ginfo in self._iter_group(n, time)):
            min_tired = INF
            min_rts = []
            for path, tlst in self._iter_route(cgrp):
                tired = sum(tlst)
                if tired > min_tired:
                    continue
                elif tired < min_tired:
                    min_tired = tired
                    min_rts = []
                route = c_route(path, grpkey, tlst, profits,
                    total_tired = tired, total_profit = total)
                min_rts.append(route)
            yield min_rts, min_rts[0].benefit, grpkey

    def recalc_profits(self, route, time):
        city_list = self.prd.get_picker().get_city_list()
        profits, total = self._calc_profit(city_list, route.path, time)
        return route.new_profits(profits, total)

    def sorted_routes(self, mxn, time = None):
        return [rts for rts, _, _ in sorted(
            self.iter_routes(mxn, time),
            key = lambda i: i[1], reverse = True)]

    def sorted_prd_routes(self, mxn, time_seq):
        rs = {}
        for time in time_seq:
            for rts, ben, gkey in self.iter_routes(mxn, time):
                if gkey in rs:
                    rs[gkey][1] += ben
                else:
                    rs[gkey] = [rts, ben]
        tlen = len(time_seq)
        return [(rts, ben / tlen) for rts, ben in sorted(
            rs.values(),
            key = lambda i: i[1], reverse = True)]

from predictor import make_predictor

def make_router():
    return c_router(make_predictor())

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    rtr = make_router()
