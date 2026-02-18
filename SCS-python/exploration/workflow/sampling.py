import os
import numpy as np
from glob import glob
from ase.io import read
import matplotlib.pyplot as plt
from ase.data import covalent_radii
from ase.geometry import get_distances
from matplotlib.lines import Line2D

def at2lmp(fname_output, traj):
    #lmptraj custom format
    headers = {
                'TIMESTEP' : "ITEM: TIMESTEP\n",
                'NAT'      : "ITEM: NUMBER OF ATOMS\n",
                'BOX'      : "ITEM: BOX BOUNDS pp pp pp\n",
                'ATOMS'    : "ITEM: ATOMS element xu yu zu\n"
            }

    #Write lammpstrj file
    with open(fname_output, 'w') as f:
        for idx, frame in enumerate(traj):
            f.write(headers['TIMESTEP']+f"{idx}\n")
            f.write(headers['NAT']+f"{len(frame)}\n")
            
            f.write(headers['BOX'])
            for i in range(3):
                length = frame.cell[i, i]
                f.write("0.0000000000000000e+00 %12.9f\n" %length)
            
            f.write(headers['ATOMS'])
            for atom in frame:
                symb = atom.symbol
                pos = atom.position
                f.write("%-4s    %12.9f    %12.9f    %12.9f\n"%(symb, pos[0], pos[1], pos[2]))

def atoms_to_pwi(fname_out, fname_temp, atoms):
    #Wrap atoms in cell
    atoms.wrap()

    #Read temp pwi file
    with open(fname_temp, 'r') as f:
        lines = f.readlines()
    
    #Insert number of atoms info
    nat = len(atoms)
    idx_nat = None
    for idx, line in enumerate(lines):
        if 'nat' in line: idx_nat = idx
    
    if idx_nat is not None:
        lines[idx_nat] = 'nat = ' + str(nat) +'\n'
    
    cell_str = '\nCELL_PARAMETERS angstrom'
    coord_str = '\n\nATOMIC_POSITIONS angstrom'
    with open(fname_out, 'w') as f:
        f.writelines(lines)
        
        f.write(cell_str)
        cell = atoms.cell
        for axis in cell:
            string = "\n%-9.6f %9.6f %9.6f" %(axis[0], axis[1], axis[2])
            f.write(string)
        
        f.write(coord_str)
        for atom in atoms:
            spec = atom.symbol
            cord = atom.position
            string = "\n%-3s %12.9f %12.9f %12.9f" %(spec, cord[0], cord[1], cord[2])
            f.write(string)
    
    return True

def plot_sampling_stat(phase, max_devis, selected_indices, high_devi_indices, checked_indices, low_devi_indices, min_devi):
    #Plot statistichs of devis
    fig, ax = plt.subplots(1,figsize=(10, 5), dpi=300)

    #Get x and y data:
    x, y = np.arange(max_devis.size), max_devis

    #Fake histogram for large data
    ax.plot(x, y, color='white', linewidth=0.01)

    #Bool arrays of sampled, high_devi, too_close and low_devi indeces
    idxs_sampled = [True if idx in selected_indices else False for idx in range(x.size)]
    idxs_highdev = [True if idx in high_devi_indices else False for idx in range(x.size)]
    idxs_tooclos = [True if idx in checked_indices else False for idx in range(x.size)]
    idxs_lowdevi = [True if idx in low_devi_indices else False for idx in range(x.size)]
    
    #Background indeces
    idxs_background = [ not ( samp or hdev or toocl or ldev ) for samp, hdev, toocl, ldev in zip(idxs_sampled, idxs_highdev, idxs_tooclos, idxs_lowdevi)]

    #Set legend
    legend_elements = []

    #Color graph area -> fake histogram for large data
    #Background: thin and blue
    ax.fill_between(x=np.arange(max_devis.size), y1=max_devis, where = idxs_background, color='blue', alpha=1, linewidth=0.2)
    legend_elements.append(Line2D([0], [0], marker='s', color='w', label='Frame deviations', markerfacecolor='blue', markersize=8))
    #Low devi: thicker and grey
    ax.fill_between(x=np.arange(max_devis.size), y1=max_devis, where = idxs_lowdevi, color='gray', alpha=1, linewidth=0.5)
    legend_elements.append(Line2D([0], [0], marker='s', color='w', label='Low deviations', markerfacecolor='gray', markersize=8))
    #Too close: thicker and red
    ax.fill_between(x=np.arange(max_devis.size), y1=max_devis, where = idxs_tooclos, color='red', alpha=1, linewidth=0.8)    
    legend_elements.append(Line2D([0], [0], marker='s', color='w', label='Too close atoms', markerfacecolor='red', markersize=8))
    #High devi: thicker and black
    ax.fill_between(x=np.arange(max_devis.size), y1=max_devis, where = idxs_highdev, color='black', alpha=1, linewidth=1.0)
    legend_elements.append(Line2D([0], [0], marker='s', color='w', label='High deviations', markerfacecolor='black', markersize=8))
    #Sampled: thicker and green
    ax.fill_between(x=np.arange(max_devis.size), y1=max_devis, where = idxs_sampled, color='green', alpha=1, linewidth=1.0)
    legend_elements.append(Line2D([0], [0], marker='s', color='w', label='Sampled frames', markerfacecolor='green', markersize=8))
    
    #Threshold lines
    ax.plot(x, min_devi*np.ones(x.size), color='black', linewidth=0.75, ls='--')
    
    #Set lims
    ax.set_xlim(0.0, x[-1])
    ax.set_ylim(0.0, np.max(y)*1.1)
    
    #Set legend
    plt.legend(handles=legend_elements,fontsize=8,loc='upper left', bbox_to_anchor=(0.05, 0.95),framealpha=0.5)
    
    #Save figure
    fig_out = 'SAMPLED/dyn' + str(phase) +'-sampling.png'
    fig.savefig(fig_out)    

