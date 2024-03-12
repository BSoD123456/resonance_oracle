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

    def goto(self, stat, **imp):
        return (stat,), imp

    def push(self, stat, **imp):
        return ('+', stat), imp

    def pop(self, dp = 1, **imp):
        return ('-',) * dp, imp

    def _ctxinit(self, ctx):
        ctx.setdefault('__ret__', {})
        ctx['__phase_lab__'] = 0
        ctx.setdefault('__phase__', 0)

    def phsw(self, ctx):
        r = (ctx['__phase_lab__'] == ctx['__phase__'])
        ctx['__phase_lab__'] += 1
        return r

    def phnxt(self, ctx):
        ctx['__phase__'] += 1

    def phrst(self, ctx):
        ctx['__phase__'] = 0

    def ctxrst(self, ctx):
        ctx.clear()

    def ctxset(self, ctx, **dst):
        ctx.update(dst)

    def ctxget(self, ctx, *keys):
        return (ctx.get(k) for k in keys)

    def ctxret(self, ctx, *keys):
        ret = ctx['__ret__']
        return (ret.get(k) for k in keys)

    def ctxflt(self, ctx, *keys):
        return {k:ctx[k] for k in keys}

    def ctxmrg(self, ctx, *keys):
        r = ctx['__ret__']
        v = []
        for k in keys:
            if k in r:
                v = r[k]
                ctx[k] = v
            else:
                v = ctx.get(k)
            rs.append(v)
        return rs

    def _resolve(self, stack):
        stat, ctx, imp = stack[-1]
        self._ctxinit(ctx)
        cmd, imp = self._emit('stat', stat, ctx, **imp)
        ctx['__ret__'].clear()
        poped = False
        for c in cmd:
            if c == '+':
                stack.append(None)
            elif c == '-':
                stack.pop()
                poped = True
            else:
                stack[-1] = (c, {}, imp)
        if stack and poped:
            stack[-1][1]['__ret__'].update(imp)
        #print('stck', [i[0] for i in stack])
        return imp

    def run(self):
        stack = [('init', {}, {})]
        while stack:
            self._resolve(stack)

class c_base_terminal(c_state_machine):

    def _parse_input(self):
        ipt = input('>> ').strip().split()
        if not ipt:
            return ['']
        return ipt

    def stat_input(self, ctx):
        return self.pop(ipt = self._parse_input())

from router import make_router

