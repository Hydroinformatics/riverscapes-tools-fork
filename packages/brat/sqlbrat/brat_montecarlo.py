""" Modified BRAT script for Monte Carlo FIS Sensitivity Analysis

    Evan Hackstadt
    July 2025

    Build a BRAT project by segmenting a river network to a specified
    length and then extract the input values required to run the
    BRAT model for each reach segment from various GIS layers.

    Philip Bailey
    30 May 2019

    Returns:
        [type]: [description]
"""

import os
import traceback
import datetime
import time
import json
from typing import List, Dict
from osgeo import ogr
from rscommons import GeopackageLayer
from rscommons.classes.rs_project import RSMeta, RSMetaTypes
from rscommons.vector_ops import copy_feature_class
from rscommons import Logger, initGDALOGRErrors, RSLayer, RSProject, ModelConfig, dotenv
from rscommons.util import parse_metadata, pretty_duration
from rscommons.build_network import build_network
from rscommons.database import create_database, SQLiteCon
from rscommons.copy_features import copy_features_fields
from rscommons.moving_window import moving_window_dgo_ids
from sqlbrat.utils.vegetation_summary import vegetation_summary
from sqlbrat.utils.vegetation_suitability import vegetation_suitability, output_vegetation_raster
from sqlbrat.utils.vegetation_fis import vegetation_fis
from sqlbrat.utils.combined_fis import combined_fis
from sqlbrat.brat_report import BratReport
from sqlbrat.__version__ import __version__

import argparse
import sys
import sqlite3
import numpy as np
import scipy.stats as stats
from analysis.vegetation_fis_custom import calculate_vegetation_fis_custom
from analysis.combined_fis_custom import calculate_combined_fis_custom

Path = str


# Useful info
input_vars = ['iVeg_30EX', 'iVeg100EX', 'iHyd_SPlow', 'iHyd_SP2', 'iGeo_Slope']

input_dists_sampled = {  # var: (distribution, param1, param2)
    'iVeg_30EX': ('norm', 2.234, 0.5708),
    'iVeg100EX': ('norm', 2.110, 0.3793),
    'iHyd_SPlow': ('expon', 0.0, 3.311),
    'iHyd_SP2': ('expon', 244.0, 302.9),
    'iGeo_Slope': ('expon', 0.0, 0.1878)
}

input_dists_uniform = {   # var: (distribution, param1, param2)
    'iVeg_30EX': ('uniform', 0, 4),
    'iVeg100EX': ('uniform', 0, 4),
    'iHyd_SPlow': ('uniform', 0, 190),
    'iHyd_SP2': ('uniform', 0, 2400),
    'iGeo_Slope': ('uniform', 0, 1)
}

adjustment_dist = { # adjustment: (param1, param2) e.g. (mu, sigma)
    'SPlow_Shift': ('norm', 0.0, 18.5),
    'SP2_Shift': ('norm', 0.0, 200),
    'Slope_Shift': ('norm', 0.0, 0.02),
    'Veg30_Scale': ('norm', 1.0, 0.75),
    'Veg100_Scale': ('norm', 1.0, 0.75),
    'SPlow_Scale': ('norm', 1.0, 0.75),
    'SP2_Scale': ('norm', 1.0, 0.75),
    'Slope_Scale': ('norm', 1.0, 0.75)
}

adj_cols = [
    "Veg30_Shift", "Veg30_Scale", "Veg100_Shift", "Veg100_Scale",
    "SPlow_Shift", "SPlow_Scale", "SP2_Shift", "SP2_Scale", "Slope_Shift", "Slope_Scale"
]


# Database functions
def create_db(database: Path):
    with SQLiteCon(database) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS Simulations(SimID PRIMARY KEY AUTOINCREMENT, Name, Start, End, N_samples)")
        cur.execute(f"CREATE TABLE IF NOT EXISTS SimulationAdjustments(AdjID PRIMARY KEY AUTOINCREMENT, SimID FOREIGN KEY, {', '.join(adj_cols)}, FOREIGN KEY (SimID) REFERENCES Simulations(SimID))")
        cur.execute("CREATE TABLE IF NOT EXISTS InputDistributions(SimID, Var, Distribution, Param1, Param2, FOREIGN KEY (SimID) REFERENCES Simulations(SimID), PRIMARY KEY (SimID, Var))")
        cur.execute("CREATE TABLE IF NOT EXISTS Results(ReachID PRIMARY KEY, SimID, iVeg_30EX, iVeg100EX, iHyd_SPlow, iHyd_SP2, iGeo_Slope, oVC_EX, oCC_EX, FOREIGN KEY (SimID) REFERENCES Simulations(SimID), FOREIGN KEY (ReachID) REFERENCES Reaches(ReachID))")
        cur.execute("CREATE TABLE IF NOT EXISTS Stats(SimID FOREIGN KEY, Mean_Veg30, Mean_Veg100, Mean_SPlow, Mean_SP2, Mean_Slope, Mean_oVC_EX, StDev_oVC_EX, Mean_oCC_EX, StDev_oCC_EX, FOREIGN KEY (SimID) REFERENCES Simulations(SimID))")


# Functions that generate values from distributions

def generate_inputs(n_samples: int, uniform: bool) -> List[Dict[str, float]]:
    """Generate synthetic inputs for the BRAT model based on the specified number of samples and distribution type.
    
    Args:
        n_samples (int): Number of samples to generate.
        uniform (bool): If True, use uniform distributions; otherwise, use Siletz input distributions.
    
    Returns:
        List[Dict[str, float]]: A list of dictionaries containing the generated inputs.
    """

    if uniform:
        input_dists = input_dists_uniform
    else:
        input_dists = input_dists_sampled
    
    inputs = [{var: None for var in input_dists.keys()}] * n_samples
    for i in range(n_samples):
        for var, (dist, param1, param2) in input_dists.items():
            if dist == 'norm':
                inputs[i][var] = np.random.normal(param1, param2)
            elif dist == 'uniform':
                inputs[i][var] = np.random.uniform(param1, param2)
            elif dist == 'expon':
                inputs[i][var] = np.random.exponential(param2) + param1
            else:
                raise ValueError(f"Unknown distribution type: {dist}")
    
    return inputs


