#! python3
# coding: utf-8

class c_base_terminal:

    def __init__(self):
        pass

    def _invoke(self, key, stat, *args, **kargs):
        mn = '_'.join([key, stat])
        mtd = getattr(self, mn, None)
        if not callable(mtd):
            return
        return mtd(*args, **kargs)

    def goto(self, stat, **ctx):
        return (stat,), ctx

    def push(self, stat, nxt = None, **ctx):
        cmd = ('+', stat)
        if not nxt is None:
            cmd = (nxt,) + cmd
        return cmd, ctx

    def pop(self, **ctx):
        return ('-',), ctx

    def _resolve(self, stat, stack, ctx):
        cmd, ctx = self._invoke('stat', stat, **ctx)
        for c in cmd:
            if c == '+':
                stack.append(stat)
            elif c == '-':
                stat = stack.pop()
            else:
                stat = c
        return stat, stack, ctx

    def _parse_input(self):
        return input('>> ').strip().split()

    def stat_input(self, **ctx):
        return self.pop(ipt = self._parse_input())

    def run(self):
        stat = 'init'
        stack = []
        ctx = {}
        while not stat is None:
            stat, stack, ctx = self._resolve(stat, stack, ctx)

class c_terminal(c_base_terminal):

    def stat_init(self, **ctx):
        print('init')
        return self.push('input', 'main')

    def stat_main(self, ipt = None, **ctx):
        print('main', ipt)
        return self.push('input')

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    foo = c_terminal()
