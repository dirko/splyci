
class FormulaBlockVertical:
    def __init__(self, template, i1, i2, dependant_types, types, width, dependencies, relative):
        self.template = template
        self.i1 = i1
        self.i2 = i2
        self.dependant_types = dependant_types
        self.types = types
        self.width = width
        self.dependencies = dependencies
        self.relative = relative
        self.block_id = 'b_' + hex(abs(hash(self)))[2:9]

    def __repr__(self):
        return f'VerticalBlock({self.template}, {self.i1}, {self.i2}, {self.width}, {self.relative})'

    def __hash__(self):
        return hash(('v', self.template, self.i1, self.i2, tuple(self.types), tuple(self.dependant_types), self.relative))


class FormulaBlockHorizontal:
    def __init__(self, template, i1, i2, dependant_types, types, height, dependencies, relative):
        self.template = template
        self.i1 = i1
        self.i2 = i2
        self.height = height
        self.dependant_types = dependant_types
        self.types = types
        self.dependencies = dependencies
        self.relative = relative
        self.block_id = 'b_' + hex(abs(hash(self)))[2:9]

    def __repr__(self):
        return f'HorizontalBlock({self.template}, {self.i1}, {self.i2}, {self.height}, {self.relative})'

    def __hash__(self):
        return hash(('h', self.template, self.i1, self.i2, tuple(self.types), tuple(self.dependant_types), self.relative))


def _split_block_types(blocks):
    non_formula_blocks = []
    formula_blocks = []
    for block in blocks:
        if block.type == 'formula':
            formula_blocks.append(block)
        else:
            non_formula_blocks.append(block)
    return non_formula_blocks, formula_blocks


def _get_block_dependencies(blocks, formula_blocks):
    cell_to_block = {}
    for block in blocks:
        for cell in block.cells:
            cell_to_block[(cell.i, cell.j)] = block
    dependencies = {}
    for block in formula_blocks:
        for cell in block.cells:
            for range_name, dcells in cell.formula.ranges.items():
                cdeps = dependencies.get(block, {})
                depblocks = {cell_to_block[dcell] for dcell in dcells}
                #print('depblocks', block, depblocks)
                #if not len(depblocks) == 1:
                #    raise AssertionError()
                cdeps[range_name] = depblocks
                dependencies[block] = cdeps
    return dependencies


def _get_block_constraints(dependencies):
    width_constraints = {}
    height_constraints = {}
    #print('gbc', dependencies)
    for block, cdeps in dependencies.items():
        for range_name, dblocks in cdeps.items():
            for dblock in dblocks:
                # Edit: Capturing all constraints
                # dblock = next(iter(dblocks))  # Just get the first because the rest should have the same shape
                if block.width == dblock.width:
                    if block.x1o == dblock.x1o:
                        relative = '-'
                    elif block.x1o > dblock.x1o:
                        relative = '>'
                    elif block.x1o < dblock.x1o:
                        relative = '<'
                    # TODO: multiple blocks might be constraints?
                    widthc = width_constraints.get((block, range_name), set())
                    widthc.add((dblock, relative))
                    width_constraints[block, range_name] = widthc
                if block.height == dblock.height:
                    if block.y1o == dblock.y1o:
                        relative = '-'
                    elif block.y1o > dblock.y1o:
                        relative = '>'
                    elif block.y1o < dblock.y1o:
                        relative = '<'
                    heightc = height_constraints.get((block, range_name), set())
                    heightc.add((dblock, relative))
                    height_constraints[block, range_name] = heightc
    return width_constraints, height_constraints


def _get_formula_templates(formula_blocks):
    formula_templates = {}
    for block in formula_blocks:
        ft = formula_templates.get(block.formula_template, set())
        ft.add(block)
        formula_templates[block.formula_template] = ft
    return formula_templates


def _get_formula_template_groups(formula_templates, height_constraints, width_constraints):
    formula_template_groups = {}
    for template, template_blocks in formula_templates.items():
        ftg = {}
        for template_block in template_blocks:
            xs = ftg.get((template_block.x1, template_block.x2), set())
            xs.add(template_block)
            ftg[template_block.x1, template_block.x2] = xs
            ys = ftg.get((template_block.y1, template_block.y2), set())
            ys.add(template_block)
            ftg[template_block.y1, template_block.y2] = ys
        for template_block in template_blocks:
            gx = ftg[template_block.x1, template_block.x2]
            gy = ftg[template_block.y1, template_block.y2]
            group_types = tuple(sorted(list(template_block.types)))
            # If more horizontally stacked formula blocks, then formula_h, because that is the direction of extension
            # Also, if they are the same (eg 1x1), then use the = instead of < or >
            if len(gx) > len(gy):
                g = formula_template_groups.get((template, template_block.x1, template_block.x2, group_types), set())
                g.add(template_block)
                formula_template_groups[template, template_block.x1, template_block.x2, group_types] = g
            elif len(gx) < len(gy):
                g = formula_template_groups.get((template, template_block.y1, template_block.y2, group_types), set())
                g.add(template_block)
                formula_template_groups[template, template_block.y1, template_block.y2, group_types] = g
            else:  # If there are arguments - might not be for =DATETIME() for example - but we filter that at the start
                # They are the same, so look for aligning perfectly
                # Only check one of the possible constraint blocks for now
                range_name = template_block.range_names[0]
                if (template_block, range_name) in height_constraints and list(height_constraints[template_block, range_name])[0][1] == '-':
                    g = formula_template_groups.get((template, template_block.x1, template_block.x2, group_types), set())
                    g.add(template_block)
                    formula_template_groups[template, template_block.x1, template_block.x2, group_types] = g
                else:  # width or no constraints
                    g = formula_template_groups.get((template, template_block.y1, template_block.y2, group_types), set())
                    g.add(template_block)
                    formula_template_groups[template, template_block.y1, template_block.y2, group_types] = g

    return formula_template_groups


