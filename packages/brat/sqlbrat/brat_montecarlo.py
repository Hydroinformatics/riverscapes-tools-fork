""" Modified BRAT script for Monte Carlo FIS Sensitivity Analysis

    Evan Hackstadt
    July 2025

    Build a BRAT project by segmenting a river network to a specified
    length and then extract the input values required to run the
    BRAT model for each reach segment from various GIS layers.

    INSTRUCTIONS:
        From the command line, with venv active, in /packages/brat/
        Run:
            $ python setup.py build
            $ python setup.py install
            $ brat_montecarlo [args]
        For help, run:
            $ brat_montecarlo -h
"""


import os
import argparse
import sys
from typing import List, Dict
import datetime
import statistics
import sqlite3
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
from analysis.vegetation_fis_custom import calculate_vegetation_fis_custom
from analysis.combined_fis_custom import calculate_combined_fis_custom
from sqlbrat.__version__ import __version__

Path = str


# Useful info
input_vars = ['iVeg_30EX', 'iVeg100EX', 'iHyd_SPLow', 'iHyd_SP2', 'iGeo_Slope']

input_dists_sampled = {  # var: (distribution, [params])
    'iVeg_30EX': ('norm', [2.234, 0.5708]),
    'iVeg100EX': ('norm', [2.110, 0.3793]),
    'iHyd_SPLow': ('expon', [0.0, 3.311]),
    'iHyd_SP2': ('expon', [244.0, 302.9]),
    # 'iGeo_Slope': ('expon', [0.0, 0.1878])
    'iGeo_Slope': ('pareto', [2.375, -0.3477, 0.3477])
}

input_dists_uniform = {   # var: (distribution, [params])
    'iVeg_30EX': ('uniform', [0, 4]),
    'iVeg100EX': ('uniform', [0, 4]),
    'iHyd_SPLow': ('uniform', [0, 190]),
    'iHyd_SP2': ('uniform', [0, 2400]),
    'iGeo_Slope': ('uniform', [0, 1])
}

adjustment_dist = {
    # adjustment: (dist, [params])
    #             truncnorm: mu, sigma, left_bound, right_bound
    'SPLow_Shift': ('truncnorm', [0.0, 18.5, -135, 135]),
    'SP2_Shift': ('truncnorm', [0.0, 200, -900, 900]),
    'Slope_Shift': ('truncnorm', [0.0, 0.02, -0.10, 0.10]),
    'Veg30_Scale': ('truncnorm', [1.0, 0.75, 0.5, 2.0]),
    'Veg100_Scale': ('truncnorm', [1.0, 0.75, 0.5, 2.0]),
    'SPLow_Scale': ('truncnorm', [1.0, 0.75, 0.5, 2.0]),
    'SP2_Scale': ('truncnorm', [1.0, 0.75, 0.5, 2.0]),
    'Slope_Scale': ('truncnorm', [1.0, 0.75, 0.5, 2.0])
}

adjustments = [
    "Veg30_Scale", "Veg100_Scale", "SPLow_Shift", "SPLow_Scale",
    "SP2_Shift", "SP2_Scale", "Slope_Shift", "Slope_Scale"
]

input_stat_cols = ["AVG_iVeg_30EX", "AVG_iVeg100EX", "AVG_iHyd_SPLow", "AVG_iHyd_SP2", "AVG_iGeo_Slope", "AVG_oVC_EX", "StDev_oVC_EX", "AVG_oCC_EX", "StDev_oCC_EX"]
result_stat_cols = ["AVG_oVC_EX", "StDev_oVC_EX", "AVG_oCC_EX", "StDev_oCC_EX"]


# HELPER FUNCTIONS

