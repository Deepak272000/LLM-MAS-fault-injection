#!/bin/bash
#SBATCH --job-name=stability_analysis
#SBATCH --output=stability_%j.log
#SBATCH --error=stability_%j.err
#SBATCH --ntasks=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00

cd /speed-scratch/$USER/LLM-MAS
source .venv/bin/activate
cd src
python stability_analysis.py
