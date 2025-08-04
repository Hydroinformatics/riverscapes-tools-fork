"""
Performs additional analysis on BRAT output data (a single BRAT database).
Checks for correlation between dam capacity and various other variables.
Can print or save matplotlib plots.

INSTRUCTIONS:
    Run the script from the terminal, passing args (e.g. path to database) as defined

Evan Hackstadt
July 2025
"""



# TODO:
    # clean up: too many graphs; decide which are relevant

#imports
import os
import sys
import argparse
import traceback
import sqlite3
import matplotlib.pyplot as plt
import numpy as np


def analyze(database, out_dir):
    """
    Master function called in main. Calls sub-functions for different analyses.
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """
    print("Analyzing database {}".format(os.path.basename(database)))
    if out_dir is not None:
        print("Output dir provided; saving plots to {}".format(out_dir))

    # > Call analysis functions. Can turn these on or off
    
    suitability_distribution(database, out_dir)
    input_distributions(database, out_dir)
    output_distribution(database, out_dir)
    capacity_scatter_plots(database, out_dir)
    capacity_scatter_plots_zoomed(database, out_dir)
    hydro_limitation(database, out_dir)
    # capacity_bar_plots(database, out_dir)

    print("Analysis complete.")


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
            out_file_path = os.path.join(out_dir, "suitability-distribution-{}.png".format(var))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()


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
        ('iHyd_SPLow', 'Baseflow (watts)', 50, 1.00),
        ('iHyd_SP2', 'Peak Flow (watts)', 50, 0.5),
        ('iGeo_Slope', 'Stream Slope', 50, 1.00),
        ('iGeo_DA', 'Upstream Drainage Area (sq km)', 50, 0.005)
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
            out_file_path = os.path.join(out_dir, "input-distribution-{}.png".format(var))
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
            plt.title("[subset] Distribution of {} at Frequent/Pervasive reaches".format(var))
            print("...{}-bin histogram for {} generated...".format(num_bins, var))

            if out_dir is not None:
                print(f"...Saving plot to output dir...")
                out_file_path = os.path.join(out_dir, "input-distribution-{}-zoomed.png".format(var))
                plt.savefig(out_file_path)
                plt.close()
            else:
                plt.show()


