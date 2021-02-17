from splyci.sheet import sheet_from_file, cells_to_range
from splyci.match import match
from splyci.block import _match_lines, _match_sets, split_lines, split_blocks, Block
from splyci.formula import generalise, FormulaBlockHorizontal, FormulaBlockVertical
from splyci.csp import create_blocks, csp
import matplotlib.pyplot as plt
import matplotlib
import pandas
import numpy as np
from openpyxl.styles.borders import Border, Side


def dependent_intersection(original_block, dblocks, di, dj, assignment):
    cells = []
    print('intersection', original_block, dblocks, di, dj)
    for dblock in dblocks:
        if isinstance(original_block, FormulaBlockVertical):
            for i in range(assignment[dblock.x1], assignment[dblock.x2] + 1):
                cells.append((i, dj + assignment[dblock.y1]))
        if isinstance(original_block, FormulaBlockHorizontal):
            for j in range(assignment[dblock.y1], assignment[dblock.y2] + 1):
                cells.append((di + assignment[dblock.x1], j))
    return cells


def fill_blocks(blocks, output_blocks, assignment):
    min_x = min(assignment[block.x1] for block in output_blocks) + 0
    min_y = min(assignment[block.y1] for block in output_blocks) + 0
    max_width = max(assignment[block.x2] for block in output_blocks) + 2 - min_x
    max_height = max(assignment[block.y2] for block in output_blocks) + 2 - min_y
    print('max_width, max_height', max_width, max_height, min_x, min_y)
    x = {c: [None for _ in range(max_height)] for c in range(max_width)}

    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active

    for nblock, block in enumerate(output_blocks):
        (ids, x1, y1, x2, y2, width, height, original_blocks, dependent_blocks) = \
            block.id, block.x1, block.y1, block.x2, block.y2, block.width, block.height, block.original, block.dependencies
        print(nblock, '/', len(output_blocks), '  ', (width, height), original_blocks)
        # TODO how to disambiguoate?
        original_block = original_blocks[0]
        if isinstance(original_block, Block):
            # Fill in cells
            for cell in original_block.cells:
                di, dj = cell.original_i - original_block.x1o, cell.original_j - original_block.y1o
                # Note: other way around (row, column)! None - not for dicts
                x[assignment[x1] + di - min_x][assignment[y1] + dj - min_y] = cell.v
                new_cell = ws.cell(row=assignment[y1] + dj - min_y + 1, column=assignment[x1] + di - min_x + 1, value=cell.v)
                new_cell.border = _new_border(di, dj, width, height)
        else: # isinstance(original_block, FormulaBlockVertical):
            # Fill in formulas
            for i in range(assignment[x1], assignment[x2] + 1):
                for j in range(assignment[y1], assignment[y2] + 1):
                    args = {}
                    di = i - assignment[x1]
                    dj = j - assignment[y1]
                    for range_name, v in original_block.dependencies.items():
                        print()
                        print('Range n', range_name, v, dependent_blocks)
                        # TODO think below case cannot happen?
                        # Note: it happens when the argument isn't used for placing
                        if isinstance(next(iter(v), None), Block):
                            dblocks = v
                            print('not placing', range_name)
                            icells = dependent_intersection(original_block, dblocks, di, dj, assignment)
                            drange = ([(ii - min_x+1, ij - min_y+1) for (ii, ij) in icells])
                            sorted_drange = sorted(list(set(drange)))
                            print('block drange', drange)
                            range_string = cells_to_range(sorted_drange)
                            print('block range_string', range_string)
                            args[range_name] = range_string
                        if isinstance(next(iter(v), None), str):
                            drange = []
                            if not range_name in dependent_blocks:
                                print('something went wrong with formulae - skipping this block')
                                break
                            dblocks = dependent_blocks[range_name]
                            print('rogo', original_block, range_name)
                            icells = dependent_intersection(original_block, dblocks, di, dj, assignment)
                            drange = ([(ii - min_x+1, ij - min_y+1) for (ii, ij) in icells])
                            print('drange', drange)
                            sorted_drange = sorted(list(set(drange)))
                            print('sdr', v)
                            print('sdr', sorted_drange)
                            range_string = cells_to_range(sorted_drange)
                            print('range_string', range_string)
                            args[range_name] = range_string
                        # Else the block is probably empty?

                    print('adding', args)
                    try:
                        new_value = original_block.template.format(**args)
                    except KeyError:
                        print('something went wrong with formulae - skipping this block')
                        new_value = ''

                    x[i - min_x][j - min_y] = new_value
                    new_cell = ws.cell(row=j - min_y + 1, column=i - min_x + 1, value=new_value)
                    new_cell.border = _new_border(di, dj, width, height)

    print('converting')
    df = pandas.DataFrame(x)
    return wb, df


