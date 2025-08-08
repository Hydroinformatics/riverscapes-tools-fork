"""
Finds the best-fit distribution to a given histogram (e.g. for input distributions).
Uses scipy's fit() (MLE method), then evaluates with the Kolmogorov-Smirnov test.
Code modified from https://stackoverflow.com/questions/6620471/fitting-empirical-distribution-to-theoretical-ones-with-scipy

INSTRUCTIONS:
    Run the script from the command line, passing in the path to your source database.

Evan Hackstadt
August 2025
"""



''' ——— UNFINISHED ——— '''



import sys
import argparse
import matplotlib.pyplot as plt
import numpy as np
import scipy
import scipy.stats
import sqlite3


# --- NON-CLI CONFIGURATION - SET MANUALLY ---

# Path to data from which to derive the distribution (e.g. brat-all-siletz-custom.db)
source_table = 'CombinedOutputs'  # TABLE NAME in the source database

# Parallel lists
inputs = ['iVeg_30EX', 'iVeg100EX', 'iHyd_SPlow', 'iHyd_SP2', 'iGeo_Slope',]
x_maxes = [(0, 4), (0, 4), (0, 75), (0, 2000), (0, 1.0)]
filter_quantiles = [1.0, 1.0, 0.995, 0.95, 0.995]  # quantiles for filtering outliers. set to 1.0 to disable filtering

# Distributions to try fitting (scipy.stats distributions)
dist_names = ['norm', 'expon', 'rayleigh']


def fit_inputs(database: str):
    """Fit the distributions for all inputs in the source database"""
    
    for input_var, xlim, quantile in zip(inputs, x_maxes, filter_quantiles):
        print(f"Fitting distributions for {input_var}...")
        plt.figure(figsize=(10, 6))

        # Load the data from the input source
        with sqlite3.connect(database) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT {input_var} FROM {source_table} WHERE {input_var} IS NOT NULL")
            raw_y = [row[0] for row in cur.fetchall()]

        # Filter outliers
        threshold = np.quantile(raw_y, quantile)
        y = [val for val in raw_y if val <= threshold]
        print(f"Max FILTERED value of {input_var}: {max(y)}")
        
        # Plot the histogram
        h = plt.hist(y, bins=100, density=True, alpha=0.5, label=f"{input_var} Histogram")
        plt.xlim(xlim[0], xlim[1])
        plt.title(input_var)
        
        # High-resolution x values for smooth PDFs
        x = np.linspace(xlim[0], xlim[1], 1000)

        for dist_name in dist_names:
            print(f"Fitting {dist_name} distribution to {input_var}...")
            dist = getattr(scipy.stats, dist_name)
            try:
                params = dist.fit(y)
                print(f"Fitted parameters for {dist_name}: {params}")
                arg = params[:-2]
                loc = params[-2]
                scale = params[-1]
                if arg:
                    pdf_fitted = dist.pdf(x, *arg, loc=loc, scale=scale)
                else:
                    pdf_fitted = dist.pdf(x, loc=loc, scale=scale)
                plt.plot(x, pdf_fitted, label=dist_name)
            except Exception as e:
                print(f"Could not fit {dist_name} to variable {input_var}: {e}")
        
        plt.title(f"Variable {input_var} Fitted")
        plt.xlim(xlim)
        plt.legend(loc='upper right')
        plt.ylabel("Density")
        plt.grid(True)
        plt.tight_layout()
        
    plt.show()
    
    
def main():

    parser = argparse.ArgumentParser(
        description='Fits distributions to input data.'
    )
    parser.add_argument('database', help='Path to a BRAT database (merged okay) with desired inputs.', type=str)
    args = parser.parse_args()

    fit_inputs(args.database)


if __name__ == '__main__':
    main()
