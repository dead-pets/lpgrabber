#!/bin/bash

source_dir=${1:-.}
target_dir=${2:-.}

pip install ipython nbconvert jupyter-client jupyter-core ipykernel

cd $target_dir & ipython nbconvert --to=html --ExecutePreprocessor.enabled=True --ExecutePreprocessor.allow_errors=True $source_dir/*.ipynb
