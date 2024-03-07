#! python3
# coding: utf-8

class c_cashier:

    def __init__(self, predictor):
        self.prd = predictor

from predictor import make_predictor

def make_cashier():
    return c_cashier(make_predictor())

if __name__ == '__main__':
    from pdb import pm
    from pprint import pprint as ppr

    csh = make_cashier()
