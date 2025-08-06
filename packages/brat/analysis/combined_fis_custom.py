"""
An alternative to the original combined_fis.py, in which the FIS can be modified for sensitivity analysis.
This script is meant to be imported into brat.py and called in place of combined_fis.py.
A similar version is provided for the combined FIS.

Much of the code is copied from the original combined_fis.py, credits:
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
from rscommons.database import load_attributes, write_db_attributes, load_dgo_attributes, write_db_dgo_attributes
from rscommons import ProgressBar, Logger, dotenv


adjustment_types = ['shift', 'scale', 'shape']
default_adjustment_values = {
    'shift': 0.0,       # no shift
    'scale': 1.0,       # no scaling
    'shape': 0.0        # indicates original shapes should be used
}

def combined_fis_custom(database: str, label: str, veg_type: str, max_drainage_area: float, dgo: bool = False, 
                 adjustment_type: str = None, adjustment_values: list = None):
    """
    Combined beaver dam capacity FIS
    :param network: Shapefile path containing necessary FIS inputs
    :param label: Plain English label identifying vegetation type ("Existing" or "Historical")
    :param veg_type: Vegetation type suffix added to end of output ShapeFile fields
    :param max_drainage_area: Max drainage above which features are not processed.
    :param adjustment_type: Type of adjustment to apply ('shift', 'scale', or 'shape')
    :param adjustment_values: List of values for adjustments (shifts or scaling factors)
    :return: None
    """

    log = Logger('Combined FIS')
    log.info('Processing {} vegetation'.format(label))
    
    # handle adjustment parameters
    if adjustment_type:
        if adjustment_type not in adjustment_types:
            raise ValueError(f"Invalid adjustment type: {adjustment_type}. Must be one of {adjustment_types}.")
        if not adjustment_values:
            raise ValueError(f"Please provide adjustment values: list of [splow, sp2, slope] shift amounts, scale factors, or curve types.")
        for val in adjustment_values:
            if adjustment_type == 'scale' and val <= 0:
                raise ValueError(f"Invalid adjustment value scale factor: {val}. Must be greater than 0.")
            if adjustment_type == 'shape' and (val != 1.0 and val != 2.0):
                raise ValueError(f"Invalid adjustment value curve type: {val}. Must be either 1.0 (best fit) or 2.0 (loose fit).")

        # output folder for fis images
        fis_dir = os.path.join(os.path.dirname(os.path.dirname(database)), 'fis/')
    
    veg_fis_field = 'oVC_{}'.format(veg_type)
    capacity_field = 'oCC_{}'.format(veg_type)
    dam_count_field = 'mCC_{}_CT'.format(veg_type)

    fields = [veg_fis_field, 'iGeo_Slope', 'iGeo_DA', 'iHyd_SP2', 'iHyd_SPLow', 'iGeo_Len', 'ReachCode']

    if not dgo:
        reaches = load_attributes(database, fields, ' AND '.join(['({} IS NOT NULL)'.format(f) for f in fields]))
        if adjustment_type:
            calculate_combined_fis_custom(reaches, veg_fis_field, capacity_field, dam_count_field, max_drainage_area,
                                          adjustment_type, adjustment_values, fis_dir)
        else:
            calculate_combined_fis(reaches, veg_fis_field, capacity_field, dam_count_field, max_drainage_area)
        write_db_attributes(database, reaches, [capacity_field, dam_count_field], log)
    else:
        feature_values = load_dgo_attributes(database, fields, ' AND '.join(['({} IS NOT NULL)'.format(f) for f in fields]))
        if adjustment_type:
            calculate_combined_fis_custom(reaches, veg_fis_field, capacity_field, dam_count_field, max_drainage_area,
                                          adjustment_type, adjustment_values, fis_dir)
        else:
            calculate_combined_fis(feature_values, veg_fis_field, capacity_field, dam_count_field, max_drainage_area)
        write_db_dgo_attributes(database, feature_values, [capacity_field, dam_count_field], log)

    log.info('Process completed successfully.')


def calculate_combined_fis_custom(feature_values: dict, veg_fis_field: str, capacity_field: str, dam_count_field: str, max_drainage_area: float,
                                  adj_type: str, adj_vals: list, fis_dir: str):
    """
    Calculate dam capacity and density using combined FIS
    :param feature_values: Dictionary of features keyed by ReachID and values are dictionaries of attributes
    :param veg_fis_field: Attribute containing the output of the vegetation FIS
    :param com_capacity_field: Attribute used to store the capacity result in feature_values
    :param com_density_field: Attribute used to store the capacity results in feature_values
    :param max_drainage_area: Reaches with drainage area greater than this threshold will have zero capacity
    :param adj_type: Type of adjustment to apply ('shift', 'scale', or 'shape')
    :param vals: List of values for adjustments (shifts or scaling factors)
    :return: Insert the dam capacity and density values to the feature_values dictionary
    """

    log = Logger('CUSTOM Combined FIS')
    log.info('Initializing CUSTOM Combined FIS')

    if not max_drainage_area:
        log.warning('Missing max drainage area. Calculating combined FIS without max drainage threshold.')

    # get arrays for fields of interest
    feature_count = len(feature_values)
    reachid_array = np.zeros(feature_count, np.int64)
    reachcode_array = np.zeros(feature_count, np.int64)
    veg_array = np.zeros(feature_count, np.float64)
    hydq2_array = np.zeros(feature_count, np.float64)
    hydlow_array = np.zeros(feature_count, np.float64)
    slope_array = np.zeros(feature_count, np.float64)
    drain_array = np.zeros(feature_count, np.float64)

    counter = 0
    for reach_id, values in feature_values.items():
        reachid_array[counter] = reach_id
        reachcode_array[counter] = values['ReachCode']
        veg_array[counter] = values[veg_fis_field]
        hydlow_array[counter] = values['iHyd_SPLow']
        hydq2_array[counter] = values['iHyd_SP2']
        slope_array[counter] = values['iGeo_Slope']
        drain_array[counter] = values['iGeo_DA']
        counter += 1

    # Adjust inputs to be within FIS membership range
    veg_array[veg_array < 0] = 0
    veg_array[veg_array > 45] = 45

    hydq2_array[hydq2_array < 0] = 0.0001
    hydq2_array[hydq2_array > 10000] = 10000

    hydlow_array[hydlow_array < 0] = 0.0001
    hydlow_array[hydlow_array > 10000] = 10000
    slope_array[slope_array > 1] = 1

    # create antecedent (input) and consequent (output) objects to hold universe variables and membership functions
    ovc = ctrl.Antecedent(np.arange(0, 45, 0.01), 'input1')
    splow = ctrl.Antecedent(np.arange(0, 10000, 1), 'input3')
    sp2 = ctrl.Antecedent(np.arange(0, 10000, 1), 'input2')
    slope = ctrl.Antecedent(np.arange(0, 1, 0.0001), 'input4')
    density = ctrl.Consequent(np.arange(0, 45, 0.01), 'result')

    # build membership functions for each antecedent and consequent object
    
    # we do NOT adjust ovc or density output - build these first
    ovc['none'] = fuzz.trimf(ovc.universe, [0, 0, 0.1])
    ovc['rare'] = fuzz.trapmf(ovc.universe, [0, 0.1, 0.5, 1.5])
    ovc['occasional'] = fuzz.trapmf(ovc.universe, [0.5, 1.5, 4, 8])
    ovc['frequent'] = fuzz.trapmf(ovc.universe, [4, 8, 12, 25])
    ovc['pervasive'] = fuzz.trapmf(ovc.universe, [12, 25, 45, 45])

    density['none'] = fuzz.trimf(density.universe, [0, 0, 0.1])
    density['rare'] = fuzz.trapmf(density.universe, [0, 0.1, 0.5, 1.5])
    density['occasional'] = fuzz.trapmf(density.universe, [0.5, 1.5, 4, 8])
    density['frequent'] = fuzz.trapmf(density.universe, [4, 8, 12, 25])
    density['pervasive'] = fuzz.trapmf(density.universe, [12, 25, 45, 45])

    if adj_type == 'shift':
        # we shift all values by the specified constant except min and max bounds
        c1 = adj_vals[0]
        splow['can'] = fuzz.trapmf(splow.universe, [0, 0, 150+c1, 175+c1])
        splow['probably'] = fuzz.trapmf(splow.universe, [150+c1, 175+c1, 180+c1, 190+c1])
        splow['cannot'] = fuzz.trapmf(splow.universe, [180+c1, 190+c1, 10000, 10000])

        c2 = adj_vals[1]
        sp2['persists'] = fuzz.trapmf(sp2.universe, [0, 0, 1000+c2, 1200+c2])
        sp2['breach'] = fuzz.trimf(sp2.universe, [1000+c2, 1200+c2, 1600+c2])
        sp2['oblowout'] = fuzz.trimf(sp2.universe, [1200+c2, 1600+c2, 2400+c2])
        sp2['blowout'] = fuzz.trapmf(sp2.universe, [1600+c2, 2400+c2, 10000, 10000])

        c3 = adj_vals[2]
        slope['flat'] = fuzz.trapmf(slope.universe, [0, 0, 0.0002, 0.005])      # do not shift tiny 'flat' MF
        slope['can'] = fuzz.trapmf(slope.universe, [0.0002, 0.005, 0.12+c3, 0.15+c3])   # treat as left edge
        slope['probably'] = fuzz.trapmf(slope.universe, [0.12+c3, 0.15+c3, 0.17+c3, 0.23+c3])
        slope['cannot'] = fuzz.trapmf(slope.universe, [0.17+c3, 0.23+c3, 1, 1])
    
    elif adj_type == 'scale':
        # scaling equations:
            #   triangles (a,b,c)
            #       a = b - ((b - a) * scalefactor)
            #       c = b + ((c - b) * scalefactor)
            #       even though the triangle may not be isosceles, we use b to yield consistent MF intersection
            #   trapezoids (a,b,c,d)
            #       a = b - ((b-a) * scalefactor)
            #       d = c + ((d-c) * scalefactor)
        
        trapezoids = {
            'splow': [
                ['can', [0, 0, 150, 175]],
                ['probably', [150, 175, 180, 190]],
                ['cannot', [180, 190, 10000, 10000]]
            ],
            'sp2': [
                ['persists', [0, 0, 1000, 1200]],
                ['blowout', [1600, 2400, 10000, 10000]]
            ],
            'slope': [
                ['flat', [0, 0, 0.0002, 0.005]],
                ['can', [0.0002, 0.005, 0.12, 0.15]],
                ['probably', [0.12, 0.15, 0.17, 0.23]],
                ['cannot', [0.17, 0.23, 1, 1]]
            ]
        }
        
        sp2_triangles = {   # only sp2 uses triangles
            'breach': [1000, 1200, 1600],
            'oblowout': [1200, 1600, 2400]
        }
        
        # scale trapezoids iteratively
        for var, mfs in trapezoids.items():
            for category, abcd in mfs:
                if var == 'splow':
                    a, b, c, d = calculate_trap_scale(abcd, adj_vals[0])
                    splow[category] = fuzz.trapmf(splow.universe, [a, b, c, d])
                if var == 'sp2':
                    a, b, c, d = calculate_trap_scale(abcd, adj_vals[1])
                    sp2[category] = fuzz.trapmf(sp2.universe, [a, b, c, d])
                if var == 'slope':
                    a, b, c, d = calculate_trap_scale(abcd, adj_vals[2])
                    slope[category] = fuzz.trapmf(slope.universe, [a, b, c, d])
        
        # scale triangles iteratively - only sp2 has tris
        for cat, abc in sp2_triangles.items():
            scale = adj_vals[1]
            b = abc[1]
            a = b - ((b - abc[0]) * scale)
            c = b + ((abc[2] - b) * scale)
            sp2[cat] = fuzz.trimf(sp2.universe, [a, b, c])
        
    elif adj_type == 'shape':
        
        # SPlow
        if adj_vals[0] == 1.0:
            log.info("Running 'best fit' custom MF shapes for SPLow.")
            splow['can'] = fuzz.pimf(splow.universe, -0.01, 0, 150, 175)
            splow['probably'] = fuzz.pimf(splow.universe, 150, 175, 180, 190)
            splow['cannot'] = fuzz.pimf(splow.universe, 180, 190, 10000, 10000.1)
        elif adj_vals[0] == 2.0:
            log.info("Running 'loose fit' custom MF shapes for SPLow.")
            splow['can'] = fuzz.gbellmf(splow.universe, 85, 8, 75)
            splow['probably'] = fuzz.gbellmf(splow.universe, 10, 2, 170)
            splow['cannot'] = fuzz.gbellmf(splow.universe, 4910, 750, 5090)
        else:
            raise ValueError(f"Invalid adjustment value curve type: {adj_vals[0]}. Must be either 1.0 (best fit) or 2.0 (loose fit).")

        # SP2
        if adj_vals[1] == 1.0:
            log.info("Running 'best fit' custom MF shapes for SP2.")
            sp2['persists'] = fuzz.pimf(sp2.universe, -0.01, 0, 1000, 1200)
            sp2['breach'] = fuzz.pimf(sp2.universe, 1000, 1200, 1200, 1600)
            sp2['oblowout'] = fuzz.pimf(sp2.universe, 1200, 1600, 1600, 2400)
            sp2['blowout'] = fuzz.pimf(sp2.universe, 1600, 2400, 10000, 10000.1)
        elif adj_vals[1] == 2.0:
            log.info("Running 'loose fit' custom MF shapes for SP2.")
            sp2['persists'] = fuzz.gbellmf(sp2.universe, 500, 5, 500)
            sp2['breach'] = fuzz.gaussmf(sp2.universe, 1200, 150)
            sp2['oblowout'] = fuzz.gaussmf(sp2.universe, 1700, 250)
            sp2['blowout'] = fuzz.gbellmf(sp2.universe, 4200, 20, 6200)
        else:
            raise ValueError(f"Invalid adjustment value curve type: {adj_vals[1]}. Must be either 1.0 (best fit) or 2.0 (loose fit).")

        # Slope
        if adj_vals[2] == 1.0:
            log.info("Running 'best fit' custom MF shapes for Slope.")
            slope['flat'] = fuzz.pimf(slope.universe, -0.01, 0, 0.0002, 0.005)
            slope['can'] = fuzz.pimf(slope.universe, 0.0002, 0.005, 0.12, 0.15)
            slope['probably'] = fuzz.pimf(slope.universe, 0.12, 0.15, 0.17, 0.23)
            slope['cannot'] = fuzz.pimf(slope.universe, 0.17, 0.23, 1, 1.01)
        elif adj_vals[2] == 2.0:
            log.info("Running 'loose fit' custom MF shapes for Slope.")
            slope['flat'] = fuzz.gbellmf(slope.universe, 0.0025, 3, 0.0025)
            slope['can'] = fuzz.gbellmf(slope.universe, 0.07, 3, 0.06)
            slope['probably'] = fuzz.gbellmf(slope.universe, 0.035, 1.5, 0.165)
            slope['cannot'] = fuzz.gbellmf(slope.universe, 0.38, 14, 0.585)
        else:
            raise ValueError(f"Invalid adjustment value curve type: {adj_vals[2]}. Must be either 1.0 (best fit) or 2.0 (loose fit).")


    # build fis rule table
    log.info('Building FIS rule table')
    comb_ctrl = ctrl.ControlSystem([
        ctrl.Rule(ovc['none'], density['none']),
        ctrl.Rule(splow['cannot'], density['none']),
        ctrl.Rule(slope['cannot'], density['none']),
        ctrl.Rule(ovc['rare'] & sp2['persists'] & splow['can'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['persists'] & splow['probably'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['breach'] & splow['can'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['breach'] & splow['probably'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['oblowout'] & splow['can'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['oblowout'] & splow['probably'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['blowout'] & splow['can'] & ~slope['cannot'], density['none']),
        ctrl.Rule(ovc['rare'] & sp2['blowout'] & splow['probably'] & ~slope['cannot'], density['none']),
        ctrl.Rule(ovc['occasional'] & sp2['persists'] & splow['can'] & ~slope['cannot'], density['occasional']),
        ctrl.Rule(ovc['occasional'] & sp2['persists'] & splow['probably'] & ~slope['cannot'], density['occasional']),
        ctrl.Rule(ovc['occasional'] & sp2['breach'] & splow['can'] & ~slope['cannot'], density['occasional']),
        ctrl.Rule(ovc['occasional'] & sp2['breach'] & splow['probably'] & ~slope['cannot'], density['occasional']),
        ctrl.Rule(ovc['occasional'] & sp2['oblowout'] & splow['can'] & ~slope['cannot'], density['occasional']),
        ctrl.Rule(ovc['occasional'] & sp2['oblowout'] & splow['probably'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['occasional'] & sp2['blowout'] & splow['can'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['occasional'] & sp2['blowout'] & splow['probably'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['can'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['can'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['probably'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['probably'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['probably'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['can'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['can'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['probably'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['probably'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['probably'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['can'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['can'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['probably'] & slope['flat'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['probably'] & slope['can'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['probably'] & slope['probably'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['can'] & slope['flat'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['can'] & slope['can'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['can'] & slope['probably'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['probably'] & slope['flat'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['probably'] & slope['can'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['probably'] & slope['probably'], density['none']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['can'] & slope['flat'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['can'] & slope['can'], density['pervasive']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['probably'] & slope['flat'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['probably'] & slope['can'], density['pervasive']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['probably'] & slope['probably'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['can'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['can'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['probably'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['probably'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['probably'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['can'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['can'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['probably'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['probably'] & slope['can'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['probably'] & slope['probably'], density['rare']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['can'] & slope['flat'], density['rare']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['can'] & slope['can'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['can'] & slope['probably'], density['rare']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['probably'] & slope['flat'], density['rare']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['probably'] & slope['can'], density['rare']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['probably'] & slope['probably'], density['rare'])
    ])

    comb_fis = ctrl.ControlSystemSimulation(comb_ctrl)

    # calculate defuzzified centroid value for density 'none' MF group
    # this will be used to re-classify output values that fall in this group
    # important: will need to update the array (x) and MF values (mfx) if the
    # density 'none' values are changed in the model
    x_vals = np.arange(0, 45, 0.01)
    mfx = fuzz.trimf(x_vals, [0, 0, 0.1])
    defuzz_centroid = round(fuzz.defuzz(x_vals, mfx, 'centroid'), 6)

    progbar = ProgressBar(len(reachid_array), 50, "Combined FIS")
    counter = 0

    for i, reach_id in enumerate(reachid_array):

        capacity = 0.0
        # Only compute FIS if the reach has less than user-defined max drainage area.
        # this enforces a stream size threshold above which beaver dams won't persist and/or won't be built
        if not max_drainage_area or drain_array[i] < max_drainage_area:

            comb_fis.input['input1'] = veg_array[i]
            comb_fis.input['input2'] = hydq2_array[i]
            comb_fis.input['input3'] = hydlow_array[i]
            comb_fis.input['input4'] = slope_array[i]
            comb_fis.compute()
            capacity = comb_fis.output['result']

            # Combined FIS result cannot be higher than limiting vegetation FIS result
            if capacity > veg_array[i]:
                capacity = veg_array[i]

            if round(capacity, 6) == defuzz_centroid:
                capacity = 0.0

        elif drain_array[i] >= max_drainage_area and reachcode_array[i] == 33600:

            comb_fis.input['input1'] = veg_array[i]
            comb_fis.input['input2'] = hydq2_array[i]
            comb_fis.input['input3'] = hydlow_array[i]
            comb_fis.input['input4'] = slope_array[i]
            comb_fis.compute()
            capacity = comb_fis.output['result']

            # Combined FIS result cannot be higher than limiting vegetation FIS result
            if capacity > veg_array[i]:
                capacity = veg_array[i]

            if round(capacity, 6) == defuzz_centroid:
                capacity = 0.0

        count = capacity * (feature_values[reach_id]['iGeo_Len'] / 1000.0)
        count = 1.0 if 0 < count < 1 else count

        feature_values[reach_id][capacity_field] = round(capacity, 2)
        feature_values[reach_id][dam_count_field] = round(count, 2)

        counter += 1
        progbar.update(counter)

    '''VISUALIZE MFS'''
    log.info('Visualizing Adjusted MFs...')
    
    # oVC - should remain unchanged
    '''
    for label, color in zip(list(ovc.terms.keys()), ['r', 'orange', 'y', 'g', 'b']):
        plt.plot(ovc.universe, ovc.terms[label].mf, color=color, linewidth=1.5, label=label.capitalize())
    plt.xlabel('Dam Density (dams/km) from Veg FIS')
    plt.ylabel('Membership')
    plt.legend(title='Capacity:')
    plt.xlim(0, 40)
    plt.tight_layout()
    out_file_path = os.path.join(fis_dir, "fis-comb-ovc.png")
    plt.savefig(out_file_path)
    plt.close()
    '''
    # SPLow
    for label, color in zip(list(splow.terms.keys()), ['g', 'y', 'r']):
        plt.plot(splow.universe, splow.terms[label].mf, color=color, linewidth=1.5, label=label.capitalize())
    plt.xlabel('SPLow Baseflow (watts)')
    plt.ylabel('Membership')
    plt.legend()
    plt.xlim(100, 250)
    plt.tight_layout()
    out_file_path = os.path.join(fis_dir, "fis-comb-SPlow.png")
    plt.savefig(out_file_path)
    plt.close()

    # SP2
    for label, color in zip(list(sp2.terms.keys()), ['g', 'y', 'orange', 'r']):
        plt.plot(sp2.universe, sp2.terms[label].mf, color=color, linewidth=1.5, label=label.capitalize())
    plt.xlabel('SP2 Peak Flow (watts)')
    plt.ylabel('Membership')
    plt.legend()
    plt.xlim(500, 3000)
    plt.tight_layout()
    out_file_path = os.path.join(fis_dir, "fis-comb-SP2.png")
    plt.savefig(out_file_path)
    plt.close()

    # Slope
    for label, color in zip(list(slope.terms.keys()), ['b', 'g', 'y', 'r']):
        plt.plot(slope.universe, slope.terms[label].mf, color=color, linewidth=1.5, label=label.capitalize())
    plt.xlabel('Slope')
    plt.ylabel('Membership')
    plt.legend()
    plt.xlim(0, 0.5)
    plt.tight_layout()
    out_file_path = os.path.join(fis_dir, "fis-comb-slope.png")
    plt.savefig(out_file_path)
    plt.close()

    # Density - should remain unchanged
    '''
    fig, axs = plt.subplots(1, 1, figsize=(12, 4))
    for label, color in zip(list(density.terms.keys()), ['r', 'orange', 'y', 'g', 'b']):
        axs.plot(density.universe, density.terms[label].mf, color=color, linewidth=1.5, label=label.capitalize())
    plt.xlabel('Overall Dam Density (dams/km)')
    plt.ylabel('Membership')
    plt.legend(title='Capacity')
    plt.xlim(0, 40)
    plt.tight_layout()
    out_file_path = os.path.join(out_dir, "fis-comb-output-density.png")
    plt.savefig(out_file_path)
    plt.close()
    '''
    progbar.finish()
    log.info('Done')


def calculate_trap_scale(abcd: list = None, scale_factor: float = 1.0):
    """
    Helper function to scale trapezoidal membership functions (MFs)
    :param abcd: vertices (left-to-right) of the trapezoid
    :param scale_factor: the adjustment_value specified for this MF
    """
    # we keep the top of the trapezoid fixed (no shifting)
    b = abcd[1]
    c = abcd[2]
    # scale the left & right vertices by distance from b or c
    a = b - ((b - abcd[0]) * scale_factor)
    d = c + ((abcd[3] - c) * scale_factor)
    return [a, b, c, d]


def calculate_combined_fis(feature_values: dict, veg_fis_field: str, capacity_field: str, dam_count_field: str, max_drainage_area: float):
    """
    Calculate dam capacity and density using combined FIS
    :param feature_values: Dictionary of features keyed by ReachID and values are dictionaries of attributes
    :param veg_fis_field: Attribute containing the output of the vegetation FIS
    :param com_capacity_field: Attribute used to store the capacity result in feature_values
    :param com_density_field: Attribute used to store the capacity results in feature_values
    :param max_drainage_area: Reaches with drainage area greater than this threshold will have zero capacity
    :return: Insert the dam capacity and density values to the feature_values dictionary
    """

    log = Logger('Combined FIS')
    log.info('Initializing Combined FIS')

    if not max_drainage_area:
        log.warning('Missing max drainage area. Calculating combined FIS without max drainage threshold.')

    # get arrays for fields of interest
    feature_count = len(feature_values)
    reachid_array = np.zeros(feature_count, np.int64)
    reachcode_array = np.zeros(feature_count, np.int64)
    veg_array = np.zeros(feature_count, np.float64)
    hydq2_array = np.zeros(feature_count, np.float64)
    hydlow_array = np.zeros(feature_count, np.float64)
    slope_array = np.zeros(feature_count, np.float64)
    drain_array = np.zeros(feature_count, np.float64)

    counter = 0
    for reach_id, values in feature_values.items():
        reachid_array[counter] = reach_id
        reachcode_array[counter] = values['ReachCode']
        veg_array[counter] = values[veg_fis_field]
        hydlow_array[counter] = values['iHyd_SPLow']
        hydq2_array[counter] = values['iHyd_SP2']
        slope_array[counter] = values['iGeo_Slope']
        drain_array[counter] = values['iGeo_DA']
        counter += 1

    # Adjust inputs to be within FIS membership range
    veg_array[veg_array < 0] = 0
    veg_array[veg_array > 45] = 45

    hydq2_array[hydq2_array < 0] = 0.0001
    hydq2_array[hydq2_array > 10000] = 10000

    hydlow_array[hydlow_array < 0] = 0.0001
    hydlow_array[hydlow_array > 10000] = 10000
    slope_array[slope_array > 1] = 1

    # create antecedent (input) and consequent (output) objects to hold universe variables and membership functions
    ovc = ctrl.Antecedent(np.arange(0, 45, 0.01), 'input1')
    sp2 = ctrl.Antecedent(np.arange(0, 10000, 1), 'input2')
    splow = ctrl.Antecedent(np.arange(0, 10000, 1), 'input3')
    slope = ctrl.Antecedent(np.arange(0, 1, 0.0001), 'input4')
    density = ctrl.Consequent(np.arange(0, 45, 0.01), 'result')

    # build membership functions for each antecedent and consequent object
    ovc['none'] = fuzz.trimf(ovc.universe, [0, 0, 0.1])
    ovc['rare'] = fuzz.trapmf(ovc.universe, [0, 0.1, 0.5, 1.5])
    ovc['occasional'] = fuzz.trapmf(ovc.universe, [0.5, 1.5, 4, 8])
    ovc['frequent'] = fuzz.trapmf(ovc.universe, [4, 8, 12, 25])
    ovc['pervasive'] = fuzz.trapmf(ovc.universe, [12, 25, 45, 45])

    sp2['persists'] = fuzz.trapmf(sp2.universe, [0, 0, 1000, 1200])
    sp2['breach'] = fuzz.trimf(sp2.universe, [1000, 1200, 1600])
    sp2['oblowout'] = fuzz.trimf(sp2.universe, [1200, 1600, 2400])
    sp2['blowout'] = fuzz.trapmf(sp2.universe, [1600, 2400, 10000, 10000])

    splow['can'] = fuzz.trapmf(splow.universe, [0, 0, 150, 175])
    splow['probably'] = fuzz.trapmf(splow.universe, [150, 175, 180, 190])
    splow['cannot'] = fuzz.trapmf(splow.universe, [180, 190, 10000, 10000])

    slope['flat'] = fuzz.trapmf(slope.universe, [0, 0, 0.0002, 0.005])
    slope['can'] = fuzz.trapmf(slope.universe, [0.0002, 0.005, 0.12, 0.15])
    slope['probably'] = fuzz.trapmf(slope.universe, [0.12, 0.15, 0.17, 0.23])
    slope['cannot'] = fuzz.trapmf(slope.universe, [0.17, 0.23, 1, 1])

    density['none'] = fuzz.trimf(density.universe, [0, 0, 0.1])
    density['rare'] = fuzz.trapmf(density.universe, [0, 0.1, 0.5, 1.5])
    density['occasional'] = fuzz.trapmf(density.universe, [0.5, 1.5, 4, 8])
    density['frequent'] = fuzz.trapmf(density.universe, [4, 8, 12, 25])
    density['pervasive'] = fuzz.trapmf(density.universe, [12, 25, 45, 45])

    # build fis rule table
    log.info('Building FIS rule table')
    comb_ctrl = ctrl.ControlSystem([
        ctrl.Rule(ovc['none'], density['none']),
        ctrl.Rule(splow['cannot'], density['none']),
        ctrl.Rule(slope['cannot'], density['none']),
        ctrl.Rule(ovc['rare'] & sp2['persists'] & splow['can'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['persists'] & splow['probably'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['breach'] & splow['can'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['breach'] & splow['probably'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['oblowout'] & splow['can'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['oblowout'] & splow['probably'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['rare'] & sp2['blowout'] & splow['can'] & ~slope['cannot'], density['none']),
        ctrl.Rule(ovc['rare'] & sp2['blowout'] & splow['probably'] & ~slope['cannot'], density['none']),
        ctrl.Rule(ovc['occasional'] & sp2['persists'] & splow['can'] & ~slope['cannot'], density['occasional']),
        ctrl.Rule(ovc['occasional'] & sp2['persists'] & splow['probably'] & ~slope['cannot'], density['occasional']),
        ctrl.Rule(ovc['occasional'] & sp2['breach'] & splow['can'] & ~slope['cannot'], density['occasional']),
        ctrl.Rule(ovc['occasional'] & sp2['breach'] & splow['probably'] & ~slope['cannot'], density['occasional']),
        ctrl.Rule(ovc['occasional'] & sp2['oblowout'] & splow['can'] & ~slope['cannot'], density['occasional']),
        ctrl.Rule(ovc['occasional'] & sp2['oblowout'] & splow['probably'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['occasional'] & sp2['blowout'] & splow['can'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['occasional'] & sp2['blowout'] & splow['probably'] & ~slope['cannot'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['can'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['can'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['probably'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['probably'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['frequent'] & sp2['persists'] & splow['probably'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['can'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['can'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['probably'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['probably'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['frequent'] & sp2['breach'] & splow['probably'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['can'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['can'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['probably'] & slope['flat'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['probably'] & slope['can'], density['occasional']),
        ctrl.Rule(ovc['frequent'] & sp2['oblowout'] & splow['probably'] & slope['probably'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['can'] & slope['flat'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['can'] & slope['can'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['can'] & slope['probably'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['probably'] & slope['flat'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['probably'] & slope['can'], density['rare']),
        ctrl.Rule(ovc['frequent'] & sp2['blowout'] & splow['probably'] & slope['probably'], density['none']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['can'] & slope['flat'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['can'] & slope['can'], density['pervasive']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['probably'] & slope['flat'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['probably'] & slope['can'], density['pervasive']),
        ctrl.Rule(ovc['pervasive'] & sp2['persists'] & splow['probably'] & slope['probably'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['can'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['can'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['probably'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['probably'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['breach'] & splow['probably'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['can'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['can'] & slope['can'], density['frequent']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['can'] & slope['probably'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['probably'] & slope['flat'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['probably'] & slope['can'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['oblowout'] & splow['probably'] & slope['probably'], density['rare']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['can'] & slope['flat'], density['rare']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['can'] & slope['can'], density['occasional']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['can'] & slope['probably'], density['rare']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['probably'] & slope['flat'], density['rare']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['probably'] & slope['can'], density['rare']),
        ctrl.Rule(ovc['pervasive'] & sp2['blowout'] & splow['probably'] & slope['probably'], density['rare'])
    ])

    comb_fis = ctrl.ControlSystemSimulation(comb_ctrl)

    # calculate defuzzified centroid value for density 'none' MF group
    # this will be used to re-classify output values that fall in this group
    # important: will need to update the array (x) and MF values (mfx) if the
    # density 'none' values are changed in the model
    x_vals = np.arange(0, 45, 0.01)
    mfx = fuzz.trimf(x_vals, [0, 0, 0.1])
    defuzz_centroid = round(fuzz.defuzz(x_vals, mfx, 'centroid'), 6)

    progbar = ProgressBar(len(reachid_array), 50, "Combined FIS")
    counter = 0

    for i, reach_id in enumerate(reachid_array):

        capacity = 0.0
        # Only compute FIS if the reach has less than user-defined max drainage area.
        # this enforces a stream size threshold above which beaver dams won't persist and/or won't be built
        if not max_drainage_area or drain_array[i] < max_drainage_area:

            comb_fis.input['input1'] = veg_array[i]
            comb_fis.input['input2'] = hydq2_array[i]
            comb_fis.input['input3'] = hydlow_array[i]
            comb_fis.input['input4'] = slope_array[i]
            comb_fis.compute()
            capacity = comb_fis.output['result']

            # Combined FIS result cannot be higher than limiting vegetation FIS result
            if capacity > veg_array[i]:
                capacity = veg_array[i]

            if round(capacity, 6) == defuzz_centroid:
                capacity = 0.0

        elif drain_array[i] >= max_drainage_area and reachcode_array[i] == 33600:

            comb_fis.input['input1'] = veg_array[i]
            comb_fis.input['input2'] = hydq2_array[i]
            comb_fis.input['input3'] = hydlow_array[i]
            comb_fis.input['input4'] = slope_array[i]
            comb_fis.compute()
            capacity = comb_fis.output['result']

            # Combined FIS result cannot be higher than limiting vegetation FIS result
            if capacity > veg_array[i]:
                capacity = veg_array[i]

            if round(capacity, 6) == defuzz_centroid:
                capacity = 0.0

        count = capacity * (feature_values[reach_id]['iGeo_Len'] / 1000.0)
        count = 1.0 if 0 < count < 1 else count

        feature_values[reach_id][capacity_field] = round(capacity, 2)
        feature_values[reach_id][dam_count_field] = round(count, 2)

        counter += 1
        progbar.update(counter)

    progbar.finish()
    log.info('Done')


def main():
    """ Combined FIS
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('database', help='BRAT SQLite database', type=argparse.FileType('r'))
    parser.add_argument('maxdrainage', help='Maximum drainage area', type=float)
    parser.add_argument('--verbose', help='(optional) verbose logging mode', action='store_true', default=False)
    args = dotenv.parse_args_env(parser)

    # Initiate the log file
    logg = Logger("Combined FIS")
    logfile = os.path.join(os.path.dirname(args.network.name), "combined_fis.log")
    logg.setup(logPath=logfile, verbose=args.verbose)

    try:
        combined_fis_custom(args.database.name, 'existing', 'EX', args.maxdrainage)
        # combined_fis_custom(args.network.name, 'historic', 'HPE', args.maxdrainage)

    except Exception as ex:
        logg.error(ex)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
