"""
An alternative to the original vegetation_fis.py, in which the FIS can be modified for sensitivity analysis.
This script is meant to be imported into brat.py and called in place of vegetation_fis.py.
A similar version is provided for the combined FIS.

Much of the code is copied from the original vegetation_fis.py, credits:
    Jordan Gilbert
    Philip Bailey

Evan Hackstadt
July 2025
"""


import os
import sys
import argparse
import traceback
import numpy as np
import skfuzzy as fuzz
import matplotlib.pyplot as plt
from skfuzzy import control as ctrl
from rscommons import Logger, ProgressBar, dotenv
from rscommons.database import load_attributes, load_dgo_attributes
from rscommons.database import write_db_attributes, write_db_dgo_attributes


adjustment_types = ['scale', 'shape']
default_adjustment_values = {
    'shift': 0.0,       # no shift
    'scale': 1.0,       # no scaling
    'shape': 0.0        # indicates original shapes should be used
}


def vegetation_fis_custom(database: str, label: str, veg_type: str, dgo: bool = None, 
                   adjustment_type: str = None, adjustment_value: float = 1.0):
    """Calculate vegetation suitability for each reach in a BRAT
    SQLite database

    Arguments:
        database {str} -- Path to BRAT SQLite database
        label {str} -- Either 'historic' or 'existing'. Only used for lof messages.
        veg_type {str} -- Prefix either 'EX' for existing or 'HPE' for historic
        adjustment_type {str} -- Type of adjustment to apply ('scale' or 'shape')
        adjustment_value {float} -- Value for the adjustment (e.g., scaling factor)
    """

    log = Logger('Vegetation FIS')
    log.info('Processing {} vegetation'.format(label))
    log.info('Adjustment type: {}, value: {}'.format(adjustment_type, adjustment_value))

    # handle adjustment parameters
    if adjustment_type:
        if adjustment_type not in adjustment_types:
            raise ValueError(f"Invalid adjustment type: {adjustment_type}. Must be one of {adjustment_types}.")
        if adjustment_type == 'scale' and adjustment_value <= 0.0:
                raise ValueError(f"Invalid adjustment value scale factor: {adjustment_value}. Must be greater than 0.")
        if adjustment_type == 'shape' and (adjustment_value != 1.0 and adjustment_value != 2.0):
                raise ValueError(f"Invalid adjustment value: {adjustment_value}. Choose either 1.0 (best fit) or 2.0 (loose fit).")

        # output folder for fis images
        fis_dir = os.path.join(os.path.dirname(os.path.dirname(database)), 'fis/')

    streamside_field = 'iVeg_30{}'.format(veg_type)
    riparian_field = 'iVeg100{}'.format(veg_type)
    out_field = 'oVC_{}'.format(veg_type)

    if not dgo:
        feature_values = load_attributes(database, [streamside_field, riparian_field], '({} IS NOT NULL) AND ({} IS NOT NULL)'.format(streamside_field, riparian_field))
        if adjustment_type:
            calculate_vegetation_fis_custom(feature_values, streamside_field, riparian_field, out_field,
                                            adjustment_type, adjustment_value, fis_dir)
        else:
            calculate_vegegtation_fis(feature_values, streamside_field, riparian_field, out_field)
        write_db_attributes(database, feature_values, [out_field])
    else:
        feature_values = load_dgo_attributes(database, [streamside_field, riparian_field], '({} IS NOT NULL) AND ({} IS NOT NULL)'.format(streamside_field, riparian_field))
        if adjustment_type:
            calculate_vegetation_fis_custom(feature_values, streamside_field, riparian_field, out_field,
                                            adjustment_type, adjustment_value, fis_dir)
        else:
            calculate_vegegtation_fis(feature_values, streamside_field, riparian_field, out_field)
        write_db_dgo_attributes(database, feature_values, [out_field])

    log.info('Process completed successfully.')



