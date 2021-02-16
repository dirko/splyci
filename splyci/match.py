import numpy as np


def similarity(a1, a2, cells, annotations):
    (in1, s1) = a1
    (in2, s2) = a2
    if a1 in annotations and a2 in annotations:
        if annotations[a1] == annotations[a2]:
            return np.inf
        else:
            return 0.0
    i1, i2 = cells[in1, s1], cells[in2, s2]
    in1 = [i for i in i1 if i]
    in2 = [i for i in i2 if i]
    num_equal = 0
    for in1v, in2v in zip(in1, in2):
        if in1v.v == in2v.v:
            num_equal += 1
        if in1v.v != in2v.v:
            break
    return num_equal


def _left_fill(cells_map):
    ncells = []
    for (i, j, s), cell in cells_map.items():
        if cell.v is not None:
            ncells.append((cell.i, cell.j, s, cell))
        else:
            for ii in range(i, 0, -1):
                if cells_map[ii, j, s].v is not None:
                    break
            ncells.append((cell.i, cell.j, s, cells_map[ii, j, s]))
    return ncells


def _top_fill(cells_map):
    ncells = []
    for (i, j, s), cell in cells_map.items():
        if cell.v is not None:
            ncells.append((cell.i, cell.j, s, cell))
        else:
            for jj in range(j, 0, -1):
                if cells_map[i, jj, s].v is not None:
                    break
            ncells.append((cell.i, cell.j, s, cells_map[i, jj, s]))
    return ncells


def match(sheets):
    annotated_matches = {}
    for sheet_nr, sheet in enumerate(sheets):
        for ann in sheet.annotations:
            if ann[0] == 'col_id' or ann[0] == 'row_id':
                annotated_matches[ann[1], sheet_nr] = ann[2]

    matches = []
    cells = [(cell.i, cell.j, sheet_nr, cell) for sheet_nr, sheet in enumerate(sheets) for cell in sheet.cells]
    cells_map = {(cell.original_i, cell.original_j, sheet_nr): cell for i, j, sheet_nr, cell in cells}
    # index_sheet = {col: sheet_nr for col, _, sheet_nr, _ in cells}
    # index_sheet.update({row: sheet_nr for _, row, sheet_nr, _ in cells})

    col_indices = {(col, sheet_nr) for col, _, sheet_nr, _ in cells}
    row_indices = {(row, sheet_nr) for _, row, sheet_nr, _ in cells}
    col_cells = {}
    cells_left_filled = _left_fill(cells_map)
    for col, si in col_indices:
        col_cells[col, si] = [cell for i, j, s, cell in cells_left_filled if i == col]
    row_cells = {}
    cells_top_filled = _top_fill(cells_map)
    for row, si in row_indices:
        row_cells[row, si] = [cell for i, j, s, cell in cells_top_filled if j == row]

    sim_matrix = {}
    for i1, s1 in col_indices:
        for i2, s2 in col_indices:
            if s1 != s2 and i1 > i2:
                sim = similarity((i1, s1), (i2, s2), col_cells, annotated_matches)
                sim_ass = sim_matrix.get((i1, s1), [])
                sim_ass.append((sim, (i2, s2)))
                sim_matrix[(i1, s1)] = sim_ass
    for (i1, s1), match_candidates in sim_matrix.items():
        sorted_m = sorted(match_candidates, reverse=True)
        sim0, (i20, s20) = sorted_m[0]
        sim1, (i21, s21) = sorted_m[1]
        if sim0 >= 1.0 and sim0 != sim1:  # Only if single unique match
            matches.append((i1, i20))
    for i1, s1 in row_indices:
        for i2, s2 in row_indices:
            if s1 != s2 and i1 > i2:
                sim = similarity((i1, s1), (i2, s2), row_cells, annotated_matches)
                sim_ass = sim_matrix.get((i1, s1), [])
                sim_ass.append((sim, (i2, s2)))
                sim_matrix[(i1, s1)] = sim_ass
    for (i1, s1), match_candidates in sim_matrix.items():
        sorted_m = sorted(match_candidates, reverse=True)
        sim0, (i20, s20) = sorted_m[0]
        sim1, (i21, s21) = sorted_m[1]
        if sim0 >= 1.0 and sim0 != sim1:
            matches.append((i1, i20))
    return matches
