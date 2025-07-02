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

## Overview of Changes (last updated: 2025-07-02)

#### Tweaks to fix bugs when running locally:

__filegdb.py__
Line 59 caused an error attempting to edit a sealed object. New code is present in the filegdb.py in this repo (/lib/commons/rscommons).

__packages/brat/sqlbrat/setup.py__
Added subfolders to the packages on Line 39. New code is present in the repo.

#### [future model fine-tuning?]
