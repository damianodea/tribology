import os
import sys
import yaml
import time
import subprocess
from glob import glob
from training.wrapper_dp import wrap_dp

def update_logfile(fname_logfile, paths_and_status):
    #Prepare string to inform user
    inform_submitted = ""
    inform_restarted = ""
    inform_scheduled = ""
    inform_finished = ""
    for path, stat in paths_and_status.items():
        #Get NN
        nn = os.path.basename(path)

        #Job needs to be restarted
        if stat == 'Submit':
            inform_submitted += f" {nn} "

        #Job needs to be restarted
        elif stat == 'Restart':
            inform_restarted += f" {nn} "        

        # Job is scheduled, wait
        elif stat == 'Scheduled':
            inform_scheduled += f" {nn} "            

        #Job has just finished
        elif stat == 'Finished':
            inform_finished += f" {nn} "

        # Job has already completed, nothing to inform
        elif stat == 'Completed':
            continue
    
    #Set string to be written
    to_write = ""
    if inform_submitted != '':
        to_write = "Check training status:\n"
        to_write += f" Submitted : {inform_submitted}\n"
    if inform_scheduled != '':
        to_write = "Check training status:\n"
        to_write += f" Scheduled : {inform_scheduled}\n"
    if inform_restarted != '':
        to_write = "Check training status:\n"
        to_write += f" Restarted : {inform_restarted}\n"
    if inform_finished != '':
        to_write = "Check training status:\n"
        to_write += f" Finished : {inform_finished}\n"

    #Update LOG file
    with open(fname_logfile, 'a') as f:
        f.write(to_write)

def write_info_job(work_dir, jobid):
    #DP info file
    dp_info_file = work_dir + '/jobinfo.yaml'

    if jobid is None: #Void jobinfo.yaml
        f = open(dp_info_file, 'w').close()
    
    else:
        #Jobid dict
        jobdict = {'Jobid' : jobid}

        #Update DP info file for possible restarts
        with open(dp_info_file, 'w') as f:
            yaml.safe_dump(jobdict, f)

def load_info_job(work_dir):
    #Read jobinfo.yaml file
    fname_jobinfo = work_dir+'/jobinfo.yaml'
    file = open(fname_jobinfo, 'r')
    mldp_info = yaml.safe_load(file)
    file.close()

    if bool(mldp_info):
        jobid = int(mldp_info['Jobid'])
    else:
        jobid = None

    return jobid

def query_job_is_scheduled(jobid, query_comand, schedule_keywords):
    #Query the scheduler for job status
    command = query_comand + ' ' + str(jobid)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, shell=True, executable="/bin/bash")
        query_result = result.stdout.strip()  
        # query_result = subprocess.check_output(command, shell = True, executable = "/bin/bash", stderr=subprocess.DEVNULL)
    except Exception as e:
        query_result = e.output
    query_result = str(query_result)

    # Job pending or running -> scheduled
    scheduled = any([schedule_keyword in query_result for schedule_keyword in schedule_keywords])

    return scheduled

def get_trainings_status(train_dir, sched_info):
    #workdir with training status
    paths_and_status = {}

    #Get query cmd and keywords
    query_comand, schedule_keywords = sched_info['Query_cmd'], sched_info['Query_keys']

    #Loop over model dir and check training status
    for nndir in glob(train_dir + '/NN*'):
        
        # If no jobinfo.yaml -> submit calculation
        if not os.path.isfile(nndir+'/jobinfo.yaml'):
            paths_and_status[nndir] = 'Submit'
            continue            

        #Load info on scheduled jobids working in this folder
        jobid = load_info_job(nndir)

        # Job is already completed if no jobid in jobinfo.yaml file
        if jobid is None:
            paths_and_status[nndir] = 'Completed'
            continue

        # Otherwise query scheduler with found jobid
        scheduled = query_job_is_scheduled(jobid, query_comand, schedule_keywords)

        #Next directory if job is scheduled: running or pending
        if scheduled:
            paths_and_status[nndir] = 'Scheduled'
            continue            

        # Otherwise previous job is no more scheduled -> check output
        # If compressed.pb exist -> Finished, check next directory
        if os.path.isfile(nndir + '/compressed.pb'):
            paths_and_status[nndir] = 'Finished'
            continue
        
        #Otherwise re-launch the calculation
        else:
            paths_and_status[nndir] = 'Restart'
            continue
    
    return paths_and_status

def update_working_directories(paths_and_status, sub_info):
    #Possible status: Submit, Restart, Scheduled, Completed, Finished, 
    conditions_to_sleep = []

    for path, stat in paths_and_status.items():
        # Job is ready to be (Re)submitted
        if stat == 'Submit' or  stat == 'Restart':
            #Set condition for sleeping
            conditions_to_sleep.append(True)
            
            #Launch dp execution
            jobid = wrap_dp(sub_info['Submit_cmd'], sub_info['Jobscript'], sub_info['Job_cmd'], path)
            
            #Write jobid
            write_info_job(path, jobid)
            continue            

        # Job is scheduled, wait
        elif stat == 'Scheduled':
            conditions_to_sleep.append(True)
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

def wait_training(scs_input_params, scs_iteration_dir):
    #Main function to: run, restart and wait for ensemble training

    #Get log file name
    fname_log = scs_iteration_dir.split('/Iterations/')[0] + f"/scs.{os.path.basename(scs_iteration_dir)}.log"
    
    #Get essential parameters for ensemble training
    #sbatch cmd, query cmd, sched keys, dp jobscript template, dp commands
    dp_job_info = scs_input_params['Training']['Job']

    #Get time to wait and maximum waiting time for scs
    wait_time = scs_input_params['Training']['Wait_time']
    max_wait_time = scs_input_params['Training']['Max_wait_time']

    #Initialize waiting conditions: set zero elapsed time and set to sleep
    start_time = time.time()
    elapsed_time = 0
    to_sleep = True

    #Training directory
    train_dir = scs_iteration_dir + '/Training'

    #Main waiting loop
    while to_sleep and elapsed_time < max_wait_time:
        # workdirs_and_status = {'workdir1' : 'status', ...}
        workdirs_and_status = get_trainings_status(train_dir, dp_job_info)

        # Update working directories based on their status
        to_sleeps = update_working_directories(workdirs_and_status, dp_job_info)

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
        sys.exit(f"Unkown error in Training phase {train_dir}, stopping...")