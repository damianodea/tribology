#!/bin/bash
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=8
#SBATCH --time=24:00:00
#SBATCH --gres=gpu:4
#SBATCH --mem=480000
#SBATCH -A AIFAC_5C0_157      # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
#SBATCH --job-name=qe
#SBATCH -e JOB.err
#SBATCH -o JOB.out

# Load modules with libraries
module purge
module load fftw/3.3.10--openmpi--4.1.4--nvhpc--23.1
module load openblas/0.3.21--nvhpc--23.1
module load openmpi/4.1.4--nvhpc--23.1-cuda-11.8 
module load nvhpc/23.1  

# Export variables
export OMP_NUM_THREADS=8
export OMP_PLACES=cores
export OMP_PROC_BIND=close

# QE executable
pw=/leonardo/home/userexternal/apacini0/q-e-qe-7.3.1/build/bin/pw.x

# Run QE distributed on 8 MPI processes and bind 8 cpu per process
# Distribute MPI on K points using QE internal parallelism
mpirun -np 8 --map-by socket:PE=8 --rank-by core $pw -nk 4 < input.pwi >> output.pwo