def report_to_logfile(fname_log, msg):
    with open(fname_log, 'a') as flog:
        flog.write(msg)

#Check distances between atoms greater than safe distance
def _check_atom_distances(frame, cutoff=0.75):
    #Get distance matrix considering pbc
    dist_matrix = get_distances(frame.positions, cell=frame.cell, pbc=True)[1]

    #Check minimum distance conditions
    for id1, at1 in enumerate(frame[:-1]):
        r1 = covalent_radii[at1.number]
        for id2, at2 in enumerate(frame[id1+1:]):
            r2 = covalent_radii[at2.number]
            
            #Get real index of second atom
            real_idx_2 = id1 + id2 + 1
            distance = dist_matrix[id1, real_idx_2]
            min_distance = ( r1 + r2 )*cutoff

            if distance < min_distance: 
               return False    
    
    return True

#Method to block-sample trajectory
def block_sample_atoms_by_devi(atoms, devi, n_samples, min_devi_threshold, max_devi_threshold, too_close_cutoff=0.75):
    #Compute number of frames for each block
    n_frames = len(atoms)
    block_size = n_frames // n_samples

    #Define list of selected frames
    selected_frames, selected_indices = [], []

    #Define list of checked(and excluded) frames
    checked_frames, checked_indices = [], []

    #Define list of frames excluded by low devi
    low_devi_frames, low_devi_indices = [], []

    #Define list of frames excluded by high devi
    high_devi_frames, high_devi_indices = [], []

    #Loop over blocks in trajectory
    stop_next_block_selection = False
    for i in range(n_samples):
        #Check condition to stop block selection
        if stop_next_block_selection: break

        #Get start and end indexes of block
        start = i * block_size
        end = (i + 1) * block_size if i < n_samples - 1 else n_frames

        #Get current proccessed block of deviations and atoms
        block_devi = devi[start:end]
        block_atoms = atoms[start:end]

        #Skip if block is empty
        if len(block_devi) == 0:
            continue

        #n_trials = number of candidate trials if distance between atoms is to small
        n_trials = int(len(block_devi)//10) #10% of blocksize
        if n_trials < 1: n_trials = 1

        #Get frame with maximum deviation: candidate frame
        max_devi_idx = np.argmax(block_devi)
        max_devi_value = block_devi[max_devi_idx]

        #Pass to next block if minimum devi is not reached
        if max_devi_value < min_devi_threshold:
            low_devi_frames.extend(block_atoms)
            low_devi_indices.extend(range(start, end))
            continue

        #Get number of available frame in block
        remaining = len(block_devi)
        
        #Maximum mdevi threshold reached: safe stop next block selections
        if max_devi_value > max_devi_threshold:
            remaining -= 1
            stop_next_block_selection = True

            #Save high devi frame and index
            high_devi_frames.append(block_atoms[max_devi_idx])
            high_devi_indices.append(start + max_devi_idx)

            #Search for next maximum devi in current block
            while True and remaining > 0:
                block_devi[max_devi_idx] = -np.inf
                max_devi_idx = np.argmax(block_devi)
                max_devi_value = block_devi[max_devi_idx]

                #Found candidate frame
                if max_devi_value < max_devi_threshold:
                    break
                #Append frame to high_devi list
                else:
                    high_devi_frames.append(block_atoms[max_devi_idx])
                    high_devi_indices.append(start + max_devi_idx)                    
                    remaining -= 1
            
            #No frame with devi lower than max_devi
            if remaining <= 0:
                break
        
        #If reached here, every other candidate frame has devi between min and max thresholds
        #Check atomic distances of candidate frame
        for _ in range(n_trials):
            #Get candidate frame
            frame = block_atoms[max_devi_idx]
            frame_index = start + max_devi_idx

            #Frame selected in current block, moving to next block
            if _check_atom_distances(frame, too_close_cutoff):
                selected_frames.append(frame)
                selected_indices.append(frame_index)
                break

            #Candidate frame not selected (too-close atoms), get next candidate if possible
            elif remaining > 0:
                remaining -= 1

                #Save frame as checked (and excluded for close distance)
                checked_frames.append(frame)
                checked_indices.append(frame_index)

                #Next candidate frame
                block_devi[max_devi_idx] = -np.inf
                max_devi_idx = np.argmax(block_devi)
            
            #No more frames to check: all remaing frames have too close atoms, next block
            else:
                break

    #Return information of selected, checked, low_devi and high_devi frames and indeces
    return {
        "selected_frames": selected_frames,
        "selected_indices": selected_indices,
        "checked_frames": checked_frames,
        "checked_indices": checked_indices,
        "low_devi_frames": low_devi_frames,
        "low_devi_indices": low_devi_indices,
        "high_devi_frame": high_devi_frames,
        "high_devi_index": high_devi_indices,
    }

#Main method to sample trajectory of current exploration phase
def sample_exploration_traj(exp_info, phase, f_pwi_temp, fname_log):    
    #Get system name
    system = os.path.basename(os.path.dirname(f_pwi_temp))

    #Get lmp traj and model devi
    lmp_traj = 'dyn' + str(phase) + '.lammpstrj'
    mdevi = 'mdevi' + str(phase) + '.out'

    #Consider 'Run' section of exploration.yaml
    exp_info = exp_info[f"Phase{phase}"]['Run']
    
    #Get max scfs to be sampled
    if 'Sampling' in exp_info.keys():
        max_frame_num = int(exp_info['Sampling'])
    else:
        max_frame_num = 0

    #Skip trajectory if nothing to sample
    if max_frame_num == 0:
        to_log = f"System {system}: 0 sampled frames in {lmp_traj}\n"
        report_to_logfile(fname_log, to_log)
        return True

    #Get min_devi
    if 'Min_devi' in exp_info.keys():
        min_devi = float(exp_info['Min_devi'])
    else:
        min_devi = 0.0

    #Get max_devi
    if 'Max_devi' in exp_info.keys():
        max_devi = float(exp_info['Max_devi'])
    else:
        max_devi = 15
    
    #Get safe_distance parameter
    if 'Safe_distance' in exp_info.keys():
        safeDistance = float(exp_info['Safe_distance'])
    else:
        safeDistance = 0.75 #% for covalent radii

    #Read dp model deviation along trajectory, skip if empty
    data_devi = np.loadtxt(mdevi, comments='#')

    #Rehsape array if only one frame
    data_devi = data_devi.reshape((-1, 7))

    if data_devi[:, 0].size == 0: 
        to_log = f"System {system}: 0 sampled frames in {lmp_traj}\n"
        report_to_logfile(fname_log, to_log)
        return False          
    
    #lmptraj and max_devis have syncronized indexes
    #Read lmptraj
    lmptraj = read(lmp_traj, format='lammps-dump-text', index=':')   
    #Get max devis
    max_devis = data_devi[:, 4]

    #Block-sample trajectory
    sampled_dict = block_sample_atoms_by_devi(lmptraj, max_devis, max_frame_num, min_devi, max_devi, safeDistance)

    #Unpack sampled dictionary
    selected_frames, selected_indices = sampled_dict['selected_frames'], sampled_dict['selected_indices']
    checked_frames, checked_indices = sampled_dict['checked_frames'], sampled_dict['checked_indices']
    low_devi_frames, low_devi_indices = sampled_dict['low_devi_frames'], sampled_dict['low_devi_indices']
    high_devi_frames, high_devi_indices = sampled_dict['high_devi_frame'], sampled_dict['high_devi_index']

    #Create pwi files using selected frames and pwi template
    #Create pwi files inside SAMPLED dir
    os.makedirs('SAMPLED', exist_ok=True)
    if len(selected_frames) != 0:
        #Refer frame index to md-trajectory
        frame_idxs = data_devi[:, 0][selected_indices]

        #Save pwi files
        for frame_idx, xyz in zip(frame_idxs, selected_frames):
            fname_pwi = f'SAMPLED/dyn{phase}_{int(frame_idx)}.pwi'
            pwi_written = atoms_to_pwi(fname_pwi, f_pwi_temp, xyz)
        
        #Dump sampled frames as lammpstrj
        at2lmp(f"SAMPLED/samples{phase}.lammpstrj", selected_frames)
    
    #Save configurations with too close atoms
    if len(checked_frames) != 0:
        #Refer frame index to md-trajectory
        frame_idxs = data_devi[:, 0][checked_indices]

        #Create folder containing checked frames
        os.makedirs('TOO-CLOSE', exist_ok=True)        
        
        #Dump checked frames as lammpstrj
        at2lmp(f"TOO-CLOSE/checked{phase}.lammpstrj", checked_frames)
    
    #Save configurations with too high deviations
    if len(high_devi_frames) != 0:
        #Refer frame index to md-trajectory
        frame_idxs = data_devi[:, 0][high_devi_indices]

        #Create folder containing high devi frames
        os.makedirs('HIGH-DEVI', exist_ok=True)        
        
        #Dump high devi frames as lammpstrj
        at2lmp(f"HIGH-DEVI/high_devi{phase}.lammpstrj", high_devi_frames)
    
    #Plot sampling statistics
    plot_sampling_stat(phase, max_devis, selected_indices, high_devi_indices, checked_indices, low_devi_indices, min_devi)

    #Update LOG file
    to_log = f"{system} | phase{phase}: {len(selected_frames)} sampled frames\n"
    report_to_logfile(fname_log, to_log)