"""
Performs additional analysis on BRAT output data (a single BRAT db).
This does not have to be the standard brat.gpkg (e.g. could be a merged db) but must contain the variables queried for.
Checks for correlation between dam capacity and various other variables.
Can print or save matplotlib plots.

INSTRUCTIONS:
    Run the script from the terminal, passing args (e.g. path to database) as defined

Evan Hackstadt
July 2025
"""



#imports
import os
import sys
import argparse
import traceback
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerLine2D
import seaborn as sns


def analyze(database, table, out_dir):
    """
    Master function called in main. Calls sub-functions for different analyses.
    :param database: path to a BRAT database containing variables of interest
    :param out_dir: optional path to a folder to save plots to
    """

    print("Analyzing database {}".format(os.path.basename(database)))
    if out_dir is not None:
        print("Output dir provided; saving plots to {}".format(out_dir))

    # > Call analysis functions. Can turn these on or off
    
    input_distributions(database, table, out_dir)
    # output_distribution(database, table, out_dir)
    # capacity_scatter_plots(database, table, out_dir)
    # capacity_scatter_plots_zoomed(database, table, out_dir)
    # hydro_limitation(database, table, out_dir)
    # capacity_bar_plots(database, out_dir)

    print("Analysis complete.")



def input_distributions(database, table, out_dir):
    """
    Generate histograms of the distribution of relevant input variables. Options to filter.
    :param database: path to a BRAT database (.gpkg)
    :param table: table to select data from in the database
    :param out_dir: optional path to a folder to save plots to
    """
    print("> FUNCTION: input_distributions()")

    x_vars = [
        # ('var name', 'description', num_bins, log_scale, cutoff_val)
        # note: log_scale and cutoff_val optional, keep as False and None if you don't want additional zoomed-in histograms
        ('iVeg_30EX', '30m Vegetation Suitability', 60, False, None),
        ('iVeg100EX', '100m Vegetation Suitability', 60, False, None),
        ('iHyd_SPLow', 'Baseflow (watts/m)', 50, True, 10),
        ('iHyd_SP2', 'Peak Flow (watts/m)', 75, True, 1500),
        ('iGeo_Slope', 'Stream Slope (decimal %)', 'auto', False, None)
    ]

    kde_switch = False

    for var, descr, num_bins, log, cutoff_val in x_vars:
        var_data = select_var(database, var, table)

        # plot raw data
        sns.histplot(data=var_data, bins=num_bins, kde=kde_switch)
        plt.xlabel(descr)
        plt.ylabel('Count')
        plt.title("Distribution of {} in Siletz Watershed".format(var))
        print("...{}-bin histogram for {} generated...".format(num_bins, var))

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(out_dir, "input-distribution-{}.png".format(var))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()

        # also generate an additional log-scale histogram if requested
        if log:
            print(f"Log-scale histogram also requested for {var}. Plotting...")
            sns.histplot(data=var_data, bins=num_bins, kde=kde_switch, log_scale=log)
            plt.xlabel(descr)
            plt.ylabel('Count')
            plt.title("Log-Scale Distribution of {} in Siletz Watershed".format(var))

            if out_dir is not None:
                print("...Saving {}-bin log-scale histogram for {}...".format(num_bins, var))
                out_file_path = os.path.join(out_dir, "input-distribution-{}-log.png".format(var))
                plt.savefig(out_file_path)
                plt.close()
            else:
                plt.show()

        # also generate an additional cut-off histogram if requested
        if cutoff_val:
            filtered_var_data = [val for val in var_data if val <= cutoff_val]
            print(f"Cut-off at {cutoff_val} histogram also requested for {var}. Plotting...")
            sns.histplot(data=filtered_var_data, bins=num_bins, kde=kde_switch)
            plt.xlabel(descr)
            plt.ylabel('Count')
            plt.title("Filtered Distribution of {} in Siletz Watershed".format(var))

            if out_dir is not None:
                print("...Saving {}-bin cut-off histogram for {}...".format(num_bins, var))
                out_file_path = os.path.join(out_dir, "input-distribution-{}-zoomed.png".format(var))
                plt.savefig(out_file_path)
                plt.close()
            else:
                plt.show()


