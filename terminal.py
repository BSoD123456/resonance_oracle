#! python3
# coding: utf-8

class c_base_terminal:

    def __init__(self):
        self.stat = 'idle'
        self.stck = []
        self.rseq = []
        self.ictx = {}
        self.ctx = {}

    def _invoke(self, key, stat, *args, **kargs):
        mn = '_'.join([key, stat])
        mtd = getattr(self, mn, None)
        if not callable(mtd):
            return
        return mtd(*args, **kargs)

    def goto(self, stat, **ctx):
        if self.stat == stat:
            return
        self.rseq.append((self.stat, stat, ctx))
        self.stat = stat

    def push(self, stat, **ctx):
        self.stck.append(self.stat)
        self.goto(stat, **ctx)

    def pop(self, **ctx):
        self.goto(self.stck.pop(), **ctx)

    def _resolve_one(self):
        if not self.rseq:
            return False
        leave, enter, ctx = self.rseq.pop(0)
        self._invoke('stat', enter, sta_from = leave, **ctx)
        return True

    def _parse_input(self):
        return input('>> ')

    def stat_input(self, **ctx):
        self.pop(ipt = self._parse_input())

    def run(self):
        self.goto('init')
        while self._resolve_one():
            pass
        self.goto('idle')
        self._resolve_one()

class c_terminal(c_base_terminal):

    def stat_init(self, **ctx):
        print('init')
        self.goto('main')

    def stat_main(self, ipt = None, **ctx):
        print('main', ipt)
        self.push('input')

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    foo = c_terminal()
