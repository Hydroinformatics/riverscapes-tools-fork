"""
Performs additional analysis on BRAT output data.
Checks for correlation between dam capacity and various other variables.
Currently just prints matplotlib plots and provides explanations.

Evan Hackstadt
July 2025
"""



# TODOs:
    # allow combination of multiple BRAT databases for combined analysis

#imports
import os
import sys
import argparse
import traceback
import sqlite3
import matplotlib.pyplot as plt
import numpy as np


def analyze(database, out_dir):
    print("Analyzing database {}".format(os.path.basename(database)))
    if out_dir is not None:
        print("Output dir provided; saving plots to {}".format(out_dir))

    # > Call analysis functions. Can turn these on or off

    hydro_limitation(database, out_dir)

    suitability_distribution(database, out_dir)
    capacity_distribution(database, out_dir)
    capacity_scatter_plots(database, out_dir)
    capacity_scatter_plots_zoomed(database, out_dir)
    capacity_bar_plots(database, out_dir)
    input_distributions(database, out_dir)


def suitability_distribution(database, out_dir):
    """
    Generate histograms of iVeg_30EX and iVeg100EX (mean veg suitabilities for each reach)
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    vars = {
        'iVeg_30EX': 'Streamside (30m) vegetation suitability',
        'iVeg100EX': 'Riparian (100m) vegetation suitability'
    }

    # Generate histograms
    for var, descr in vars.items():
        var_data = select_var(database, var)
        plt.hist(var_data, bins=10, edgecolor='black')
        plt.xlabel(var)
        plt.title(f"{descr} Distribution")
        print(f"...Plot for {var} generated...")

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(os.path.dirname(out_dir), "{}-hist.png".format(var))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()


def capacity_distribution(database, out_dir):
    """
    Generate two histograms of the dam capacities, one with few bins and one with many
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    histogram_bin_counts = [4, 12, 100, 250]
    capacity_data = select_var(database, 'oCC_EX')

    for num_bins in histogram_bin_counts:
        plt.hist(capacity_data, bins=num_bins, edgecolor='black')
        plt.xlabel('oCC_EX')
        plt.ylabel("Count")
        plt.title("Overall Dam Capacity (oCC_EX) {}-bin Histogram".format(num_bins))
        print("...{}-bin histogram for oCC_EX generated...".format(num_bins))

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(os.path.dirname(out_dir), "oCC_EX-hist-{}bin.png".format(num_bins))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()



def capacity_scatter_plots(database, out_dir):
    """
    Generate scatters of oCC_EX and continuous variables
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    # Variables of interest from ReachAttributes. Can easily be modified.
    x_vars = {
        'oVC_EX': 'Existing Veg FIS Score',
        'iVeg100EX': 'Existing Veg Suitability (100m buffer)',
        'iVeg_30EX': 'Existing Veg Suitability (30m buffer)',
        'iVeg100HPE': 'Historic Veg Suitability (100m buffer)',
        'iVeg_30HPE': 'Historic Veg Suitability (30m buffer)',
        'iGeo_Slope': 'Stream Slope',
        'iGeo_DA': 'Upstream Drainage Area (sq km)',
        'iHyd_SPLow': 'Baseflow Stream Power (watts)',
        'iHyd_SP2': 'Peak Flow Stream Power (watts)'
    }

    # Get dam capacity outputs
    capacity_data = select_var(database, 'oCC_EX')

    # Get each variable, create scatter
    for var, descr in x_vars.items():
        var_data = select_var(database, var)
        
        # generate a plot
        plt.scatter(var_data, capacity_data, s=0.75, marker='.')
        plt.xlabel(var)
        plt.ylabel("Overall Dam Capacity (oCC_EX)")
        plt.title(f"{descr} vs. Dam Capacity")
        print(f"...Plot for {var} generated...")

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(os.path.dirname(out_dir), "{}.png".format(var))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()


def capacity_scatter_plots_zoomed(database, out_dir):
    """
    Generate "zoomed-in" scatters of oCC_EX and certain continuous variables with log-scale x-axis
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    # Variables of interest from ReachAttributes. Can easily be modified.
    x_vars = {
        # variable name: ('description', x-cutoff scalar)
        'iGeo_Slope': ('Stream Slope', 0.20),
        'iHyd_SPLow': ('Baseflow Stream Power (watts)', 0.025),
        'iHyd_SP2': ('Peak Flow Stream Power (watts)', 0.025)
    }

    # Get dam capacity outputs
    capacity_data = select_var(database, 'oCC_EX')

    # Get each variable, create zoomed-in scatter
    for var, info in x_vars.items():
        var_data = select_var(database, var)
        pairs = dict(zip(var_data, capacity_data))

        x_cutoff = (max(var_data) * info[1])   # view the first quarter of the x-axis
        filtered_pairs = {x: y for x, y in pairs.items() if x < x_cutoff}
        print(f"...generating zoomed-in plot for {var} with x cutoff = {x_cutoff}...")
        
        plt.scatter(filtered_pairs.keys(), filtered_pairs.values(), s=0.75, marker='.')
        plt.xlabel(var)
        plt.ylabel("Overall Dam Capacity (oCC_EX)")
        plt.title(f"[subset] {info[0]} vs. Dam Capacity")
        print(f"...Plot for {var} generated...")

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(os.path.dirname(out_dir), "{}-zoomed.png".format(var))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()