def create_db(database: Path):
    with sqlite3.connect(database) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        
        cur.execute("CREATE TABLE IF NOT EXISTS Simulations(SimID INTEGER PRIMARY KEY AUTOINCREMENT, Name, Start, End, N_Inputs, N_Simulations)")
        cur.execute("CREATE TABLE IF NOT EXISTS InputDistributions(SimID, Var, Distribution, Parameters, FOREIGN KEY (SimID) REFERENCES Simulations(SimID), PRIMARY KEY (SimID, Var))")
        cur.execute("CREATE TABLE IF NOT EXISTS AdjustmentDistributions(SimID, Adjustment, Distribution, Parameters, FOREIGN KEY (SimID) REFERENCES Simulations(SimID), PRIMARY KEY (SimID, Adjustment))")
        cur.execute(f"CREATE TABLE IF NOT EXISTS Inputs(ReachID INTEGER PRIMARY KEY, SimID, {', '.join(input_vars)}, FOREIGN KEY (SimID) REFERENCES Simulations(SimID))")
        cur.execute(f"CREATE TABLE IF NOT EXISTS Adjustments(AdjID INTEGER PRIMARY KEY AUTOINCREMENT, SimID INTEGER, {', '.join(adjustments)}, FOREIGN KEY (SimID) REFERENCES Simulations(SimID))")
        cur.execute(f"CREATE TABLE IF NOT EXISTS Results(ResultID INTEGER PRIMARY KEY, SimID, AdjID, ReachID, {', '.join(input_vars)}, {', '.join(adjustments)}, oVC_EX, oCC_EX, FOREIGN KEY (SimID) REFERENCES Simulations(SimID), FOREIGN KEY (AdjID) REFERENCES Adjustments(AdjID), FOREIGN KEY (ReachID) REFERENCES Inputs(ReachID))")
        cur.execute(f"CREATE TABLE IF NOT EXISTS InputStats(SimID INTEGER PRIMARY KEY, {', '.join(input_stat_cols)}, FOREIGN KEY (SimID) REFERENCES Simulations(SimID))")
        cur.execute(f"CREATE TABLE IF NOT EXISTS ResultStats(AdjID INTEGER PRIMARY KEY, SimID, {', '.join(adjustments)}, {', '.join(result_stat_cols)}, FOREIGN KEY (AdjID) REFERENCES Adjustments(AdjID), FOREIGN KEY (SimID) REFERENCES Simulations(SimID))")


def generate_inputs(n_inputs: int, uniform: bool) -> List[Dict[str, float]]:
    """Generate synthetic inputs for the BRAT model based on the specified number of samples and distribution type.
    
    Args:
        n_samples (int): Number of samples to generate.
        uniform (bool): If True, use uniform distributions; otherwise, use Siletz input distributions.
    
    Returns:
        List[Dict[str, float]]: A list of dictionaries containing the generated inputs.
    """

    if uniform:
        input_dists = input_dists_uniform
        # print(f"Generating {n_inputs} synthetic inputs using uniform distributions.")
    else:
        input_dists = input_dists_sampled
        # print(f"Generating {n_inputs} synthetic inputs using sampled distributions.")
    
    inputs = [{var: None for var in input_dists.keys()} for _ in range(n_inputs)]
    for i in range(n_inputs):
        for var, (dist, params) in input_dists.items():
            if dist == 'norm':
                inputs[i][var] = round(np.random.normal(params[0], params[1]), 3)
                # print(f"Generated {var} with normal distribution: {inputs[i][var]}")
            elif dist == 'uniform':
                inputs[i][var] = round(np.random.uniform(params[0], params[1]), 3)
                # print(f"Generated {var} with uniform distribution: {inputs[i][var]}")
            elif dist == 'expon':
                inputs[i][var] = round(np.random.exponential(params[1]) + params[0], 3)
                # print(f"Generated {var} with exponential distribution: {inputs[i][var]}")
            elif dist == 'pareto':
                val = float(stats.pareto.rvs(params[0], params[1], params[2], size=1))
                inputs[i][var] = round(val, 3)
            else:
                raise ValueError(f"Unknown distribution type: {dist}")
    
    return inputs

def generate_adjustments() -> Dict[str, float]:
    """Generate adjustments for the BRAT model based on predefined distributions.
    
    Returns:
        Dict[str, float]: A dictionary containing the generated adjustments.
    """
    
    adjustments = {}
    for adj, (dist, params) in adjustment_dist.items():
        # print(f"Generating adjustment {adj} with distribution {dist} and parameters ({param1}, {param2})")
        if dist == 'norm':
            if 'Scale' in adj:  # scale factor should be positive
                adjustments[adj] = round(abs(np.random.normal(params[0], params[1])), 2)
            else:
                adjustments[adj] = round(np.random.normal(params[0], params[1]), 2)
        elif dist == 'truncnorm':
            loc, scale, a, b = params
            a_transformed, b_transformed = (a - loc) / scale, (b - loc) / scale     # per scipy docs
            rv = stats.truncnorm(a_transformed, b_transformed, loc=loc, scale=scale)
            adjustments[adj] = round(float(rv.rvs(size=1)), 2)
            # print(f"Truncnorm called for {adj}. Given loc={loc}, scale={scale}, a={a}, b={b}. Generated val = {adjustments[adj]} using truncnorm({a_transformed}, {b_transformed}, {loc}, {scale})")
        elif dist == 'uniform':
            adjustments[adj] = round(np.random.uniform(params[0], params[1]), 2)
        else:
            raise ValueError(f"Unknown distribution type: {dist}")
    
    # print(f"Generated adjustments: {adjustments}")
    return adjustments



