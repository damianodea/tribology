import os
import sys
import subprocess

def write_lmp_jobscript(job_temp_fname, lmp_cmds, packmol, workdir):
    #Read jobscript template
    with open(job_temp_fname, 'r') as f:
        lines = f.readlines()
    
    #Get python executable path
    pyexe = sys.executable

    #Get workflow directory
    workflow_dir = os.path.dirname(os.path.abspath(__file__))

    #Append workflow directory to python path
    lines.append(f"\nexport PYTHONPATH={workflow_dir}:$PYTHONPATH\n")

    #Get workflow.py python script
    workflow_py = workflow_dir + '/workflow/workflow.py'    

    #Set command to launch python
    jobscript_cmd = f"\n\n{pyexe} {workflow_py} \"{lmp_cmds}\" {packmol}"

    #Get lines to write
    lines.append(jobscript_cmd)

    #Set jobscript name
    scs_job_name = "exp-lmp.scs.sh"

    #Write custom jobscript
    with open(workdir + "/" + scs_job_name, 'w') as f:
        f.writelines(lines)
    
    return scs_job_name

def submit_lmp(sub_cmd):
    try:
        result = subprocess.run(sub_cmd, capture_output=True, text=True, check=True, shell=True, executable="/bin/bash")
        output = result.stdout.strip()
        jobid = int(output.split()[-1])
    except:
        sys.exit("Error in submitting exploration job, stopping...")

    return jobid   

def wrap_lmp(sbatch_cmd, joscript_lmp_template, lmp_run_cmds, packmol_path, work_dir):
    #Write jobscript to be launched from scs
    job_scs_name = write_lmp_jobscript(joscript_lmp_template, lmp_run_cmds, packmol_path, work_dir)

    #Submit command
    sub_command = f"cd {work_dir}; {sbatch_cmd} {job_scs_name}"
    
    #Submit jobscript
    jobid = submit_lmp(sub_command)

    return jobid