#! python3
# coding: utf-8

import itertools

TIRED_TAB = {
    'i': {
        n: i
        for i, n in enumerate([
            '阿妮塔能源研究所',
            '阿妮塔战备工厂',
            '七号自由港',
            '澄明数据中心',
            '修格里城',
            '铁盟哨站',
            '荒原站',
            '曼德矿场',
            '淘金乐园',
        ])
    },
    'v': [
        [23, # not sure
         23, 28, 31, 34, 38, 39, 44],
        [23, 27, 30, 33, 37, 38, 43], # not sure
        [24, 27, 30, 33, 34, 39],
        [24, 23, 26, 27, 33],
        [23, 23, 24, 27],
        [23, 23, 23],
        [23, 24],
        [24],
    ]
}

class c_route:

    def __init__(self, path, tired):
        self.path = path
        self.tlst = tired
        self.tired = sum(tired)

class c_router:

    def __init__(self, predictor, tired_tab):
        self.prd = predictor
        self.tired = tired_tab

    def _pick_tired(self, tab, i1, i2):
        if i1 == i2:
            return 0
        elif i1 > i2:
            _v = i2
            i2 = i1
            i1 = _v
        return tab[i1][i2 - i1 - 1]

    def _iter_tired(self, path):
        itab = self.tired['i']
        vtab = self.tired['v']
        ipath = [itab[n] for n in path]
        lp = len(ipath)
        for i in range(lp -1):
            yield self._pick_tired(vtab, ipath[i], ipath[i + 1])
        yield self._pick_tired(vtab, ipath[lp - 1], ipath[0])

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
            yield c_route(path, tuple(self._iter_tired(path)))

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
                        #assert self.prd.pck.get_buy(nm, dst) # static price missed sometimes
                        continue
                    prf = sell_info['price'] - buy_info['price']
                    if not nm in profits or prf > profits[nm][1]:
                        if prf > 0:
                            num = buy_info['number']
                        else:
                            num = 0
                        profits[nm] = (nm, prf, num)
        total = sum(p * n for _, p, n in profits.values())
        return profits, total

    def _iter_group(self, n, time):
        city_list = self.prd.pck.get_city_list()
        for cgrp in itertools.combinations(city_list.keys(), n):
            profits, total = self._calc_profit(city_list, cgrp, time)
            yield cgrp, total, profits

    def _sorted_group(self, mxn, time):
        return sorted((
                ginfo
                for n in range(2, mxn + 1)
                for ginfo in self._iter_group(n, time)
            ),
            key = lambda ginfo: ginfo[1], reverse = True)

from predictor import make_predictor

def make_router():
    return c_router(make_predictor(), TIRED_TAB)

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    rtr = make_router()
