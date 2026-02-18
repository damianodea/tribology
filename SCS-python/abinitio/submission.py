import os
import sys
import yaml
import time
import subprocess
from glob import glob
import abinitio.qe as qe
from abinitio.wrapper_qe import wrap_qe

def update_logfile(fname_log, systems_and_status):
    #Define lines to be written
    to_write = ["\nDFT calculation phase update:\n"]

    #Get status string for each system
    for system, status_dict in systems_and_status.items():
        status = list(status_dict.keys())[0]
        val = list(status_dict.values())[0]
        line = ""
        match status:
            case 'Submit':
                line = f"{system}: Submitted {val}\n"
            
            case 'Resubmit':
                line = f"{system}: Resubmitted {val}\n"

            case 'Scheduled':
                line = f"{system}: Scheduled {val}\n"

            case 'Finished':
                line = f"{system}: Finished {val}\n"
            
            case 'Completed':
                line = f"{system}: Completed\n"  
        to_write.append(line)  

    #Append lines to log file
    with open(fname_log, 'a') as f:
        f.writelines(to_write)

def write_jobinfo(working_dir, job_ids=None, ref_info=None):
    #Three possibilites: 'Submit' -> write jobids + restarts_from_ref, 'Resubmit' -> write jobids + restarts, 'Finished' -> void

    # 'Submit'
    if ref_info is not None:
        #Get jobinfo
        jobinfo = {'Restarts' : ref_info['Restarts'], 'Jobids' : job_ids}
    
    # 'Resubmit'
    elif job_ids is not None:
        #Get jobinfo from jobinfo.yaml inside working directory
        file = open(working_dir+'/jobinfo.yaml', 'r')
        jobinfo = yaml.safe_load(file)
        file.close()      
        
        #Get list of new scheduled jobids
        jobids = [jid for jid in jobinfo['Jobids'] if jid not in job_ids['Terminated']] + job_ids['Scheduled']

        #Get number of new available restarts
        num_restarts = jobinfo['Restarts'] - len(job_ids['Scheduled'])        

        #Update jobinfo
        jobinfo = {'Restarts' : int(num_restarts), 'Jobids' : jobids}
    
    # 'Finished'
    elif job_ids is None and ref_info is None:
        jobinfo = None
    
    #Crash
    else:
        sys.exit(f"Unexpected status in {working_dir}, stopping...")

    #Update jobinfo.yaml inside working directory
    file = open(working_dir+'/jobinfo.yaml', 'w')
    if jobinfo is not None: yaml.safe_dump(jobinfo, file, default_flow_style=True) #Update with new restarts and scheduled jobids
    file.close() #Blanck jobinfo.yaml -> 'Completed'

def read_dft_info(reference_dir):
    #File structure:
    #'Restarts' : 2 , 'Groups' : 4, 'job_template' : "/path/to/job/template", 'job_cmd' : "/path/to/job/command"

    #Read info file for ab initio calculations
    file = open(reference_dir+'/dftinfo.yaml', 'r')
    dft_info = yaml.safe_load(file)
    file.close()

    return dft_info

def query_scheduler(jobids, query_comand, query_keywords):
    #Query the scheduler for job status
    scheduled_jobids = []
    for jobid in jobids:
        command = query_comand + ' ' + str(jobid)
        try:
            query_result = subprocess.check_output(command, shell = True, executable = "/bin/bash", stderr=subprocess.DEVNULL)
        except Exception as e:
            query_result = e.output
        query_result = str(query_result)

        for query_keyword in query_keywords:
            if query_keyword in query_result:
                scheduled_jobids += [jobid]
                break
    return scheduled_jobids
                  
def submit_multiple_jobs(work_dir, num_submissions, submit_cmd, dft_info):
    #Write 1 jobscript and submit multiple jobs
    jobids = wrap_qe(submit_cmd, dft_info, work_dir, num_submissions)

    return jobids

def get_system_status(working_dir, query_cmd, query_key):
    #Possible status: Submit, Resubmit, Finished, Scheduled, Completed 
    status = {}

    #No jobinfo.yaml -> 'Submit'
    if not os.path.isfile(working_dir+'/jobinfo.yaml'):
        status['Submit'] = True
    
    #Empty jobinfo.yaml -> 'Completed'
    elif os.stat(working_dir+'/jobinfo.yaml').st_size == 0:
        status['Completed'] = True
    
    #Non-empty jobinfo.yaml
    else:
        #Get jobinfo
        file = open(working_dir+'/jobinfo.yaml', 'r')
        jobinfo = yaml.safe_load(file)
        file.close()

        #Get number of available restarts
        num_restarts = jobinfo['Restarts']

        #Get jobids
        jobids = jobinfo['Jobids']

        #Get scheduled jobids
        scheduled_jobids = query_scheduler(jobids, query_cmd, query_key)

        #All jobs are scheduled -> 'Scheduled'
        if set(scheduled_jobids) == set(jobids):
            status['Scheduled'] = scheduled_jobids
        
        #At least one job has finished
        else:
            #Clean pwo directories and return #remaining pwos = missing + unconverged + crashed + working
            remaining_pwos = qe.clean_qe_outputs(working_dir)

            #Remaining pwos
            if remaining_pwos > 0:
                #With available restarts -> 'Resubmit'
                if num_restarts > 0:
                    #Save terminated jobids and number of new available restarts
                    status['Resubmit'] = {'Terminated' : [id for id in jobids if id not in scheduled_jobids], 'Restarts' : num_restarts}
                
                #No available restarts
                else:
                    #No scheduled jobs -> 'Finished'
                    if len(scheduled_jobids) == 0:
                        status['Finished'] = True
                    
                    #Scheduled jobs -> 'Scheduled'
                    else:
                        status['Scheduled'] = scheduled_jobids
            
            #No remaining pwos
            else:
                #No scheduled jobs -> 'Finished'
                if len(scheduled_jobids) == 0:
                    status['Finished'] = True  

                #Scheduled jobs -> 'Scheduled' (It should not happend cause remaining_pwos counts also #working pwos)
                else:
                    status['Scheduled'] = scheduled_jobids
    
    return status

