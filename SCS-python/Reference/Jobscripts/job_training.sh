#!/bin/bash
#SBATCH -A EUHPC_E02_036      # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
#SBATCH --time 24:00:00        # format: HH:MM:SS
#SBATCH --nodes=1              # nodes
#SBATCH --ntasks-per-node=1    # 32cpu+4gpu per nodo -> 128 virt
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1           # 1 gpus per node out of 4
#SBATCH --mem=120000          # memory per node out of 512000 MB
#SBATCH --job-name=scsT
#SBATCH -e JOB.err
#SBATCH -o JOB.out

#Module loading for deepmd
module purge
module load profile/chem-phys
module load deepmd/2.2.6

export SRUN_CPU_PER_TASK=${SLURM_CPUS_PER_TASK}
export KMP_AFFINITY=compact

#Training from scratch or restart training session
if test -f checkpoint
then
        dp train -l training.log --restart model.ckpt input.json > training.out
else
        dp train -l training.log input.json > training.out
fi

#Freeze final checkpoint
dp freeze -o graph.pb > freeze.out

#Compres the freezed model (faster for inference)
dp compress -i graph.pb -o compressed.pb > compress.out
