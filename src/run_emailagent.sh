#!/bin/bash
#SBATCH --job-name=emailagent_fi
#SBATCH --output=emailagent_%j.log
#SBATCH --error=emailagent_%j.err
#SBATCH --ntasks=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00

VENV=/speed-scratch/$USER/LLM-MAS/src/shippingservice/.venv
PYTHON=$VENV/bin/python

# Always pull latest before running so the fix is guaranteed to be present
git -C /speed-scratch/$USER/LLM-MAS pull origin deepak/fault-injection

cd /speed-scratch/$USER/LLM-MAS/src/emailserviceagent
$PYTHON -m pip install -q python-dotenv
$PYTHON test_fault_injection.py
