#!/bin/bash
#SBATCH --job-name=cross_agent_prop
#SBATCH --output=cross_agent_%j.log
#SBATCH --error=cross_agent_%j.err
#SBATCH --ntasks=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00

VENV=/speed-scratch/$USER/LLM-MAS/src/shippingservice/.venv
PYTHON=$VENV/bin/python

cd /speed-scratch/$USER/LLM-MAS/src
$PYTHON -m pip install -q python-dotenv
$PYTHON cross_agent_propagation.py
