#! python3
# coding: utf-8

import itertools

class c_route:

    def __init__(self, path, tired, profits, total = None):
        self.path = path
        self.tlst = tired
        self.tired = sum(tired)
        if total is None:
            total = sum(p * n for _, p, n in profits.values())
        self.profits = profits
        self.total = total
        self.benefit = total / self.tired

    def __repr__(self):
        return f'<rt {len(self.path)}: {", ".join(self.path)} | {self.benefit:.2f}: {self.total:.2f}/{self.tired}>'

class c_router:

    def __init__(self, predictor):
        self.prd = predictor

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
        city_list = self.prd.get_picker().get_city_list()
        for cgrp in itertools.combinations(city_list.keys(), n):
            profits, total = self._calc_profit(city_list, cgrp, time)
            yield cgrp, total, profits

    def iter_routes(self, mxn, time):
        for cgrp, total, profits in (
                ginfo
                for n in range(2, mxn + 1)
                for ginfo in self._iter_group(n, time)):
            rtt = {}
            for path, tired in self._iter_route(cgrp):
                route = c_route(path, tired, profits, total)
                tt = route.tired
                if tt in rtt:
                    rtt[tt].append(route)
                else:
                    rtt[tt] = [route]
            for rts in rtt.values():
                yield rts, rts[0].benefit

    def sorted_routes(self, mxn = 4, time = None):
        return [rts for rts, _ in sorted(
            self.iter_routes(mxn, time),
            key = lambda i: i[1], reverse = True)]

from predictor import make_predictor

def make_router():
    return c_router(make_predictor())

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    rtr = make_router()