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
        ctx['__ret__'] = {}

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
            print('正在从商会获取数据 ... ')
            if self.router.update():
                break
            print('failed')
            print('开始重试')
        #print('done')
        return self.goto('main')

    def stat_main(self, ctx):
        if self.phsw(ctx):
            print('欢迎使用[索思学会]戏言神谕机，且听戏言:')
            print('1: 行情预测')
            print('c: 配置车组信息')
            print('r: 更新数据')
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
                return self.push('config', page = 'game')
            elif cmd == 'r':
                return self.goto('init')
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
            time_min = self._cfgv('mk/tm/n')
            time_max = self._cfgv('mk/tm/x')
            calced, = self.ctxget(ctx, 'calced')
            if calced:
                cur, mktt, rank = self.ctxget(ctx, 'cur', 'mktt', 'rank')
            else:
                cur = nowtime()
                max_cities = self._cfgv('mk/xct')
                max_ranks = self._cfgv('mk/xrk')
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
            print(f"最小买入利润: {self._cfgv('mk/prth'):+.2f}")
            print(f'大盘总利润: {mktt:.2f}')
            for i, (rts, ben) in enumerate(rank):
                rt = rts[0]
                mh1, mh2 = rt.max_hold_mass
                if mh1 < mh2:
                    mh = mh1
                    mhd = '正'
                else:
                    mh = mh2
                    mhd = '反'
                print(f'{i+1:>2}: 利润/疲劳: {ben:.2f} 载货:{mh:>4.0f}({mhd}) 线路:{rt.plen}站 {rt.repr_path()}')
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
                self.ctxrst(ctx)
                return self.push('config', page = 'market')
            elif cmd == 'x':
                return self.pop()
            else:
                return self.push('input')

    def stat_market_detail(self, ctx, cur, rank):
        if self.phsw(ctx):
            rtr = self.router
            cfg = self.config
            time_min = self._cfgv('mk/tm/n')
            time_max = self._cfgv('mk/tm/x')
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
                print(f'{i+1:>2}:' + ','.join(rs))
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
            print(f'最大载货占用: {route.max_hold_mass[0]:.0f} 正向 / {route.max_hold_mass[1]:.0f} 反向')
            print(f'最大载货利润: {route.max_hold_prof[0]:.2f} 正向 / {route.max_hold_prof[1]:.2f} 反向')
            for c in route.path:
                stt = route.station[c]
                print(f'\n\n=====')
                print(f"{c}: 载货占用: {stt['hold_mass'][0]:.0f} 正向 / {stt['hold_mass'][1]:.0f} 反向 载货利润: {stt['hold_prof'][0]:.2f} 正向 / {stt['hold_prof'][1]:.2f} 反向")
                print(f"--- 入货总利润: {stt['buy_total']:.2f} ---")
                rs = []
                for nm, p, _ in stt['buy']:
                    rs.append(f'{nm}(入{p:+.2f})')
                print(', '.join(rs))
                rs.clear()
                print(f"--- 出货总利润: {stt['sell_total']:.2f} ---")
                for nm, p, _ in stt['sell']:
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

    CFGKEYS = {
        'mk/tm/n': (['market', 'time min'], 0),
        'mk/tm/x': (['market', 'time max'], 60),
        'mk/xct': (['market', 'max cities'], 3),
        'mk/xrk': (['market', 'max ranks'], 5),
        'mk/prth': (['market', 'profit threshold'], 0),
        'sk/tr': (['skill', 'tired'], 1),
        'blk/c': lambda c: (['city block', c], False),
        'repu': lambda c: (['reputation', c], 0),
        'sc/c': lambda c: (['city num scale', c], 0),
        'blk/t': lambda t: (['item block', t], False),
        'sc/t': lambda t: (['item num scale', t], 0),
        'sc/g': (['global num scale'], True),
    }

    def _cfgprs(self, key, args):
        ck = self.CFGKEYS[key]
        if args:
            ck = ck(*args)
        return ck

    def _cfgk(self, key, *args):
        return self._cfgprs(key, args)[0]

    def _cfgv(self, key, *args):
        return self.config.get(*self._cfgprs(key, args))

    CFGPAGES = {
        'market': lambda self, ctx, imp: (lambda pctx:(
            '统计参数',
            [
                (f"路线最大站数: {pctx['xct']} 站", ':pos_int', {
                    'ckey': self._cfgk('mk/xct'),
                    'intro': f"规划路线最多 {pctx['xct']} 站",
                }),
                (f"预测起始时间: {pctx['ntm']} 分", ':pos_int', {
                    'ckey': self._cfgk('mk/tm/n'),
                    'intro': f"预测从第 {pctx['ntm']} 分钟开始",
                }),
                (f"预测终止时间: {pctx['xtm']} 分", ':pos_int', {
                    'ckey': self._cfgk('mk/tm/x'),
                    'intro': f"预测到第 {pctx['xtm']} 分钟结束",
                }),
                (f"最小买入利润: {pctx['prth']:+.2f}", ':pos_float', {
                    'ckey': self._cfgk('mk/prth'),
                    'intro': f"仅当利润大于 {pctx['prth']:+.2f} 时买入",
                }),
                (f"排行最大数量: {pctx['xrk']} 条", ':pos_int', {
                    'ckey': self._cfgk('mk/xrk'),
                    'intro': f"排行榜最多 {pctx['xrk']} 条",
                }),
            ],
        ))({
            'xct': self._cfgv('mk/xct'),
            'ntm': self._cfgv('mk/tm/n'),
            'xtm': self._cfgv('mk/tm/x'),
            'xrk': self._cfgv('mk/xrk'),
            'prth': self._cfgv('mk/prth'),
        }),
        'game': lambda self, ctx, imp: (lambda pctx:(
            '车组相关信息',
            [
                ('车组技能', 'skill'),
                ('城市信息', 'cities'),
                (f"进货加成总开关: {pctx['gsc']}", ':yes_or_no', {
                    'ckey': self._cfgk('sc/g'),
                    'intro': f"当进货加成总开关 关闭 时，将不再计算任何进货加成(包括封锁的货物也将正常进货)。\n"
                    f"当前 已{pctx['gsc']}",
                }),
            ],
        ))({
            'gsc': '开启' if self._cfgv('sc/g') else '关闭',
        }),
        'skill': lambda self, ctx, imp: (lambda pctx:(
            '车组成员总技能加成',
            [
                (f"疲劳轻减: {pctx['tired']}", ':pos_int', {
                    'ckey': self._cfgk('sk/tr'),
                    'intro': f"当前每次行车减轻 {pctx['tired']} 点疲劳\n"
                    '（修改该设置后需重启程序生效）',
                }),
            ],
        ))({
            'tired': self._cfgv('sk/tr'),
        }),
        'cities': lambda self, ctx, imp: (lambda pctx:(
            '城市相关信息',
            [
                (lambda city:(
                    f"{pctx['func'](city)['blck']}{city} {pctx['func'](city)['ascale']:+.0f}%", 'city', {
                        'city': city,
                    },
                ))(city) # multiply uniq city var to argument
                for city in pctx['clst']
            ],
        ))({
            'clst': list(self.router.get_city_list().keys()),
            'func': lambda c: {
                'blck': '(X) ' if self._cfgv('blk/c', c) else '',
                'ascale': (
                    self._cfgv('repu', c) * 10
                    + self._cfgv('sc/c', c)),
            }
        }),
        'city': lambda self, ctx, imp: (lambda pctx:(
            f"城市: {imp['city']}\n"
            f"货物总加成: {pctx['repu'] * 10 + pctx['nscale']:+.0f}% = {pctx['repu'] * 10:+.0f}%(声望){pctx['nscale']:+.0f}%(额外)",
            [
                (f"封锁: {pctx['blck']}", ':yes_or_no', {
                    'ckey': self._cfgk('blk/c', imp['city']),
                    'intro': f"{imp['city']} 当前 {pctx['blck']}",
                }),
                (f"声望等级: {pctx['repu']}", ':pos_int', {
                    'ckey': self._cfgk('repu', imp['city']),
                    'intro': f"{imp['city']} 当前声望 {pctx['repu']} 级",
                }),
                (f"额外进货加成: {pctx['nscale']:+.0f}%", ':int', {
                    'ckey': self._cfgk('sc/c', imp['city']),
                    'intro': f"{imp['city']} 当前额外进货加成 {pctx['nscale']:+.0f}%",
                }),
                ('详细货物进货设置', 'items', {
                    'city': imp['city'],
                    'cscale': pctx['repu'] * 10 + pctx['nscale'],
                }),
            ],
        ))({
            'blck': '已封锁' if self._cfgv('blk/c', imp['city']) else '未封锁',
            'repu': self._cfgv('repu', imp['city']),
            'nscale': self._cfgv('sc/c', imp['city']),
        }),
        'items': lambda self, ctx, imp: (lambda pctx:(
            f"城市货物进货设置: {imp['city']}",
            [
                (lambda tname:(
                    f"{pctx['func'](tname)['blck']}{tname} {pctx['func'](tname)['ascale']:+.0f}%", 'item', {
                        'city': imp['city'],
                        'cscale': imp['cscale'],
                        'item': tname,
                    },
                ))(tname) # multiply uniq city var to argument
                for tname in pctx['tlst']
            ],
        ))({
            'tlst': self.router.get_city_list()[imp['city']],
            'func': lambda t: {
                'blck': '(X) ' if self._cfgv('blk/t', t) else '',
                'ascale': imp['cscale'] + self._cfgv('sc/t', t),
            }
        }),
        'item': lambda self, ctx, imp: (lambda pctx:(
            f"{imp['item']} 来自 {imp['city']}\n"
            f"货物总加成: {imp['cscale'] + pctx['nscale']:+.0f}% = {imp['cscale']:+.0f}%(城市){pctx['nscale']:+.0f}%(额外)",
            [
                (f"封锁: {pctx['blck']}", ':yes_or_no', {
                    'ckey': self._cfgk('blk/t', imp['item']),
                    'intro': f"{imp['item']} 当前 {pctx['blck']}",
                }),
                (f"额外进货加成: {pctx['nscale']:+.0f}%", ':int', {
                    'ckey': self._cfgk('sc/t', imp['item']),
                    'intro': f"{imp['item']} 当前额外进货加成 {pctx['nscale']:+.0f}%",
                }),
            ],
        ))({
            'blck': '已封锁' if self._cfgv('blk/t', imp['item']) else '未封锁',
            'nscale': self._cfgv('sc/t', imp['item']),
        }),
    }
    def stat_config(self, ctx, page, **imp):
        if self.phsw(ctx):
            cfg = self.config
            cpg = self.CFGPAGES[page]
            if callable(cpg):
                cpg = cpg(self, ctx, imp)
            self.ctxset(ctx, cpg = cpg)
            intro, cfg_list = cpg
            print(intro)
            for i, (ttl, *_) in enumerate(cfg_list):
                print(f'{i+1}: {ttl}')
            print('x: 返回')
            self.phnxt(ctx)
            return self.push('input')
        elif self.phsw(ctx):
            ipt, = self.ctxret(ctx, 'ipt')
            cmd = ipt[0]
            cpg, = self.ctxget(ctx, 'cpg')
            _, cfg_list = cpg
            if cmd.isdigit() and 1 <= int(cmd) <= len(cfg_list):
                _, dst, *ks = cfg_list[int(cmd)-1]
                if ks:
                    k = ks[0]
                else:
                    k = {}
                self.ctxrst(ctx)
                if dst.startswith(':'):
                    return self.push('config_input', page = dst[1:], **k)
                else:
                    return self.push('config', page = dst, **k)
            elif cmd == 'x':
                return self.pop()
            else:
                return self.push('input')

    CFGIPTPAGES = {
        'int': (
            '请输入一个整数:',
            lambda val: int(val[0]),
            None,
        ),
        'pos_int': (
            '请输入一个正整数:',
            lambda val: int(val[0]),
            lambda val: val >= 0,
        ),
        'pos_float': (
            '请输入一个正数:',
            lambda val: float(val[0]),
            lambda val: val >= 0,
        ),
        'yes_or_no': (
            '开启请输入 y ，关闭请输入 n :',
            lambda val: {'y': True, 'n': False}.get(val[0].lower()),
            lambda val: not val is None,
        ),
    }
    def stat_config_input(self, ctx, page, ckey, intro = None):
        hint, prv, chk = self.CFGIPTPAGES[page]
        if self.phsw(ctx):
            if intro:
                print(intro)
            print('x: 返回')
            if hint:
                print(hint)
            self.phnxt(ctx)
            return self.push('input')
        elif self.phsw(ctx):
            ipt, = self.ctxret(ctx, 'ipt')
            cmd = ipt[0]
            if cmd == 'x':
                return self.pop()
            else:
                cfg = self.config
                if prv:
                    try:
                        val = prv(ipt)
                    except:
                        val = None
                    if val is None:
                        return self.push('input')
                else:
                    val = ipt
                if chk and not chk(val):
                    return self.push('input')
                cfg.set(ckey, val)
                return self.pop()

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    tm = c_terminal()
    tm.run()