def capacity_bar_plots(database, out_dir):
    """
    Generate bar charts for oCC_EX and categorical variables
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    # Variables of interest. Can easily be modified.
    x_vars = {
        # var name: ('description', '(optional) lookup table field', '(optional) lookup table name')
        'RiskID': ('Risk of conflict from damming', 'Name', 'DamRisks'),
        'isPeren': ('If stream is intermittent (0) or perennial (1)', '', ''),
        #'ownership': ('If land is private (PVT) or public (USFS)', '', '')             # this breaks the function currently
    }

    # Get dam capacity outputs
    capacity_data = select_var(database, 'oCC_EX')

    # Get each variable, create scatter
    for var, info in x_vars.items():
        var_data = select_var(database, var)
        categories = list(set(var_data))      # unique categories

        # sort capacity data by category
        categorized_capacities = {}     # {category: [capacities list]}
        capacity_means = []
        for cat in categories:
            categorized_capacities[cat] = []
            for i in range(len(var_data)):      # var_data and capacity_data are parallel
                if var_data[i] == cat:
                    categorized_capacities[cat].append(capacity_data[i])
            # Find mean capacity in each category
            capacity_means.append(np.mean(categorized_capacities[cat]))
        
        # optionally change categories to names from an (ordered) lookup table
        if info[1] != '' and info[2] != '':
            conn = sqlite3.connect(database)
            curs = conn.cursor()
            curs.execute('SELECT {} FROM {}'.format(info[1], info[2]))
            result = curs.fetchall()
            categories = [row[0] for row in result]   # convert to ints from tuples
            curs.close()
         
        # generate a plot
        plt.bar(categories, capacity_means, width=0.7, tick_label=categories)
        plt.xlabel(var)
        plt.ylabel("Mean Dam Capacity (oCC_EX)")
        plt.title(f"{info[0]} vs. Dam Capacity")
        print(f"...Plot for {var} generated...")

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(os.path.dirname(out_dir), "{}.png".format(var))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()
        
        #TODO: also generate a stacked bar plot showing capacity categories, for each var category


def input_distributions(database, out_dir):
    """
    Generate histograms of the distribution of certain input variables
        for reaches with Frequent or Pervasive dams (oCC_EX > 5)
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """
    x_vars = [
        # ('var name', 'description', num_bins, x_scalar)
        # note: set x_scalar to 1.00 if you want the full histogram
        ('iGeo_Slope', 'Stream Slope (deg)', 250, 0.75),
        ('iGeo_DA', 'Upstream Drainage Area (sq km)', 250, 0.05),
        ('iHyd_QLow', 'Baseflow (CFS)', 250, 0.05),
        ('iHyd_Q2', 'Peak Flow (CFS)', 250, 0.05)
    ]

    capacity_data = select_var(database, 'oCC_EX')

    for var, descr, num_bins, x_scalar in x_vars:
        var_data = select_var(database, var)
        # filter data to high capacity
        pairs = dict(zip(var_data, capacity_data))
        filtered_pairs = {var: cap for var, cap in pairs.items() if cap > 5}

        # plot
        plt.hist(filtered_pairs.keys(), bins=num_bins)
        plt.xlabel(descr)
        plt.ylabel('Count')
        plt.title("Distribution of {} at Frequent/Pervasive reaches".format(var))
        print("...{}-bin histogram for {} generated...".format(num_bins, var))

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(os.path.dirname(out_dir), "{}-hist-{}bin.png".format(num_bins))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()

        if x_scalar != 1.00:
            # simply remove pairs past the x-cutoff
            cutoff = max(filtered_pairs.keys())*x_scalar
            filtered_pairs = {var: cap for var, cap in filtered_pairs.items() if var < cutoff}
            # plot
            plt.hist(filtered_pairs.keys(), bins=num_bins)
            plt.xlabel(descr)
            plt.ylabel('Count')
            plt.title("[subset] Distribution of {} at Frequent/Pervasiv reaches".format(var))
            print("...{}-bin histogram for {} generated...".format(num_bins, var))

            if out_dir is not None:
                print(f"...Saving plot to output dir...")
                out_file_path = os.path.join(os.path.dirname(out_dir), "{}-hist-{}bin-zoomed.png".format(var, num_bins))
                plt.savefig(out_file_path)
                plt.close()
            else:
                plt.show()




def hydro_limitation(database, out_dir):
    print("Hydro limitation called.")

    # Report what % of reaches were hydrologically limited
    print("HYDRO_LIMITATION REPORT:")
    oVC_EX = select_var(database, 'oVC_EX')
    oCC_EX = select_var(database, 'oCC_EX')

    num_diff = 0
    for i in range(len(oCC_EX)):
        if oCC_EX[i] != oVC_EX:
            num_diff += 1
    print("> {} ({} percent of watershed) reaches had their suitability limited by hydrology in Combined FIS".format(num_diff, num_diff/len(oCC_EX)))

    #TODO: report what factors limited these reaches (e.g. x% slope limited)??

    # Print histograms of baseflow, peakflow, and slope based on their BRAT FIS cutoffs
    print("...Generating hydrology histograms corresponding to rule cutoffs")
    hist_vars = [
        # 'var_name', 'description', [bins sequence], [labels sequence]
        ('iHyd_SPlow', 'Baseflow stream power (watts)', [0, 160, 185, 10000], ['Can build', 'Probably can build', 'Cannot build']),
        ('iHyd_SP2', 'Peakflow stream power (watts)', [0, 1100, 1400, 2200, 500000], ['Persists', 'Occ Breach', 'Occ Blowout', 'Blowout']),
        ('iGeo_Slope', 'Stream Slope', [0, 0.0026, 0.135, 0.20, 1], ['Flat', 'Can build', 'Probably can build', 'Cannot build'])
    ]

    for var, descr, bins_seq, bin_labels in hist_vars:
        var_data = select_var(database, var)
        plt.hist(var_data, bins=bins_seq, edgecolor='black')
        plt.xlabel(descr)
        plt.ylabel("Count")
        plt.title("Distribution of {} within FIS rule cutoffs".format(var))
        plt.suptitle("Bins (left-to-right): {}".format(bin_labels))
        print("...Cutoff histogram for {} generated...".format(var))

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(os.path.dirname(out_dir), "{}_cutoffs_hist.png".format(var))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()
    

    


def select_var(database, var: str):
    """
    Return column of values for a specified feature from ReachAttributes
    :param database: path to a BRAT database (.gpkg)
    :param var: database name of the feature to be returned"""

    conn = sqlite3.connect(database)
    curs = conn.cursor()
    curs.execute(f'SELECT {var} FROM ReachAttributes')
    result = curs.fetchall()
    var_data = [row[0] for row in result]   # convert to ints from tuples
    curs.close()

    print("Obtained {} {} values from database...".format(len(var_data), var))
    return var_data



def main():
    # TODO: Figure out if argparse can take a variable number of BRAT databases

    parser = argparse.ArgumentParser(
        description='Takes a BRAT databases and performs additional analysis on the output variables in an attempt to identify any patterns.'
    )
    parser.add_argument('database', help='Path to at least one BRAT SQLite database (.gpkg). Add additional paths separated by spaces.', type=str)
    parser.add_argument('-o', '--output', help='(Optional) Path to an output directory where plots will be saved instead of displayed at runtime. If none provided, plots will not be saved.', type=str)
    args = parser.parse_args()
    print(args.database)

    try:
        analyze(args.database, args.output)

    except Exception as ex:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