def output_distribution(database, table, out_dir):
    """
    Generate two histograms of the dam capacities, one with few bins and one with many
    :param database: path to a BRAT database (.gpkg)
    :param table: table to select data from in the database
    :param out_dir: optional path to a folder to save plots to
    """
    print("> FUNCTION: output_distribution()")

    histogram_bin_counts = [4, 12, 24, 50]
    capacity_data = select_var(database, 'oCC_EX', table)

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



def capacity_scatter_plots(database, table, out_dir):
    """
    Generate scatters of oCC_EX vs. continuous variables
    :param database: path to a BRAT database (.gpkg)
    :param table: table to select data from in the database
    :param out_dir: optional path to a folder to save plots to
    """
    print("> FUNCTION: capacity_scatter_plots()")

    # Variables of interest from ReachAttributes. Can easily be modified.
    x_vars = {
        'oVC_EX': 'Existing Veg FIS Score',
        'iVeg100EX': 'Existing Veg Suitability (100m buffer)',
        'iVeg_30EX': 'Existing Veg Suitability (30m buffer)',
        'iGeo_Slope': 'Stream Slope',
        # 'iGeo_DA': 'Upstream Drainage Area (sq km)',
        'iHyd_SPLow': 'Baseflow Stream Power (watts)',
        'iHyd_SP2': 'Peak Flow Stream Power (watts)'
    }

    # Get dam capacity outputs
    capacity_data = select_var(database, 'oCC_EX', table)

    # Get each variable, create scatter
    for var, descr in x_vars.items():
        var_data = select_var(database, var, table)
        
        # generate a plot
        plt.scatter(var_data, capacity_data, s=0.75, marker='.')
        # sns.scatterplot(x=var_data, y=capacity_data, marker='.', alpha=0.75)
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


def capacity_scatter_plots_zoomed(database, table, out_dir):
    """
    Generate "zoomed-in" scatters of oCC_EX and certain continuous variables with log-scale x-axis
    :param database: path to a BRAT database (.gpkg)
    :param table: table to select data from in the database
    :param out_dir: optional path to a folder to save plots to
    """
    print("> FUNCTION: capacity_scatter_plots_zoomed()")

    # Variables of interest from ReachAttributes. Can easily be modified.
    x_vars = {
        # variable name: ('description', x-cutoff scalar)
        'iHyd_SPLow': ('SPLow baseflow (watts/m)', 0.025),
        'iHyd_SP2': ('Peak Flow Stream Power (watts/m)', 0.025),
        'iGeo_Slope': ('Stream Slope', 0.20)
    }

    # Get dam capacity outputs
    capacity_data = select_var(database, 'oCC_EX', table)

    # Get each variable, create zoomed-in scatter
    for var, info in x_vars.items():
        var_data = select_var(database, var, table)
        pairs = dict(zip(var_data, capacity_data))

        x_cutoff = (max(var_data) * info[1])   # apply the x-scalar
        filtered_pairs = {x: y for x, y in pairs.items() if x < x_cutoff}
        print(f"...generating zoomed-in plot for {var} with x cutoff = {x_cutoff}...")
        
        plt.scatter(filtered_pairs.keys(), filtered_pairs.values(), s=0.75, marker='.')
        # sns.scatterplot(x=filtered_pairs.keys(), y=filtered_pairs.values(), marker='.', alpha=0.75)
        plt.xlabel(var)
        plt.ylabel("Overall Dam Capacity (oCC_EX)")
        plt.title(f"{info[0]} vs. Dam Capacity")
        print(f"...Plot for {var} generated...")

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(out_dir, "scatter-{}-zoomed.png".format(var))
            plt.savefig(out_file_path)
            plt.close()
        else:
            plt.show()


