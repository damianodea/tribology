#!/bin/bash
#SBATCH -A EUHPC_E02_036      # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
###SBATCH --qos=boost_qos_dbg
#SBATCH --time 02:30:00        # format: HH:MM:SS
#SBATCH --nodes=1              # nodes
#SBATCH --ntasks-per-node=1    # 32cpu+4gpu per nodo -> 128 virt
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1           # 1 gpus per node out of 4
#SBATCH --mem=120000          # memory per node out of 512000 MB
#SBATCH --job-name=dpTest
#SBATCH -e JOB.err
#SBATCH -o JOB.out

#Module load
module purge
module load profile/chem-phys
module load deepmd/2.2.6

export SRUN_CPU_PER_TASK=${SLURM_CPUS_PER_TASK}
export KMP_AFFINITY=compact

#Test model against training and validation data

model_path=$1
data_path=$2

#Test against training data
dp test -m $model_path -s $data_path/Train -d test-train

#Test against validation data
dp test -m $model_path -s $data_path/Valid -d test-valid

#Parity plot script
parity_plot_py=/leonardo/home/userexternal/apacini0/SCS-python/utils/parity_plot.py

#python env with dpdata and ase
source /leonardo/home/userexternal/apacini0/.envs/dp-env/bin/activate

#Execute parity plot on training forces
python $parity_plot_py  test-train.f.out  $data_path/Train  parity_plot_train.png

#Execute parity plot on testing forces
python $parity_plot_py  test-valid.f.out  $data_path/Valid  parity_plot_valid.png