class c_terminal(c_base_terminal):

    TIME_COLS = 4
    TIME_STEP = 15

    def stat_init(self, ctx):
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

    def stat_main(self, ctx):
        if self.phsw(ctx):
            print('欢迎使用[索思学会]戏言神谕机，且听戏言:')
            print('1: 行情预测')
            print('c: 配置车组信息')
            print('x: 返回')
            self.phnxt(ctx)
            return self.push('input')
        elif self.phsw(ctx):
            ipt, = self.ctxret(ctx, 'ipt')
            cmd = ipt[0]
            if cmd == '1':
                self.phrst(ctx)
                return self.push('market')
            elif cmd == 'c':
                self.phrst(ctx)
                return self.push('config_game')
            elif cmd == 'x':
                return self.pop()
            else:
                return self.push('input')

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

    def stat_market(self, ctx):
        if self.phsw(ctx):
            rtr = self.router
            cfg = self.config
            time_min = cfg.get(['market', 'time min'], 0)
            time_max = cfg.get(['market', 'time max'], 60)
            calced, = self.ctxget(ctx, 'calced')
            if calced:
                cur, mktt, rank = self.ctxget(ctx, 'cur', 'mktt', 'rank')
            else:
                cur = nowtime()
                max_cities = cfg.get(['market', 'max cities'], 3)
                max_ranks = cfg.get(['market', 'max ranks'], 5)
                tseq = [cur + t * 60 for t in self._rng_seq_stp(
                    time_min, time_max, self.TIME_STEP)]
                mktt = rtr.calc_prd_market(tseq)
                rank = rtr.sorted_prd_routes(
                    max_cities, tseq)[:max_ranks]
                self.ctxset(ctx,
                    calced = True,
                    cur = cur,
                    mktt = mktt,
                    rank = rank)
            print(f'预测时间: {ctime(cur)}')
            print(f'预测范围: {time_min} 分 ~ {time_max} 分')
            print(f'大盘总利润: {mktt:.2f}')
            for i, (rts, ben) in enumerate(rank):
                rt = rts[0]
                print(f'{i+1}: 利润/疲劳: {ben:.2f} 线路:{rt.plen}站 {rt.repr_path()}')
            print('d: 详细走势')
            print('c: 配置统计信息')
            print('x: 返回')
            self.phnxt(ctx)
            return self.push('input')
        elif self.phsw(ctx):
            ipt, = self.ctxret(ctx, 'ipt')
            rank, = self.ctxget(ctx, 'rank')
            cmd = ipt[0]
            if cmd.isdigit() and 1 <= int(cmd) <= len(rank):
                rt = rank[int(cmd) - 1][0][0]
                self.phrst(ctx)
                return self.push('route', route = rt)
            elif cmd == 'd':
                self.phrst(ctx)
                return self.push('market_detail',
                    **self.ctxflt(ctx, 'cur', 'rank'))
            elif cmd == 'c':
                self.phrst(ctx)
                return self.push('config', page = 'market')
            elif cmd == 'x':
                return self.pop()
            else:
                return self.push('input')

    def stat_market_detail(self, ctx, cur, rank):
        if self.phsw(ctx):
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
            self.phnxt(ctx)
            return self.push('input')
        elif self.phsw(ctx):
            ipt, = self.ctxret(ctx, 'ipt')
            cmd = ipt[0]
            if cmd.isdigit() and 1 <= int(cmd) <= len(rank):
                rt = rank[int(cmd) - 1][0][0]
                self.phrst(ctx)
                return self.push('route', route = rt)
            elif cmd == 'x':
                return self.pop()
            else:
                return self.push('input')

    def stat_route(self, ctx, route):
        if self.phsw(ctx):
            print('站数:', route.plen)
            print('路线:', route.repr_path())
            print(f'疲劳: {route.tired} = ' + ' + '.join(
                [str(i) for i in route.tlst]))
            print(f'利润: {route.total:.2f}')
            print(f'利润/疲劳: {route.total / route.tired:.2f}')
            pr = {}
            for (nm, src), (dst, p, n) in sorted(
                    route.profits.items(),
                    key = lambda v: v[1][1], reverse = True):
                if n == 0:
                    continue
                if not src in pr:
                    pr[src] = ([], [])
                if not dst in pr:
                    pr[dst] = ([], [])
                pr[src][0].append((nm, p))
                pr[dst][1].append((nm, p))
            for c in route.path:
                print(f'=====')
                print(f'{c}:')
                rs = []
                for nm, p in pr[c][0]:
                    rs.append(f'{nm}(入{p:+.2f})')
                print(', '.join(rs))
                rs.clear()
                for nm, p in pr[c][1]:
                    rs.append(f'{nm}(出{p:+.2f})')
                print(', '.join(rs))
            print('x: 返回')
            self.phnxt(ctx)
            return self.push('input')
        elif self.phsw(ctx):
            ipt, = self.ctxret(ctx, 'ipt')
            cmd = ipt[0]
            if cmd == 'x':
                return self.pop()
            else:
                return self.push('input')

    def stat_config_game(self, **ctx):
        print('1: 车组技能')
        print('2: 城市信息')
        print('x: 返回')
        return self.ivk('input', self.push('config_game_post'))

    def stat_config_game_post(self, ipt, **ctx):
        cmd = ipt[0]
        if cmd == '1':
            return self.goto('config', page = 'skill')
        elif cmd == '2':
            #return self.goto('config_city')
            return self.goto('config', page = 'cities')
        elif cmd == 'x':
            return self.pop(2)
        else:
            return self.ivk('input', self.goto('config_game_post'))

    def stat_config_city(self, **ctx):
        city_list = list(self.router.get_city_list().keys())
        cfg = self.config
        for i, city in enumerate(city_list):
            lv = cfg.get(['reputation', city])
            if lv is None:
                lv = 0
            blk = cfg.get(['city block', city])
            blk_rpr = 'X ' if blk else ''
            print(f'{i+1}: 声望:{lv: 2} {blk_rpr}{city}')
        print('x: 返回')
        return self.ivk('input',
            self.push('config_city_post', clst = city_list))

    def stat_config_city_post(self, ipt, clst, **ctx):
        cmd = ipt[0]
        if cmd.isdigit() and 1 <= int(cmd) <= len(clst):
            return self.goto('config',
                page = 'city', city = clst[int(cmd) - 1])
        elif cmd == 'x':
            return self.pop(2)
        else:
            return self.ivk('input',
                self.goto('config_city_post', clst = clst))

    def stat_config_itemblock(self, city, **ctx):
        item_tab = self.router.get_city_list()[city]
        cfg = self.config
        for i, name in enumerate(item_tab):
            pass

    PAGES = {
        'cities': (
            lambda self, cfg, ctx: {
                'city_list': list(self.router.get_city_list().keys()),
                'repu': lambda c: cfg.get(['reputation', c], 0),
                'blck': lambda c: cfg.get(['city block', c], False),
            },
            '城市信息',
            lambda cfg, ctx: [
                (lambda city:(
                    lambda cfg, ctx:
                        f'声望:{ctx["repu"](city): 2} '
                        f'{"X " if ctx["blck"](city) else ""}{city}',
                    lambda cfg, ctx:(
                        'city', {}
                    ),
                ))(city) # multiply uniq city var to argument
                for city in ctx['city_list']
            ],
        ),
        'city': (
            lambda self, cfg, ctx: {
                'repu': cfg.get(['reputation', ctx['city']], 0),
                'blck': cfg.get(['city block', ctx['city']], False),
            },
            lambda cfg, ctx: f'{ctx["city"]}',
            [(
                lambda cfg, ctx: f'声望: {ctx["repu"]}',
                lambda cfg, ctx:
                    f'城市: {ctx["city"]}\n'
                    f'声望: {ctx["repu"]}\n'
                    f'进货加成: +{ctx["repu"] * 10}%\n'
                    '输入声望等级:',
                lambda cfg, ctx, val: int(val[0]),
                lambda cfg, ctx, val: val >= 0,
                lambda cfg, ctx, val: [
                    (['reputation', ctx['city']], val),
                ],
            ), (
                lambda cfg, ctx: f'忽略: {"yes" if ctx["blck"] else "no"}',
                lambda cfg, ctx:
                    f'城市: {ctx["city"]}\n'
                    f'忽略: {"yes" if ctx["blck"] else "no"}\n'
                    '是否忽略该城市(y/n):',
                lambda cfg, ctx, val: val[0].lower(),
                lambda cfg, ctx, val: val in ('y', 'n'),
                lambda cfg, ctx, val: [
                    (['city block', ctx['city']],
                     True if val == 'y' else False if val == 'n' else None),
                ],
            ), (
                '货物锁定',
                lambda cfg, ctx: (
                    'config_itemblock', {
                        'city': ctx['city'],
                }),
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
                nctx = nctx(self, cfg, ctx)
            actx = ctx.copy()
            if nctx:
                actx.update(nctx)
            vf = lambda v: v(cfg, actx) if callable(v) else v
            intro = vf(intro)
            cfglist = vf(cfglist)
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
            desc = sels[int(cmd) - 1][1:]
            if isinstance(desc[0], tuple):
                dpage, dctx = desc[1]
                return self.goto(dstat, page = page, pctx = pctx, **dctx)
            else:
                return self.goto('config_input',
                    desc = desc, page = page, pctx = pctx)
        elif cmd == 'x':
            return self.pop(2)
        else:
            return self.ivk('input',
                self.goto('config_post', page = page, pctx = pctx))

    def stat_config_input(self, desc, page, pctx, **ctx):
        intro, *_ = desc
        print(intro)
        print('x: 返回')
        return self.ivk('input',
            self.push('config_input_post',
                desc = desc, page = page, pctx = pctx))

    def stat_config_input_post(self, ipt, desc, page, pctx, **ctx):
        if ipt[0] == 'x':
            return self.pop(2, page = page, pctx = pctx)
        cfg = self.config
        _, prhndl, chk, hndl = desc
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