def hydro_limitation(database, table, out_dir):
    """
    Analyze how hydro parameters (baseflow, peakflow, slope) limited the vegetative capacity.
    Reports # and % of reaches limited; generates colored scatters; generates summary scatter
    :param database: path to a BRAT database (.gpkg)
    :param table: table to select data from in the database
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
            {'label': 'Can build', 'color': 'b', 'min': 0, 'max': 160, 'limit': 0},
            {'label': 'Probably can build', 'color': 'y', 'min': 160, 'max': 185, 'limit': 1},
            {'label': 'Cannot build', 'color': 'r', 'min': 185, 'limit': 2}
        ],
        'iHyd_SP2': [
            {'label': 'Persists', 'color': 'b', 'min': 0, 'max': 1100, 'limit': 0},
            {'label': 'Occasional Breach', 'color': 'g', 'min': 1100, 'max': 1400, 'limit': 1},
            {'label': 'Occasional Blowout', 'color': 'y', 'min': 1400, 'max': 2200, 'limit': 1},
            {'label': 'Blowout', 'color': 'r', 'min': 2200, 'limit': 2}
        ],
        'iGeo_Slope': [
            {'label': 'Flat', 'color': 'c', 'min': 0, 'max': 0.0026, 'limit': 0},
            {'label': 'Can build', 'color': 'b', 'min': 0.0026, 'max': 0.135, 'limit': 0},
            {'label': 'Probably can build', 'color': 'g', 'min': 0.135, 'max': 0.20, 'limit': 1},
            {'label': 'Cannot build', 'color': 'r', 'min': 0.20, 'limit': 2}
        ]
    }

    # Report what % of reaches were hydrologically limited
    print("HYDRO_LIMITATION REPORT:")
    oVC_EX = select_var(database, 'oVC_EX', table)
    oCC_EX = select_var(database, 'oCC_EX', table)

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
        var_data = select_var(database, var, table)
        var_cats = [None] * len(var_data)
        # colors = []

        # for each hydro value, color it based on its category
        for i in range(len(oCC_EX)):
            for cat in var_cat_list:
                categorized = False
                min_val = cat['min'] if 'min' in cat else None
                max_val = cat['max'] if 'max' in cat else None
                if (min_val is None or var_data[i] >= min_val) and (max_val is None or var_data[i] < max_val):
                    var_cats[i] = cat['label']
                    # colors.append(cat['color'])
                    categorized = True
                    break
            if not categorized:     # assign last category if logic failed
                var_cats[i] = cat['label']
                # colors.append(cat['color'])

        data = pd.DataFrame(zip(oVC_EX, oCC_EX, var_cats), columns=['oVC', 'oCC', 'category'])
        
        # generate a plot
        # plt.scatter(oVC_EX, oCC_EX, s=0.75, marker='.', c=var_cats, alpha=0.5)
        hue_order = [cat['label'] for cat in var_cat_list]
        palette = sns.color_palette("muted")
        custom_palette = [palette[9], palette[2], palette[1], palette[3]]
        if var == 'iGeo_Slope':
            custom_palette = [palette[2], palette[9], palette[1], palette[3]]   # swap blue and green
        
        plt.figure(figsize=(8,8))
        sns.scatterplot(data=data, x='oVC', y='oCC', hue='category', hue_order=hue_order,
                        s=15, edgecolor='none', marker='.', alpha=0.6, palette=custom_palette)
        plt.grid(True, alpha=0.1)
        plt.legend(title=f'{var} Categories', markerscale=3, 
               handler_map={plt.Line2D: HandlerLine2D(update_func=change_alpha)})
        # plt.plot([0, 40], [0, 40], color='black', linestyle='--', label='1:1 line', alpha=0.33)     # add y=x line
        plt.xlabel('oVC_EX (Veg FIS Capacity)')
        plt.ylabel("oCC_EX (Overall FIS Capacity)")
        plt.title(f"Veg Capacity vs. Overall Capacity - {var}")
        print(f"...Plot for {var} generated...")

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(out_dir, "hydro-limit-{}-coded.png".format(var))
            plt.savefig(out_file_path, dpi=600)
            plt.close()
        else:
            plt.show()
   
    # Generate summary oVC vs. oCC scatter, color-coded by most limiting factor
    print("Generating summary scatter:")
    
    # Pre-fetch all variable arrays for efficiency and correctness
    var_data_dict = {var: select_var(database, var, table) for var in categories.keys()}
    limiting_cats = ["None"] * len(oCC_EX)
    for i in range(len(oCC_EX)):
        cat_severities = {}
        for var, var_cat_list in categories.items():
            value = var_data_dict[var][i]
            var_cat_limit = None
            for cat in var_cat_list:
                min_val = cat['min'] if 'min' in cat else None
                max_val = cat['max'] if 'max' in cat else None
                if (min_val is None or value >= min_val) and (max_val is None or value < max_val):
                    var_cat_limit = cat['limit']
                    break
            cat_severities[var] = var_cat_limit
            
        # for this reach, record the most limiting category or categories as a string
        max_severity = max(cat_severities.values())
        if max_severity > 0.0:
            limiting_cats[i] = ', '.join([cat[cat.find("_")+1:] for cat, val in cat_severities.items() if val == max_severity])
        else:
            limiting_cats[i] = 'None'

    data = pd.DataFrame(zip(oVC_EX, oCC_EX, limiting_cats), columns=['oVC', 'oCC', 'limitation'])
    
    # generate a plot
    hue_order = ['None'] + [cat for cat in data['limitation'].unique() if cat != 'None']
    plt.figure(figsize=(8,8))
    sns.scatterplot(data=data, x='oVC', y='oCC', hue='limitation',
                    hue_order=hue_order, s=5, edgecolor='none', alpha=0.6)
    plt.grid(True, alpha=0.1)
    plt.legend(title=f'Most Limiting Variable(s)', markerscale=3, 
               handler_map={plt.Line2D: HandlerLine2D(update_func=change_alpha)})
    # make legend colors opaque
    plt.xlabel('oVC_EX (Veg FIS Capacity)')
    plt.ylabel("oCC_EX (Overall FIS Capacity)")
    plt.title(f"Hydrologic Limitation of Veg Capacity")
    print(f"...Summary scatter generated...")

    if out_dir is not None:
        print(f"...Saving plot to output dir...")
        out_file_path = os.path.join(out_dir, "hydro-limit-summary.png")
        plt.savefig(out_file_path, dpi=600)
        plt.close()
    else:
        plt.show()
    
    

def capacity_bar_plots(database, out_dir):
    """
    Generate bar charts for oCC_EX and categorical variables
    :param database: path to a BRAT database containing variables of interest
    :param out_dir: optional path to a folder to save plots to
    """
    print("> FUNCTION: capacity_bar_plots()")

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
    

    
# HELPER functions

def select_var(database: str, var: str, table: str = "ReachAttributes"):
    """
    Utility function to return column of values for a specified feature from specified table
    :param database: path to a BRAT database (.gpkg)
    :param var: database name of the feature to be returned"""

    conn = sqlite3.connect(database)
    curs = conn.cursor()
    curs.execute(f'SELECT {var} FROM {table}')
    result = curs.fetchall()
    var_data = [row[0] for row in result]   # convert to ints from tuples
    curs.close()

    print("Obtained {} {} values from database...".format(len(var_data), var))
    return var_data


def change_alpha(handle, original):
    handle.update_from(original)
    handle.set_alpha(1)
    handle.set_marker('.')



def main():

    parser = argparse.ArgumentParser(
        description='Takes a BRAT database and performs additional analysis on the output variables in an attempt to identify any patterns.'
    )
    parser.add_argument('database', help='Path to at least one BRAT SQLite database (.gpkg). Add additional paths separated by spaces.', type=str)
    parser.add_argument('-t', '--table', help='(Optional) Table to query in the provided database. Defaults to ReachAttributes, but use CombinedOutputs for merged dbs.', type=str, default='ReachAttributes')
    parser.add_argument('-o', '--output', help='(Optional) Path to an output directory where plots will be saved instead of displayed at runtime. If none provided, plots will not be saved.', type=str)
    args = parser.parse_args()
    print(args.database)

    try:
        analyze(args.database, args.table, args.output)

    except Exception as ex:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
