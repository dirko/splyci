


class OutputBlock:
    def __init__(self, bid, x1, y1, x2, y2, width, height, original, dependencies):
        self.id, self.x1, self.y1, self.x2, self.y2, self.width, self.height, self.original, self.dependencies = \
            bid, x1, y1, x2, y2, width, height, original, dependencies

    def __repr__(self):
        return f'OutputBlock({self.x1}, {self.y1}, {self.x2}, {self.y2})'


def unpack_dependency_trace(deps):
    trace = []
    while deps.value != 'none':
        bid, range_name, deps = deps.args[0].value, deps.args[1].value, deps.args[2]
        trace.append((bid, range_name))
    return trace


def create_blocks(blocks, matches):
    pblocks = []
    types = []
    ranges = []
    dependant_types = []
    block_lookup = {}
    match_f = []
    for i, mi in matches:
        match_f.append(f'match({i}, {mi})')
    for block in blocks:
        block_id = block.block_id
        block_lookup[block.block_id] = block
        if isinstance(block, Block):
            pblocks.append(f'data_block({block_id}, {block.x1}, {block.y1}, {block.x2}, {block.y2}, {block.width}, {block.height})')
        if isinstance(block, FormulaBlockHorizontal):
            template = block.template.replace('"', '')
            pblocks.append(f'h_formula_block({block_id}, "{template}", {block.i1}, {block.i2}, {block.height}, {block.relative})')
            for range_name, range_types in block.dependant_types.items():
                ranges.append(f'range({block_id}, {block_id}_{range_name}, {range_name})')
                for type in range_types:
                    dependant_types.append(f'raw_depends({block_id}_{range_name}, {type})')
        if isinstance(block, FormulaBlockVertical):
            template = block.template.replace('"', '')
            pblocks.append(f'v_formula_block({block_id}, "{template}", {block.i1}, {block.i2}, {block.width}, {block.relative})')
            for range_name, range_types in block.dependant_types.items():
                ranges.append(f'range({block_id}, {block_id}_{range_name}, {range_name})')  # Otherwise ranges from different formulas interfere
                for type in range_types:
                    dependant_types.append(f'raw_depends({block_id}_{range_name}, {type})')
        for type in block.types:
            types.append(f'raw_type({block_id}, {type})')

    prolog = Prolog()
    print('prolog:-----')
    with open('tmp/debug_n.pl', 'w') as outfile:
        with open('tmp/debug.pl', 'r') as infile:
            for line in infile:
                outfile.write(line)
        for s in pblocks + types + ranges + dependant_types + match_f:
            sout = s + '.'
            outfile.write(sout + '\n')
            print(sout)

    #for s in pblocks + types + dependant_types + match_f:
    #    print(s)
    #    prolog.assertz(s)
    print('-------------')
    prolog.consult('tmp/debug_n.pl')

    for ans in prolog.query('output(Blocks)'):
        oblocks = list(ans['Blocks'])
    print('outputb', oblocks)

    blocks = [OutputBlock([orb.value for orb in b.args[0]], b.args[1].value, b.args[2].value, b.args[3].value,
                          b.args[4].value, b.args[5], b.args[6], [block_lookup[orb.value] for orb in b.args[0]],
                          [(debb.args[0].value, debb.args[1].value, unpack_dependency_trace(debb.args[2])) for debb in b.args[7]])
              for b in oblocks]
    # Convert dependencies list to references to OutputBlocks
    block_name_map = {(bid, tuple([(deps[0], deps[1])] + deps[2])): block for block in blocks for bid in block.id for deps in block.dependencies}
    print('block_name_map', block_name_map)
    for block in blocks:
        new_dependencies = {}
        for name, range_name, trace in block.dependencies:
            if name != 'none':
                edep = new_dependencies.get(range_name, [])
                edep.append(block_name_map[name, tuple(trace)])
                new_dependencies[range_name] = edep
        block.old_dependencies = block.dependencies
        block.dependencies = new_dependencies
    print('blocks! ', blocks)
    return blocks


