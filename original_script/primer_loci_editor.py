#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : TopGen
@Time    : 2023/6/25 17:01
@Author  : lbfeng
@File    :  primer_loci_editor.py
"""
import os
import argparse
import pandas as pd
import numpy as np
from pandas.api.types import is_numeric_dtype


__doc__ = """
Use indexes or specify column values to add, remove, or replace DataFrame rows. When adding, some columns will be filled with positive values and added to the first row in sequence; 
When deleting, you can pass in the index row (single or list) or the specified value of the specified row; Replacement must use index rows and specified column values. 
When adding, deleting, and replacing coexist, the priority is Replace>Delete>Add.

Example of adding data: 
    Example command:
    
        $python3 primer_loci_editor.py -i original.tsv --add chrom=chr3 pos=178917478 ref=G alt=A vaf=0.136 gene=PIK3CA --add chrom=? pos=? ref=? alt=? -o edited.tsv
        
    Precautions:
    
        Add several rows of data separated by - add, with each row represented by key value pairs and separated by spaces; 
        Primer design requires information such as chrome, pos, ref, alt, and selected data such as gene, vaf, depth, cHGVS, pHGVS.
        
Example of deleting data:
    Example command:
    
        $python3 primer_loci_editor.py -i original.tsv --del_kv chrom=chr7 ref=G --delete index=2 -o edited.tsv
        
        $python3 primer_loci_editor.py -i original.tsv --del_ind 1 5 9 7 10 --del_kv chrom=chr7 ref=G --delete index=2 -o edited.tsv
        
        $python3 primer_loci_editor.py -i original.tsv --del_kv chrom=chr3 pos=178917478 --del_kv chrom=? pos=? -o edited.tsv
        
    Precautions:
    
        Deleting data can be achieved by deleting the number of index rows
        (deleting the header row means that if the first row is the header and the second row is the data in the file, the index should be passed in as 1), 
        or by matching multiple criteria and multiple index rows (try matching unique rows to improve accuracy).

Example of replacing data:
    Example command:
    
        $python3 primer_loci_editor.py -i original.tsv --rep index=1 chrom=chr7,chr9 cancer_type_ID=TS01,TEST pos=55249071,121121 -o test.csv
   
    Precautions:
    
        The replacement principle is to use index rows, match column values, and then replace column values. Index uses index=, 
        and the matching column values and replacement column values are separated by ','. Multiple row matching can be performed, with the highest priority.
        
