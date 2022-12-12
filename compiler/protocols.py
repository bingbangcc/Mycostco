import math
import os
import yaml

from collections import defaultdict
from enum import Enum
from typing import Dict, List, Optional

# 成本的类型
class CostType(Enum):
    # 运行时间
    RT = "RT"
    # 峰值内存消耗
    MEM = "MEM"
    # ？？论文里第三种应该是网络通信
    # 从cost.yml来看这里RT_MEM_PRESSURE是RT和MEM的乘积
    RT_MEM_PRESSURE = "RT_MEM_PRESSURE"

# CostTotals是继承自dict类，即其本质就是一个dict
class CostTotals(dict):
    def __init__(self):
        # super是调用父类dict的__init__函数
        super(CostTotals, self).__init__()
        # 将三种类型的成本都初始化为0，这里用一个dict来记录每种cost
        for ct in CostType:
            self[ct] = 0

    # 返回一个CostTotals对象
    def copy(self):
        ret = CostTotals()
        for ct in CostType:
            ret[ct] = self[ct]
        return self

    def __mul__(self, other):
        ret = self.copy()
        # 这里 *= 会调用下面啊的__imul__方法，并根据other的类型进行不同的乘法操作
        ret *= other
        return ret

    def __imul__(self, other):
        if isinstance(other, CostTotals):
            for ct, c in other.items():
                self[ct] *= c
        elif isinstance(other, (int, float)):
            # 这里self是一个dict，则for ct in self就是遍历dict的key
            for ct in self:
                self[ct] *= other
        else:
            raise ValueError("invalid operand: %s" % other)
        return self

    def __add__(self, other):
        ret = self.copy()
        ret += other
        return ret

    def __iadd__(self, other):
        if isinstance(other, CostTotals):
            for ct, c in other.items():
                self[ct] += c
        elif isinstance(other, (int, float)):
            for ct in self:
                self[ct] += other
        else:
            raise ValueError("invalid operand: %s" % other)
        return self


class Circuit:
    DEPTH = "d"
    INPUT = "INPUT"
    B = "b"
    COST_FILE = ""
    OPS = []

    def __init__(self, bitlen: int):
        self.bitlen = bitlen
        self.costs = {}
        if self.COST_FILE:
            file_path = os.path.join("compiler", "models", self.COST_FILE)
            with open(file_path, "r") as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
                ops = self.OPS + [self.B]
                for op in ops:
                    costs_by_type = {}
                    d = 0
                    if op in data:
                        d = data[op]
                    if isinstance(d, dict):
                        for ct, c in data[op].items():
                            costs_by_type[CostType[ct]] = c
                    else:
                        for ct in CostType:
                            costs_by_type[ct] = d
                    self.costs[op] = costs_by_type

    def __repr__(self):
        return self.__class__.__name__

    # 输出一个电路circuit的cost
    def get_cost(self, gates: Dict[str, int], total: CostTotals):
        # 遍历该circuit的门的种类及数量
        for g, c in gates.items():
            # 遍历三种cost类型
            # 这里costs是两层dict，第一层是门类型，第二层是cost类型
            # 这里记录整个circuit的代价也是用门的cost乘以门的数量，和HyCC是一样的啊？？？目前没看懂
            for ct in self.costs[g]:
                total[ct] += self.costs[g][ct] * c
        #return total # + self.costs[self.B]

    def get_input_cost(self, n: int, total: CostTotals):
        return self.get_cost({self.INPUT: n}, total)

    def get_one_time_cost(self, total: CostTotals):
        return self.get_cost({self.B: 1}, total)


