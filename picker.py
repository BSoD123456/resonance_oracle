#! python3
# coding: utf-8

import os, os.path
import json, re
import time
from urllib import request, parse

DOM_URL = 'https://www.resonance-columba.com'
DAT_URL = '/api/get-prices'

class c_raw_picker:

    def __init__(self, dom_url, dat_url,
            sta_thr = 3600 * 24, dyn_thr = 60 * 20, enc = 'utf-8'):
        self.enc = 'utf-8'
        self.dom_url = dom_url
        self.dat_url = parse.urljoin(dom_url, dat_url)
        self.sta_thr = sta_thr
        self.dyn_thr = dyn_thr
        self._update()

    def _get_dynamic(self, url):
        resp = request.urlopen(url)
        return json.load(resp)['data']

    def _get_static(self, url):
        resp = request.urlopen(url)
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

    def _update(self):
        upd_time = time.time()
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

class c_picker(c_raw_picker):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.gdat = {}
        self.gdat['item'] = self._get_item_list()
        self.gdat['city'] = self._get_city_list(self.gdat['item'])

    def _get_item_list(self):
        tlst = {}
        for itm in self.sta_dat['data']:
            nm = itm['name']
            assert not nm in tlst
            tlst[nm] = itm
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

    def _get_dyn_sale(self, tkey, name, city):
        itm = self.dyn_dat['data'].get(name, {}).get(tkey, {}).get(city, None)
        if itm is None:
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
        info = self._get_dyn_sale('buy', name, city)
        if info is None:
            return None
        sinfo = self._get_sta_buy(name, city)
        if sinfo is None:
            return None
        info.update(sinfo)
        return info

    def get_sell(self, name, city):
        info = self._get_dyn_sale('sell', name, city)
        if info is None:
            return None
        sinfo = self._get_sta_sell(name, city)
        if sinfo is None:
            return None
        info['base'] = sinfo
        return info

def make_picker():
    return c_picker(DOM_URL, DAT_URL)

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr
    
    pck = make_picker()
