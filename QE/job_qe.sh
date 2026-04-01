#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=1:00:00
#SBATCH --exclusive
#SBATCH --gres=gpu:1
#SBATCH -A IscrC_MeThioML     # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
###SBATCH --qos=boost_qos_dbg
#SBATCH --job-name=SCS-labelling
#SBATCH -e JOB.err
#SBATCH -o JOB.out

# Load modules/libraries
module purge
module load profile/chem-phys
module load quantum-espresso/7.4.1--hpcx-mpi--2.19--nvhpc--24.5-openblas
 
# Define useful env variables
export OMP_NUM_THREADS=8
export OMP_PLACES=cores
export OMP_PROC_BIND=close

for pwi in *.pwi
do
pwo=${pwi//.pwi/.pwo}
if ! test -f $pwo
then

mpirun -np 1 --map-by socket:PE=8 --rank-by core pw.x -nk 1 < $pwi > $pwo

fi
done
