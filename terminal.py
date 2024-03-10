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
        #print('stck', stack)
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
    TIME_STEP = 20

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
        print('x: 退出')
        return self.ivk('input', self.push('main_post'))

    def stat_main_post(self, ipt = None, **ctx):
        cmd = ipt[0]
        if cmd == '1':
            return self.goto('market')
        elif cmd == 'c':
            return self.goto('config')
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

    def stat_market(self, **ctx):
        cur = nowtime()
        print(f'预测时间: {ctime(cur)}')
        rtr = self.router
        cfg = self.config
        time_min = cfg.get(['market', 'time min'], 0)
        time_max = cfg.get(['market', 'time max'], 60)
        print(f'预测范围: {time_min} 分 ~ {time_max} 分')
        max_cities = cfg.get(['market', 'max cities'], 3)
        max_ranks = cfg.get(['market', 'max ranks'], 5)
        tseq = [cur + t * 60 for t in self._rng_seq_stp(
            time_min, time_max, self.TIME_STEP)]
        mktt = rtr.calc_prd_market(tseq)
        print(f'大盘总利润: {mktt:.2f}')
        rank = rtr.sorted_prd_routes(
            max_cities, tseq)[:max_ranks]
        for i, (rts, ben) in enumerate(rank):
            rt = rts[0]
            print(f'{i+1}: 平均利润:{ben:.2f} 线路:{rt.plen}站 {rt.repr_path()}')
        print('d: 详细走势')
        print('c: 配置统计信息')
        print('x: 退出')
        return self.ivk('input', self.push('market_post', rank = rank))

    def stat_market_post(self, ipt, rank, **ctx):
        cmd = ipt[0]
        if cmd == 'd':
            return self.goto('market_detail', rank = rank)
        elif cmd == 'c':
            return self.goto('config', page = 'market')
        elif cmd == 'x':
            return self.pop(2)
        else:
            return self.ivk('input', self.push('market_post', rank = rank))

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    tm = c_terminal()
    tm.run()