def _get_formula_template_types(blocks, formula_template_groups, width_constraints, height_constraints):
    formula_template_types = {}
    for (template, i1, i2, group_types), template_blocks in formula_template_groups.items():
        # (All blocks in template_blocks should have the same range_names)
        for range_name in list(template_blocks)[0].range_names:
            print('ranw', range_name, width_constraints)
            print('ranh', range_name, height_constraints)
            constraint_blocks = {
                block
                for template_block in template_blocks
                for block, _ in width_constraints.get((template_block, range_name), [])
            }
            constraint_blocks = constraint_blocks.union({
                block
                for template_block in template_blocks
                for block, _ in height_constraints.get((template_block, range_name), [])
            })
            non_constraint_blocks = {block for block in blocks if block not in constraint_blocks}
            # Get positive types
            print('template_blocks', template_blocks, [t in height_constraints for t in template_blocks])
            print('constraint-blocks', [b.types for b in constraint_blocks])
            #print('non-constraint-blocks', non_constraint_blocks)
            #pos = set.intersection(*([block.types for block in constraint_blocks]))
            pos = set(t for block in constraint_blocks for t in block.types)
            # Prune types if one negative example exists
            neg = set(t for block in non_constraint_blocks for t in block.types)
            print('PosNeg')
            print(pos, neg, pos - neg)
            type_intersection = formula_template_types.get((template, i1, i2, group_types), {})
            # Should only be assigned once per range_name because we filter constraints on range_name above
            type_intersection[range_name] = pos - neg
            formula_template_types[template, i1, i2, group_types] = type_intersection
    return formula_template_types


def _get_formula_template_blocks(dependencies, formula_template_groups, formula_template_types, height_constraints, width_constraints):
    formula_template_blocks = []
    all_height_constraints = {block for block, _ in height_constraints.keys()}
    all_width_constraints = {block for block, _ in width_constraints.keys()}
    for (template, i1, i2, group_types), template_blocks in formula_template_groups.items():
        #  Only first is necessary - the other blocks should encode exactly the same information
        for template_block in list(template_blocks)[:1]:
            print('template', template, i1, i2, group_types, template_blocks)
            if template_block in all_height_constraints:
                types = formula_template_types[template, i1, i2, group_types]
                cdeps = {}
                for range_name, dep_blocks in dependencies[template_block].items():
                    dblocks, relatives = zip(*height_constraints[template_block, range_name])

                    print('deb', dep_blocks, dblocks)
                    if dep_blocks != set(dblocks):
                        cdeps[range_name] = dep_blocks
                    else:
                        cdeps[range_name] = types[range_name]
                        relative_match = relatives[0]  # Use one of the relatives that is used to constrain the orientation
                print('m', cdeps)
                new_block = FormulaBlockVertical(template_block.formula_range_template, template_block.x1, template_block.x2,
                                                 types, template_block.types, template_block.width, cdeps, relative_match)
            elif template_block in all_width_constraints:
                types = formula_template_types[template, i1, i2, group_types]
                print('depe', dependencies[template_block])
                cdeps = {}
                for range_name, dep_blocks in dependencies[template_block].items():
                    dblocks, relatives = zip(*width_constraints[template_block, range_name])
                    if dep_blocks != set(dblocks):
                        cdeps[range_name] = dep_blocks
                    else:
                        cdeps[range_name] = types[range_name]
                        relative_match = relatives[0]  # Use one of the relatives that is used to constrain the orientation
                new_block = FormulaBlockHorizontal(template_block.formula_range_template, template_block.y1, template_block.y2,
                                                   types, template_block.types, template_block.height, cdeps, relative_match)
            formula_template_blocks.append(new_block)
    return formula_template_blocks


def generalise(blocks):
    non_formula_blocks, formula_blocks = _split_block_types(blocks)
    dependencies = _get_block_dependencies(blocks, formula_blocks)
    print('dependencies', dependencies)
    width_constraints, height_constraints = _get_block_constraints(dependencies)
    formula_templates = _get_formula_templates(formula_blocks)
    formula_template_groups = _get_formula_template_groups(formula_templates, height_constraints, width_constraints)

    print('formula_templates', formula_templates)
    print('formua_template_groups', formula_template_groups)
    print('width_constraints', width_constraints)
    print('heigh_constraints', height_constraints)

    formula_template_types = _get_formula_template_types(blocks, formula_template_groups, width_constraints, height_constraints)
    print('formula_template_types', formula_template_types)
    formula_template_blocks = _get_formula_template_blocks(dependencies, formula_template_groups, formula_template_types, height_constraints, width_constraints)

    print('formula_template_blocks', formula_template_blocks)

    return non_formula_blocks + formula_template_blocks
