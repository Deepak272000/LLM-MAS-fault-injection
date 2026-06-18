#!/bin/bash
#SBATCH --job-name=currencyagent_fi
#SBATCH --output=currencyagent_%j.log
#SBATCH --error=currencyagent_%j.err
#SBATCH --ntasks=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00

VENV=/speed-scratch/$USER/LLM-MAS/src/shippingservice/.venv
PYTHON=$VENV/bin/python

cd /speed-scratch/$USER/LLM-MAS/src/currencyagent
$PYTHON -m pip install -q python-dotenv
$PYTHON test_fault_injection.py
