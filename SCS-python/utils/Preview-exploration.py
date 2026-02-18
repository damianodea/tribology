import os, sys
#Get SCS path
scs_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#Append SCS python path
sys.path.append(scs_path)

#Import method
from exploration.workflow.workflow import read_exploration_input, init_exploration_phase

def preview_exploration(fname_exploration, packmol_exe_path, exploration_phase=0):
    #Read exploration input file: exploration.yaml
    exp_info = read_exploration_input(fname_exploration)

    #Create geometries (.data and .xyz) and lmp input files for the selected phase
    init_exploration_phase(exp_info, exploration_phase, packmol_exe_path)

if __name__ == '__main__':
    usg_str = "Usage:\npython Preview-exploration.py /path/to/system/exploration.yaml /packmol/exe/path [phase, default=0]"
    if len(sys.argv) != 3 and len(sys.argv) != 4: sys.exit(usg_str)

    exploration_system_path = sys.argv[1]
    packmol_path = sys.argv[2]
    if len(sys.argv) == 4: phase = int(sys.argv[3])
    else: phase = 0 #Default phase

    preview_exploration(exploration_system_path, packmol_path, phase)