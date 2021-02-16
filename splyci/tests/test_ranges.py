from unittest import TestCase
from constraint_integration.constraints import Block, Cell, AnCell, AnLeft, AnTop, SheetAssignment, Sorted
from constraint_integration.constraints import SumRows, SumCols, RunningTotal
from constraint_integration.constraints import Csp, BlockCell, RawRange

from constraint_integration.ranges import PatternRange


class TestRanges(TestCase):
    def test_fit_small(self):
        g1, g2, gt, rt = AnTop('g1'), AnTop('g2'), AnTop('gt'), AnTop('rt')
        a, b, c, t = AnLeft('a'), AnLeft('b'), AnLeft('c'), AnLeft('t')
        assignment = {
            g1: 0, g2: 1, gt: 2, rt: 3, a: 2, b: 1, c: 0,
            t: 3, Cell(c, g2): 1, Cell(a, gt): 5, Cell(b, gt): 4,
            Cell(c, gt): 2, Cell(b, g2): 2, Cell(t, gt): 11,
            Cell(b, g1): 2, Cell(a, rt): 11, Cell(b, rt): 6,
            Cell(c, rt): 2, Cell(t, rt): 22, Cell(a, g2): 4,
            Cell(c, g1): 1, Cell(a, g1): 1}

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

        pr = PatternRange(constraints)
        pr.fit(assignment, [a, b, c])

        actual = pr.annotations(assignment)
        self.assertEqual(actual, [a, b, c])

        print('model', pr.model.coef_)