def _parse_indices(indices, match_tuples):
    matches = _match_tuples_to_dict(match_tuples)
    relative_less = []
    relative_equal = []
    for index in indices:
        s = index
        while s.startswith('xindex') or s.startswith('yindex'):
            relation = s[7]
            right_index = s[10:-1]
            if relation == '-':
                relative_equal.append((s, right_index))
            if relation == '>':
                relative_less.append((right_index, s))
            if relation == '<':
                relative_less.append((s, right_index))
            if right_index in matches:
                for matchi in matches[right_index]:
                    relative_equal.append((right_index, matchi))
            s = right_index
    return relative_less, relative_equal


def _match_tuples_to_dict(match_tuples):
    matches = {}
    for i1, i2 in match_tuples:
        i1m = matches.get(i1, set())
        i1m.add(i2)
        matches[i1] = i1m
    return matches


def _location_constraints(cols, rows, sheets, match_tuples):
    matches = _match_tuples_to_dict(match_tuples)

    left = set()
    above = set()
    row_runs = {}
    col_runs = {}
    for sheet in sheets:
        for (i, j), (ni, nj) in sheet.index_map.items():
            r = row_runs.get(nj, [])
            #if ni in cols:
            r.append((i, ni))
            row_runs[nj] = r
            c = col_runs.get(ni, [])
            #if nj in rows:
            c.append((j, nj))
            col_runs[ni] = c
    for _, r in row_runs.items():
        r = sorted(r)
        for (_, r1), (_, r2) in zip(r, r[1:]):
            #left.add((r1, r2))
            #print('runs', r1, r2)
            for m1 in matches.get(r1, [r1]):
                for m2 in matches.get(r2, [r2]):
                    left.add((m1, m2))

    for _, c in col_runs.items():
        c = sorted(c)
        for (_, c1), (_, c2) in zip(c, c[1:]):
            #above.add((c1, c2))
            for m1 in matches.get(c1, [c1]):
                for m2 in matches.get(c2, [c2]):
                    above.add((m1, m2))

    left = list(left)
    above = list(above)
    return left, above


