from constraint_integration.integrate import ConstraintIntegrator
from constraint_integration.constraints import AnTop, AnLeft, AnCell, Block, SumCols, RawRange, Sorted, RunningTotal
from constraint_integration.constraints import SumRows, BlockCell, Csp, SheetAssignment, LocalSolver, display
from unittest import TestCase


class TestIntegrator(TestCase):
    def test_find_ranges(self):
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

        integrator = ConstraintIntegrator(None)
        res_csp = integrator.find_p_ranges(csp)
        print('ass')
        print(res_csp.assignment)
        print('cons')
        for c in res_csp.constraints:
            print(c)
            print(c.__dict__)
            print()

    def test_map_annotations(self):
        g1, g2, gt, rt = AnTop('g1'), AnTop('g2'), AnTop('gt'), AnTop('rt')
        a, b, c, t = AnLeft('a'), AnLeft('b'), AnLeft('c'), AnLeft('t')
        cells = {AnCell(a, g1): 1, AnCell(a, g2): 4,
                 AnCell(b, g1): 2, AnCell(b, g2): 2,
                 AnCell(c, g1): 1, AnCell(c, g2): 1}
        block = Block([a, b, c, t], [g1, g2, gt, rt])
        constraints = [
            block,
            SumCols(RawRange([a, b, c]), RawRange([g1, g2]), RawRange([a, b, c]), gt),
            Sorted(RawRange([a, b, c]), gt),
            RunningTotal(gt, rt),
            SumRows(RawRange([a, b, c]), RawRange([gt]), t, RawRange([gt]))]
        constraints = constraints + [BlockCell(cell, value) for cell, value in cells.items()]

        csp = Csp(SheetAssignment([g1, g2, gt, rt, a, b, c, t]), constraints)

        integrator = ConstraintIntegrator(None)
        cspp = integrator.find_p_ranges(csp)

        mg2 = AnTop('gg2')
        mblock = Block([a], [g1, mg2])
        matches = {g2: mg2, block: mblock}

        print('============')

        res_csp = integrator.map_annotations(cspp, matches)

        print('ass')
        print(res_csp.assignment)
        print('cons')
        for c in res_csp.constraints:
            print(c)
            print(c.__dict__)
            print()

    def test_union(self):
        g1, g2 = AnTop('g1'), AnTop('g2')
        a, b = AnLeft('a'), AnLeft('b')
        cells = {AnCell(a, g1): 1, AnCell(a, g2): 4, AnCell(b, g1): 2, AnCell(b, g2): 2}
        block1 = Block([a, b], [g1, g2])
        constraints = [block1, Sorted(RawRange([a, b]), g1)]
        constraints1 = constraints + [BlockCell(cell, value) for cell, value in cells.items()]
        csp1 = Csp(SheetAssignment([g1, g2, a, b]), constraints1)

        g3, g4 = AnTop('g3'), AnTop('g4')
        c, d = AnLeft('c'), AnLeft('d')
        cells = {AnCell(c, g3): 1, AnCell(c, g4): 4, AnCell(c, g3): 4, AnCell(c, g4): 2}
        block2 = Block([c, d], [g3, g4])
        constraints = [block2, Sorted(RawRange([c, d]), g3)]
        constraints2 = constraints + [BlockCell(cell, value) for cell, value in cells.items()]
        csp2 = Csp(SheetAssignment([g3, g4, c, d]), constraints2)

        integrator = ConstraintIntegrator(None)
        cspp1 = integrator.find_p_ranges(csp1)
        cspp2 = integrator.find_p_ranges(csp2)

        print('Matches ============')

        matches = {g3: g1, g4: g2, block2: block1}
        csppm2 = integrator.map_annotations(cspp2, matches)

        print('Union ===========')

        res_csp = integrator.union(cspp1, csppm2, matches)

        print('ass')
        print(res_csp.assignment)
        print('cons')
        for c in res_csp.constraints:
            print(c)
            print(c.__dict__)
            print()

    def test_integrate(self):
        g1, g2 = AnTop('g1'), AnTop('g2')
        a, b = AnLeft('a'), AnLeft('b')
        cells = {AnCell(a, g1): 1, AnCell(a, g2): 4, AnCell(b, g1): 2, AnCell(b, g2): 2}
        block1 = Block([a, b], [g1, g2])
        constraints = [block1, Sorted(RawRange([a, b]), g1)]
        constraints1 = constraints + [BlockCell(cell, value) for cell, value in cells.items()]
        csp1 = Csp(SheetAssignment([g1, g2, a, b]), constraints1)

        g3, g4 = AnTop('g3'), AnTop('g4')
        c, d = AnLeft('c'), AnLeft('d')
        cells = {AnCell(c, g3): 1, AnCell(c, g4): 4, AnCell(d, g3): 4, AnCell(d, g4): 2}
        block2 = Block([c, d], [g3, g4])
        constraints = [block2, Sorted(RawRange([c, d]), g3)]
        constraints2 = constraints + [BlockCell(cell, value) for cell, value in cells.items()]
        csp2 = Csp(SheetAssignment([g3, g4, c, d]), constraints2)

        matches = {g3: g1, g4: g2, block2: block1}

        integrator = ConstraintIntegrator(LocalSolver())
        solved, solution = integrator.integrate(csp1, csp2, matches)

        print('sol--------')
        print(solved)
        print(solution)

        print(display(solution))
