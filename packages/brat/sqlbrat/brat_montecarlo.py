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
import argparse
import os
import sys
import traceback
import datetime
import time
import json
import sqlite3
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

from sqlbrat.utils.vegetation_fis import calculate_vegegtation_fis
from sqlbrat.utils.combined_fis import calculate_combined_fis

Path = str


# Useful info
input_dist = {
    'iVeg_30EX'
}


# Database functions
def create_db(database: Path):
    with SQLiteCon(database) as conn:
        cur = conn.cursor()

        cur.execute("CREATE TABLE IF NOT EXISTS Simulations_Log(Run INTEGER PRIMARY KEY, Start_DateTime, End_DateTime, N_Simulations)")
        cur.execute("CREATE TABLE IF NOT EXISTS Input_Distributions(Variable, Distribution, )")


def log_start(database: Path):
    with SQLiteCon(database) as conn:
        cur = conn.cursor()
        
        create_stmt = "CREATE TABLE IF NOT EXISTS Simulations_Log(Run INTEGER PRIMARY KEY, Start_DateTime, End_DateTime, N_Simulations)"
        cur.execute(create_stmt)

        insert_stmt = "INSERT INTO Simulations_Log (Run, Start_DateTime) DATETIME('now') INTO "


def brat_montecarlo(n_simulations: int, database: Path, uniform_inputs: bool):
    """Perform a Monte Carlo simulation on the Standard BRAT FIS
        :param n_simulations: the number of times to run the simulation
        :param database: path to an existing or new sqlite database to log results. If existing, previous results will not be overwritten.
        :param uniform_inputs: use uniform distributions within bounds to generate inputs if True; otherwise use Siletz input distributions
    """

    # Determine if database exists
    # Log the date and time of this monte carlo in Log table

    # Perform the monte carlo



def main():
    """ CLI
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
