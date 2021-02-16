from unittest import TestCase
from constraint_integration.constraints import Block, Cell, AnCell, AnLeft, AnTop, SheetAssignment, Sorted
from constraint_integration.constraints import SumRows, SumCols, RunningTotal
from constraint_integration.constraints import Csp, BlockCell, RawRange, LocalSolver, display


class TestConstraints(TestCase):
    def test_block(self):
        """
        sc g1 g2 t
        a  2  3  1
        b  2  1  3
        """
        a = AnLeft('a')
        b = AnLeft('b')
        g1 = AnTop('g1')
        g2 = AnTop('g2')
        gt = AnTop('t')
        block = Block([a, b], [g1, g2, gt])
        empty_ass = SheetAssignment([a, b, g1, g2, gt])
        self.assertFalse(block.satisfied(empty_ass))

        ass = SheetAssignment([a, b, g1, g2, gt])
        ass[a] = 1
        ass[b] = 1
        ass[g1] = 1
        ass[g2] = 3
        ass[gt] = 3
        self.assertFalse(block.satisfied(ass))

        sat_ass = block.satisfy(ass)
        self.assertTrue(block.satisfied(sat_ass))

        print('1', sat_ass)

        sat_ass = block.satisfy(empty_ass)
        self.assertTrue(block.satisfied(sat_ass))
        print('2', sat_ass)

    def test_sorted(self):
        """
        sc g1 g2 t
        a  2  3  1
        b  2  1  3
        b ->
        sc g2 g1 t
        a  3  2  1
        b  1  2  3
        """
        a = AnLeft('a')
        b = AnLeft('b')
        g1 = AnTop('g1')
        g2 = AnTop('g2')
        gt = AnTop('t')
        cells = {AnCell(a, g1): 2, AnCell(b, gt): 3, AnCell(a, gt): 1,
                 AnCell(a, g2): 3, AnCell(b, g2): 1, AnCell(b, g1): 2}
        block = Block([a, b], [g1, g2, gt])
        sort_range = RawRange([g1, g2, gt])
        sort = Sorted(sort_range, b)
        empty_ass = SheetAssignment([a, b, g1, g2, gt])
        empty_ass.update(cells)
        # ?
        self.assertTrue(sort.satisfied(empty_ass))

        ass = SheetAssignment([a, b, g1, g2, gt])
        ass[a] = 1
        ass[b] = 1
        ass[g1] = 1
        ass[g2] = 3
        ass[gt] = 3
        # ?
        self.assertTrue(sort.satisfied(ass))

        sat_ass = block.satisfy(ass)
        sat_ass = sort.satisfy(sat_ass)
        self.assertTrue(sort.satisfied(sat_ass))

        sat_ass.update(cells)
        print(sat_ass)
        self.assertFalse(sort.satisfied(sat_ass))
        sat_ass = sort.satisfy(sat_ass)
        print('satass', sat_ass)
        self.assertTrue(sort.satisfied(sat_ass))
        print(sat_ass)

    def test_sum_rows(self):
        """
        sc g1 g2 t
        a  2  3  1
        b  2  1  3
        b ->
        sc g1 g2 t
        a  2  3  1
        b  2  1  3
        t     4  4
        """
        a = AnLeft('a')
        b = AnLeft('b')
        t = AnLeft('t')
        g1 = AnTop('g1')
        g2 = AnTop('g2')
        gt = AnTop('gt')
        cells = {AnCell(a, g1): 2, AnCell(b, gt): 3, AnCell(a, gt): 1,
                 AnCell(a, g2): 3, AnCell(b, g2): 1, AnCell(b, g1): 2}
        empty_ass = SheetAssignment([a, b, t, g1, g2, gt])
        empty_ass.update(cells)

        range_left = RawRange([a, b])
        range_top = RawRange([g2, gt])
        assign_range_top = RawRange([g2, gt])
        sumr = SumRows(range_left, range_top, t, assign_range_top)
        self.assertFalse(sumr.satisfied(empty_ass))

        sat_ass = sumr.satisfy(empty_ass)
        self.assertTrue(sumr.satisfied(sat_ass))

        print(sat_ass)

    def test_sum_cols(self):
        """
        sc g1 g2 t
        a  2  3
        b  2  1
        b ->
        sc g1 g2 t
        a  2  3  5
        b  2  1  3
        """
        a = AnLeft('a')
        b = AnLeft('b')
        g1 = AnTop('g1')
        g2 = AnTop('g2')
        gt = AnTop('gt')
        cells = {AnCell(a, g1): 2, AnCell(a, g2): 3,
                 AnCell(b, g1): 3, AnCell(b, g2): 1}
        empty_ass = SheetAssignment([a, b, g1, g2, gt])
        empty_ass.update(cells)

        range_left = RawRange([a, b])
        range_top = RawRange([g1, g2])
        assign_range_left = RawRange([a, b])
        sumc = SumCols(range_left, range_top, assign_range_left, gt)
        self.assertFalse(sumc.satisfied(empty_ass))

        sat_ass = sumc.satisfy(empty_ass)
        print(sat_ass)
        self.assertTrue(sumc.satisfied(sat_ass))

        print(sat_ass)

    def test_running_total(self):
        """
          g  gt
        a 3  3
        b 2  5
        c 9  14
        """
        a = AnLeft('a')
        b = AnLeft('b')
        c = AnLeft('c')
        g = AnTop('g')
        gt = AnTop('gt')
        ass = SheetAssignment([a, b, c, g, gt])
        cells = {AnCell(a, g): 3, AnCell(b, g): 2, AnCell(c, g): 9}
        ass.update(cells)

        constraint = RunningTotal(g, gt)

        self.assertFalse(constraint.satisfied(ass))
        un_ass = constraint.satisfy(ass)
        print(un_ass)
        # First need index assignments
        self.assertFalse(constraint.satisfied(un_ass))

        indices = {a: 0, b: 1, c: 2}
        ass.update(indices)
        self.assertFalse(constraint.satisfied(ass))
        un_ass = constraint.satisfy(ass)
        print(un_ass)
        self.assertTrue(constraint.satisfied(un_ass))


