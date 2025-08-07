# Experiments related to recovering the original sheets

import json
import os
import glob
import sys
import argparse
import time

import pandas as pd
from splyci.sheet import sheet_from_file


def merge(indir, outdir):
    from splyci.integration import extract
    for dataset in ['develop', 'test']:
        files = glob.glob(indir + f'/{dataset}/*.xlsx')
        for file in files:
            base_name = file.split('.')[0].split('/')[-1]
            file_dir = outdir + '/' + dataset + '/' + base_name
            os.makedirs(file_dir, exist_ok=True)
            sheets_in = [(file, 1), (file, 2)]
            extract(sheets_in, file_dir)


def _diff(f1, s1, f2, s2, sheet_from_file, rowcolaligndist, tadmodist):
    # /Users/dirkocoetsee/Documents/programming/spreadsheet-block-diff/move_diff.py
    val_map, ground_sheet = sheet_from_file(f1, s1)
    val_map, actual_sheet = sheet_from_file(f2, s2, val_map)
    rowcolalign_diff = rowcolaligndist(ground_sheet, actual_sheet)
    tadmo_diff = tadmodist(ground_sheet, actual_sheet)
    return rowcolalign_diff, tadmo_diff


def compare(indir, resultdir, outdir):
    import move_diff
    import baseline
    import greedy
    from joblib import Memory

    memory = Memory("cache", verbose=0)
    # memory.clear()

    @memory.cache
    def rowcoldist(s1, s2):
        _, res = baseline.rowcolalign(s1, s2)
        return res

    @memory.cache
    def tadmodist(s1, s2):
        res = greedy.spreadsheet_diff(s1, s2)
        return res


    for dataset in ['develop', 'test']:
        eval_dir = outdir + '/' + dataset
        os.makedirs(eval_dir, exist_ok=True)
        infiles = glob.glob(indir + f'/{dataset}/*.xlsx')
        for sheet_in in infiles:
            base_name = sheet_in.split('.')[0].split('/')[-1]
            sheet_result = resultdir + '/' + dataset + '/' + base_name + '/' + 'output.xlsx'
            rowcolalign_diff, tadmo_diff = _diff(sheet_in, 0, sheet_result, 0, move_diff.sheet_from_file, rowcoldist, tadmodist)
            print(f"{dataset:<10} {base_name:>30} {rowcolalign_diff.distance():>5} {tadmo_diff.bound:>4} {len(tadmo_diff.moves):>4}")


def summarise_result(resultdir, outdir):
    report_df_list = []
    for dataset in ['develop', 'test']:
        infiles = sorted(glob.glob(resultdir + f'/{dataset}/*/report.json'))
        reports = []
        for infile in infiles:
            with open(infile, 'r') as f:
                json_data = json.load(f)
                reports.append(json_data)
        report_df = pd.DataFrame(reports)
        report_df['dataset'] = dataset
        report_df['nr'] = report_df.index + 1
        report_df_list.append(report_df)
    report_df = pd.concat(report_df_list, ignore_index=True)
    for col in ['num_generalised_formula_blocks', 'num_sheet_blocks', 'num_sheet_formula_blocks']:
        report_df[col] = report_df[col].apply(lambda x: x[0] + x[1])
    report_df['formatted_used_blocks'] = report_df.apply(
        lambda x: f"{x['num_used_blocks']}/{x['num_output_blocks']}", axis=1
    )
    report_df['formatted_used_constraints'] = report_df.apply(
        lambda x: f"{x['num_used_positional_constraints']}/{x['num_total_positional_constraints']}", axis=1
    )
    report_output = report_df[
        ['dataset', 'nr', 'num_sheet_blocks', 'num_sheet_formula_blocks', 'num_generalised_formula_blocks',
         'formatted_used_blocks', 'formatted_used_constraints']
    ]
    report_output['dataset'] = report_output['dataset'].replace('develop', 'dev')
    # Only keep the first occurence of dataset, fill the rest with blank
    report_output['dataset'] = report_output['dataset'].where(report_output['dataset'] != report_output['dataset'].shift(), '')
    report_latex = report_output.to_latex(index=False)
    print(report_latex)
    with open(outdir + '/block_constraint.tex', 'w') as f:
        f.write(report_latex)

