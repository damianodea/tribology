import os
import sys
import yaml
import subprocess
from sampling import sample_exploration_traj
from geometry import get_atomic_info, get_current_geometry, get_last_geometry, write_lmp_data, write_lmp_input

#This module has to be launched by the computing node and it substitutes job_exploration.sh

#TODO Check exploration.yaml input file parameters
def check_input_parameters(input_dict):
    #What to check:
    #1- At least 1 atomic_species in the whole dictionary
    return True

def read_exploration_input(fname_exp_input):
    #Read exploration.yaml file
    finput = open(fname_exp_input, 'r')
    exp_input = yaml.safe_load(finput)
    finput.close()

    #Check input!
    check_input_parameters(exp_input)

    return exp_input

def run_lammps(run_cmd, idx):
    #Set input and output file names
    fname_input = f"input{idx}.in"
    fname_output = f"output{idx}.out"

    try:
        # Run LAMMPS with GPU
        command = f"{run_cmd} {fname_input} > {fname_output}"
        
        # Launch LAMMPS and wait till ending
        subprocess.run(command, shell=True, check=True, executable="/bin/bash")
        
        # Warn user LAMMPS execution status
        print(f"LAMMPS exploration phase {idx} completed: {fname_output}.")
    
    except subprocess.CalledProcessError as e:
        print(f"Error during LAMMPS execution: {e}, stopping...")

def init_exploration_phase(exp_info, num_phase, pkmol_path):
    #Get atomic info
    species_and_masses = get_atomic_info(exp_info, num_phase)

    #Build initial geometry defined in current phase
    if 'Geometry' in exp_info[f"Phase{num_phase}"]:
        #Tuple containing ase atoms and group dictionary
        atoms, groups = get_current_geometry(exp_info, num_phase, pkmol_path)
    
    #Get last available geometry if no geometry definition in current phase
    else:
        atoms, groups = get_last_geometry(num_phase)
    
    #Write geometry file: lmp data, ase xyz
    write_lmp_data(atoms, species_and_masses, num_phase)

    #Write lmp input file: input#.in
    write_lmp_input(exp_info, species_and_masses, groups, num_phase)    

def run_exploration_workflow(lmp_cmd, pkmol_path):
    #This has to be launched inside system exploration directory
    system_exploration_dir = os.getcwd()

    #Get system name
    system_name = os.path.basename(system_exploration_dir)

    #Get SCS main dir
    scs_main_dir = system_exploration_dir.split('/Iterations/')[0]

    #Get SCS logfile
    iter_dir = system_exploration_dir.split('/Exploration/')[0]
    log_fname = scs_main_dir + f"/scs.{os.path.basename(iter_dir)}.log"

    #Get exploration.yaml and input.pwi template for this system
    exploration_input = scs_main_dir + '/Reference/Systems/' + system_name + '/exploration.yaml'
    template_pwi = scs_main_dir + '/Reference/Systems/' + system_name + '/input.pwi'

    #Read exploration input file: exploration.yaml
    exp_info = read_exploration_input(exploration_input)

    #Loop over user defined exploration phases
    for phase in exp_info.keys(): #Check they mantain the same order as input.yaml
        #Get current phase number
        num_phase = int(phase.strip('Phase'))
        
        #Initialize current exploration phase: Create geometries and lmp input files
        init_exploration_phase(exp_info, num_phase, pkmol_path)
        
        #Run lammps
        run_lammps(lmp_cmd, num_phase)

        #Sampling from trajectory
        sample_exploration_traj(exp_info, num_phase, template_pwi, log_fname)

if __name__ == '__main__':
    lmp_cmd = sys.argv[1]
    packmol_path = sys.argv[2]
    run_exploration_workflow(lmp_cmd, packmol_path)