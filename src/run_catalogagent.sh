#!/bin/bash
#SBATCH --job-name=catalogagent_fi
#SBATCH --output=catalogagent_%j.log
#SBATCH --error=catalogagent_%j.err
#SBATCH --ntasks=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00

VENV=/speed-scratch/$USER/LLM-MAS/src/shippingservice/.venv
PYTHON=$VENV/bin/python

cd /speed-scratch/$USER/LLM-MAS/src/productcatalogagent
$PYTHON -m pip install -q python-dotenv
$PYTHON test_fault_injection.py