def summarise_data(indir, outdir):
    rows = []
    for dataset in ['develop', 'test']:
        infiles = sorted(glob.glob(indir + f'/{dataset}/*.xlsx'))
        for n, infile in enumerate(infiles):
            merged_sheet = sheet_from_file(infile, 0, 0, use_cut_annotations=True, use_border_style=False)
            left_sheet = sheet_from_file(infile, 1, 0, use_cut_annotations=True, use_border_style=False)
            right_sheet = sheet_from_file(infile, 2, 0, use_cut_annotations=True, use_border_style=False)
            for sheet_name, sheet in [('merged', merged_sheet), ('left', left_sheet), ('right', right_sheet)]:
                size_x = max(i for i, j in sheet.index_map.keys())
                size_y = max(j for i, j in sheet.index_map.keys())
                n_formulas = len([s for s in sheet.cells if s.formula])
                n_cut_ann = len(sheet.cut_annotations)
                n_match_ann = len(sheet.annotations)
                n_type_ann = len(set(t for cell in sheet.cells for t in cell.types if 'theme' in t)) - 1  # Don't count the default theme
                rows.append((dataset, n, sheet_name, size_x, size_y, n_formulas, n_cut_ann, n_match_ann, n_type_ann))
    report_df = pd.DataFrame(rows, columns=['dataset', 'nr', 'sheet_name', 'size_x', 'size_y', 'n_formulas', 'n_cut_ann', 'n_match_ann', 'n_type_ann'])
    report_df = pd.pivot(report_df, index=['dataset', 'nr'], columns='sheet_name', values=['size_x', 'size_y', 'n_formulas', 'n_cut_ann', 'n_match_ann', 'n_type_ann'])
    report_df = report_df.reset_index()
    report_df.columns = ['_'.join(col).strip() for col in report_df.columns.values]
    print(report_df)
    report_df['dataset'] = report_df['dataset_'].replace('develop', 'dev')
    report_df['dataset'] = report_df['dataset'].where(report_df['dataset'] != report_df['dataset'].shift(), '')
    for sheet_name in ['merged', 'left', 'right']:
        report_df[f'annotations_{sheet_name}'] = report_df.apply(
            lambda x: f"{x[f'n_cut_ann_{sheet_name}']}/{x[f'n_match_ann_{sheet_name}']}/{x[f'n_type_ann_{sheet_name}']}", axis=1
        )
        report_df[f'size_{sheet_name}'] = report_df.apply(
            lambda x: f"${x[f'size_y_{sheet_name}']} \\times {x[f'size_x_{sheet_name}']}$", axis=1
        )
    print(report_df)
    report_output = report_df[
        ['dataset', 'nr_', 'size_merged', 'n_formulas_merged',
         'size_left', 'n_formulas_left', 'annotations_left',
         'size_right', 'n_formulas_right', 'annotations_right']
    ]
    report_latex = report_output.to_latex(index=False, escape=False)
    print(report_latex)
    with open(outdir + '/data.tex', 'w') as f:
        f.write(report_latex)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Recover original sheets from results.')
    parser.add_argument('command', type=str, choices=['merge', 'compare', 'summarise_result', 'summarise_data'], help='Command to execute: merge or compare')
    parser.add_argument('--raw', type=str, help='Input directory with original sheets', default='experiments')
    parser.add_argument('--result', type=str, help='Directory with results', default='output/experiments/merge')
    parser.add_argument('--eval', type=str, help='Output directory for results', default='output/experiments/merge_eval')
    args = parser.parse_args()
    if args.command == 'merge':
        merge(indir=args.raw, outdir=args.result)
    elif args.command == 'compare':
        compare(indir=args.raw, resultdir=args.result, outdir=args.eval)
    elif args.command == 'summarise_result':
        summarise_result(resultdir=args.result, outdir=args.eval)
    elif args.command == 'summarise_data':
        summarise_data(indir=args.raw, outdir=args.eval)
    else:
        print("Unknown command")
        print(parser.format_help())
        sys.exit(1)