def update_working_directories(exp_path, ref_path, job_info):
    #Possible status: Submit, Resubmit, Finished, Scheduled, Completed 
    conditions_to_sleep = []

    #Define dict of systems and status for LOG file
    systems_and_status = {}

    #Loop over systems' exploration working directories
    for work_dir in glob(exp_path):
        #Get system name
        sysname = os.path.basename(os.path.dirname(work_dir))

        #Get system reference directory
        ref_dir = ref_path + '/' + sysname

        #Get system status
        status = get_system_status(work_dir, job_info['Query_cmd'], job_info['Query_keys'])

        #Get status case
        status_case = list(status.keys())[0]        

        #Update system working directory based on its status
        match status_case:
            case 'Submit':
                #Set conditions for sleep
                conditions_to_sleep.append(True)

                #Get submission info
                dft_info = read_dft_info(ref_dir)    

                #Get number of submission (number of groups)
                num_submissions = dft_info['Groups']

                #Submit multiple ab initio loop jobs
                jobids = submit_multiple_jobs(work_dir, num_submissions, job_info['Submit_cmd'], dft_info)

                #Update jobinfo in work_dir
                write_jobinfo(work_dir, job_ids=jobids, ref_info=dft_info)

                #Get system status
                systems_and_status[sysname] = {'Submit' : jobids}
        
            case 'Resubmit':
                #Set conditions for sleep
                conditions_to_sleep.append(True)

                #Get resubmission info
                terminated_jobids, num_restarts = status['Resubmit']['Terminated'], status['Resubmit']['Restarts']

                #Get number of resubmission
                num_resub = min([len(terminated_jobids), num_restarts])

                #Get submission info
                dft_info = read_dft_info(ref_dir)    

                #Submit multiple ab initio loop jobs
                jobids = submit_multiple_jobs(work_dir, num_resub, job_info['Submit_cmd'], dft_info)

                #Update jobinfo in work_dir
                write_jobinfo(work_dir, job_ids={'Terminated' : terminated_jobids, 'Scheduled' : jobids})

                #Get system status
                systems_and_status[sysname] = {'Resubmit' : jobids}                
        
            case 'Scheduled':
                #Set conditions for sleep
                conditions_to_sleep.append(True)

                #Get scheduled jobids
                scheduled_jobids = status['Scheduled']

                #Get system status
                systems_and_status[sysname] = {'Scheduled' : scheduled_jobids}                

            case 'Finished':
                #Set conditions for sleep
                conditions_to_sleep.append(False)

                #Clean dft folder for finalization
                dft_status = qe.finalize_labelling(work_dir)

                #Update jobinfo in work_dir
                write_jobinfo(work_dir)                

                #Get system status
                systems_and_status[sysname] = {'Finished' : {'Converged' : dft_status[0], 'Missing' : dft_status[1], 'Failed' : dft_status[2], 'Crashed' : dft_status[3]}}
            
            case 'Completed':
                #Set conditions for sleep
                conditions_to_sleep.append(False)

                #Get system status
                systems_and_status[sysname] = {'Completed' : True}                

    return systems_and_status, conditions_to_sleep

def wait_dft(scs_input_params, scs_iteration_dir):
    #Main function to: run, restart and wait for ab-initio sampling jobs

    #Get log file name
    fname_log = scs_iteration_dir.split('/Iterations/')[0] + f"/scs.{os.path.basename(scs_iteration_dir)}.log"    
    
    #Get essential parameters for ab initio sampling job
    #sbatch cmd, query cmd, sched keys, dp jobscript template, dp commands
    qe_job_info = scs_input_params['Abinitio']['Job']    

    #Get waiting time and maximum waiting time for scs
    wait_time = scs_input_params['Abinitio']['Wait_time']
    max_wait_time = scs_input_params['Abinitio']['Max_wait_time']

    #Initialize waiting conditions: set zero elapsed time and set to sleep
    start_time = time.time()
    elapsed_time = 0
    to_sleep = True

    #Abinitio directories
    exploration_path = scs_iteration_dir + '/Exploration/*/SAMPLED'
    system_dirs = scs_input_params['Abinitio']['Systems']

    #Main waiting loop
    while to_sleep and elapsed_time < max_wait_time:
        #Loop over system directories and update them based on their status
        systems_and_status, to_sleeps = update_working_directories(exploration_path, system_dirs, qe_job_info)

        # Update LOG file
        update_logfile(fname_log, systems_and_status)           

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
        sys.exit(f"Unkown error in dft phase, stopping...")    
    return True