"""


def execute(input_path, del_dicts, add_dicts, replace_dicts, output_path):
    df = pd.read_csv(input_path, sep='\t')
    print('LOGGING: The original input file is {}, and the dataframe abbreviation is displayed as: \n{}\n'.format(input_path, df))
    # 删除信息
    if del_dicts:
        for del_d in del_dicts:
            if 'index' in del_d:
                if type(del_d['index']) is list:
                    for index in del_d['index']:
                        index = int(index) - 1
                        df = df.drop(index)
                elif type(del_d['index']) is str:
                    index = int(del_d['index']) - 1
                    df = df.drop(index)
                else:
                    raise TypeError('Unknown index type, index supports list and str.')
            else:
                # 构建删除条件
                condition = None
                for key, value in del_d.items():
                    if key in ['pos', 'vaf', 'depth', 'snp', 'driver', 'cellular_prevalence']:
                        value = int(value)
                    if condition is None:
                        condition = (df[key] == value)
                    else:
                        condition &= (df[key] == value)
                df = df[~condition]
    # 添加信息
    if add_dicts:
        for add_d in add_dicts:
            # python3.10以后版本适用
            # df.loc[-1] = add_d

            # 兼容所有python版本（更推荐）
            # 创建一个新行，确保所有需要的列都在其中
            new_data = {col: add_d.get(col, np.nan) for col in df.columns}
            new_row = pd.Series(new_data)
            # 将新行添加到DataFrame的开始
            df = pd.concat([pd.DataFrame([new_row]), df], ignore_index=True)

            # 指定需要填充的列
            columns_to_fill = ['sampleSn', 'cancer_type', 'cancer_type_ID']
            # 使用后面的值填充指定列
            df[columns_to_fill] = df[columns_to_fill].fillna(method='bfill')
            df = df.sort_index().reset_index(drop=True)

    # 替换信息
    if replace_dicts:
        for replace_d in replace_dicts:
            if 'index' in replace_d:
                index = int(replace_d['index'])
                if 1 <= index <= len(df):
                    index -= 1  # 减去1以匹配DataFrame的索引
                    columns_to_replace = [key for key in replace_d.keys() if key != 'index']
                    if all(column in df.columns for column in columns_to_replace):
                        condition_met = True
                        for key, value in replace_d.items():
                            if key != 'index':
                                original_value, replacement_value = value.split(',')
                                column_type = df.dtypes[key]
                                if is_numeric_dtype(column_type):
                                    original_value = pd.to_numeric(original_value, errors='coerce')
                                    replacement_value = pd.to_numeric(replacement_value, errors='coerce')
                                if df.loc[index, key] != original_value:
                                    condition_met = False
                                    break
                        if condition_met:
                            for key, value in replace_d.items():
                                if key != 'index':
                                    original_value, replacement_value = value.split(',')
                                    df.loc[index, key] = replacement_value
                    else:
                        raise ValueError('Invalid columns specified for replacement.')
                else:
                    raise ValueError('Invalid index specified for replacement.')
            else:
                raise ValueError('Index not specified for replacement.')

    print('LOGGING: After editing, the output file is {}, and the dataframe abbreviation is displayed as: \n{}\n'.format(output_path, df))
    df.to_csv(output_path, sep='\t', encoding='utf-8', index=False)
    print('LOGGING: File written successfully!')


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    # 添加命令行参数
    parser.add_argument('-i', '--input_path', type=str, required=True, help='Path to the input file')
    parser.add_argument('--del_ind', nargs='+', metavar='INDEX', action='append', help='Indexes of rows to delete')
    parser.add_argument('--del_kv', nargs='+', metavar='KEY=VALUE', action='append', help='Data values to delete')
    parser.add_argument('--add', nargs='+', metavar='KEY=VALUE', action='append', help='Data values to add')
    parser.add_argument('--rep', nargs='+', metavar='KEY=VALUE', action='append', help='Data values to replace')
    parser.add_argument('-o', '--output_path', type=str, help='Path to the output file')

    # 解析命令行参数
    args = parser.parse_args()
    if os.path.exists(args.input_path):
        input_path = os.path.abspath(args.input_path)
    else:
        return

    if not args.output_path:
        output_path = input_path
    else:
        output_path = os.path.abspath(args.output_path)

    # 创建要添加和删除的字典列表
    del_dicts = []
    if args.del_ind:
        for indexes in args.del_ind:
            del_d = {'index': indexes}
            del_dicts.append(del_d)

    if args.del_kv:
        for data in args.del_kv:
            del_d = {}
            for item in data:
                key, value = item.split('=')
                del_d[key] = value
            del_dicts.append(del_d)
        print(f'LOGGING: Deleted list data: {args.del_kv}, deleted data conversion dictionary data: \n{del_dicts}\n')

    add_dicts = []
    if args.add:
        for data in args.add:
            add_d = {}
            for item in data:
                key, value = item.split('=')
                add_d[key] = value
            add_dicts.append(add_d)
        print(f'LOGGING: Added list data: {args.add} Added data conversion dictionary data: \n{add_dicts}\n')

    replace_dicts = []
    if args.rep:
        for data in args.rep:
            replace_d = {}
            for item in data:
                key, value = item.split('=')
                replace_d[key] = value
            replace_dicts.append(replace_d)
        print(
            f'LOGGING: Replaced list data: {args.rep} Replaced data conversion dictionary data: \n{replace_dicts}\n')

    # 调用execute函数
    execute(input_path, del_dicts, add_dicts, replace_dicts, output_path)


if __name__ == '__main__':
    main()
