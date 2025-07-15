# PREREQUISITES:
# Python 3.10.x
# Virtual environment activated with rs tools installed
# The brat package and its dependencies are installed in the environment
# Script executed from: /packages/brat

# We need these environment variables to be set:
# $RS = path to the RS data directory
# $HYDRO = path to the HYDRO data directory
# $ANTHRO = path to the ANTHRO data directory
# $VBET = path to the VBET data directory
# $HUC10 = HUC10 code for the watershed to run BRAT on
# $OUT_DIR = path to the output directory where BRAT results will be saved

'''TODO: write this into a proper script with permissions etc.
            Currently functioning as a place to stash commands to run manually.'''

cd /Users/evan/Code/OSU-EB3-REU/sqlBRAT/riverscapes-tools-fork/packages/brat

'''TODO: write a command to take inputs for these variables
            so that this script can be generalized.'''

echo "———Inputs Paths:———"
echo "RS: $RS"
echo "HYDRO: $HYDRO"
echo "ANTHRO: $ANTHRO"
echo "VBET: $VBET"
echo "———Other Vars:———"
echo "HUC10: $HUC10"
echo "OUTPUT_DIR: $OUTPUT_DIR"

# build and install
python setup.py build
python setup.py install

# manual copying for some reason
cp sqlbrat/layer_descriptions.json /Users/evan/anaconda3/envs/sqlbrat/lib/python3.10/site-packages/sqlbrat-5.1.5-py3.10.egg/sqlbrat
cp sqlbrat/brat_report.css /Users/evan/anaconda3/envs/sqlbrat/lib/python3.10/site-packages/sqlbrat-5.1.5-py3.10.egg/sqlbrat
cp -R database /Users/evan/anaconda3/envs/sqlbrat/lib/python3.10/site-packages/sqlbrat-5.1.5-py3.10.egg

echo "Copied layer_descriptions, css, and database into EGG"

# Run the tool for Lower Siletz

echo "Running BRAT for HUC $HUC10"

brat $HUC10 \
    $RS/topography/dem_hillshade.tif \
    $HYDRO/outputs/hydro.gpkg/vwReaches \
    $HYDRO/outputs/hydro.gpkg/IGOGeometry \
    $HYDRO/outputs/hydro.gpkg/vwDgos \
    $ANTHRO/outputs/anthro.gpkg/vwReaches \
    $ANTHRO/outputs/anthro.gpkg/IGOGeometry \
    $ANTHRO/outputs/anthro.gpkg/vwDgos \
    $RS/vegetation/existing_veg.tif \
    $RS/vegetation/historic_veg.tif \
    $VBET/outputs/vbet.gpkg/vbet_full \
    30 \
    100 \
    $OUT_DIR \
    --reach_codes 33400,33600,33601,33603,46000,46003,46006,46007 \
    --canal_codes 33600,33601,33603 \
    --peren_codes 46006 \
    --flow_areas $RS/hydrology/nhdplushr.gpkg/NHDArea \
    --waterbodies $RS/hydrology/nhdplushr.gpkg/NHDWaterbody \
    --verbose