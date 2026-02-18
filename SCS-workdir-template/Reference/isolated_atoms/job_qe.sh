#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --exclusive
#SBATCH --gres=gpu:4
#SBATCH -A AIFAC_S02_132     # progetto -> saldo -b
#SBATCH -p boost_usr_prod      # partizione
#SBATCH --qos=boost_qos_dbg
#SBATCH --job-name=SCS-isolated
#SBATCH -e JOB.err
#SBATCH -o JOB.out

module purge
module load fftw/3.3.10--openmpi--4.1.4--nvhpc--23.1
module load openblas/0.3.21--nvhpc--23.1
module load openmpi/4.1.4--nvhpc--23.1-cuda-11.8
module load nvhpc/23.1

export OMP_NUM_THREADS=8
export OMP_PLACES=cores
export OMP_PROC_BIND=close

export PATH="/leonardo/home/userexternal/apacini0/q-e-qe-7.3.1/build/bin/:$PATH"

for pwi in *.pwi
do
pwo=${pwi//.pwi/.pwo}
if ! test -f $pwo
then

mpirun -np 4 --map-by socket:PE=8 --rank-by core pw.x -nk 2 < $pwi > $pwo

fi
done
