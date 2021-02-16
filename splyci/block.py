import numpy as np


class Block:
    def __init__(self, cells):
        cells = [cell for cell in cells if cell]
        self.cells = cells
        maxi = 0
        maxni = None
        mini = np.inf
        minni = None
        maxj = 0
        maxnj = None
        minj = np.inf
        minnj = None
        for cell in cells:
            if cell.original_i >= maxi:
                maxi = cell.original_i
                maxni = cell.i
            if cell.original_i <= mini:
                mini = cell.original_i
                minni = cell.i
            if cell.original_j >= maxj:
                maxj = cell.original_j
                maxnj = cell.j
            if cell.original_j <= minj:
                minj = cell.original_j
                minnj = cell.j
        self.x1 = minni
        self.x2 = maxni
        self.y1 = minnj
        self.y2 = maxnj
        self.x1o = mini
        self.y1o = minj
        self.width = maxi - mini + 1
        self.height = maxj - minj + 1
        self.type = 'formula'
        for cell in cells:
            if cell.formula is None:
                self.type = 'data'
            else:
                self.formula_range_template = cell.formula.range_template
                self.formula_template = cell.formula.r1c1
                self.range_names = list(cell.formula.ranges.keys())
        # Was previously if all(...), but think it should be any(...) because a block should have no type if
        #  it is completely empty.
        self.types = set.intersection(*[cell.types for cell in cells if cell.v is not None]) if any(c.v is not None for c in cells) else set()
        print('types', self.types, [cell.types for cell in cells if cell.v is not None], [c.v is not None for c in cells])
        self.block_id = 'b_' + hex(abs(hash(self)))[2:9]

    def __repr__(self):
        return f'Block({self.x1}, {self.y1}, {self.x2}, {self.y2})'

    def __hash__(self):
        return hash((self.x1, self.y1, self.x2, self.y2))


def _match_sets(match_tuples):
    matches = {}
    for i1, i2 in match_tuples:
        i1m = matches.get(i1, set())
        i1m.add(i2)
        matches[i1] = i1m
        i2m = matches.get(i2, set())
        i2m.add(i1)
        matches[i2] = i2m
    return matches


def _index_cut(c, cr, cl, clr):
    lines = []
    if c and cr and cl and clr:
        if (c.i == cl.i and cr.i != clr.i) or (c.i != cl.i and cr.i == clr.i):
            lines.append((c.i, cr.i))
            lines.append((cl.i, clr.i))
        if (c.j == cr.j and cl.j != clr.j) or (c.j != cr.j and cl.j == clr.j):
            lines.append((c.j, cl.j))
            lines.append((cr.j, clr.j))
    return lines


def _cut(c, cr, cl, clr):
    lines = []
    if c and cr:
        if c.j != cr.j:
            lines.append((c.i, cr.i))
    if c and cl:
        if c.i != cl.i:
            lines.append((c.j, cl.j))
    return lines


def _diff_formulas(c, cr, cl, clr):
    if not c:
        return []
    cf = c.formula.r1c1 if c is not None and c.formula is not None else None
    lines = []
    if cr:
        rcf = cr.formula.r1c1 if cr.formula is not None else None
        if cf != rcf:
            lines.append((c.i, cr.i))
    if cl:
        lcf = cl.formula.r1c1 if cl.formula is not None else None
        if cf != lcf:
            lines.append((c.j, cl.j))
    return lines


def _diff_args(c, cr, cl, clr):
    ca = c.arg_from if c else []
    cra = cr.arg_from if cr else []
    cla = cl.arg_from if cl else []
    formula_templates_n = {(f.formula.r1c1, tuple(f.formula.dependency_backmap[(c.i, c.j)])) for f in ca if f.formula}
    formula_templates_rn = {(f.formula.r1c1, tuple(f.formula.dependency_backmap[(cr.i, cr.j)])) for f in cra if f.formula}
    formula_templates_ln = {(f.formula.r1c1, tuple(f.formula.dependency_backmap[(cl.i, cl.j)])) for f in cla if f.formula}
    lines = []
    if c and cr and formula_templates_n != formula_templates_rn:
        lines.append((c.i, cr.i))
    if c and cl and formula_templates_n != formula_templates_ln:
        lines.append((c.j, cl.j))
    return lines


