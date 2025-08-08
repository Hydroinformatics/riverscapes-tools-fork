"""
Finds the best-fit distribution to a given histogram (e.g. for input distributions).
Uses scipy's fit() (MLE method), then evaluates with the Kolmogorov-Smirnov test

INSTRUCTIONS:


Evan Hackstadt
August 2025
"""

import matplotlib.pyplot as plt
import numpy as np
import scipy
import scipy.stats
import sqlite3


# --- CONFIGURATION ---

# Path to data from which to derive the distribution (e.g. brat-all-siletz-custom.db)
source_db = ''
source_table = 'CombinedOutputs'  # TABLE NAME in the source database

inputs = [
    'iVeg_30EX',
    'iVeg100EX',
    'iHyd_SPlow',
    'iHyd_SP2',
    'iGeo_Slope'
]

dist_names = ['norm', 'expon']  # try these to fit


def fit_inputs():
    """Fit the distributions for all inputs in the source database"""
    for input in inputs:
        fit_distribution(input)


def fit_distribution(input):

    # Load the data from the input source
    with sqlite3.connect(source_db) as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT {input} FROM {source_table} WHERE {input} IS NOT NULL")
        y = [row[0] for row in cur.fetchall()]
        x = range(len(y))
        size = len(y)

    # Plot the histogram
    h = plt.hist(y, bins=50)

    for dist_name in dist_names:
        dist = getattr(scipy.stats, dist_name)
        params = dist.fit(y)
        arg = params[:-2]
        loc = params[-2]
        scale = params[-1]
        if arg:
            pdf_fitted = dist.pdf(x, *arg, loc=loc, scale=scale) * size
        else:
            pdf_fitted = dist.pdf(x, loc=loc, scale=scale) * size
        plt.plot(pdf_fitted, label=dist_name)
        plt.xlim(0,47)
    plt.legend(loc='upper right')
    plt.show()

    # return []