def csp(blocks, sheets, matches):
    print('numblocks', len(blocks))
    blocks = blocks[:]
    model = minizinc.Model()
    model.add_string("""
    include "globals.mzn";

    int: num_blocks;
    int: num_rows;
    int: num_cols;
    set of int: b=1..num_blocks;
    set of int: rows=1..num_rows;
    set of int: cols=1..num_cols;
    array[b] of cols: x1;
    array[b] of cols: x2;
    array[b] of rows: y1;
    array[b] of rows: y2;
    array[b] of int: w;
    array[b] of int: h;
    array[rows] of var int: rowsa;
    array[cols] of var int: colsa;
    int: num_left;
    int: num_above;
    set of int: l=1..num_left;
    set of int: t=1..num_above;
    array[l] of cols: left1;
    array[l] of cols: left2;
    array[t] of rows: above1;
    array[t] of rows: above2;
    
    int: num_left_equal;
    int: num_above_equal;
    set of int: le=1..num_left_equal;
    set of int: te=1..num_above_equal;
    array[le] of cols: left_equal1;
    array[le] of cols: left_equal2;
    array[te] of rows: above_equal1;
    array[te] of rows: above_equal2;
    
    int: max_col = sum(w) + 1;
    int: max_row = sum(h) + 1;
        
    array[b] of var bool: use_block;
    array[b] of var int: wf;
    array[b] of var int: hf;
    constraint forall(bl in b) ((use_block[bl] -> wf[bl] = w[bl]) /\ 
                                (not use_block[bl] -> wf[bl] = 0));
    constraint forall(bl in b) ((use_block[bl] -> hf[bl] = h[bl]) /\ 
                                (not use_block[bl] -> hf[bl] = 0));
                                
    array[l] of var bool: use_left;
    array[t] of var bool: use_above;   
    array[le] of var bool: use_left_equal;                         
    array[te] of var bool: use_above_equal;                         

    constraint forall(c in cols) (colsa[c] > 0 /\ colsa[c] <= max_col);
    constraint forall(r in rows) (rowsa[r] > 0 /\ rowsa[r] <= max_row);

    constraint diffn([colsa[x1[bl]] | bl in b], 
                     [rowsa[y1[bl]] | bl in b],  
                     [wf[bl] | bl in b],
                     [hf[bl] | bl in b]);
    constraint forall(i in b) (colsa[x1[i]] + w[i] -1= colsa[x2[i]]);
    constraint forall(i in b) (rowsa[y1[i]] + h[i] -1= rowsa[y2[i]]);
    constraint forall(i in l) (use_left[i] <-> (colsa[left1[i]] < colsa[left2[i]]));
    constraint forall(i in t) (use_above[i] <-> (rowsa[above1[i]] < rowsa[above2[i]]));
    constraint forall(i in le) (use_left_equal[i] <-> (colsa[left_equal1[i]] = colsa[left_equal2[i]]));
    constraint forall(i in te) (use_above_equal[i] <-> (rowsa[above_equal1[i]] = rowsa[above_equal2[i]]));

    %solve satisfy;
    %solve minimize sum(rowsa) + sum(colsa);
    solve maximize sum(use_left) + sum(use_above) + sum(use_block) + sum(use_left_equal) + sum(use_above_equal);    
    """)

    cols = sorted(list(set(block.x1 for block in blocks).union(set(block.x2 for block in blocks))))
    rows = sorted(list(set(block.y1 for block in blocks).union(set(block.y2 for block in blocks))))
    relative_left, relative_left_equals = _parse_indices(cols, matches)
    relative_above, relative_above_equals = _parse_indices(rows, matches)
    colsi = {col: i+1 for i, col in enumerate(cols)}
    rowsi = {row: i+1 for i, row in enumerate(rows)}
    left, above = _location_constraints(cols, rows, sheets, matches)
    left = [(l1, l2) for l1, l2 in left if l1 in cols and l2 in cols] + relative_left
    above = [(a1, a2) for a1, a2 in above if a1 in rows and a2 in rows] + relative_above
    print('blocks', blocks)

    ProjectedBlock = collections.namedtuple('ProjectedBlock', 'x1 y1 x2 y2 width height')
    pblocks = list(set(ProjectedBlock(block.x1, block.y1, block.x2, block.y2, block.width, block.height) for block in blocks))
    for b in blocks:
        print(' ', b)
    print(len(blocks), len(pblocks))
    for b in pblocks:
        print('  ', b)
    print('pblocks', len(pblocks), pblocks)
    print('colsi', colsi)
    print('rowsi', rowsi)

    gecode = minizinc.Solver.lookup("chuffed")
    minst = minizinc.Instance(gecode, model)
    inst = {}
    inst['num_blocks'] = len(pblocks)
    inst['num_rows'] = len(rows)
    inst['num_cols'] = len(cols)
    inst['x1'] = [colsi[block.x1] for block in pblocks]
    inst['x2'] = [colsi[block.x2] for block in pblocks]
    inst['y1'] = [rowsi[block.y1] for block in pblocks]
    inst['y2'] = [rowsi[block.y2] for block in pblocks]
    inst['w'] = [block.width for block in pblocks]
    inst['h'] = [block.height for block in pblocks]
    inst['num_left'] = len(left)
    inst['num_above'] = len(above)
    inst['left1'] = [colsi[l1] for l1, _ in left]
    inst['left2'] = [colsi[l2] for _, l2 in left]
    inst['above1'] = [rowsi[a1] for a1, _ in above]
    inst['above2'] = [rowsi[a2] for _, a2 in above]
    inst['num_left_equal'] = len(relative_left_equals)
    inst['num_above_equal'] = len(relative_above_equals)
    inst['left_equal1'] = [colsi[l1] for l1, _ in relative_left_equals]
    inst['left_equal2'] = [colsi[l2] for _, l2 in relative_left_equals]
    inst['above_equal1'] = [rowsi[a1] for a1, _ in relative_above_equals]
    inst['above_equal2'] = [rowsi[a2] for _, a2 in relative_above_equals]

    print(inst)
    for k, v in inst.items():
        minst[k] = v
    # Solve the instance
    print('CSP')
    result = minst.solve(all_solutions=False)
    print('res', result)
    print(result['rowsa'])
    print(result['colsa'])
    assignment = {col: r for col, r in zip(cols, result['colsa'])}
    assignment.update(**{row: r for row, r in zip(rows, result['rowsa'])})
    used_blocks = {}
    for block, used in zip(pblocks, result['use_block']):
        used_blocks[block] = used
        print(used)
        if not used:
            print('Warning not used:', block)
            for oblock in blocks:
                if oblock.x1 == block.x1 and oblock.y1 == block.y1 and oblock.x2 == block.x2 and oblock.y2 == block.y2:
                    print('Original block:', oblock)

    print('assignment', assignment)
    return assignment