def _matches(matches, index_locations, c, cr, cl, clr):
    if not c or not cr or not cl:
        return []
    mnis = matches.get(c.i, set())
    mnirs = matches.get(cr.i, set())
    mis = {index_locations[mni] for mni in mnis}
    mirs = {index_locations[mnir] for mnir in mnirs}
    lines = []
    for mi in mis:
        if not mi + 1 in mirs:
            lines.append((c.i, cr.i))
    for mi in mirs:
        if not mi - 1 in mis:
            lines.append((c.i, cr.i))

    mnjs = matches.get(c.j, set())
    mnjls = matches.get(cl.j, set())
    mjs = {index_locations[mnj] for mnj in mnjs}
    mjls = {index_locations[mnjl] for mnjl in mnjls}
    for mj in mjs:
        if not mj + 1 in mjls:
            lines.append((c.j, cl.j))
    for mj in mjls:
        if not mj - 1 in mjs:
            lines.append((c.j, cl.j))
    return lines


def _match_lines(lines, matches, index_locations):
    new_lines = []
    for i1, i2 in lines:
        if i1 in matches and i2 in matches:
            m1s = matches[i1]
            m2s = matches[i2]
            for m1, m2 in itertools.product(m1s, m2s):
                ri1 = index_locations[m1]
                ri2 = index_locations[m2]
                if abs(ri1 - ri2) == 1:
                    new_lines.append((m1, m2))
    return new_lines


def _max_lines(sheet, index_locations):
    # TODO: This should be per block, because there can be multiple indices the max
    maxi = 0
    maxj = 0
    for cell in sheet.cells:
        if cell.v is not None:
            if cell.original_i >= maxi:
                maxi = cell.original_i
            if cell.original_j >= maxj:
                maxj = cell.original_j
    mli = (index_locations[maxi], index_locations[maxi + 1]) if maxi + 1 in index_locations else None
    mlj = (index_locations[maxj], index_locations[maxj + 1]) if maxj + 1 in index_locations else None
    return [ml for ml in [mli, mlj] if ml]


def _lines(sheet, matches, index_locations):
    lines = []
    for (i, j), (ni, nj) in sheet.index_map.items():
        # (i,j)   (ri,rj)
        # (ri,rj) (rli,rlj)
        c = sheet[i, j]
        cr = sheet[i + 1, j]
        cl = sheet[i, j + 1]
        clr = sheet[i + 1, j + 1]
        # Contains index cut
        lines.extend(_index_cut(c, cr, cl, clr))
        # More cells (cut)
        lines.extend(_cut(c, cr, cl, clr))
        # Cells with different formulas
        lines.extend(_diff_formulas(c, cr, cl, clr))
        # Args to different formulas
        lines.extend(_diff_args(c, cr, cl, clr))
        # Mis-match
        lines.extend(_matches(matches, index_locations, c, cr, cl, clr))
    lines.extend(_max_lines(sheet, index_locations))
    return lines


def _fill(sheet, lines):
    cells = {(c.original_i, c.original_j): c for c in sheet.cells.copy()}
    blocks = []
    while cells:
        c = cells.pop(next(iter(cells.keys())))

        block = [c]
        to_try = [c]
        while to_try:
            c = to_try.pop()

            for (i, j) in [(c.original_i - 1, c.original_j), (c.original_i + 1, c.original_j)]:
                if (i, j) in cells:
                    cr = cells[i, j]
                    if not ((c.i, cr.i) in lines or (cr.i, c.i) in lines):
                        block.append(cr)
                        cells.pop((i, j))
                        to_try.append(cr)

            for (i, j) in [(c.original_i, c.original_j - 1), (c.original_i, c.original_j + 1)]:
                if (i, j) in cells:
                    cl = cells[i, j]
                    if not ((c.j, cl.j) in lines or (cl.j, c.j) in lines):
                        block.append(cl)
                        cells.pop((i, j))
                        to_try.append(cl)
        blocks.append(block)
    return blocks


def split_lines(sheet, match_sets, index_locations):
    lines = _lines(sheet, match_sets, index_locations)
    return lines


def split_blocks(sheet, lines):
    blocks = _fill(sheet, lines)
    return [Block(b) for b in blocks if any(c.v for c in b) or any(c.arg_from for c in b)]  # Only keep non-empty blocks & dependencies
