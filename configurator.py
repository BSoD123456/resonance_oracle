#! python3
# coding: utf-8

import json

class c_configurator:

    def __init__(self, fname = 'config.json', codec = 'utf-8'):
        self.fname = fname
        self.codec = codec
        self.dat = {}
        self._load()

    def _load(self):
        try:
            with open(self.fname, 'r', encoding=self.codec) as fd:
                dat = json.load(fd)
        except:
            self._save()
        else:
            self.dat.update(dat)

    def _save(self):
        with open(self.fname, 'w', encoding=self.codec) as fd:
            json.dump(self.dat, fd, ensure_ascii=False, indent=4, sort_keys=False)

    def set(self, path, val, skip_save = False):
        keys = path.split('/')
        cur = self.dat
        for k in keys[:-1]:
            if not k in cur:
                if val is None:
                    return False
                cur[k] = {}
            cur = cur[k]
        k = keys[-1]
        if cur.get(k, None) == val:
            return False
        cur[k] = val
        if not skip_save:
            self._save()
        return True

    def get(self, path, default = None):
        keys = path.split('/')
        cur = self.dat
        for k in keys:
            if not k in cur:
                if not default is None:
                    self.set(path, default)
                return default
            cur = cur[k]
        return cur

    def batch(self, info):
        dirty = False
        for k, v in info.items():
            if self.set(k, v, True):
                dirty = True
        if dirty:
            self._save()

GLB_CFG = c_configurator()
