#!/bin/bash

source_dir=${1:-.}
target_dir=${2:-.}

# On Ubuntu you need these packages to be installed
# sudo apt-get install libpng-dev libjpeg8-dev libfreetype6-dev
pip install ipython nbconvert jupyter-client jupyter-core ipykernel matplotlib numexpr

cd $target_dir && ipython nbconvert --to=html --ExecutePreprocessor.enabled=True --ExecutePreprocessor.allow_errors=True $source_dir/*.ipynb
