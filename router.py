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

    def __init__(self, city_list, tired_tab):
        assert(len(city_list) > 1)
        self.city = city_list
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

    def iter_route(self):
        clst = self.city
        for iseq in self._iter_idx(len(clst)):
            path = tuple(clst[i] for i in iseq)
            yield c_route(path, tuple(self._iter_tired(path)))

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    foo = c_router(['七号自由港', '修格里城', '曼德矿场', '淘金乐园'], TIRED_TAB)
    #for i in foo.iter_route():
    #    print(i.path, i.tlst, i.tired)
