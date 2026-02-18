#!/bin/bash

#Activate python environment
source /leonardo/home/userexternal/apacini0/.envs/scs-env/bin/activate

#Path to SCS main
scs_main_py=/leonardo_work/IscrC_ASIM/SCS-python/main.py

#Launch SCS
nohup python $scs_main_py &

#Save SCS PID
echo $! > PID
