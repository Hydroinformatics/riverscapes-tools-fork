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
inputs = ['iVeg_30EX', 'iVeg100EX', 'iHyd_SPlow', 'iHyd_SP2', 'iGeo_Slope']
xlabels = ['30m Vegetation Suitability', '100m Vegetation Suitability', 'Baseflow (watts/m)', 'Peak Flow (watts/m)', 'Slope (decimal %)']
xbounds = [(0, 4), (0, 4), (0, 15), (0, 1200), (0, 0.8)]
filter_quantiles = [1.0, 1.0, 0.995, 0.95, 0.995]  # quantiles for filtering outliers. set to 1.0 to disable filtering

# Distributions to try fitting (scipy.stats distributions)
dist_names = ['norm', 'expon', 'pareto']
# dist_names = ['norm', 'lognorm', 't', 'expon', 'gamma', 'weibull_min', 'pareto']


def fit_inputs(database: str):
    """Fit the distributions for all inputs in the source database"""
    
    for i, input_var in enumerate(inputs):
        print(f"--- Fitting distributions for {input_var} ---")
        plt.figure(figsize=(10, 6))

        # Load the data from the input source
        with sqlite3.connect(database) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT {input_var} FROM {source_table} WHERE {input_var} IS NOT NULL")
            raw_y = [row[0] for row in cur.fetchall()]

        # Filter outliers
        threshold = np.quantile(raw_y, filter_quantiles[i])
        y = [val for val in raw_y if val <= threshold]
        print(f" -- Max filtered value of {input_var}: {max(y)}")
        
        # Plot the histogram
        h = plt.hist(y, bins=100, density=True, alpha=0.5, label=f"{input_var} Histogram")
        plt.xlim(xbounds[i][0], xbounds[i][1])
        plt.xlabel(xlabels[i])
        plt.title(input_var)
        # Set y-limit to 1.2x the max histogram density to avoid extreme PDF values distorting the plot
        hist_max = max(h[0]) if len(h[0]) > 0 else 1
        plt.ylim(0, hist_max * 1.2)
        
        # High-resolution x values for smooth PDFs
        x = np.linspace(xbounds[i][0], xbounds[i][1], 1000)
            
        for dist_name in dist_names:
            dist = getattr(scipy.stats, dist_name)
            if 'iHyd' in input_var or 'iGeo' in input_var:
                if dist_name == 'norm' or dist_name == 't':
                    continue
            try:
                params = dist.fit(y)
                print(f"- {input_var}: {dist_name}")
                print(f" -- Fitted parameters = {params}")
                arg = params[:-2]
                loc = params[-2]
                scale = params[-1]
                if arg:
                    pdf_fitted = dist.pdf(x, *arg, loc=loc, scale=scale)
                else:
                    pdf_fitted = dist.pdf(x, loc=loc, scale=scale)
                plt.plot(x, pdf_fitted, label=dist_name)
                # fit_tests(y, dist_name, params)

            except Exception as e:
                print(f"Could not fit {dist_name} to variable {input_var}: {e}")
        
        plt.title(f"Input {input_var} Fitted")
        plt.ylim()
        plt.xlim(xbounds[i])
        plt.ylabel("Density")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

    plt.show()
    
def fit_tests(y, dist_name, params):
    # Kolmogorov-Smirnov test
    ks_stat, p_value = scipy.stats.kstest(y, dist_name, args=params)
    print(f" -- KS test statistic = {ks_stat}")
    print(f" -- KS test p-value = {p_value}")

    # Anderson-Darling test
    result = scipy.stats.anderson(y, dist='norm')  # or 'expon', 'logistic', etc.
    print(f" -- Anderson-Darling statistic: {result.statistic}")
    print(f" -- Critical values: {result.critical_values}")
    print(f" -- Significance levels: {result.significance_level}")

    
def main():

    parser = argparse.ArgumentParser(
        description='Fits distributions to input data.'
    )
    parser.add_argument('database', help='Path to a BRAT database (merged okay) with desired inputs.', type=str)
    args = parser.parse_args()

    fit_inputs(args.database)


if __name__ == '__main__':
    main()
