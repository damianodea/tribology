import os
from glob import glob
from datetime import datetime

def modify_unconverged_pwi(fname_pwi):
    #Read pwi and search for beta and max_num_steps
    with open(fname_pwi, 'r') as fpwi:
        lines = fpwi.readlines()
    idx_beta = 0
    idx_maxstep = 0
    for i, line in enumerate(lines):
        if 'mixing_beta' in line:
            beta = float(line.split('=')[1].strip().strip(','))
            beta = beta/2
            idx_beta = i
        
        elif 'electron_maxstep' in line:
            maxstep = int(line.split('=')[1].strip().strip(','))
            maxstep = int(maxstep*1.2)
            idx_maxstep = i
    
    #Overwrite beta and max_num_steps
    if idx_beta > 0: lines[idx_beta] = 'mixing_beta = ' + str(beta) + '\n'
    if idx_maxstep > 0: lines[idx_maxstep] = 'electron_maxstep = ' + str(maxstep) + '\n'

    #Overwrite pwi with new parameters
    with open(fname_pwi, 'w') as fpwi:
        fpwi.writelines(lines)

def check_pwo_status(fname_pwo):
    with open(fname_pwo, 'r') as fpwo:
        lines = fpwo.readlines()
    
    converged = False
    crashed = True
    for line in lines:
        if 'Total force =' in line: converged = True
        elif 'JOB DONE' in line: crashed = False
    return converged, crashed

def clean_qe_outputs(out_path):
    #Clean qe output dir for resubmission
    n_cleaned = 0

    pwis = glob(out_path+'/*.pwi')
    for pwi in pwis:
        pwo = pwi.replace('.pwi', '.pwo')

        #If no pwo, add as if not converged
        if not os.path.isfile(pwo):
            n_cleaned += 1
            continue

        #If recent pwo, skip            
        last_modified_time = os.path.getmtime(pwo)
        delta_time = datetime.now() - datetime.fromtimestamp(last_modified_time)
        if delta_time.total_seconds() < 60: #1m
            n_cleaned += 1
            continue

        #Check pwo status
        converged, crashed = check_pwo_status(pwo)

        #Remove crashed pwo
        if crashed:
            os.remove(pwo)
            n_cleaned += 1
            continue
        
        #Remove and replace pwi in failed pwo
        if not converged:
            modify_unconverged_pwi(pwi)
            os.remove(pwo)
            n_cleaned += 1
            continue            

    return n_cleaned

def finalize_labelling(system_dir):
    #Clean qe output dir for finalization
    n_converged = 0
    n_missing = 0
    n_failed = 0
    n_crashed = 0

    #Make directory for crashed and failed calculations
    failed_dir = system_dir+'/Failed/'
    os.makedirs(failed_dir, exist_ok=True)
    crash_dir = system_dir+'/Crashed/'
    os.makedirs(crash_dir, exist_ok=True)
    miss_dir = system_dir+'/Missing/'
    os.makedirs(miss_dir, exist_ok=True)

    pwis = glob(system_dir+'/*.pwi')
    for pwi in pwis:
        pwo = pwi.replace('.pwi', '.pwo')

        #Missing calculation
        if not os.path.isfile(pwo):
            n_missing += 1
            os.rename(pwi, miss_dir + os.path.basename(pwi))
            continue

        converged, crashed = check_pwo_status(pwo)

        #Crashed calculation
        if crashed:
            n_crashed += 1            
            os.rename(pwi, crash_dir + os.path.basename(pwi))
            os.remove(pwo)
            continue
        
        #Failed calculation
        if not converged:
            n_failed += 1
            os.rename(pwi, failed_dir + os.path.basename(pwi))
            os.remove(pwo)
            continue
        #Else
        n_converged += 1

    return [n_converged, n_missing, n_failed, n_crashed]