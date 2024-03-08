#! python3
# coding: utf-8

import os, os.path
import json, re
from time import time as nowtime
from urllib import request, parse, error as uerr
from socket import error as serr

DOM_URL = 'https://www.resonance-columba.com'
DAT_URL = '/api/get-prices'

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
        [24, 26, 30, 33, 34, 39],
        [23, 23, 26, 27, 32],
        [23, 23, 23, 27],
        [23, 23, 23],
        [23, 24],
        [23],
    ]
}

class c_raw_picker:

    def __init__(self, dom_url, dat_url,
            sta_thr = 3600 * 24, dyn_thr = 60 * 20,
            enc = 'utf-8', timeout = 10):
        self.enc = 'utf-8'
        self.timeout = timeout
        self.dom_url = dom_url
        self.dat_url = parse.urljoin(dom_url, dat_url)
        self.sta_thr = sta_thr
        self.dyn_thr = dyn_thr
        self.update()

    def _get_dynamic(self, url):
        resp = request.urlopen(url, timeout = self.timeout)
        return json.load(resp)['data']

    def _get_static(self, url):
        resp = request.urlopen(url, timeout = self.timeout)
        raw = resp.read().decode(self.enc)
        m = re.search(r'<script src\s*=\s*\"([^\"]+?page-\w+\.js)"', raw)
        url = parse.urljoin(self.dom_url, m.group(1))
        resp = request.urlopen(url)
        raw = resp.read().decode(self.enc)
        m = re.search(r'\w+\s*=\s*(\[[^"]+?name\s*\:\s*\"[^\"]+\"\s*,.*?\])', raw)
        dat = re.sub(r'([{,]\s*)([^\s{}:,\"]+?)\s*:', r'\1"\2":', m.group(1))
        dat = re.sub(r'([^\w])(\.\d+[^\w])', r'\g<1>0\2', dat)
        return json.loads(dat)

    def _cache(self, cur, thr, fn, cb):
        enc = 'utf-8'
        try:
            with open(fn, 'r', encoding = enc) as fd:
                old = json.load(fd)
        except:
            old = None
        if (old and 'time' in old and 'data' in old
                and old['time'] + thr > cur):
            return old
        dat = {'time': cur, 'data': cb()}
        try:
            with open(fn, 'w', encoding = enc) as fd:
                json.dump(
                    dat, fd,
                    ensure_ascii = False, indent = 4,
                    sort_keys = False)
        except:
            pass
        return dat

    def update(self):
        upd_time = nowtime()
        try:
            self.sta_dat = self._cache(
                upd_time,
                self.sta_thr,
                'static.json',
                lambda: self._get_static(self.dom_url))
            self.dyn_dat = self._cache(
                upd_time,
                self.dyn_thr,
                'dynamic.json',
                lambda: self._get_dynamic(self.dat_url))
        except (uerr.URLError, serr) as e:
            return False
        except:
            raise
        return True

class c_picker(c_raw_picker):

    def __init__(self, *args, tired_tab, glb_cfg, **kargs):
        self.gcfg = glb_cfg
        self.udat = {
            'tired': tired_tab,
        }
        super().__init__(*args, **kargs)

    def update(self):
        if not super().update():
            return False
        self.gdat = {}
        self.gdat['tired'] = self._get_tired_tab(self.udat['tired'])
        self.gdat['item'] = self._get_item_list()
        self.gdat['city'] = self._get_city_list(self.gdat['item'])
        return True

    def _pick_tired(self, tab, i1, i2):
        if i1 == i2:
            return 0
        elif i1 > i2:
            _v = i2
            i2 = i1
            i1 = _v
        return tab[i1][i2 - i1 - 1]

    def _get_tired_tab(self, tab):
        itab = tab['i']
        vtab = tab['v']
        rtab = {}
        for i1, c1 in enumerate(itab):
            ln = {}
            for i2, c2 in enumerate(itab):
                ln[c2] = self._pick_tired(vtab, i1, i2)
            rtab[c1] = ln
        return rtab

    def get_tired(self, c1, c2):
        return self.gdat['tired'].get(c1, {}).get(c2, None)

    def _get_item_list(self):
        tlst = {}
        for itm in self.sta_dat['data']:
            nm = itm['name']
            assert not nm in tlst
            ritm = itm.copy()
            sls = ritm['sellPrices']
            for c, prc in sls.items():
                if not prc is None:
                    continue
                elif not ritm.get('buyPrices', {}).get(c, None) is None:
                    continue
                # guess missing base sell price
                for t, s in sorted((
                        (t, s)
                        for s, t in self.gdat['tired'].get(c, {}).items()
                        if t > 0
                    ),
                    key = lambda v: v[0]
                ):
                    nprc = sls.get(s, None)
                    if not nprc is None:
                        sls[c] = nprc
                        break
            tlst[nm] = ritm
        return tlst

    def _get_city_list(self, tlst):
        clst = {}
        for nm, itm in tlst.items():
            assert nm == itm['name']
            cns = set()
            #for cn in itm.get('buyPrices', []):
            #    cns.add(cn)
            for cn in itm.get('buyLot', []):
                cns.add(cn)
            for cn in sorted(cns):
                if cn in clst:
                    ilst = clst[cn]
                else:
                    ilst = []
                    clst[cn] = ilst
                ilst.append(nm)
        return clst

    def get_city_list(self):
        return self.gdat['city']

    def _get_sta_buy(self, name, city):
        tlst = self.gdat['item']
        if not name in tlst:
            return None
        itm = tlst[name]
        if not 'buyLot' in itm:
            return None
        price = itm.get('buyPrices', {}).get(city, None)
        number = itm.get('buyLot', {}).get(city, None)
        if price is None or number is None:
            return None
        num_scale = self.gcfg.get(['num_scale', city, name])
        if not num_scale is None:
            number *= num_scale
        return {
            'base': price,
            'number': number,
        }

    def _get_sta_sell(self, name, city):
        tlst = self.gdat['item']
        if not name in tlst:
            return None
        itm = tlst[name]
        return itm.get('sellPrices', {}).get(city, None)

    def _get_dyn_sale(self, tkey, name, city, force = False):
        itm = self.dyn_dat['data'].get(name, {}).get(tkey, {}).get(city, None)
        if itm is None:
            if force:
                # just guess 100% for missing sale info
                return {
                    'time': nowtime(),
                    'up': False,
                    'sale': 100,
                }
            else:
                return None
        up = (itm.get('trend') == 'up')
        time = itm.get('time', {})
        # time reformat only for old version
        #time = time.get('_seconds', -1) + time.get('_nanoseconds', 0) / 1e9
        return {
            'time': time,
            'up': up,
            'sale': itm.get('variation', 100),
        }

    def get_buy(self, name, city):
        sinfo = self._get_sta_buy(name, city)
        if sinfo is None:
            return None
        info = self._get_dyn_sale('buy', name, city, force = True)
        if info is None:
            return None
        info.update(sinfo)
        return info

    def get_sell(self, name, city):
        sinfo = self._get_sta_sell(name, city)
        if sinfo is None:
            return None
        info = self._get_dyn_sale('sell', name, city, force = True)
        if info is None:
            return None
        info['base'] = sinfo
        return info

from configurator import GLB_CFG

def make_picker():
    return c_picker(DOM_URL, DAT_URL,
        tired_tab = TIRED_TAB, glb_cfg = GLB_CFG)

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr
    
    pck = make_picker()
