import sys
import subprocess

def write_dp_jobscript(job_temp_fname, commands, workdir):
    #Read jobscript template
    with open(job_temp_fname, 'r') as f:
        lines = f.readlines()

    # #Get jobscript command
    # commands = ["\ndp train -l training.log input.json > training.out\n"
    #                     "dp train -l training.log --restart model.ckpt input.json > training.out\n"
    #                     "dp freeze -o graph.pb > freeze.out\n"
    #                     "dp compress -i graph.pb -o compressed.pb > compress.out\n"]

    #Get lines to write
    lines += commands

    #Set jobscript name
    scs_job_name = "ml-dp.scs.sh"

    #Write custom jobscript
    with open(workdir + "/" + scs_job_name, 'w') as f:
        f.writelines(lines)
    
    return scs_job_name

def submit_dp(sub_cmd):
    try:
        result = subprocess.run(sub_cmd, capture_output=True, text=True, check=True, shell=True, executable="/bin/bash")
        output = result.stdout.strip()
        jobid = int(output.split()[-1])
    except:
        sys.exit("Error in submitting exploration job, stopping...")

    return jobid   

def wrap_dp(sbatch_cmd, joscript_dp_template, job_cmd, work_dir):
    #Write jobscript to be launched from scs
    job_scs_name = write_dp_jobscript(joscript_dp_template, job_cmd, work_dir)

    #Define sub command
    sub_command = f"cd {work_dir}; {sbatch_cmd} {job_scs_name}"
    
    #Submit jobscript
    jobid = submit_dp(sub_command)

    return jobid