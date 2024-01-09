#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : TopGen
@Time    : 2023/3/27 14:12
@Author  : lbfeng
@File    :  to_fastq.py
"""
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO

# 定义序列
seq = Seq("GTTCAGAGTTCTACAGTCCGACGATCNNWNNWGCATCTGCCTCACCTCCA")

# 定义序列记录
seq_record = SeqRecord(seq, id='chr7', description='')

# 将记录保存为fasta格式的文件
SeqIO.write(seq_record, 'chr7.fa', 'fasta')
