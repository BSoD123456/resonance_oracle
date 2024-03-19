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
        self._calc_station()

    def _calc_station(self):
        plen = self.plen
        path = self.path
        stts = {k: {
            'idx': i,
            'buy': [],
            'sell_raw': [],
            'sell': [],
            'buy_total': 0,
            'sell_total': 0,
            'hold_mass': [0, 0],
            'hold_prof': [0, 0],
        } for i, k in enumerate(path)}
        sell_avg = {k: {} for k in path}
        for (nm, src), (dst, p, n) in sorted(
                self.profits.items(),
                key = lambda v: v[1][1], reverse = True):
            if n == 0:
                continue
            stts[src]['buy'].append((nm, p, n))
            stts[dst]['sell_raw'].append(((nm, src), p, n))
            dst_sell_avg = sell_avg[dst]
            if nm in dst_sell_avg:
                _op, _on = dst_sell_avg[nm]
                _nn = _on + n
                _np = (_op * _on + p * n) / _nn
                dst_sell_avg[nm] = (_np, _nn)
            else:
                dst_sell_avg[nm] = (p, n)
        for dst, sa in sell_avg.items():
            stts[dst]['sell'] = sorted((
                (nm, p, n) for nm, (p, n) in sa.items()),
                key = lambda v: v[0], reverse = True)
        for snm, stt in stts.items():
            buy_total = 0
            buy_mass = 0
            for _, p, n in stt['buy']:
                buy_total += p * n
                buy_mass += n
            sell_total = sum(p * n for _, p, n in stt['sell'])
            stt['buy_total'] = buy_total
            stt['sell_total'] = sell_total
            bsi = stt['idx']
            stt['hold_mass'][0] += buy_mass
            stt['hold_mass'][1] += buy_mass
            stt['hold_prof'][0] += buy_total
            stt['hold_prof'][1] += buy_total
            hold_mass = [buy_mass, buy_mass]
            hold_prof = [buy_total, buy_total]
            for di in range(1, plen):
                for stp, hi in [(1, 0), (-1, 1)]:
                    dstt = stts[path[(bsi + di * stp) % plen]]
                    for (nm, src), p, n in dstt['sell_raw']:
                        if src != snm:
                            continue
                        hold_mass[hi] -= n
                        assert hold_mass[hi] > -1
                        hold_prof[hi] -= p * n
                    dstt['hold_mass'][hi] += hold_mass[hi]
                    dstt['hold_prof'][hi] += hold_prof[hi]
        self.station = stts
        max_hold_mass = [0, 0]
        max_hold_prof = [0, 0]
        for stt in stts.values():
            for hi in [0, 1]:
                if stt['hold_mass'][hi] > max_hold_mass[hi]:
                    max_hold_mass[hi] = stt['hold_mass'][hi]
                if stt['hold_prof'][hi] > max_hold_prof[hi]:
                    max_hold_prof[hi] = stt['hold_prof'][hi]
        self.max_hold_mass = max_hold_mass
        self.max_hold_prof = max_hold_prof

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
        cfg = self.get_config()
        prf_thr = cfg.get(['market', 'profit threshold'], 0)
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
                        if prf > prf_thr:
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
