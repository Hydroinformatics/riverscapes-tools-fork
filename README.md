# Riverscapes Tools - Fork

This is a monorepo housing the python open-source GIS tools for Riverscapes.
It is a fork that includes some tweaks needed to run the tools locally.
See the [original repo](https://github.com/Riverscapes/riverscapes-tools) for the latest changes and fully original code.

* [Riverscapes Context](./packages/rscontext)
* [BRAT](./packages/brat)
* [VBET](./packages/vbet)

## How to Use sqlBRAT
My personal experience setting up sqlBRAT locally as of June 2025:
https://oregonstate.box.com/s/ad54dxkhnnmaaj159awk7ndgt6n5rjtb
(Future TODO: I may move this documentation locally onto the repo)

## Overview of Changes (last updated: 2025-07-10)
*See commit history for proper log of changes*

### Tweaks to fix bugs when running locally:

**filegdb.py**
Line 59 caused an error attempting to edit a sealed object. New code is present in the filegdb.py in this repo (/lib/commons/rscommons).

**setup.py files**
Added subfolders (e.g. ./utils) to the setup.py packages for BRAT, Anthro, Hydro, and VBET. New code is present in the repo.

**Change NHDPlusV2 Paths**
Changed the manual paths to the NHDPlusV2 gpkg contents to match the names of the 2022 Oregon snapshot.
If you're not running BRAT with the same input file (e.g. for a different state), you'll need to change this.


### [future model fine-tuning?]
