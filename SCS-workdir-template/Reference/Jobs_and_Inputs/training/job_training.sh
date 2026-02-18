#!/bin/bash
#SBATCH -A AIFAC_5C0_157      # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
#SBATCH --time 24:00:00        # format: HH:MM:SS
#SBATCH --nodes=1              # nodes
#SBATCH --ntasks-per-node=1    # 32cpu+4gpu per nodo -> 128 virt
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1           # 1 gpus per node out of 4
#SBATCH --mem=120000          # memory per node out of 512000 MB
#SBATCH --job-name=SCS-training
#SBATCH -e JOB.err
#SBATCH -o JOB.out

#Source environment with MACE
source /leonardo_scratch/fast/EUHPC_A04_113/Alberto/MLIP/MACE/env_mace/bin/activate

#Module load
module purge
module load cuda/12.1

#Set env variable OMP_NUM_THREADS
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

#Run training
srun mace_run_train --config input.yaml

#Run conversion for mliap-LAMMPS model
if test -f MACE_stagetwo.model 
then
    mace_create_lammps_model  MACE_stagetwo.model --dtype=float32 --format=mliap --head=Default
elif test -f MACE.model
then
    mace_create_lammps_model  MACE.model --dtype=float32 --format=mliap --head=Default
else
    echo "Model file not found!"
    exit 1
fi
