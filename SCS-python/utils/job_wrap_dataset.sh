#!/bin/bash
#SBATCH -A EUHPC_E02_036      # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
#SBATCH --qos=boost_qos_dbg
#SBATCH --time 00:30:00        # format: HH:MM:SS
#SBATCH --nodes=1              # nodes
#SBATCH --ntasks-per-node=1    # 32cpu+4gpu per nodo -> 128 virt
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1           # 1 gpus per node out of 4
#SBATCH --mem=120000          # memory per node out of 512000 MB
#SBATCH --job-name=wrap-dataset
#SBATCH -e JOB.err
#SBATCH -o JOB.out

#Module load
module purge

#Activate environment
source /leonardo/home/userexternal/apacini0/.envs/scs-env/bin/activate

data_path_regex="$1"

python /leonardo_work/IscrC_ASIM/SCS-New-Scripts/Utils/wrap_npy_dataset.py "$data_path_regex"
