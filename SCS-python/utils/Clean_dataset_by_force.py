import numpy as np
import dpdata as dp
from glob import glob

#Load dataset from a directory containing multiple systems as Multisystem object
def load_dataset(dataset_path, atom_types):
    """
    Load dataset from a directory containing multiple systems.
    """
    dataset = dp.MultiSystems(type_map=atom_types)
    for sys_path in glob(dataset_path + '/*'):
        lab_sys = dp.LabeledSystem(sys_path, fmt='deepmd/npy')
        dataset.append(lab_sys)
    
    return dataset

#Clean dataset by removing structures with atomic forces above a certain threshold
def clean_system_dataset(system_dataset, force_threshold=1e-2):
    """
    Clean dataset by removing structures with atomic forces above a certain threshold.
    """
    #Get atomic forces: (n_frames, n_atoms, 3)
    forces = system_dataset['forces']
    forces = np.abs(forces)
    
    #Get indices of structures with atomic forces above threshold
    atom_idxs_to_keep = np.all(forces < force_threshold, axis=2) # (n_frames, n_atoms)
    frame_idxs_to_keep = np.all(atom_idxs_to_keep, axis=1) # (n_frames)

    #Get clean dataset
    clean_dataset = system_dataset[frame_idxs_to_keep]
    
    return clean_dataset

if __name__ == '__main__':
    import sys
    usg_str = "Usage:\npython Clean_dataset_by_force.py [full_dataset_path ,str] [at1:...:atN ,str] [force_threshold(eV/A) :float]\
    \nClean dataset by removing structures with atomic forces above a certain threshold."

    if len(sys.argv) != 4: sys.exit(usg_str)

    full_dataset_path = sys.argv[1]
    atom_types = sys.argv[2].split(':')
    force_threshold = float(sys.argv[3])

    #Load dataset from path
    dataset = load_dataset(full_dataset_path, atom_types)

    #Inform user about cleaning procedure
    print(f"Start cleaning procedure: remove structures with |atomic_forces| > {force_threshold} eV/A.")

    #Clean dataset by removing structures with atomic forces above threshold
    clean_dataset = dp.MultiSystems(type_map=atom_types)
    for system_name, system_data in dataset.systems.items():
        #Get clean data for each system
        clean_sys_dataset = clean_system_dataset(system_data, force_threshold)

        #Get statistichs of forces
        num_frames, num_clean_frames = system_data.get_nframes(), clean_sys_dataset.get_nframes()
        num_exclude_frames = num_frames - num_clean_frames

        if num_clean_frames == 0:
            print(f"{system_name}: No frames left after cleaning. Skipping this system.")
            continue

        #Inform user about the number of excluded frames
        print(f"{system_name}: exlcuded {num_exclude_frames} frames out of {num_frames} frames.")

        #Append clean data to clean dataset
        clean_dataset.append(clean_sys_dataset)
    
    #Save clean dataset
    dataset_name = "Clean-data-" + "".join(atom_types)
    clean_dataset.to_deepmd_npy(dataset_name)
    print(f"Clean dataset with {clean_dataset.get_nframes()} frames saved in {dataset_name}")