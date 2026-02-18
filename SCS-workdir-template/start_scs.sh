#!/bin/bash

#Activate python environment (MACE, DPDATA, MATPLOTLIB, LAMMPS)
source /leonardo_scratch/fast/EUHPC_A04_113/Alberto/MLIP/MACE/env_mace/bin/activate #MACE env

#Path to SCS main
scs_main_py=/leonardo/home/userexternal/apacini0/SCS-python/main.py

#Launch SCS in background and No hangup
nohup python $scs_main_py &

#Save SCS PID
echo $! > PID
