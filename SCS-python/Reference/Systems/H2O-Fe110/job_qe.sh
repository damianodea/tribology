#!/bin/bash
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=8
#SBATCH --time=24:00:00
#SBATCH --exclusive
#SBATCH --gres=gpu:4
#SBATCH -A IscrB_TMD-MX      # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
#SBATCH --job-name=labCOUM
#SBATCH -e JOB.err
#SBATCH -o JOB.out

# Module load for Quantum Espresso
module purge
module load profile/chem-phys
module load quantum-espresso/7.2--openmpi--4.1.4--nvhpc--23.1-openblas-cuda-11.8

export OMP_NUM_THREADS=8
export OMP_PLACES=cores
export OMP_PROC_BIND=close