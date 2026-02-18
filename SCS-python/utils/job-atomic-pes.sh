#!/bin/bash
#SBATCH -A IscrB_TMD-MX      # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
#SBATCH --qos=normal    # sottopartizione di debug 2h_max 2nodi_max 
#SBATCH --qos=boost_qos_dbg
#SBATCH --time 00:30:00        # format: HH:MM:SS
#SBATCH --nodes=1              # nodes
#SBATCH --ntasks-per-node=1    # 32cpu+4gpu per nodo -> 128 virt
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1           # 1 gpus per node out of 4
#SBATCH --mem=120000           # memory per node out of 512000 MB
#SBATCH --job-name=dp-pes
#SBATCH -e JOB.err
#SBATCH -o JOB.out

#Module load
module purge
source /leonardo/home/userexternal/apacini0/.envs/dp-env/bin/activate

#Input parameters
modelpath=$1
types=$2
maxR=$3
nBins=$4

python /leonardo_work/IscrC_ASIM/SCS-New-Scripts/SCS-SiCOH/Analysis/ase_atomic_pes.py $modelpath $types $maxR $nBins