class TestCsp(TestCase):
    def test_csp_small(self):
        """
             g1 g2 gt  rt
        a    1  4
        b    2  2
        c    1  1
        t
        ->
             g1 g2 gt  rt
        c    1  1  2   2
        b    2  2  4   6
        a    1  4  5  11
        t         11
        """
        g1, g2, gt, rt = AnTop('g1'), AnTop('g2'), AnTop('gt'), AnTop('rt')
        a, b, c, t = AnLeft('a'), AnLeft('b'), AnLeft('c'), AnLeft('t')
        cells = {AnCell(a, g1): 1, AnCell(a, g2): 4,
                 AnCell(b, g1): 2, AnCell(b, g2): 2,
                 AnCell(c, g1): 1, AnCell(c, g2): 1}
        constraints = [
            Block([a, b, c, t], [g1, g2, gt, rt]),
            SumCols(RawRange([a, b, c]), RawRange([g1, g2]), RawRange([a, b, c]), gt),
            Sorted(RawRange([a, b, c]), gt),
            RunningTotal(gt, rt),
            SumRows(RawRange([a, b, c]), RawRange([gt]), t, RawRange([gt]))]
        constraints = constraints + [BlockCell(cell, value) for cell, value in cells.items()]

        csp = Csp(SheetAssignment([g1, g2, gt, rt, a, b, c, t]), constraints)
        solver = LocalSolver(30)
        solved, assignment = solver.solve(csp)
        print(assignment)
        self.assertTrue(solved)
        print(display(assignment))

    def test_csp_smaller(self):
        """
             g1 g2
        a    1  4
        b    2  2
        c    1  1
        d    3  2
        """
        g1, g2 = AnTop('g1'), AnTop('g2')
        a, b, c, d = AnLeft('a'), AnLeft('b'), AnLeft('c'), AnLeft('d')
        cells = {AnCell(a, g1): 1, AnCell(a, g2): 4,
                 AnCell(b, g1): 2, AnCell(b, g2): 2,
                 AnCell(c, g1): 1, AnCell(c, g2): 1,
                 AnCell(d, g1): 1, AnCell(d, g2): 1}
        constraints = [
            Block([a, b, c, d], [g1, g2]),
            Sorted(RawRange([a, b, c, d]), g1)
        ]
        constraints = constraints + [BlockCell(cell, value) for cell, value in cells.items()]

        csp = Csp(SheetAssignment([g1, g2, a, b, c, d]), constraints)
        solver = LocalSolver(30)
        solved, assignment = solver.solve(csp)
        print(assignment)
        self.assertTrue(solved)
        print(display(assignment))
