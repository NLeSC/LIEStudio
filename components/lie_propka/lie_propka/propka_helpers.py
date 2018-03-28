# -*- coding: utf-8 -*-

"""
file: propka_helpers.py

Helper functions to parse PROPKA output
"""

from pandas import DataFrame


def parse_propka_pkaoutput(pkafile):
    """
    Parse PROPKA .pka output

    Extract pka SUMMARY block and parse to Pandas dataframe

    :param pkafile: pka file
    :type pkafile:  :py:str

    :return:        Pandas DataFrame
    """

    output = []
    with open(pkafile, 'r') as pkf:
        p = None
        for line in pkf.readlines():
            if line.startswith('SUMMARY OF THIS PREDICTION'):
                p = 1
                continue
            if line.startswith('------'):
                p = None
                continue
            if isinstance(p, int):
                if p <= 0:
                    output.append(line.split())
                p -= 1

    df = DataFrame(output)
    if df.empty:
        return df

    if df.shape[1] == 5:
        df.columns = ['resname', 'resnum', 'chain', 'pKa', 'model-pKa']
    else:
        df.columns = ['resname', 'resnum', 'chain', 'pKa', 'model-pKa', 'lig-attype']

    # Convert dtypes
    df['pKa'] = df['pKa'].astype(float)
    df['model-pKa'] = df['model-pKa'].astype(float)

    return df
