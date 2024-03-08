#! python3
# coding: utf-8

import time

DUMB_CFG = {
    'period': 20,
    'threshold': 20, #60,
    'step': 2,
    'range': (80, 120),
}

class c_predictor:

    def __init__(self, picker):
        self.pck = picker

    def _predict_sale(self, cur, stamp, val, up):
        return None

    def get_picker(self):
        return self.pck

    def _get_sale(self, itm, cur):
        if cur is None:
            cur = time.time()
        prd = self._predict_sale(
            cur, itm['time'],
            itm['sale'], itm['up'])
        ritm = itm.copy()
        if not prd is None:
            sale, up = prd
            ritm.update({
                'time': cur,
                'up': up,
                'sale': sale,
            })
        ritm['price'] = ritm['base'] * ritm['sale'] / 100
        return ritm

    def get_buy(self, name, city, time = None):
        itm = self.pck.get_buy(name, city)
        if itm is None:
            return None
        ritm = self._get_sale(itm, time)
        ritm['total'] = ritm['price'] * ritm['number']
        return ritm

    def get_sell(self, name, city, time = None):
        itm = self.pck.get_sell(name, city)
        if itm is None:
            return None
        return self._get_sale(itm, time)

class c_dumb_predictor(c_predictor):

    def __init__(self, *args, cfg = {}, **kargs):
        super().__init__(*args, **kargs)
        self.cfg = cfg

    def _predict_sale(self, cur, stamp, val, up):
        dtime = (cur - stamp) / 60
        if 0 <= dtime < self.cfg['threshold']:
            return None
        stp = self.cfg['step']
        delt = int(dtime // self.cfg['period'])
        rng = self.cfg['range']
        if delt < 0:
            delt = - delt
            up = not up
        if not up:
            stp = - stp
        cval = val
        for i in range(delt):
            cval += stp
            if not rng[0] <= cval <= rng[1]:
                cval -= 2 * stp
                stp = - stp
        return cval, stp >= 0

from picker import make_picker

def make_predictor():
    return c_dumb_predictor(make_picker(), cfg = DUMB_CFG)

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr
    
    prd = make_predictor()
