import os
import sys
import time
from glob import glob
from exploration.wrapper_lmp import wrap_lmp
from training.dp_wait import load_info_job, query_job_is_scheduled, write_info_job

def update_logfile(fname_logfile, paths_and_status):
    #Prepare string to inform user
    inform_lmp_submit = ""
    inform_lmp_sched = ""
    inform_lmp_crash = ""
    inform_lmp_finish = ""

    #Get string based on exploration status
    for path, stat in paths_and_status.items():
        #Get system
        system = os.path.basename(path)

        #Job needs to be restarted
        if stat == 'Submit':
            inform_lmp_submit += f" {system} "
        
        elif stat == 'Scheduled':
            inform_lmp_sched += f" {system} "        

        elif stat == 'Crashed':
            inform_lmp_crash += f" {system} "

        elif stat == 'Finished':
            inform_lmp_finish += f" {system} "
    
    #Set string to be written
    to_write = "Check exploration status:\n"
    if inform_lmp_submit != '':
        to_write += f" Submitted exploration workflow for system {inform_lmp_submit}\n"
    if inform_lmp_sched != '':
        to_write += f" Scheduled exploration workflow for system {inform_lmp_submit}\n"        
    if inform_lmp_crash != '':
        to_write += f" Crashed exploration workflow for system {inform_lmp_submit}, sampling what is possible...\n"
    if inform_lmp_finish != '':
        to_write += f" Finished exploration workflow for system {inform_lmp_submit}\n"

    #Update LOG file
    with open(fname_logfile, 'a') as f:
        f.write(to_write)    

def get_exploration_status(systems_path, sched_info):
    #Workdir with lammps status
    paths_and_status = {}

    #Get query cmd and keywords
    query_comand, schedule_keywords = sched_info['Query_cmd'], sched_info['Query_keys']    

    #Loop over system dirs and check lammps status
    for system_path in glob(systems_path):
        
        # If no jobinfo.yaml -> submit calculation
        if not os.path.isfile(system_path+'/jobinfo.yaml'):
            paths_and_status[system_path] = 'Submit'
            continue            

        #Load info on scheduled jobids working in this folder
        jobid = load_info_job(system_path)

        # Job is already completed if no jobid in jobinfo.yaml file
        if jobid is None:
            paths_and_status[system_path] = 'Completed'
            continue

        # Otherwise query scheduler with found jobid
        scheduled = query_job_is_scheduled(jobid, query_comand, schedule_keywords)

        #Next directory if job is scheduled: running or pending
        if scheduled:
            paths_and_status[system_path] = 'Scheduled'
            continue            

        # Otherwise previous job is no more scheduled -> check output
        # If every output#.out finish with 'Total wall time' -> finished
        lmp_inputs = glob(system_path+'/input*.in')
        check_outputs = {}
        for lmp_input in lmp_inputs:
            #For each input file get its corresponding output
            out_name = os.path.basename(lmp_input).replace('input', 'output')
            out_name = out_name.replace('.in', '.out')
            lmp_output = os.path.dirname(lmp_input) + '/' + out_name

            #Tag missing outputs
            if not os.path.isfile(lmp_output):
                check_outputs[lmp_output] = False
                continue
            
            #Read lmp output
            with open(lmp_output, 'r') as f:
                lines = f.readlines()
            
            #Finished
            if 'Total wall time' in lines[-1]:
                check_outputs[lmp_output] = True
            #Crashed/interrupted run
            else:
                check_outputs[lmp_output] = False
        
        if not all(check_outputs.values()):
            paths_and_status[system_path] = 'Crashed'
        else:
            paths_and_status[system_path] = 'Finished'
    
    return paths_and_status

def update_working_directories(paths_and_status, sub_info):
    #Possible status: Submit, Scheduled, Crashed, Finished, Completed 
    conditions_to_sleep = []

    for path, stat in paths_and_status.items():
        # Job is ready -> Submit job
        if stat == 'Submit':
            conditions_to_sleep.append(True)

            #Launch lmp execution
            jobid = wrap_lmp(sub_info['Submit_cmd'], sub_info['Jobscript'], sub_info['Lammps'], sub_info['Packmol'], path)            
            
            #Write jobid
            write_info_job(path, jobid)
            continue            

        # Job is scheduled, wait
        elif stat == 'Scheduled':
            conditions_to_sleep.append(True)
            continue

        # Job is crashed, move on and sample what is possible
        elif stat == 'Crashed':
            conditions_to_sleep.append(False)
            write_info_job(path, None)
            continue                

        #Job has just finished
        elif stat == 'Finished':
            conditions_to_sleep.append(False)
            write_info_job(path, None)
            continue

        # Job has already completed, do nothing
        elif stat == 'Completed':
            conditions_to_sleep.append(False)
            continue
        
        #If something else -> throw error
        else:
            sys.exit(f"Unkown {stat} training status, skipping...")

    return conditions_to_sleep

def wait_exploration(scs_input_params, scs_iteration_dir):
    #Main function to: run and wait for exploration workflow job
    
    #Get log file name
    fname_log = scs_iteration_dir.split('/Iterations/')[0] + f"/scs.{os.path.basename(scs_iteration_dir)}.log"    

    #sbatch cmd, query cmd, sched keys, packmol path
    lmp_job_info = scs_input_params['Exploration']['Job']

    #Get time to wait and maximum waiting time for scs
    wait_time = scs_input_params['Exploration']['Wait_time']
    max_wait_time = scs_input_params['Exploration']['Max_wait_time']    

    #Initialize waiting conditions: set zero elapsed time and set to sleep
    start_time = time.time()
    elapsed_time = 0
    to_sleep = True

    #Exploration directory
    exploration_systems_path = scs_iteration_dir + '/Exploration/*'

    #Main waiting loop
    while to_sleep and elapsed_time < max_wait_time:
        # workdirs_and_status = {'workdir1' : 'status', ...}
        workdirs_and_status = get_exploration_status(exploration_systems_path, lmp_job_info)      

        # Update working directories based on their status
        to_sleeps = update_working_directories(workdirs_and_status, lmp_job_info)

        # Update LOG file
        update_logfile(fname_log, workdirs_and_status)           

        #Get elapsed time
        elapsed_time = time.time() - start_time

        #Get to sleep condition
        to_sleep = any(to_sleeps)     
        if to_sleep: time.sleep(wait_time)
    
    #Finished
    if not to_sleep:
        return True
    
    #Out of time
    elif elapsed_time > max_wait_time:
        return False

    #Unknown error
    else:
        sys.exit(f"Unkown error in phase EXPLORATION, stopping...")

def startup_exploration(scs_params, scs_iteration_dir): 
    #Get system exploration path from scs input parameters
    explorations_path = scs_params['Exploration']['Systems']

    #Create directories to start exploration workflow for each system
    for system in glob(explorations_path+'/*'):        
        #Get system name
        sys_name = os.path.basename(system)
        
        #Get working system exploration directory
        work_sys_dir = scs_iteration_dir+'/Exploration/'+sys_name

        #Create directories
        os.makedirs(work_sys_dir, exist_ok=True)