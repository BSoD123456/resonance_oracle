#! python3
# coding: utf-8

import os, os.path
import json, re
from time import time as nowtime
from urllib import request, parse, error as uerr
from socket import error as serr

DOM_URL = 'https://www.resonance-columba.com'
#DAT_URL = '/api/get-prices'
DAT_URL = '/api/get-prices-v2'
RT_URL = '/route'

class c_raw_picker:

    def __init__(self, dom_url, dat_url, rt_url,
            sta_thr = 3600 * 24, dyn_thr = 60 * 10,
            enc = 'utf-8', timeout = 10):
        self.enc = 'utf-8'
        self.timeout = timeout
        self.dom_url = dom_url
        self.dat_url = parse.urljoin(dom_url, dat_url)
        self.rt_url = parse.urljoin(dom_url, rt_url)
        self.sta_thr = sta_thr
        self.dyn_thr = dyn_thr

    def _get_dynamic(self, url):
        resp = request.urlopen(url, timeout = self.timeout)
        return json.load(resp)['data']

    @staticmethod
    def _js2json(s):
        dat = re.sub(r'([{,]\s*)([^\s{}:,\"]+?)\s*:', r'\1"\2":', s)
        dat = re.sub(r'([^\w])(\.\d+[^\w])', r'\g<1>0\2', dat)
        dat = json.loads(dat)
        return dat

    def _get_static(self, url):
        resp = request.urlopen(url, timeout = self.timeout)
        raw = resp.read().decode(self.enc)
        #m = re.search(r'<script src\s*=\s*\"([^\"]+?page-\w+\.js)"', raw)
        m = re.search(r'<script src\s*=\s*\"([^\"]+?975-\w+\.js)"', raw)
        url = parse.urljoin(self.dom_url, m.group(1))
        resp = request.urlopen(url)
        raw = resp.read().decode(self.enc)
        m = re.search(r'\w+\s*=\s*(\[[^"]+?name\s*\:\s*\"[^\"]+\"\s*,.*?\])', raw)
        return self._js2json(m.group(1))

    def _get_route(self, url):
        resp = request.urlopen(url, timeout = self.timeout)
        raw = resp.read().decode(self.enc)
        m = re.search(r'<script src\s*=\s*\"([^\"]+?page-\w+\.js)"', raw)
        url = parse.urljoin(self.dom_url, m.group(1))
        resp = request.urlopen(url)
        raw = resp.read().decode(self.enc)
        m = re.search(r'\w+\s*=\s*(\[(\s*\{.*?cities\s*\:\s*\[[^\]]+]\s*,.*?fatigue\s*\:\s*\d+.*?\})+\s*\])', raw)
        return self._js2json(m.group(1))

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
            self.rt_dat = self._cache(
                upd_time,
                self.sta_thr,
                'route.json',
                lambda: self._get_route(self.rt_url))
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

    def __init__(self, *args, glb_cfg, **kargs):
        self.cfg = glb_cfg
        self.udat = {}
        super().__init__(*args, **kargs)

    def update(self):
        if not super().update():
            return False
        self.udat['guess_sell'] = {}
        self.gdat = {}
        self.gdat['tired'] = self._get_tired_tab()
        self.gdat['item'] = self._get_item_list()
        self.gdat['city'] = self._get_city_list(self.gdat['item'])
        return True

    def get_config(self):
        return self.cfg

    def _get_tired_tab(self):
        rtab = {}
        tofs = self.cfg.get(['skill', 'tired'], 1)
        for ti in self.rt_dat['data']:
            for si, di in [(0, 1), (1, 0)]:
                src = ti['cities'][si]
                dst = ti['cities'][di]
                if not src in rtab:
                    rtab[src] = {src: 0}
                assert not dst in rtab[src]
                rtab[src][dst] = ti['fatigue'] + 1 - tofs
        return rtab

    def get_tired(self, c1, c2):
        return self.gdat['tired'].get(c1, {}).get(c2, None)

    def _get_item_list(self):
        guess_sell = self.udat['guess_sell']
        tlst = {}
        for itm in self.sta_dat['data']:
            nm = itm['name']
            #assert not nm in tlst # sometimes it's duplicated
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
                        #sls[c] = nprc
                        guess_sell[(nm, c)] = (nprc, False)
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

    def _calc_num_scale(self, name, city):
        cfg = self.cfg
        if not cfg.get(['global num scale'], True):
            return 1
        if cfg.get(['item block', name], False):
            return 0
        repu = cfg.get(['reputation', city], 0)
        cscl = cfg.get(['city num scale', city], 0)
        tscl = cfg.get(['item num scale', name], 0)
        return 1 + (repu * 10 + cscl + tscl) / 100

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
        num_scale = self._calc_num_scale(name, city)
        if not num_scale is None:
            number *= num_scale
        return {
            'base': price,
            'number': number,
        }

    def _get_sta_sell(self, name, city):
        guess_sell = self.udat['guess_sell']
        tlst = self.gdat['item']
        if not name in tlst:
            return None
        itm = tlst[name]
        sprcs = itm.get('sellPrices', {})
        if not city in sprcs:
            return None
        sprc = sprcs[city]
        if sprc is None:
            gs = guess_sell.get((name, city))
            if gs is None:
                return None
            sprc, gsure = gs
            r = {
                'base': sprc,
            }
            if not gsure:
                r['guess_sell'] = True
            return r
        else:
            return {
                'base': sprc,
            }

    def _get_dyn_sale(self, tkey, name, city, force = False):
        itm = self.dyn_dat['data'].get(name, {}).get(tkey, {}).get(city, None)
        if itm is None:
            if force:
                # just guess 100% for missing sale info
                return {
                    'time': nowtime(),
                    'up': False,
                    'sale': 100,
                    'guess_sale': True,
                }
            else:
                return None
        up = (itm.get('trend') == 'up')
        time = itm.get('time', {})
        # time reformat only for old version
        #time = time.get('_seconds', -1) + time.get('_nanoseconds', 0) / 1e9
        r = {
            'time': time,
            'up': up,
            'sale': itm.get('variation', 100),
        }
        if 'price' in itm:
            r['dyn_price'] = itm['price']
        return r

    def _sync_dyn_price(self, itm, name, city):
        if not 'dyn_price' in itm:
            return
        guess_sell = self.udat['guess_sell']
        dsale = itm['dyn_price'] * 100 / itm['base']
        if itm['sale'] == 0:
            itm['sale'] = dsale
        else:
            if itm.get('guess_sell'):
                dsell = itm['dyn_price'] * 100 / itm['sale']
                guess_sell[(name, city)] = (dsell, True)
                itm['base'] = dsell
            else:
                assert abs(dsale - itm['sale']) < 1

    def get_buy(self, name, city):
        sinfo = self._get_sta_buy(name, city)
        if sinfo is None:
            return None
        info = self._get_dyn_sale('buy', name, city, force = True)
        if info is None:
            return None
        info.update(sinfo)
        self._sync_dyn_price(info, name, city)
        return info

    def get_sell(self, name, city):
        sinfo = self._get_sta_sell(name, city)
        if sinfo is None:
            return None
        info = self._get_dyn_sale('sell', name, city, force = True)
        if info is None:
            return None
        info.update(sinfo)
        self._sync_dyn_price(info, name, city)
        return info

from configurator import make_config

def make_picker():
    return c_picker(DOM_URL, DAT_URL, RT_URL, glb_cfg = make_config())

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr
    
    pck = make_picker()