def generate_adjustments() -> Dict[str, float]:
    """Generate adjustments for the BRAT model based on predefined distributions.
    
    Returns:
        Dict[str, float]: A dictionary containing the generated adjustments.
    """
    
    adjustments = {}
    for adj, (dist, param1, param2) in adjustment_dist.items():
        if dist == 'norm':
            adjustments[adj] = np.random.normal(param1, param2)
        elif dist == 'uniform':
            adjustments[adj] = np.random.uniform(param1, param2)
        else:
            raise ValueError(f"Unknown distribution type: {dist}")
    
    return adjustments



def brat_montecarlo(n_simulations: int, database: Path, uniform_inputs: bool):
    """
    Perform a Monte Carlo simulation on the Standard BRAT FIS
        :param n_simulations: the number of times to run the simulation
        :param database: path to an existing or new sqlite database to log results. If existing, previous results will not be overwritten.
        :param uniform_inputs: use uniform distributions within bounds to generate inputs if True; otherwise use Siletz input distributions
    """

    # Handle database
    create_db(database)
    with sqlite3.connect(database) as conn:
        cur = conn.cursor()

        # Log the simulation start time
        start_time = datetime.datetime.now()
        cur.execute("INSERT INTO Simulations(Name, Start, N_samples) VALUES (?, ?, ?)", ("Monte Carlo Simulation", start_time, n_simulations))
        sim_id = cur.lastrowid

        # Log the input distributions used
        input_dist = input_dists_uniform if uniform_inputs else input_dists_sampled
        for var, (dist, param1, param2) in input_dist.items():
            cur.execute("INSERT INTO InputDistributions(SimID, Var, Distribution, Param1, Param2) VALUES (?, ?, ?, ?, ?)",
                        (sim_id, var, dist, param1, param2))

        # Generate the synthetic inputs
        input_reaches = generate_inputs(n_simulations, uniform_inputs)

        # Now perform the Monte Carlo simulation on our inputs
        for i in range(n_simulations):
            result_id = i + 1
            sim_results = []

            # Generate and log adjustments for this simulation
            sim_adjustments = generate_adjustments()
            placeholders = ', '.join(['?'] * len(adj_cols))
            insert_stmt = f"INSERT INTO SimulationAdjustments(SimID, {', '.join(adj_cols)}) VALUES (?, {placeholders})"
            cur.executemany(insert_stmt, (sim_id, *[sim_adjustments[col] for col in adj_cols]))

            # Prepare inputs as feature_values to pass to the FIS functions
            # :param feature_values: Dictionary of features keyed by ReachID and values are dictionaries of attributes
            veg_feature_values = {reachi + 1: None for reachi in len(input_reaches)}
            for reachi, reach_dict in enumerate(input_reaches):
                reachid = reachi + 1
                veg_feature_values[reachid] = {'iVeg_30EX': reach_dict['iVeg_30EX'], 'iVeg100Ex': reach_dict['iVeg100EX']}
            
            comb_feature_values = {reachi + 1: None for reachi in len(input_reaches)}
            for reachi, reach_dict in enumerate(input_reaches):
                reachid = reachi + 1
                comb_feature_values[reachid] = {
                    'iHyd_SPlow': reach_dict['iHyd_SPlow'],
                    'iHyd_SP2': reach_dict['iHyd_SP2'],
                    'iGeo_Slope': reach_dict['iGeo_Slope']
                }

            # Run BRAT FIS for this simulation
            calculate_vegetation_fis_custom(veg_feature_values, 'iVeg_30EX', 'iVeg100EX', 'oVC_EX',
                                            sim_adjustments['Veg30_Scale'], sim_adjustments['Veg100_Scale'])
            # veg_feature_values[reachid]['oVC_EX'] now contains oVC output for each reach

            # calculate_combined_fis_custom


            # Log the results of this simulation
            insert_stmt = "INSERT INTO Inputs(iVeg_30EX, iVeg100EX, iHyd_SPlow, iHyd_SP2, iGeo_Slope, oVC_EX, oCC_EX) VALUES (?, ?, ?, ?, ?, ?, ?)"
            cur.executemany(insert_stmt, [(reach['iVeg_30EX'], reach['iVeg100EX'],
                                           reach['iHyd_SPlow'], reach['iHyd_SP2'], reach['iGeo_Slope'],
                                           reach['oVC_EX'], reach['oCC_EX']) for reach in input_reaches])


def main():
    """
    CLI
    """

    parser = argparse.ArgumentParser(
        description='Perform a Monte Carlo simulation on the Standard BRAT FIS:',
        # epilog="This is an epilog"
    )
    parser.add_argument('n_simulations', help='Integer number of simulations to run. This can be a large number.', type=int)
    parser.add_argument('database', help='Path to an SQLite database to store results. Can be an existing monte carlo database, in which case the results will be appended, or a new database.', type=Path)
    parser.add_argument('--uniform_inputs', help='(optional) Include this flag to use uniform distributions to generate the inputs, rather than Siletz distributions', action='store_true', default=False)

    # Substitute patterns for environment varaibles
    args = dotenv.parse_args_env(parser)

    uniform = args.uniform_inputs if args.uniform_inputs else False

    brat_montecarlo(args.n_simulations, args.database, uniform)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
