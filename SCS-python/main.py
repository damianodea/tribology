import os
import sys
import yaml
from abinitio import wait_dft
from dataset import update_dataset
from training import startup_training, wait_training
from exploration import startup_exploration, wait_exploration

def finalize_phase(fname_log, scs_phase, new_scs_phase):
    #Update log file
    with open(fname_log, 'a') as f:
        f.write(f"\n{scs_phase} phase is successfully terminated, moving to {new_scs_phase} phase...\n")

def read_scs_input(fname):
    # Read scs_input.yaml file and store input paramters as dict
    fin = open(fname, 'r')
    scs_params = yaml.safe_load(fin)
    fin.close()

    return scs_params

def read_scs_restart(fname):
    # Default iteration and phase if no restart -> from scratch
    scs_iter = 1
    scs_phase = 'START'    
    
    # Read scs.restart and get current iteration and phase
    if os.path.isfile(fname):
        fre = open(fname, 'r')
        scs_restart = yaml.safe_load(fre)
        fre.close()

        scs_iter = scs_restart['Current_iteration']
        scs_phase = scs_restart['Current_phase']

    return scs_iter, scs_phase

def write_logfile(fname_log, current_ite, current_params):
    #Get relevant information to run scs
    #General
    atomic_types = current_params['Dataset']['Atom_types']

    #Training
    number_of_models = current_params['Training']['N_models']
    dataset_path = current_params['Training']['Dataset_path']

    #Exploration
    sys_dir = current_params['Exploration']['Systems']
    sys_dirs = os.listdir(sys_dir)

    #Get strings to be written to logfile
    to_write = [f'Starting SCS iteration {current_ite}--------------------------------------------------------\n',
                f'Using {len(atomic_types)} atomic types: {atomic_types}\n',
                f'Ensemble training with {number_of_models} models using dataset in {dataset_path}\n',
                f'Exploring {len(sys_dirs)} systems found in {sys_dir}\n',
                f'--------------------------------------------------------------------------------\n']
    
    #Write logfile
    with open(fname_log, 'w') as f:
        f.writelines(to_write)

def outoftime_logfile(fname_log, phase):
    #Write phase is out of time
    with open(fname_log, 'a') as f:
        f.write(f"\n{phase} phase out of time, stopping...\n")

def write_restart(current_iteration, begin_phase, scs_dir):
    #Get scs restart file
    fname_restart = scs_dir + '/scs.restart.yaml'

    #Get restart dict
    restart = {'Current_iteration' : current_iteration, 'Current_phase' : begin_phase}

    #Write restart.yaml file
    with open(fname_restart, 'w') as f:
        yaml.dump(restart, f)

def forward_phase(scs_ite, scs_phase, scs_params, main_dir):
    # Current iteration directory
    iter_dir = main_dir +'/Iterations/' + str(scs_ite)

    #Create iteration directory if not exist (START phase)
    os.makedirs(iter_dir, exist_ok=True)

    # Current logfile
    fname_log = main_dir + f"/scs.{scs_ite}.log"

    #Main method for scs iteration
    match scs_phase:

        case 'START':
            #Inform user about current ite, dataset and system used in this iteration
            write_logfile(fname_log, scs_ite, scs_params)

            #Ready for next iteration
            next_phase = 'TRAINING'
        
        case 'TRAINING':
            # Initialize training, skip if already initialized
            startup_training(scs_params, iter_dir)

            # Run training: from scratch or restart and wait to completion
            train_success = wait_training(scs_params, iter_dir)

            # Check training is finished
            if not train_success:
                outoftime_logfile(fname_log, scs_phase)
                sys.exit()
            
            #Ready for next iteration
            else:
                next_phase = 'EXPLORATION'

            # Update logfile with closing phase
            finalize_phase(fname_log, scs_phase, next_phase)

        case 'EXPLORATION':
            # Submit lammps workflow to compute nodes, workflow restarting handled by this method
            startup_exploration(scs_params, iter_dir)        

            # Wait till exploration workflow completes
            exploration_success = wait_exploration(scs_params, iter_dir)

            # Check training is finished
            if not exploration_success:
                outoftime_logfile(fname_log, scs_phase)
                sys.exit()    

            #Ready for next iteration
            else:
                next_phase = 'ABINITIO'                        

            # Update logfile with closing phase
            finalize_phase(fname_log, scs_phase, next_phase)
        
        case 'ABINITIO':
            # Wait till dft sampling completes and restart them when necessary
            abinitio_success = wait_dft(scs_params, iter_dir)

            # Check abinitio is not out-of-time
            if not abinitio_success:
                outoftime_logfile(fname_log, scs_phase)
                sys.exit()              

            #Ready for next iteration
            else:
                next_phase = 'CONVERTING'                       

            # Update logfile with closing phase
            finalize_phase(fname_log, scs_phase, next_phase)

        case 'CONVERTING':
            # Dump new updated dataset to npy data
            update_dataset(scs_params, iter_dir)

            #Ready for next iteration
            next_phase = 'END'

            # Update logfile with closing phase
            finalize_phase(fname_log, scs_phase, next_phase)            
    
    #Update restart file and return
    write_restart(scs_ite, next_phase, main_dir)

    return next_phase

if __name__ == '__main__':
    #Launch inside scs main directory
    scs_main_dir = os.getcwd()

    #SCS input parameters file
    fname_scs_input = scs_main_dir + '/scs.input.yaml'
    params = read_scs_input(fname_scs_input)    

    #SCS restart file
    fname_scs_restart = scs_main_dir + '/scs.restart.yaml'
    ite, phase = read_scs_restart(fname_scs_restart)   

    #Start new iteration if previous one is finished
    if phase == 'END':
        ite = ite + 1
        phase = 'START'

    #Launch scs main method till current iteration is finished
    while phase != 'END':
        phase = forward_phase(ite, phase, params, scs_main_dir)