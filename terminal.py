#! python3
# coding: utf-8

from time import ctime, time as nowtime

class c_state_machine:

    def __init__(self):
        pass

    def _emit(self, key, stat, *args, **kargs):
        mn = '_'.join([key, stat])
        mtd = getattr(self, mn, None)
        if not callable(mtd):
            return
        return mtd(*args, **kargs)

    def goto(self, stat, **ctx):
        return (stat,), ctx

    def push(self, stat, **ctx):
        return ('+', stat), ctx

    def pop(self, dp = 1, **ctx):
        return ('-',) * dp, ctx

    def ivk(self, stat, scmd):
        return scmd[0] + ('+', stat), scmd[1]

    def _resolve(self, stat, stack, ctx):
        cmd, ctx = self._emit('stat', stat, **ctx)
        for c in cmd:
            if c == '+':
                stack.append(stat)
            elif c == '-':
                stat = stack.pop()
            else:
                stat = c
        print('stck', stack)
        return stat, stack, ctx

    def run(self):
        stat = 'init'
        stack = []
        ctx = {}
        while not stat is None:
            stat, stack, ctx = self._resolve(stat, stack, ctx)

class c_base_terminal(c_state_machine):

    def _parse_input(self):
        ipt = input('>> ').strip().split()
        if not ipt:
            return ['']
        return ipt

    def stat_input(self, **ctx):
        return self.pop(ipt = self._parse_input(), **ctx)

from router import make_router

