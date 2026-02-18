import os
import shutil
import random
import dpdata as dp
from glob import glob
from ase.io import read
from datetime import date

def _check_pwo_force_threshold(pwo, threshold=30.0):
    #Load pwo as ase atoms
    frame = read(pwo)

    #Get forces (n_atoms, 3)
    forces = frame.get_forces()

    #Check if any force is above threshold
    if any([any(force > threshold) for force in forces]):
        return False
    else:
        return True

def qe2npy(path_to_sys, atomic_species):
    #Get path to pwo files
    pwos = glob(path_to_sys + '/SAMPLED/*.pwo')

    #If zero pwo skip this system
    if len(pwos) == 0:
        return len(pwos)

    #Define multysystem object with correct atomic order
    ms = dp.MultiSystems(type_map=atomic_species)
    
    #Fill multisystem with new NPY data
    for pwo in pwos:
        #Load pwo as ase atoms
        try:
            frame = read(pwo)
        except:
            print(f"Cannot read {pwo}")
        
        #Remove virials if present
        if 'stress' in frame.calc.results.keys():
            frame.calc.results.pop('stress')
        
        if not _check_pwo_force_threshold(pwo):
            print(f"Force threshold exceeded in {pwo}")
            continue

        #Convert to dpdata object
        lab_sys = dp.LabeledSystem(frame, fmt='ase/structure')

        #Append to dataset
        ms.append(lab_sys)

    #Overwrite NPY folder for this system
    path_to_npy = path_to_sys + '/NPY'
    if os.path.exists(path_to_npy):
        shutil.rmtree(path_to_npy)
    os.makedirs(path_to_npy)

    #Dump dataset to NPY folder
    ms.to_deepmd_npy(path_to_npy)

    #Get number of frames dumped
    num_data = ms.get_nframes()

    return num_data

def collect_dataset(initial_data_path, new_data_paths, atomic_species):
    #Define MultiSystems
    ms = dp.MultiSystems(type_map=atomic_species)

    #Load initial dataset
    for system in glob(initial_data_path+'/*'):
        lab_sys = dp.LabeledSystem(system, fmt='deepmd/npy')
        ms.append(lab_sys)

    #Load scs generated dataset
    for npy in glob(new_data_paths):
        #Check is not empty
        if not os.listdir(npy):
            continue

        #Load new data for each system
        for system in glob(npy+'/*'):
            lab_sys = dp.LabeledSystem(system, fmt='deepmd/npy')
            ms.append(lab_sys)

    #Split dataset to train and valid dataset
    seed = random.randint(0, 10000)
    ms_train, ms_valid, _ = ms.train_test_split(0.05, seed)

    #Get datasets number of data
    num_tot, num_train, num_valid = ms.get_nframes(), ms_train.get_nframes(), ms_valid.get_nframes()

    #Get dataset output dir
    new_dataset_path = os.path.dirname(initial_data_path)

    #Create empty directory to store new dataset
    all_data_path = new_dataset_path + '/' + ''.join(atomic_species) + '-' + str(date.today())
    if os.path.exists(all_data_path):
        shutil.rmtree(all_data_path)
    
    #Create empty directory to store new training dataset
    train_data_path = new_dataset_path + '/Train'
    if os.path.exists(train_data_path):
        shutil.rmtree(train_data_path)

    #Create empty directory to store new validation dataset
    valid_data_path = new_dataset_path + '/Valid'
    if os.path.exists(valid_data_path):
        shutil.rmtree(valid_data_path)    

    #Dump datasets to empty output dirs
    ms.to_deepmd_npy(all_data_path)
    ms_train.to_deepmd_npy(train_data_path)
    ms_valid.to_deepmd_npy(valid_data_path)

    #Get dataset info dict
    data_info = {''.join(atomic_species) + '-' + str(date.today()) : [num_tot, num_train, num_valid]}

    return data_info

def update_logfile(fname_log, dataset_info=None, header=None):
    #Define lines to write
    to_write = []

    #Get header line
    if header is not None:
        to_write.append(f"{header}\n")
    
    #Get dataset info lines
    if dataset_info is not None:
        for system, data in dataset_info.items():
            to_write.append(f"{system}: {data}\n")

    #Append lines to LOG file
    if len(to_write) > 0:
        with open(fname_log, 'a') as f:
            f.writelines(to_write)

def update_dataset(scs_params, iter_dir):
    #Get new dft iteration dirs
    system_dirs = iter_dir + '/Exploration/*'

    #Get atomic species order for dataset construction
    spec_order = scs_params['Dataset']['Atom_types']

    #Get LOG file
    fname_log = iter_dir.split('/Iterations/')[0] + f"/scs.{os.path.basename(iter_dir)}.log"

    #Update LOG file
    update_logfile(fname_log, dataset_info=None, header="Create NPY dataset from ab initio data:")

    #Loop over new dft dirs
    for sys_dir in glob(system_dirs):
        #Get system name
        sysname = os.path.basename(sys_dir)

        #Create new npy dataset
        num_data = qe2npy(sys_dir, spec_order)

        #Get system dataset info
        dataset_info = {sysname : [num_data]}

        #Update LOG file
        update_logfile(fname_log, dataset_info)
    
    #Get initial reference data
    ref_data_path = scs_params['Dataset']['Initial']

    #Get iterations data: /scs/Iterations/*(ite)/Exploration/*(systems)/NPY
    scs_data_path = os.path.dirname(iter_dir) + '/*/Exploration/*/NPY'

    #Collect new updated dataset
    dataset_info = collect_dataset(ref_data_path, scs_data_path, spec_order)

    #Update LOG file
    update_logfile(fname_log, dataset_info, header=f"Collecting all initial and generated dataset up to iteration {os.path.basename(iter_dir)}")    