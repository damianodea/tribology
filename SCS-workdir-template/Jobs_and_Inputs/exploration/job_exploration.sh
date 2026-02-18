#!/bin/bash
#SBATCH -A AIFAC_5C0_157      # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
###SBATCH --qos=boost_qos_dbg
#SBATCH --time 24:00:00        # format: HH:MM:SS
#SBATCH --nodes=1              # nodes
#SBATCH --ntasks-per-node=1    # 32cpu+4gpu per nodo -> 128 virt
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1           # 1 gpus per node out of 4
#SBATCH --mem=120000           # memory per node out of 512000 MB
#SBATCH --job-name=SCS-exploration
#SBATCH -e JOB.err
#SBATCH -o JOB.out

#Load environment
module purge
source /leonardo_scratch/fast/EUHPC_A04_113/Alberto/MLIP/MACE/env_mace/bin/activate

#Module load
module purge
module load openmpi/4.1.6--gcc--12.2.0 cuda/12.1 cudnn/8.9.7.29-12--gcc--12.2.0-cuda-12.1
