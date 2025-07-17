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

    # call analysis functions. can turn these on or off
    capacity_scatter_plots(database, out_dir)
    capacity_bar_plots(database, out_dir)
    coord_scatter_plot(database, out_dir)
    hydro_limitation(database)


def capacity_scatter_plots(database, out_dir):                      #BROKEN: Fix getting oCC_EX means for each category
    """
    Examine patterns between oCC_EX and continuous variables
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    # Variables of interest from ReachAttributes. Can easily be modified.
    x_vars = {
        'NHDPlusID': 'NHDPlus ID',
        'iGeo_Slope': 'Stream segment slope',
        'iVeg100EX': 'Existing Veg Suitability (100m buffer)',
        'iVeg_30EX': 'Existing Veg Suitability (30m buffer)',
        'iVeg100HPE': 'Historic Veg Suitability (100m buffer)',
        'iVeg_30HPE': 'Historic Veg Suitability (30m buffer)',
        'oVC_EX': 'Existing Veg FIS Score',
        'iHyd_SPLow': 'Baseflow Stream Power (watts)',
        'iHyd_SP2': 'Peak Flow Stream Power (watts)',
    }


    conn = sqlite3.connect(database)
    curs = conn.cursor()

    # Get oCC_EX
    curs.execute('SELECT oCC_EX FROM ReachAttributes')
    capacity_data = curs.fetchall()
    print("Obtained {} oCC_EX values from database...".format(len(capacity_data)))
    '''
    # Get each variable, create scatter, analyze correlation
    for var in x_vars:
        curs.execute('SELECT {} FROM ReachAttributes'.format(var))
        var_data = curs.fetchall()
        print("Obtained {} {} values from database...".format(len(var_data), var))

        pairs = dict(zip(var_data, capacity_data))

        # get mean capacity for each unique category
        var_categories = set(var_data)
        capacity_means = np.zeros(len(var_categories))

        for i in range(len(var_categories)):
            capacity_filtered = []
            for cat in pairs:
                if cat == var_categories[i]:
                    capacity_filtered.append(pairs[cat])
            capacity_means[i] = np.mean(capacity_filtered)
            
        
        # generate a plot
        plt.scatter(var_data, capacity_means, s=0.75, marker='.')
        plt.xlabel(var)
        plt.ylabel("Overall Dam Capacity (oCC_EX)")
        plt.title(f"{x_vars[var]} vs. Dam Capacity")

        print(f"...Plot for {var} generated...")
        plt.show()

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(os.path.dirname(out_dir), "{}.png".format(var))
            plt.savefig(out_file_path)
    '''
    curs.close()


def capacity_bar_plots(database, out_dir):
    """
    Examine patterns between oCC_EX and categorical variables
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    # Variables of interest. Can easily be modified.
    vars = {
        'RiskID': 'Risk of conflict from damming',
        'ReachType': 'Type of stream',

    }

    conn = sqlite3.connect(database)
    curs = conn.cursor()

    # Get oCC_EX
    curs.execute('SELECT oCC_EX FROM ReachAttributes')
    capacity_data = curs.fetchall()
    print("Obtained {} oCC_EX values from database...".format(len(capacity_data)))

    # Get each variable, create scatter, analyze correlation
    for var in vars:
        curs.execute('SELECT {} FROM ReachAttributes'.format(var))
        var_data = curs.fetchall()
        print("Obtained {} {} values from database...".format(len(var_data), var))
        
        # generate a plot
        plt.bar(var_data, capacity_data)
        plt.xlabel(var)
        plt.ylabel("Overall Dam Capacity (oCC_EX)")
        plt.title(f"{vars[var]} vs. Dam Capacity")

        print(f"...Plot for {var} generated...")
        plt.show()

        if out_dir is not None:
            print(f"...Saving plot to output dir...")
            out_file_path = os.path.join(os.path.dirname(out_dir), "{}.png".format(var))
            plt.savefig(out_file_path)

    curs.close()


def coord_scatter_plot(database, out_dir):
    """
    Examine spatial distribution of oCC_EX using long & lat
    :param database: path to a BRAT database (.gpkg)
    :param out_dir: optional path to a folder to save plots to
    """

    vars = ['Longitude', 'Latitude']

    conn = sqlite3.connect(database)
    curs = conn.cursor()

    # Get oCC_EX
    curs.execute('SELECT oCC_EX FROM ReachAttributes')
    capacity_data = curs.fetchall()
    print("Obtained {} oCC_EX values from database...".format(len(capacity_data)))

    # Get Long & Lat; plot
    curs.execute('SELECT Longitude FROM Observations')
    long_data = curs.fetchall()
    print("Obtained {} Longitude values from database...".format(len(long_data)))

    curs.execute('SELECT Latitude FROM Observations')
    lat_data = curs.fetchall()
    print("Obtained {} Latitude values from database...".format(len(lat_data)))

    # generate a plot
    plt.scatter(lat_data, long_data, s=1, c=capacity_data, marker='.')
    plt.xlabel('Latitude')
    plt.ylabel("Longitude")
    plt.title(f"Coordinates of Points colored by Capacity")

    print(f"...Plot for Coordinates generated...")
    plt.show()

    if out_dir is not None:
        print(f"...Saving plot to output dir...")
        out_file_path = os.path.join(os.path.dirname(out_dir), "coordinates.png")
        plt.savefig(out_file_path)



    curs.close()


def hydro_limitation(database):
    print("Hydro limitation called.")
    # TODO



def main():
    # TODO: Figure out if argparse can take a variable number of BRAT databases

    parser = argparse.ArgumentParser(
        description='Takes a BRAT databases and performs additional analysis on the output variables in an attempt to identify any patterns.'
    )
    parser.add_argument('database', help='Path to at least one BRAT SQLite database (.gpkg). Add additional paths separated by spaces.', type=str)
    parser.add_argument('-o', '--output', help='(Optional) Path to an output directory where plots will be saved. If none provided, plots will not be saved', type=str)
    args = parser.parse_args()
    print(args.database)

    # For now just use argv
    # print(sys.argv)     # argv[0] is the script name, argv[1:] is database path(s)

    try:
        analyze(args.database, args.output)

    except Exception as ex:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
