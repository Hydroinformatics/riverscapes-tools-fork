# PREREQUISITES:
# Python 3.10.x
# The brat package and its dependencies are installed in the environment
# Script executed from: /packages/brat

# We need these environment variables to be set
# input sources (paths to directories):
(: "${RS?}")
(: "${HYDRO?}")
(: "${ANTHRO?}")
(: "${VBET?}")
# logistical:
(: "${ENV_EGG?}")
(: "${OUTPUT_DIR?}")

echo "RS_DIR: $RS_DIR"
echo "HYDRO_DIR: $HYDRO_DIR"
echo "ANTHRO_DIR: $ANTHRO_DIR"
echo "VBET_DIR: $VBET_DIR"

# build and install
python setup.py build
python setup.py install

# manual copying for some reason
cp sqlbrat/layer_descriptions.json \
    /Users/evan/anaconda3/envs/sqlbrat/lib/python3.10/site-packages/sqlbrat-5.1.5-py3.10.egg/sqlbrat
cp -R database \
    /Users/evan/anaconda3/envs/sqlbrat/lib/python3.10/site-packages/sqlbrat-5.1.5-py3.10.egg
cp sqlbrat/brat_report.css /Users/evan/anaconda3/envs/sqlbrat/lib/python3.10/site-packages/sqlbrat-5.1.5-py3.10.egg/sqlbrat


# Run the tool for Lower Siletz
brat 1710020407 \
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
    $OUTPUT_DIR \
    --reach_codes 33400,33600,33601,33603,46000,46003,46006,46007 \
    --canal_codes 33600,33601,33603 \
    --peren_codes 46006,55800,33400 \
    --flow_areas $RS/hydrology/nhdplushr.gpkg/NHDArea \
    --waterbodies $RS/hydrology/nhdplushr.gpkg/NHDWaterbody \
    --verbose