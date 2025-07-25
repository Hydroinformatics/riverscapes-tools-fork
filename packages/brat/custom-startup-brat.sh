# PREREQUISITES:
# Python 3.10.x
# Virtual environment activated with rs tools installed
# The brat package and its dependencies are installed in the environment
# Script executed from: /packages/brat

# We need these environment variables to be set:
# $ANTHRO = path to the ANTHRO data directory
# $HYDRO = path to the HYDRO data directory
# $RS = path to the RS data directory
# $VBET = path to the VBET data directory
# $HUC10 = HUC10 code for the watershed to run BRAT on
# $OUTPUT_DIR = path to the output directory where BRAT results will be saved

'''TODO: write this into a proper script with permissions etc.
            Currently functioning as a place to stash commands to run manually.'''

cd /Users/evan/Code/OSU-EB3-REU/sqlBRAT/riverscapes-tools-fork/packages/brat

'''TODO: write a command to take inputs for these variables
            so that this script can be generalized.'''

echo "———Inputs Paths:———"
echo "ANTHRO: $ANTHRO"
echo "HYDRO: $HYDRO"
echo "RS: $RS"
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
    $HYDRO/outputs/hydro.gpkg/vwIGOs \
    $HYDRO/outputs/hydro.gpkg/vwDGOs \
    $ANTHRO/outputs/anthro.gpkg/vwReaches \
    $ANTHRO/outputs/anthro.gpkg/vwIgos \
    $ANTHRO/outputs/anthro.gpkg/vwDgos \
    $RS/vegetation/existing_veg.tif \
    $RS/vegetation/historic_veg.tif \
    $VBET/outputs/vbet.gpkg/vbet_full \
    30.0 \
    100.0 \
    $OUTPUT_DIR \
    --reach_codes 33400,33600,33601,33603,46000,46003,46006,46007 \
    --canal_codes 33600,33601,33603 \
    --peren_codes 46006 \
    --flow_areas $RS/hydrology/nhdplushr.gpkg/NHDArea \
    --waterbodies $RS/hydrology/nhdplushr.gpkg/NHDWaterbody \
    --max_waterbody 0.001 \
    --verbose

'''
usage: brat [-h] [--reach_codes REACH_CODES] [--canal_codes CANAL_CODES]
            [--peren_codes PEREN_CODES] [--flow_areas FLOW_AREAS]
            [--waterbodies WATERBODIES] [--max_waterbody MAX_WATERBODY] [--meta META]
            [--verbose] [--debug]
            huc hillshade hydro_flowlines hydro_igos hydro_dgos anthro_flowlines
            anthro_igos anthro_dgos existing_veg historical_veg valley_bottom
            streamside_buffer riparian_buffer output_folder

Build the inputs for an eventual brat_run:

positional arguments:
  huc                   huc input
  hillshade             hillshade input
  hydro_flowlines       hydro flowlines input
  hydro_igos            hydro igos input
  hydro_dgos            hydro dgos input
  anthro_flowlines      anthro flowlines input
  anthro_igos           anthro igos input
  anthro_dgos           anthro dgos input
  existing_veg          existing_veg input
  historical_veg        historical_veg input
  valley_bottom         Valley bottom shapeFile
  streamside_buffer     streamside_buffer input
  riparian_buffer       riparian_buffer input
  output_folder         output_folder input

options:
  -h, --help            show this help message and exit
  --reach_codes REACH_CODES
                        Comma delimited reach codes (FCode) to retain when filtering
                        features. Omitting this option retains all features.
  --canal_codes CANAL_CODES
                        Comma delimited reach codes (FCode) representing canals. Omitting
                        this option retains all features.
  --peren_codes PEREN_CODES
                        Comma delimited reach codes (FCode) representing perennial features
  --flow_areas FLOW_AREAS
                        (optional) path to the flow area polygon feature class containing
                        artificial paths
  --waterbodies WATERBODIES
                        (optional) waterbodies input
  --max_waterbody MAX_WATERBODY
                        (optional) maximum size of small waterbody artificial flows to be
                        retained
  --meta META           riverscapes project metadata as comma separated key=value pairs
  --verbose             (optional) a little extra logging
  --debug               (optional) more output about things like memory usage. There is a
                        performance cost
'''