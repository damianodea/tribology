#!/bin/bash
#SBATCH -A IscrC_MeThioML      # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
###SBATCH --qos=normal    # sottopartizione di debug 2h_max 2nodi_max
###SBATCH --qos=boost_qos_dbg   #sottopartizione che limita a 8 ore walltime
#SBATCH --time 08:00:00        # format: HH:MM:SS
#SBATCH --nodes=1              # nodes: ok visto che sono conti veloci ed è meglio non aspettare la coda di leonardo
#SBATCH --ntasks-per-node=2    # 32cpu+4gpu per nodo -> 128 virt
#SBATCH --cpus-per-task=8       # this is per task. increase to 16 in case
#SBATCH --gres=gpu:2            # this is in total. only 1 gpu per mpi process for lammps: ok visto che sono conti veloci ed è meglio non aspettare la coda di leonardo
#SBATCH --mem=120000           # memory per node out of 512000 MB
#SBATCH --job-name=lmp_mace
#SBATCH -e JOB_T_%j.err
#SBATCH -o JOB_T_%j.out

#Module loading for MACE
module load cuda/12.2
module load gcc/12.2.0
module load openmpi/4.1.6--gcc--12.2.0-cuda-12.2

#source /leonardo/pub/userexternal/epedrett/.venv/mace/bin/activate
#source /leonardo/pub/userexternal/epedrett/.venv/macedev/bin/activate

# Activate your Python environment if needed (for MACE): modify accordingly to Ferrari cluster environments
source /leonardo/pub/userexternal/epedrett/.venv/mace/bin/activate

# Set variable lmp with LAMMPS executable
#lmp='/leonardo/home/userexternal/prestucc/lammps_mace/build-mliap/lmp'
lmp='/leonardo/pub/userexternal/epedrett/software/lammps-mace-mliap/build/lmp'
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/leonardo/pub/userexternal/epedrett/software/lammps-mace-mliap/build

# Get LAMMPS input file
LAMMPS_INPUT=2_T_ramp.in         # <-- name of your LAMMPS input script

# Run LAMMPS with multi-processing: distributed memory, processes communicate using message passing
#mpirun -np 8 lmp -in $LAMMPS_INPUT

## or multi-threading, suggested for MACE and LAMMPS: the program parallelizes work internally (shared memory)
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
# Run: 2 MPI tasks, each with 8 CPUs and 1 GPU (16 CPUs and 2 GPUs in total)
mpirun -np 2 $lmp -k on g 8 -sf kk -pk kokkos newton on neigh half -in $LAMMPS_INPUT > ${LAMMPS_INPUT//.in}_$SLURM_JOB_ID.out