class Boolean(Circuit):
    COST_FILE = "bool.yml"
    AND = "AND"
    XOR = "XOR"
    OPS = [AND, XOR, Circuit.DEPTH, Circuit.INPUT]

    def add(self, n, depth):
        gates = defaultdict(int)
        gates[self.AND] += n
        gates[self.XOR] += n
        gates[self.DEPTH] += depth

        gates[self.XOR] += 2 * n
        gates[self.AND] += 2 * n
        gates[self.DEPTH] += depth
        gates[self.XOR] += n
        return gates

    def gt(self, n, depth):
        gates = defaultdict(int)
        gates[self.AND] += n
        gates[self.XOR] += n
        gates[self.DEPTH] += depth
        gates[self.AND] += 2 * n
        gates[self.XOR] += 2 * n
        gates[self.DEPTH] += depth
        return gates

    def mux(self, n, depth):
        gates = defaultdict(int)
        gates[self.XOR] += n
        gates[self.AND] += n
        gates[self.DEPTH] += depth
        gates[self.XOR] += n
        return gates

    def eq(self, n, depth):
        gates = defaultdict(int)
        gates[self.XOR] += n
        gates[self.AND] += n
        gates[self.DEPTH] += depth * (math.log(self.bitlen, 2) - 1)
        return gates

    def mul(self, n, depth):
        gates = defaultdict(int)
        gates[self.AND] += n * self.bitlen
        gates[self.DEPTH] += depth
        add_gates = self.add(n, depth)
        gates[self.AND] += add_gates[self.AND] * self.bitlen
        gates[self.XOR] += add_gates[self.XOR] * self.bitlen
        gates[self.DEPTH] += depth * (math.log(self.bitlen, 2) - 1)
        return gates

    def sub(self, n, depth):
        gates = defaultdict(int)
        gates[self.AND] += n
        gates[self.XOR] += n
        gates[self.DEPTH] += depth * self.bitlen
        return gates


class Yao(Boolean):
    COST_FILE = "yao.yml"
    def add(self, n, _depth):
        gates = defaultdict(int)
        gates[self.XOR] += 3 * n
        gates[self.AND] += n
        gates[self.XOR] += n
        gates[self.XOR] += n
        #gates[self.DEPTH] = 3
        return gates

    def mul(self, n, depth):
        gates = defaultdict(int)
        gates[self.AND] += n * self.bitlen
        #gates[self.DEPTH] += 1
        add_gates = self.add(n, depth)
        gates[self.AND] += add_gates[self.AND] * self.bitlen
        gates[self.XOR] += add_gates[self.XOR] * self.bitlen
        #gates[self.DEPTH] += math.log(self.bitlen, 1) - 1
        return gates

    def gt(self, n, _depth):
        gates = defaultdict(int)
        gates[self.XOR] = 3
        gates[self.AND] = 1
        #gates[self.DEPTH] = self.bitlen
        return gates


class Arithmetic(Circuit):
    COST_FILE = "arith.yml"
    ADD = "ADD"
    MUL = "MUL"
    OPS = [ADD, MUL, Circuit.DEPTH, Circuit.INPUT]

    def add(self, n, _depth):
        return {self.ADD: n, self.DEPTH: 0}

    def mul(self, n, depth):
        return {self.MUL: n, self.DEPTH: depth}

    def sub(self, n, depth):
        return self.add(n, depth)


def make_conversion_class(name: str, cost_file: str, ops: List[str]):
    return type(name, (Circuit,), {
        "COST_FILE": cost_file,
        "OPS": ops,
    })


A2Y = make_conversion_class(
    name='A2Y',
    cost_file='a2y.yml',
    ops = ['A2Y'],
)

A2B = make_conversion_class(
    name='A2B',
    cost_file='a2b.yml',
    ops = ['A2B'],
)

B2Y = make_conversion_class(
    name='B2Y',
    cost_file='b2y.yml',
    ops = ['B2Y'],
)

B2A = make_conversion_class(
    name='B2A',
    cost_file='b2a.yml',
    ops = ['B2A'],
)

Y2B = make_conversion_class(
    name='Y2B',
    cost_file='y2b.yml',
    ops = ['Y2B'],
)

Y2A = make_conversion_class(
    name='Y2A',
    cost_file='y2a.yml',
    ops = ['Y2A'],
)

