import os
import sys
import subprocess

def write_qe_jobscript(job_temp_fname, jobscript_cmd):
    #Read jobscript template
    with open(job_temp_fname, 'r') as f:
        lines = f.readlines()
    
    #Get python executable path
    pyexe = sys.executable

    #Get run_qe.py python script
    run_qe_py = os.path.dirname(os.path.abspath(__file__)) + '/run_qe.py'  

    #Get jobscript command
    jobscript_cmds = [f'\n\n{pyexe} {run_qe_py} "{jobscript_cmd}"']

    #Get lines to write
    lines += jobscript_cmds

    #Set jobscript name
    scs_job_name = "ai-qe.scs.sh"

    #Write custom jobscript
    with open(scs_job_name, 'w') as f:
        f.writelines(lines)
    
    return scs_job_name

def write_qe_loop_jobscript(job_temp_fname, job_cmd, work_dir):
    #Read jobscript template
    with open(job_temp_fname, 'r') as f:
        lines = f.readlines()
    
    #Get python executable path
    pyexe = sys.executable

    #Get run_qe.py python script
    qeloop_py = os.path.dirname(os.path.abspath(__file__)) + '/run_qe.py'  

    #Get jobscript command
    jobscript_cmds = [f"\n{pyexe} {qeloop_py} \"{job_cmd}\""]

    #Get lines to write
    lines += jobscript_cmds

    #Set jobscript name
    scs_job_name = "ai-qe.scs.sh"

    #Write custom jobscript
    with open(work_dir + "/" + scs_job_name, 'w') as f:
        f.writelines(lines)

    print("Method write_qe_loop_jobscript: begin", flush=True)
    print(job_temp_fname, flush=True)
    print(job_cmd, flush=True)
    print(work_dir + "/" + scs_job_name, flush=True)
    print("Method write_qe_loop_jobscript: End", flush=True)
    print("---------------------------------------------------------------", flush=True)
    
    return scs_job_name    


def submit_qe(sub_cmd):
    print(sub_cmd, flush=True)
    try:
        result = subprocess.run(sub_cmd, capture_output=True, text=True, check=True, shell=True, executable="/bin/bash")
        output = result.stdout.strip()
        jobid = int(output.split()[-1])
    except:
        sys.exit("Error in submitting ab initio loop job, stopping...")

    return jobid   

def wrap_qe(sbatch_cmd, job_info, workdir, num_submission):
    #Command line qe submission
    # qe_job_cmd = f"'mpirun -np 8 --map-by socket:PE=8 --rank-by core pw.x -nk 2 -input {fname_input} >> {fname_output}'"

    #Get job template and job command
    job_temp_fname, job_cmd = job_info["Jobscript"], job_info["Job_cmd"]

    #Write jobscript to be launched from scs
    job_scs_name = write_qe_loop_jobscript(job_temp_fname, job_cmd, workdir)

    #Submit command
    sub_command = f"cd {workdir} ; {sbatch_cmd} {job_scs_name}"

    #Define jobids array
    jobids = []

    #Submit multiple qe_loop.py jobscripts
    for n in range(num_submission):
        #Submit jobscript
        jobid = submit_qe(sub_command)

        #Save submitted jobid
        jobids.append(jobid)

    return jobids