def brat_montecarlo(n_simulations: int, n_inputs: int, database: str, uniform_inputs: bool, name: str = None):
    """
    Perform a Monte Carlo simulation on the Standard BRAT FIS
        :param n_simulations: the number of times to run the simulation
        :param database: path to an existing or new sqlite database to log results. If existing, previous results will not be overwritten.
        :param uniform_inputs: use uniform distributions within bounds to generate inputs if True; otherwise use Siletz input distributions
    """

    # Handle database
    if os.path.isdir(database):
        database = os.path.join(database, 'brat_montecarlo.db')
    if not database.endswith('.db'):
        database += '.db'
    create_db(database)
    with sqlite3.connect(database) as conn:
        cur = conn.cursor()

        # Log the simulation
        start_time = datetime.datetime.now()
        log_name = "Monte Carlo Simulation" if name is None else name
        cur.execute("INSERT INTO Simulations(Name, Start, N_Inputs, N_Simulations) VALUES (?, ?, ?, ?)", (log_name, start_time, n_inputs, n_simulations))
        sim_id = cur.lastrowid
        print(f"SimID: {sim_id}")

        # Log the input distributions used
        input_dist = input_dists_uniform if uniform_inputs else input_dists_sampled
        for var, (dist, params) in input_dist.items():
            cur.execute("INSERT INTO InputDistributions(SimID, Var, Distribution, Parameters) VALUES (?, ?, ?, ?)",
                        (sim_id, var, dist, str(params)))
        
        # Log the adjustment distributions used
        for adj, (dist, params) in adjustment_dist.items():
            cur.execute("INSERT INTO AdjustmentDistributions(SimID, Adjustment, Distribution, Parameters) VALUES (?, ?, ?, ?)",
                        (sim_id, adj, dist, str(params)))
        
        conn.commit()

        # Generate and log the synthetic inputs
        input_reaches = generate_inputs(n_inputs, uniform_inputs)
        placeholders = ', '.join(['?'] * len(input_vars))
        for reach in input_reaches:
            insert_stmt = f"INSERT INTO Inputs(SimID, {', '.join(input_vars)}) VALUES (?, {placeholders})"
            cur.execute(insert_stmt, (sim_id, *[reach[var] for var in input_vars]))

        # Now perform the Monte Carlo simulation on our inputs
        for i in range(n_simulations):

            print(f">>> Performing simulation {i+1} of {n_simulations}...")

            # Generate and log adjustments for this simulation
            sim_adjustments = generate_adjustments()
            placeholders = ', '.join(['?'] * len(adjustments))
            insert_stmt = f"INSERT INTO Adjustments(SimID, {', '.join(adjustments)}) VALUES (?, {placeholders})"
            cur.execute(insert_stmt, (sim_id, *[sim_adjustments[col] for col in adjustments]))
            adj_id = cur.lastrowid

            # Prepare data storage to pass to the FIS functions
            # :param feature_values: Dictionary of features keyed by ReachID and values are dictionaries of attributes
            feature_values = {}
            for reachi, reach_dict in enumerate(input_reaches):
                reachid = reachi + 1
                feature_values[reachid] = {
                    'iVeg_30EX': reach_dict['iVeg_30EX'],
                    'iVeg100EX': reach_dict['iVeg100EX'],
                    'oVC_EX': None, # Placeholder, will be filled by Veg FIS
                    'iGeo_Slope': reach_dict['iGeo_Slope'],
                    'iHyd_SPLow': reach_dict['iHyd_SPLow'],
                    'iHyd_SP2': reach_dict['iHyd_SP2'],
                    'iGeo_Len': 150,  # Use a static but reasonable value, since only used to calculate mCC_CT
                    'iGeo_DA': 0.1,  # Placeholder, not used since max_drainage_area is None
                    'ReachCode': 0   # Placeholder, not used since max_drainage_area is None
                }

            # Run BRAT FIS for this simulation
            calculate_vegetation_fis_custom(feature_values, 'iVeg_30EX', 'iVeg100EX', 'oVC_EX',
                                            'scale', sim_adjustments['Veg30_Scale'],
                                            'scale', sim_adjustments['Veg100_Scale'])
            
            # feature_values[reachid]['oVC_EX'] now contains oVC output for each reach; used by combined fis

            calculate_combined_fis_custom(feature_values, 'oVC_EX', 'oCC_EX', 'mCC_EX_CT', None,
                                          sim_adjustments['SPLow_Shift'], sim_adjustments['SPLow_Scale'], 0.0,
                                          sim_adjustments['SP2_Shift'], sim_adjustments['SP2_Scale'], 0.0,
                                          sim_adjustments['Slope_Shift'], sim_adjustments['Slope_Scale'], 0.0)


            # Log the results of this simulation
            placeholders = ', '.join(['?'] * (3 + len(input_vars) + len(adjustments) + 2))
            insert_stmt = f"INSERT INTO Results(SimID, AdjID, ReachID, {', '.join(input_vars)}, {', '.join(adjustments)}, oVC_EX, oCC_EX) VALUES ({placeholders})"
            cur.executemany(insert_stmt, [(sim_id, adj_id, reach_i+1,
                                           reach['iVeg_30EX'], reach['iVeg100EX'], reach['iHyd_SPLow'], reach['iHyd_SP2'], reach['iGeo_Slope'],
                                           *[sim_adjustments[adj] for adj in adjustments],
                                           reach['oVC_EX'], reach['oCC_EX']) for reach_i, reach in enumerate(feature_values.values())])
            conn.commit()
            
        # Log end time of simulation
        end_time = datetime.datetime.now()
        cur.execute("UPDATE Simulations SET End = ? WHERE SimID = ?", (end_time, sim_id))
        
        print("Monte Carlo Simulation complete.")
        print(f"Start datetime: {start_time}")
        print(f"End datetime: {end_time}")
        
        # Populate InputStats table
        print("Now populating InputStats table...")
        input_stat_data = {}
        for stat in input_stat_cols:
            if "AVG" in stat:
                var = stat.replace("AVG_", "")
                cur.execute(f"SELECT AVG({var}) FROM Results")
                input_stat_data[stat] = round(cur.fetchone()[0], 3)
            elif "StDev" in stat:
                var = stat.replace("StDev_", "")
                cur.execute(f"SELECT {var} FROM Results")
                values = [row[0] for row in cur.fetchall() if row[0] is not None]
                if len(values) > 1:
                    stdev = round(statistics.stdev(values), 3)
                else:
                    stdev = None
                input_stat_data[stat] = stdev
        
        placeholders = ', '.join(['?'] * (1 + len(input_stat_data.values())))
        row = [sim_id] + [val for val in input_stat_data.values()]
        cur.execute(f"INSERT INTO InputStats VALUES ({placeholders})", row)

        # Populate ResultStats table
        print("Now populating ResultStats table...")

        cur.execute(f"SELECT AdjID FROM Adjustments WHERE SimID = {sim_id}")
        adj_ids = [row[0] for row in cur.fetchall()]
        result_stat_data = []       # list of tuples where each tuple is vals for a row
        for adj_id in adj_ids:
            row_data = []
            # select adjustment data
            cur.execute(f"SELECT AdjID, SimID, {', '.join(adjustments)} FROM Adjustments WHERE SimID = {sim_id} AND AdjID = {adj_id}")
            row_data.extend(cur.fetchone())
            # select stat data
            for stat in result_stat_cols:
                if "AVG" in stat:
                    var = stat.replace("AVG_", "")
                    cur.execute(f"SELECT AVG({var}) FROM Results WHERE AdjID = {adj_id}")
                    avg = round(cur.fetchone()[0], 3)
                    row_data.append(avg)
                elif "StDev" in stat:
                    var = stat.replace("StDev_", "")
                    cur.execute(f"SELECT {var} FROM Results WHERE AdjID = {adj_id}")
                    values = [row[0] for row in cur.fetchall() if row[0] is not None]
                    if len(values) > 1:
                        stdev = round(statistics.stdev(values), 3)
                    else:
                        stdev = None
                    row_data.append(stdev)
            result_stat_data.append(tuple(row_data))
        
        placeholders = ', '.join(['?'] * (2 + len(adjustments) + len(result_stat_cols)))
        cur.executemany(f"INSERT INTO ResultStats VALUES ({placeholders})", result_stat_data)
        conn.commit()


def main():
    """
    CLI
    """

    parser = argparse.ArgumentParser(
        description='Perform a Monte Carlo simulation on the Standard BRAT FIS:',
        # epilog="This is an epilog"
    )
    parser.add_argument('n_simulations', help='Integer number of simulations to run. This can be a large number.', type=int)
    parser.add_argument('n_synthetic_inputs', help="Integer number of inputs to generate. It is recommended that this isn't quite as large as n_simulations.", type=int)
    parser.add_argument('database', help='Path to an SQLite database to store results. Can be an existing monte carlo database, in which case the results will be appended, or a new database, or a directory in which to create a new database.', type=str)
    parser.add_argument('--uniform_inputs', help='(optional) Include this flag to use uniform distributions to generate the inputs, rather than Siletz distributions.', action='store_true', default=False)
    parser.add_argument('--name', help='(optional) Give this Monte Carlo run a custom name for logging purposes.', type=str, default=None)

    args = parser.parse_args()

    uniform = args.uniform_inputs if args.uniform_inputs else False
    name = args.name if args.name else None

    brat_montecarlo(args.n_simulations, args.n_synthetic_inputs, args.database, uniform, name)
    
    print(f"BRAT Monte Carlo run complete! Results logged in {args.database}")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
