import os
import sys
import time
import random
import subprocess
from glob import glob

#Run inside computing node

def run_qe(command):
    #command
    # 'mpirun -np 8 --map-by socket:PE=8 --rank-by core pw.x -nk 2 < {fname_input} >> {fname_output}'

    try:        
        # Launch QE and wait till ending
        subprocess.run(command, shell=True, check=True, executable="/bin/bash")
        
        # Warn user LAMMPS execution status
        print(f"QE calculation completed")
    
    except subprocess.CalledProcessError as e:
        print(f"Error during QE execution: {e}, stopping...")    

    return

def run_qe_loop(job_cmd):
    #Get working directory
    work_dir = os.getcwd()

    #Get pwi files
    pwis = glob(work_dir+"/*.pwi")

    #Loop over pwi
    for pwi in pwis:
        #Get pwo
        pwo = pwi.replace('.pwi', '.pwo')

        #Sleep random time between 0 and 1s in case loop started "at same time" for different "run_qe_loop"
        time.sleep(random.uniform(0, 1))

        #Check if pwo does not exist
        if not os.path.isfile(pwo):
            #Create pwo file to prevent other "run_qe_loop"
            open(pwo, 'w').close()

            #Create qe scf command line #TODO check that each pwo is calculated only once
            qe_cmd = job_cmd + f" < {os.path.basename(pwi)} >> {os.path.basename(pwo)}"

            #Run qe scf calculation
            run_qe(qe_cmd)

if __name__ == '__main__':
    #Collect all program arguments = 'qe command line job w/out fnames
    qe_job_cmd = sys.argv[1]

    #Launch qe loop calculations inside computing node
    run_qe_loop(qe_job_cmd)