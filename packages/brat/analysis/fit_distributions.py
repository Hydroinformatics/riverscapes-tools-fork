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


size = 30000
x = np.arange(size)
y = scipy.int_(np.round_(scipy.stats.vonmises.rvs(5,size=size)*47))
h = plt.hist(y, bins=range(48))

dist_names = ['norm', 'expon']

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