# custom Veg FIS function that allows for sensitivity analysis adjustments
def calculate_vegetation_fis_custom(feature_values: dict, streamside_field: str, riparian_field: str, out_field: str,
                                    adj_type: str, adj_val: float, fis_dir: str):
    """
    Adjustable beaver dam capacity vegetation FIS
    :param feature_values: Dictionary of features keyed by ReachID and values are dictionaries of attributes
    :param streamside_field: Name of the feature streamside vegetation attribute
    :param riparian_field: Name of the riparian vegetation attribute
    :param adj_type: Type of adjustment to apply ('scale' or 'shape')
    :param adj_val: Value for the adjustment (scaling factor)
    """

    log = Logger('CUSTOM Vegetation FIS')
    log.info('Initializing CUSTOM Vegetation FIS')

    feature_count = len(feature_values)
    reachid_array = np.zeros(feature_count, np.int64)
    riparian_array = np.zeros(feature_count, np.float64)
    streamside_array = np.zeros(feature_count, np.float64)

    counter = 0
    for reach_id, values in feature_values.items():
        reachid_array[counter] = reach_id
        riparian_array[counter] = values[riparian_field]
        streamside_array[counter] = values[streamside_field]
        counter += 1

    # Ensure vegetation inputs are within the 0-4 range
    riparian_array[riparian_array < 0] = 0
    riparian_array[riparian_array > 4] = 4
    streamside_array[streamside_array < 0] = 0
    streamside_array[streamside_array > 4] = 4

    # create antecedent (input) and consequent (output) objects to hold universe variables and membership functions
    riparian = ctrl.Antecedent(np.arange(0, 4, 0.01), 'input1')     # to be adjusted
    streamside = ctrl.Antecedent(np.arange(0, 4, 0.01), 'input2')   # to be adjusted
    density = ctrl.Consequent(np.arange(0, 45, 0.01), 'result')     # do not adjust output!

    # build membership functions for each antecedent and consequent object --- apply adjustments here
    
    # we do NOT adjust density
    density['none'] = fuzz.trimf(density.universe, [0, 0, 0.1])
    density['rare'] = fuzz.trapmf(density.universe, [0, 0.1, 0.5, 1.5])
    density['occasional'] = fuzz.trapmf(density.universe, [0.5, 1.5, 4, 8])
    density['frequent'] = fuzz.trapmf(density.universe, [4, 8, 12, 25])
    density['pervasive'] = fuzz.trapmf(density.universe, [12, 25, 45, 45])

    if adj_type == 'scale':
        # scaling equations:
        #   triangles (a,b,c)
        #       a = b - ((b - a) * scalefactor)
        #       c = b + ((c - b) * scalefactor)
        #       even though the triangle may not be isosceles, we use b to yield consistent MF intersection
        #   trapezoids (a,b,c,d)
        #       a = b - ((b-a) * scalefactor)
        #       d = c + ((d-c) * scalefactor)
        
        # scale trapezoids
        a0, b0, c0, d0 = 0, 0, 0.1, 1   # from standard MFs
        a1 = b0 - ((b0 - a0) * adj_val)
        d1 = c0 + ((d0 - c0) * adj_val)     # we do not change top (b or c)
        riparian['unsuitable'] = fuzz.trapmf(riparian.universe, [a1, b0, c0, d1])
        streamside['unsuitable'] = fuzz.trapmf(streamside.universe, [a1, b0, c0, d1])
        
        # scale triangles iteratively
        tri_centers = {     # from standard MFs
            'barely': [0.1, 1, 2],
            'moderately': [1, 2, 3], 
            'suitable': [2, 3, 4],
            'preferred': [3, 4, 4]
        }
        for cat, abc in tri_centers.items():
            b = abc[1]      # we do not change the top of the triangle since we don't want to shift
            a = b - ((b - abc[0]) * adj_val)
            c = b + ((abc[2] - b) * adj_val)
            riparian[cat] = fuzz.trimf(riparian.universe, [a, b, c])
            streamside[cat] = fuzz.trimf(streamside.universe, [a, b, c])  # MFs are identical

    elif adj_type == 'shape':
        
        # 'best fit' curves
        if adj_val == 1.0:
            log.info("Running 'best fit' custom MF shapes.")
            riparian['unsuitable'] = fuzz.pimf(riparian.universe, -0.01, 0, 0.1, 1) # need to cover 0 input
            riparian['barely'] = fuzz.gaussmf(riparian.universe, 1, .4)
            riparian['moderately'] = fuzz.gaussmf(riparian.universe, 2, .4)
            riparian['suitable'] = fuzz.gaussmf(riparian.universe, 3, .4)
            riparian['preferred'] = fuzz.gaussmf(riparian.universe, 4, .4)

            streamside['unsuitable'] = fuzz.pimf(riparian.universe, -0.01, 0, 0.1, 1) # need to cover 0 input
            streamside['barely'] = fuzz.gaussmf(streamside.universe, 1, .4)
            streamside['moderately'] = fuzz.gaussmf(streamside.universe, 2, .4)
            streamside['suitable'] = fuzz.gaussmf(streamside.universe, 3, .4)
            streamside['preferred'] = fuzz.gaussmf(streamside.universe, 4, .4)
        
        # 'loose fit' curves
        elif adj_val == 2.0:
            log.info("Running 'loose fit' custom MF shapes.")
            riparian['unsuitable'] = fuzz.gbellmf(riparian.universe, 0.4, 2, 0.1)
            riparian['barely'] = fuzz.gaussmf(riparian.universe, 1, .4)
            riparian['moderately'] = fuzz.gaussmf(riparian.universe, 2, .4)
            riparian['suitable'] = fuzz.gaussmf(riparian.universe, 3, .4)
            riparian['preferred'] = fuzz.gaussmf(riparian.universe, 4, .4)

            streamside['unsuitable'] = fuzz.gbellmf(riparian.universe, 0.4, 2, 0.1)
            streamside['barely'] = fuzz.gaussmf(streamside.universe, 1, .4)
            streamside['moderately'] = fuzz.gaussmf(streamside.universe, 2, .4)
            streamside['suitable'] = fuzz.gaussmf(streamside.universe, 3, .4)
            streamside['preferred'] = fuzz.gaussmf(streamside.universe, 4, .4)
    

    # build fis rule table --- we don't adjust this for FIS SA
    veg_ctrl = ctrl.ControlSystem([
        ctrl.Rule(riparian['unsuitable'] & streamside['unsuitable'], density['none']),
        ctrl.Rule(riparian['barely'] & streamside['unsuitable'], density['rare']),
        ctrl.Rule(riparian['moderately'] & streamside['unsuitable'], density['rare']),
        ctrl.Rule(riparian['suitable'] & streamside['unsuitable'], density['occasional']),
        ctrl.Rule(riparian['preferred'] & streamside['unsuitable'], density['occasional']),
        ctrl.Rule(riparian['unsuitable'] & streamside['barely'], density['rare']),
        ctrl.Rule(riparian['barely'] & streamside['barely'], density['rare']),  # matBRAT has consequnt as 'occasional'
        ctrl.Rule(riparian['moderately'] & streamside['barely'], density['occasional']),
        ctrl.Rule(riparian['suitable'] & streamside['barely'], density['occasional']),
        ctrl.Rule(riparian['preferred'] & streamside['barely'], density['occasional']),
        ctrl.Rule(riparian['unsuitable'] & streamside['moderately'], density['rare']),
        ctrl.Rule(riparian['barely'] & streamside['moderately'], density['occasional']),
        ctrl.Rule(riparian['moderately'] & streamside['moderately'], density['occasional']),
        ctrl.Rule(riparian['suitable'] & streamside['moderately'], density['frequent']),
        ctrl.Rule(riparian['preferred'] & streamside['moderately'], density['frequent']),
        ctrl.Rule(riparian['unsuitable'] & streamside['suitable'], density['occasional']),
        ctrl.Rule(riparian['barely'] & streamside['suitable'], density['occasional']),
        ctrl.Rule(riparian['moderately'] & streamside['suitable'], density['frequent']),
        ctrl.Rule(riparian['suitable'] & streamside['suitable'], density['frequent']),
        ctrl.Rule(riparian['preferred'] & streamside['suitable'], density['pervasive']),
        ctrl.Rule(riparian['unsuitable'] & streamside['preferred'], density['occasional']),
        ctrl.Rule(riparian['barely'] & streamside['preferred'], density['frequent']),
        ctrl.Rule(riparian['moderately'] & streamside['preferred'], density['pervasive']),
        ctrl.Rule(riparian['suitable'] & streamside['preferred'], density['pervasive']),
        ctrl.Rule(riparian['preferred'] & streamside['preferred'], density['pervasive'])
    ])
    veg_fis = ctrl.ControlSystemSimulation(veg_ctrl)

    # calculate defuzzified centroid value for density 'none' MF group
    # this will be used to re-classify output values that fall in this group
    # important: will need to update the array (x) and MF values (mfx) if the
    #            density 'none' values are changed in the model
    x_vals = np.arange(0, 45, 0.01)
    mfx = fuzz.trimf(x_vals, [0, 0, 0.1])
    defuzz_centroid = round(fuzz.defuzz(x_vals, mfx, 'centroid'), 6)

    mfx_pervasive = fuzz.trapmf(x_vals, [12, 25, 45, 45])
    defuzz_pervasive = round(fuzz.defuzz(x_vals, mfx_pervasive, 'centroid'))

    # run fuzzy inference system on inputs and defuzzify output
    progbar = ProgressBar(len(reachid_array), 50, "Vegetation FIS")
    counter = 0
    for i, reach_id in enumerate(reachid_array):
        veg_fis.input['input1'] = riparian_array[i]
        veg_fis.input['input2'] = streamside_array[i]
        veg_fis.compute()
        result = veg_fis.output['result']

        # set ovc_* to 0 if output falls fully in 'none' category and to 40 if falls fully in 'pervasive' category
        if round(result, 6) == defuzz_centroid:
            result = 0.0

        if round(result) >= defuzz_pervasive:
            result = 40.0

        feature_values[reach_id][out_field] = round(result, 2)

        counter += 1
        progbar.update(counter)

    progbar.finish()
    log.info('Custom Veg FIS Done')
    
    
    '''VISUALIZE MEMBERSHIP FUNCTIONS'''
    log.info('Visualizing Adjusted MFs...')
    
    # Riparian
    for label, color in zip(list(riparian.terms.keys()), ['r', 'orange', 'y', 'g', 'b']):
        plt.plot(riparian.universe, riparian.terms[label].mf, color=color, linewidth=1.5, label=label.capitalize())
    plt.xlabel('Riparian (100m) Suitability')
    plt.ylabel('Membership')
    plt.legend(loc='upper right')
    plt.tight_layout()
    out_file_path = os.path.join(fis_dir, "fis-veg-riparian.png")
    plt.savefig(out_file_path)
    plt.close()

    # Streamside
    for label, color in zip(list(streamside.terms.keys()), ['r', 'orange', 'y', 'g', 'b']):
        plt.plot(streamside.universe, streamside.terms[label].mf, color=color, linewidth=1.5, label=label.capitalize())
    plt.xlabel('Streamside (30m) Suitability')
    plt.ylabel('Membership')
    plt.legend(loc='upper right')
    plt.tight_layout()
    out_file_path = os.path.join(fis_dir, "fis-veg-streamside.png")
    plt.savefig(out_file_path)
    plt.close()

    # Density - should remain unchanged
    '''
    fig, axs = plt.subplots(1, 1, figsize=(12, 4))
    for label, color in zip(list(density.terms.keys()), ['r', 'orange', 'y', 'g', 'b']):
        axs.plot(density.universe, density.terms[label].mf, color=color, linewidth=1.5, label=label.capitalize())
    plt.xlabel('Dam Density (dams/km) from Vegetation FIS')
    plt.ylabel('Membership')
    plt.legend(title='Capacity:')
    plt.xlim(0, 40)
    plt.tight_layout()
    out_file_path = os.path.join(fis_dir, "fis-veg-density.png")
    plt.savefig(out_file_path)
    plt.close()
    '''