class c_terminal(c_base_terminal):

    TIME_COLS = 4
    TIME_STEP = 15

    def stat_init(self, **ctx):
        self.router = make_router()
        self.config = self.router.get_config()
        while True:
            print('正在从商会获取数据 ... ', end = '')
            if self.router.update():
                break
            print('failed')
            print('开始重试')
        print('done')
        return self.goto('main')

    def stat_main(self, **ctx):
        print('欢迎使用[索思学会]戏言神谕机，且听戏言:')
        print('1: 行情预测')
        print('c: 配置车组信息')
        print('x: 返回')
        return self.ivk('input', self.push('main_post'))

    def stat_main_post(self, ipt = None, **ctx):
        cmd = ipt[0]
        if cmd == '1':
            return self.goto('market')
        elif cmd == 'c':
            return self.goto('config_game')
        elif cmd == 'x':
            return self.goto(None)
        else:
            return self.ivk('input', self.goto('main_post'))

    @staticmethod
    def _rng_seq(mn, mx, n):
        if n < 1:
            return []
        elif n == 1 or mn == mx:
            return [int(mn)]
        elif mx < mn:
            _t = mx
            mx = mn
            mn = _t
        stp = (mx - mn) / (n - 1)
        return [*(round(mn + i * stp) for i in range(n-1)), round(mx)]

    @staticmethod
    def _rng_seq_stp(mn, mx, stp):
        return [*range(int(round(mn)), int(round(mx + stp / 2)), stp)]

    def stat_market(self, market = None, **ctx):
        rtr = self.router
        cfg = self.config
        time_min = cfg.get(['market', 'time min'], 0)
        time_max = cfg.get(['market', 'time max'], 60)
        if market is None:
            cur = nowtime()
            max_cities = cfg.get(['market', 'max cities'], 3)
            max_ranks = cfg.get(['market', 'max ranks'], 5)
            tseq = [cur + t * 60 for t in self._rng_seq_stp(
                time_min, time_max, self.TIME_STEP)]
            mktt = rtr.calc_prd_market(tseq)
            rank = rtr.sorted_prd_routes(
                max_cities, tseq)[:max_ranks]
            market = {
                'time': cur,
                'total': mktt,
                'rank': rank,
            }
        else:
            cur = market['time']
            mktt = market['total']
            rank = market['rank']
        print(f'预测时间: {ctime(cur)}')
        print(f'预测范围: {time_min} 分 ~ {time_max} 分')
        print(f'大盘总利润: {mktt:.2f}')
        for i, (rts, ben) in enumerate(rank):
            rt = rts[0]
            print(f'{i+1}: 利润/疲劳: {ben:.2f} 线路:{rt.plen}站 {rt.repr_path()}')
        print('d: 详细走势')
        print('c: 配置统计信息')
        print('x: 返回')
        return self.ivk('input', self.push('market_post', market = market))

    def stat_market_post(self, ipt, market, **ctx):
        cmd = ipt[0]
        rank = market['rank']
        if cmd.isdigit() and 1 <= int(cmd) <= len(rank):
            rt = rank[int(cmd) - 1][0][0]
            return self.goto('route', route = rt, market = market)
        elif cmd == 'd':
            return self.goto('market_detail', market = market)
        elif cmd == 'c':
            return self.goto('config', page = 'market')
        elif cmd == 'x':
            return self.pop(2)
        else:
            return self.ivk('input', self.goto('market_post', market = market))

    def stat_market_detail(self, market, **ctx):
        cur = market['time']
        rank = market['rank']
        rtr = self.router
        cfg = self.config
        time_min = cfg.get(['market', 'time min'], 0)
        time_max = cfg.get(['market', 'time max'], 60)
        print(f'预测时间: {ctime(cur)}')
        print(f'预测范围: {time_min} 分 ~ {time_max} 分')
        tab = []
        for rts, ben in rank:
            tab.append((rts[0], []))
        tseq = self._rng_seq(time_min, time_max, self.TIME_COLS)
        for time in (cur + t * 60 for t in tseq):
            for rt, dat in tab:
                nrt = rtr.recalc_profits(rt, time)
                dat.append([nrt, nrt.benefit, 0, 0])
        rows = len(tab)
        cols = len(tseq)
        for c in range(cols):
            bens = [tab[r][1][c][1] for r in range(rows)]
            max_ben = max(bens)
            for r in range(rows):
                itm = tab[r][1][c]
                itm[2] = itm[1] - max_ben
                if c > 0:
                    itm[3] = itm[1] - tab[r][1][c - 1][1]
        print(f'  {str(tseq[0])+"m": ^10},' + ','.join(f'  {str(t)+"m": ^17}' for t in tseq[1:]))
        for i, (_, row) in enumerate(tab):
            rs = []
            for rt, ben, dc, dr in row:
                if dc:
                    r = f'{dc:+10.2f}'
                else:
                    r = f'{ben: 10.2f}'
                if dr:
                    r += f'({dr:+7.2f})'
                rs.append(r)
            print(f'{i+1}:' + ','.join(rs))
        print('x: 返回')
        return self.ivk('input', self.push('market_detail_post', market = market))

    def stat_market_detail_post(self, ipt, market, **ctx):
        cmd = ipt[0]
        rank = market['rank']
        if cmd.isdigit() and 1 <= int(cmd) <= len(rank):
            rt = rank[int(cmd) - 1][0][0]
            return self.goto('route', route = rt, market = market)
        elif cmd == 'x':
            return self.pop(2, market = market)
        else:
            return self.ivk('input',
                self.goto('market_detail_post', market = market))

    def stat_route(self, route, market, **config):
        print('站数:', route.plen)
        print('路线:', route.repr_path())
        print(f'疲劳: {route.tired} = ' + ' + '.join(
            [str(i) for i in route.tlst]))
        print(f'利润: {route.total:.2f}')
        print(f'利润/疲劳: {route.total / route.tired:.2f}')
        pr = {}
        for (nm, src), (dst, p, n) in route.profits.items():
            if n == 0:
                continue
            if not src in pr:
                pr[src] = ([], [])
            if not dst in pr:
                pr[dst] = ([], [])
            pr[src][0].append(nm)
            pr[dst][1].append((nm, p))
        for c in route.path:
            rs = []
            for nm in pr[c][0]:
                rs.append(f'{nm}(入)')
            for nm, p in pr[c][1]:
                rs.append(f'{nm}(出{p:+.2f})')
            print(f'{c}:', ', '.join(rs))
        print('x: 返回')
        return self.ivk('input',
            self.push('route_post', route = route, market = market))

    def stat_route_post(self, ipt, route, market, **ctx):
        cmd = ipt[0]
        if cmd == 'x':
            return self.pop(2, market = market)
        else:
            return self.ivk('input',
                self.goto('route_post', route = route, market = market))

    def stat_config_game(self, **ctx):
        print('1: 车组技能')
        print('2: 城市声望')
        print('x: 返回')
        return self.ivk('input', self.push('config_game_post'))

    def stat_config_game_post(self, ipt, **ctx):
        cmd = ipt[0]
        if cmd == '1':
            return self.goto('config', page = 'skill')
        elif cmd == '2':
            return self.goto('config_repu')
        elif cmd == 'x':
            return self.pop(2)
        else:
            return self.ivk('input', self.goto('config_game_post'))

    def stat_config_repu(self, **ctx):
        city_list = list(self.router.get_city_list().keys())
        cfg = self.config
        for i, city in enumerate(city_list):
            lv = cfg.get(['reputation', city])
            if lv is None:
                lv = 0
            print(f'{i+1}: 声望:{lv: 2} {city}')
        print('x: 返回')
        return self.ivk('input',
            self.push('config_repu_post', clst = city_list))

    def stat_config_repu_post(self, ipt, clst, **ctx):
        cmd = ipt[0]
        if cmd.isdigit() and 1 <= int(cmd) <= len(clst):
            return self.goto('config',
                page = 'city', city = clst[int(cmd) - 1])
        elif cmd == 'x':
            return self.pop(2)
        else:
            return self.ivk('input',
                self.goto('config_repu_post', clst = clst))

    PAGES = {
        'city': (
            lambda cfg, ctx: {
                'repu': cfg.get(['reputation', ctx['city']], 0),
                'nscl': cfg.get(['num scale', ctx['city']], 0),
            },
            lambda cfg, ctx: f'{ctx["city"]}',
            [(
                lambda cfg, ctx: f'声望 {ctx["repu"]}',
                lambda cfg, ctx:
                    f'城市: {ctx["city"]}\n'
                    f'声望: {ctx["repu"]}\n'
                    f'进货加成: {ctx["nscl"]}\n'
                    '输入声望等级:',
                lambda cfg, ctx, val: int(val[0]),
                lambda cfg, ctx, val: val >= 0,
                lambda cfg, ctx, val: [
                    (['reputation', ctx['city']], val),
                    (['num scale', ctx['city']], val * 10),
                ],
            )],
        ),
        'market': [(
            '时间起点(分)',
            ['market', 'time min'],
            lambda s: int(s),
            0, None,
        )],
    }
    def stat_config(self, page, pctx = None, **ctx):
        cfg = self.config
        if pctx is None:
            nctx, intro, cfglist = self.PAGES[page]
            if callable(nctx):
                nctx = nctx(cfg, ctx)
            actx = ctx.copy()
            if nctx:
                actx.update(nctx)
            vf = lambda v: v(cfg, actx) if callable(v) else v
            intro = vf(intro)
            sels = []
            for citm in cfglist:
                sels.append((*(vf(v) for v in citm[:2]), *citm[2:]))
            pctx = {
                'ctx': actx,
                'intro': intro,
                'sels': sels,
                'octx': ctx,
            }
        print(pctx['intro'])
        for i, (title, *_) in enumerate(pctx['sels']):
            print(f'{i+1}: {title}')
        print('x: 返回')
        return self.ivk('input',
            self.push('config_post', page = page, pctx = pctx))

    def stat_config_post(self, ipt, page, pctx, **ctx):
        cmd = ipt[0]
        sels = pctx['sels']
        if cmd.isdigit() and 1 <= int(cmd) <= len(sels):
            return self.goto('config_input',
                desc = sels[int(cmd) - 1], page = page, pctx = pctx)
        elif cmd == 'x':
            return self.pop(2)
        else:
            return self.ivk('input',
                self.goto('config_post', page = page, pctx = pctx))

    def stat_config_input(self, desc, page, pctx, **ctx):
        _, intro, *_ = desc
        print(intro)
        print('x: 返回')
        return self.ivk('input',
            self.push('config_input_post',
                desc = desc, page = page, pctx = pctx))

    def stat_config_input_post(self, ipt, desc, page, pctx, **ctx):
        if ipt[0] == 'x':
            return self.pop(2, page = page, pctx = pctx)
        cfg = self.config
        _, _, prhndl, chk, hndl = desc
        idle = self.ivk('input',
            self.goto('config_input_post',
                desc = desc, page = page, pctx = pctx))
        actx = pctx['ctx']
        try:
            val = prhndl(cfg, actx, ipt)
        except:
            val = None
        if val is None:
            print('无效输入')
            return idle
        try:
            valid = chk(cfg, actx, val)
        except:
            valid = False
        if not valid:
            print('无效输入')
            breakpoint()
            return idle
        for key, kval in hndl(cfg, actx, val):
            if kval is None:
                continue
            cfg.set(key, kval)
        return self.pop(2, page = page, pctx = None, **pctx['octx'])

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    tm = c_terminal()
    tm.run()