def output_distribution(database, out_dir):
    """
    Generate two histograms of the dam capacities, one with few bins and one with many
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    histogram_bin_counts = [4, 12, 24, 50]
    capacity_data = select_var(database, 'oCC_EX')

    for num_bins in histogram_bin_counts:
        plt.hist(capacity_data, bins=num_bins, edgecolor='black')
        plt.xlabel('oCC_EX')
        plt.ylabel("Count")
        plt.title("Overall Dam Capacity (oCC_EX) {}-bin Histogram".format(num_bins))
        print("...{}-bin histogram for oCC_EX generated...".format(num_bins))

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(out_dir, "output-distribution-{}bin.png".format(num_bins))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()



def capacity_scatter_plots(database, out_dir):
    """
    Generate scatters of oCC_EX vs. continuous variables
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    # Variables of interest from ReachAttributes. Can easily be modified.
    x_vars = {
        'oVC_EX': 'Existing Veg FIS Score',
        'iVeg100EX': 'Existing Veg Suitability (100m buffer)',
        'iVeg_30EX': 'Existing Veg Suitability (30m buffer)',
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
            out_file_path = os.path.join(out_dir, "scatter-{}.png".format(var))
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
        'iHyd_SPLow': ('Baseflow Stream Power (watts)', 0.025),
        'iHyd_SP2': ('Peak Flow Stream Power (watts)', 0.025),
        'iGeo_Slope': ('Stream Slope', 0.20)
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
            out_file_path = os.path.join(out_dir, "scatter-{}-zoomed.png".format(var))
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
            out_file_path = os.path.join(out_dir, "bar-{}.png".format(var))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()




def hydro_limitation(database, out_dir):
    """
    Analyze how hydro parameters (baseflow, peakflow, slope) limited the vegetative capacity.
    Reports # and % of reaches limited; generates colored scatters; generates cutoff-based histograms
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    # Hydrologic variables of interest (inputs into the Combined FIS)

    x_vars = {
        'iHyd_SPlow': 'Baseflow stream power (watts)',
        'iHyd_SP2': 'Peakflow stream power (watts)',
        'iGeo_Slope': 'Stream Slope'
    }
    categories = {  # var: [ {label, color, min, max}, ... ]
        'iHyd_SPlow': [
            {'label': 'Can build', 'color': 'b', 'min': 0, 'max': 160},
            {'label': 'Probably can build', 'color': 'y', 'min': 160, 'max': 185},
            {'label': 'Cannot build', 'color': 'r', 'min': 185}
        ],
        'iHyd_SP2': [
            {'label': 'Persists', 'color': 'b', 'min': 0, 'max': 1100},
            {'label': 'Occasional Breach', 'color': 'g', 'min': 1100, 'max': 1400},
            {'label': 'Occasional Blowout', 'color': 'y', 'min': 1400, 'max': 2200},
            {'label': 'Blowout', 'color': 'r', 'min': 2200}
        ],
        'iGeo_Slope': [
            {'label': 'Flat', 'color': 'c', 'min': 0, 'max': 0.0026},
            {'label': 'Can build', 'color': 'b', 'min': 0.0026, 'max': 0.135},
            {'label': 'Probably can build', 'color': 'g', 'min': 0.135, 'max': 0.20},
            {'label': 'Cannot build', 'color': 'r', 'min': 0.20, 'max': 1}
        ]
    }


    # Report what % of reaches were hydrologically limited
    print("HYDRO_LIMITATION REPORT:")
    oVC_EX = select_var(database, 'oVC_EX')
    oCC_EX = select_var(database, 'oCC_EX')

    num_diff = 0
    for i in range(len(oCC_EX)):
        if oCC_EX[i] != oVC_EX[i]:
            num_diff += 1
    perc_diff = round(100 * num_diff / len(oCC_EX), 2)
    print("> Of {} reaches, {} ({} percent) had their suitability limited by hydrology in Combined FIS".format(len(oCC_EX), num_diff, perc_diff))

    plt.pie([num_diff, len(oCC_EX) - num_diff], labels=['Limited by Hydrology', 'Not Limited by Hydrology'], autopct='%1.1f%%')
    if out_dir is not None:
        print(f"...Saving plot to output dir...")
        out_file_path = os.path.join(out_dir, "hydro-limit-pie.png")
        plt.savefig(out_file_path)
        plt.close()
    else:
        plt.show()

    # Generate color-coded oVC vs. oCC scatters to identify clusters & limiting factors
    print("Generating color-coded scatters:")
    for var, var_cat_list in categories.items():
        var_data = select_var(database, var)
        colors = []

        # for each value, replace it with the correct category label
        for i in range(len(var_data)):
            for cat in var_cat_list:
                label = cat['label']
                min = cat['min'] if 'min' in cat else None
                max = cat['max'] if 'max' in cat else None
                if (min is None or var_data[i] >= min) and (max is None or var_data[i] < max):
                    var_data[i] = label
                    colors.append(cat['color'])
                    break

        # generate a plot
        plt.scatter(oVC_EX, oCC_EX, s=0.75, marker='.', c=colors, alpha=0.5)
        for cat in var_cat_list:
            plt.scatter([], [], c=cat['color'], label=cat['label'])
        plt.legend(title=f'{var} Categories')
        plt.xlabel('oVC_EX (Veg FIS Capacity)')
        plt.ylabel("oCC_EX (Overall FIS Capacity)")
        plt.title(f"Veg Capacity vs. Overall Capacity - {var}")
        print(f"...Plot for {var} generated...")

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(out_dir, "hydro-limit-{}-coded.png".format(var))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()
    

    


def select_var(database, var: str):
    """
    Utility function to return column of values for a specified feature from ReachAttributes
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