# the standard Veg FIS from sqlBRAT
def calculate_vegegtation_fis(feature_values: dict, streamside_field: str, riparian_field: str, out_field: str):
    """
    Beaver dam capacity vegetation FIS
    :param feature_values: Dictionary of features keyed by ReachID and values are dictionaries of attributes
    :param streamside_field: Name of the feature streamside vegetation attribute
    :param riparian_field: Name of the riparian vegetation attribute
    :return: Inserts 'FIS' key into feature dictionaries with the vegetation FIS values
    """

    log = Logger('Vegetation FIS')

    feature_count = len(feature_values)
    reachid_array = np.zeros(feature_count, np.int64)
    riparian_array = np.zeros(feature_count, np.float64)
    streamside_array = np.zeros(feature_count, np.float64)

    counter = 0
    for reach_id, values in feature_values.items():
        reachid_array[counter] = reach_id
        riparian_array[counter] = values[riparian_field]
        streamside_array[counter] = values[streamside_field]
        counter += 1

    # Ensure vegetation inputs are within the 0-4 range
    riparian_array[riparian_array < 0] = 0
    riparian_array[riparian_array > 4] = 4
    streamside_array[streamside_array < 0] = 0
    streamside_array[streamside_array > 4] = 4

    # create antecedent (input) and consequent (output) objects to hold universe variables and membership functions
    riparian = ctrl.Antecedent(np.arange(0, 4, 0.01), 'input1')
    streamside = ctrl.Antecedent(np.arange(0, 4, 0.01), 'input2')
    density = ctrl.Consequent(np.arange(0, 45, 0.01), 'result')

    # build membership functions for each antecedent and consequent object
    riparian['unsuitable'] = fuzz.trapmf(riparian.universe, [0, 0, 0.1, 1])
    riparian['barely'] = fuzz.trimf(riparian.universe, [0.1, 1, 2])
    riparian['moderately'] = fuzz.trimf(riparian.universe, [1, 2, 3])
    riparian['suitable'] = fuzz.trimf(riparian.universe, [2, 3, 4])
    riparian['preferred'] = fuzz.trimf(riparian.universe, [3, 4, 4])

    streamside['unsuitable'] = fuzz.trapmf(streamside.universe, [0, 0, 0.1, 1])
    streamside['barely'] = fuzz.trimf(streamside.universe, [0.1, 1, 2])
    streamside['moderately'] = fuzz.trimf(streamside.universe, [1, 2, 3])
    streamside['suitable'] = fuzz.trimf(streamside.universe, [2, 3, 4])
    streamside['preferred'] = fuzz.trimf(streamside.universe, [3, 4, 4])

    density['none'] = fuzz.trimf(density.universe, [0, 0, 0.1])
    density['rare'] = fuzz.trapmf(density.universe, [0, 0.1, 0.5, 1.5])
    density['occasional'] = fuzz.trapmf(density.universe, [0.5, 1.5, 4, 8])
    density['frequent'] = fuzz.trapmf(density.universe, [4, 8, 12, 25])
    density['pervasive'] = fuzz.trapmf(density.universe, [12, 25, 45, 45])

    # build fis rule table
    veg_ctrl = ctrl.ControlSystem([
        ctrl.Rule(riparian['unsuitable'] & streamside['unsuitable'], density['none']),
        ctrl.Rule(riparian['barely'] & streamside['unsuitable'], density['rare']),
        ctrl.Rule(riparian['moderately'] & streamside['unsuitable'], density['rare']),
        ctrl.Rule(riparian['suitable'] & streamside['unsuitable'], density['occasional']),
        ctrl.Rule(riparian['preferred'] & streamside['unsuitable'], density['occasional']),
        ctrl.Rule(riparian['unsuitable'] & streamside['barely'], density['rare']),
        ctrl.Rule(riparian['barely'] & streamside['barely'], density['rare']),  # matBRAT has consequnt as 'occasional'
        ctrl.Rule(riparian['moderately'] & streamside['barely'], density['occasional']),
        ctrl.Rule(riparian['suitable'] & streamside['barely'], density['occasional']),
        ctrl.Rule(riparian['preferred'] & streamside['barely'], density['occasional']),
        ctrl.Rule(riparian['unsuitable'] & streamside['moderately'], density['rare']),
        ctrl.Rule(riparian['barely'] & streamside['moderately'], density['occasional']),
        ctrl.Rule(riparian['moderately'] & streamside['moderately'], density['occasional']),
        ctrl.Rule(riparian['suitable'] & streamside['moderately'], density['frequent']),
        ctrl.Rule(riparian['preferred'] & streamside['moderately'], density['frequent']),
        ctrl.Rule(riparian['unsuitable'] & streamside['suitable'], density['occasional']),
        ctrl.Rule(riparian['barely'] & streamside['suitable'], density['occasional']),
        ctrl.Rule(riparian['moderately'] & streamside['suitable'], density['frequent']),
        ctrl.Rule(riparian['suitable'] & streamside['suitable'], density['frequent']),
        ctrl.Rule(riparian['preferred'] & streamside['suitable'], density['pervasive']),
        ctrl.Rule(riparian['unsuitable'] & streamside['preferred'], density['occasional']),
        ctrl.Rule(riparian['barely'] & streamside['preferred'], density['frequent']),
        ctrl.Rule(riparian['moderately'] & streamside['preferred'], density['pervasive']),
        ctrl.Rule(riparian['suitable'] & streamside['preferred'], density['pervasive']),
        ctrl.Rule(riparian['preferred'] & streamside['preferred'], density['pervasive'])
    ])
    veg_fis = ctrl.ControlSystemSimulation(veg_ctrl)

    # calculate defuzzified centroid value for density 'none' MF group
    # this will be used to re-classify output values that fall in this group
    # important: will need to update the array (x) and MF values (mfx) if the
    #            density 'none' values are changed in the model
    x_vals = np.arange(0, 45, 0.01)
    mfx = fuzz.trimf(x_vals, [0, 0, 0.1])
    defuzz_centroid = round(fuzz.defuzz(x_vals, mfx, 'centroid'), 6)

    mfx_pervasive = fuzz.trapmf(x_vals, [12, 25, 45, 45])
    defuzz_pervasive = round(fuzz.defuzz(x_vals, mfx_pervasive, 'centroid'))

    # run fuzzy inference system on inputs and defuzzify output
    progbar = ProgressBar(len(reachid_array), 50, "Vegetation FIS")
    counter = 0
    for i, reach_id in enumerate(reachid_array):
        veg_fis.input['input1'] = riparian_array[i]
        veg_fis.input['input2'] = streamside_array[i]
        veg_fis.compute()
        result = veg_fis.output['result']

        # set ovc_* to 0 if output falls fully in 'none' category and to 40 if falls fully in 'pervasive' category
        if round(result, 6) == defuzz_centroid:
            result = 0.0

        if round(result) >= defuzz_pervasive:
            result = 40.0

        feature_values[reach_id][out_field] = round(result, 2)

        counter += 1
        progbar.update(counter)

    progbar.finish()
    log.info('Done')


def main():
    """ Main Vegetation FIS
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('database', help='BRAT SQLite database', type=argparse.FileType('r'))
    parser.add_argument('--verbose', help='(optional) verbose logging mode', action='store_true', default=False)
    args = dotenv.parse_args_env(parser)

    # Initiate the log file
    logg = Logger("Vegetation FIS")
    logfile = os.path.join(os.path.dirname(args.network.name), "vegetation_fis.log")
    logg.setup(logPath=logfile, verbose=args.verbose)

    try:
        # vegetation_fis_custom(args.network.name, 'historic', 'HPE')
        vegetation_fis_custom(args.database.name, 'existing', 'EX')

    except Exception as ex:
        logg.error(ex)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