def _new_border(di, dj, w, h):
    left = Side(border_style='thick') if di == 0 else None
    right = Side(border_style='thick') if di == w - 1 else None
    top = Side(border_style='thick') if dj == 0 else None
    bottom = Side(border_style='thick') if dj == h - 1 else None
    border = Border(left=left, right=right, top=top, bottom=bottom)
    return border


def get_index_locations(sheets):
    locations = {}
    for sheet in sheets:
        for (i, j), (ni, nj) in sheet.index_map.items():
            locations[ni] = i
            locations[nj] = j
    return locations


def extract(filesin, fileout=None):
    sheets = [sheet_from_file(filein, sheetnr, sheet_counter)
              for sheet_counter, (filein, sheetnr) in enumerate(filesin)]
    index_locations = get_index_locations(sheets)
    match_tuples = match(sheets)
    match_sets = _match_sets(match_tuples)

    lines = [line for sheet in sheets for line in split_lines(sheet, match_sets, index_locations)]
    lines.extend(_match_lines(lines, match_sets, index_locations))
    sheet_blocks = [split_blocks(sheet, lines) for sheet in sheets]

    try:
        generalised_sheet_blocks = [generalise(blocks) for blocks in sheet_blocks]
        blocks = [block for blocks in generalised_sheet_blocks for block in blocks]
        output_blocks = create_blocks(blocks, match_tuples)
        assignment = csp(output_blocks, sheets, match_tuples)
        wb, df = fill_blocks(blocks, output_blocks, assignment)
        print('done')
        pandas.options.display.width = 0
        print(df)
    except Exception as error:
        print('Error')
        print(error)
        raise error
    finally:
        #print(df)
        if fileout:
            for i, blocks in enumerate(sheet_blocks):
                draw_blocks(blocks, fileout + f'/{i}.svg')
    if fileout:
        filen = fileout + '/output.xlsx'
        #df.to_excel(filen, header=False, index=False)
        wb.save(filen)
        copy_prolog_file(fileout)
    return df


def copy_prolog_file(dir):
    with open('tmp/debug_n.pl', 'r') as fi:
        with open(dir + '/blocks.pl', 'w') as fo:
            fo.write(fi.read())


def draw_blocks(blocks, filename):
    fig2 = plt.figure(figsize=(9, 8))
    ax2 = fig2.add_subplot(111, aspect='equal')
    min_x = min(b.x1o for b in blocks)
    min_y = min(b.y1o for b in blocks)
    max_width = max(b.x1o + b.width for b in blocks)
    max_height = max(b.y1o + b.height for b in blocks)

    for block in blocks:
        ax2.add_patch(
            matplotlib.patches.Rectangle(
                (block.x1o * 1.0 + np.random.random() * 0.2,
                 block.y1o * 1.0 + np.random.random() * 0.2),
                block.width * 0.96,
                block.height * 0.96,
                fill=False  # remove background
            ))

    plt.xlim(0, max_width + 1)
    plt.ylim(max_height + 1, 0)
    plt.show()
    plt.savefig(filename)
