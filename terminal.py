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

    def goto(self, stat):
        if self.stat == stat:
            return
        self.rseq.append((self.stat, stat))
        self.stat = stat

    def push(self, stat):
        self.stck.append(self.stat)
        self.goto(stat)

    def pop(self):
        self.goto(self.stck.pop())

    def _resolve_one(self):
        if not self.rseq:
            return False
        sw = self.rseq.pop(0)
        self.ictx['sta_sw'] = sw
        lv, en = sw
        self._invoke('leave', lv)
        self._invoke('enter', en)
        return True

    def _parse_input(self):
        return input('>>')

    def run(self):
        self.goto('init')
        while self._resolve_one():
            self.ictx['input'] = self._parse_input()
        self.goto('idle')
        self._resolve_one()

class c_terminal(c_base_terminal):

    pass

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    foo = c_terminal()
