#!/bin/bash
#SBATCH --job-name=stability_analysis
#SBATCH --output=stability_%j.log
#SBATCH --error=stability_%j.err
#SBATCH --ntasks=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00

VENV=/speed-scratch/$USER/LLM-MAS/src/shippingservice/.venv
PYTHON=$VENV/bin/python

cd /speed-scratch/$USER/LLM-MAS

# Install missing package into the venv explicitly
$PYTHON -m pip install -q python-dotenv

cd src
$PYTHON stability_analysis.py
