import unittest

# from .protocols import Boolean, CostType
from protocols import Boolean, CostType

from protocols import CostTotals

TEST_BITLEN = 32


class TestBoolean(unittest.TestCase):
    def test_get_cost(self):
        print("here")
        b = Boolean(TEST_BITLEN)
        print("here")
        total = CostTotals()
        # return self.get_cost({self.INPUT: n}, total)
        cost = b.get_cost(b.add(3, 2), total)
        print(cost)
        # print("here")
        self.assertIn(CostType.RT, cost)
        self.assertIn(CostType.MEM, cost)
        self.assertIn(CostType.RT_MEM_PRESSURE, cost)


if __name__ == '__main__':
    test = TestBoolean()
    test.test_get_cost()
#     print("here")
#     b = Boolean(TEST_BITLEN)
#     print("here")
#     cost = b.get_cost(b.add(10, 2))
#     print("here")
#     # assertIn(CostType.RT, cost)
#     # assertIn(CostType.MEM, cost)
#     # assertIn(CostType.RT_MEM_PRESSURE, cost)
