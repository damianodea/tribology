import os
import sys
import json
import random
import dpdata as dp
from glob import glob

def load_dataset(data_path, atomic_species):
    #Load dataset
    ms = dp.MultiSystems(type_map=atomic_species)

    #Load dataset
    for system in glob(data_path+'/*'):
        lab_sys = dp.LabeledSystem(system, fmt='deepmd/npy')
        ms.append(lab_sys)    

    #Get number of frames
    num_data = ms.get_nframes()

    return ms, num_data

def read_dp_input(f_train_temp, npy_data_dir, species, num_epochs, fname_log):
    #Open LOG file
    fLOG = open(fname_log, 'a')

    #Read dp template input
    with open(f_train_temp, 'r') as f:
        dp_params = json.load(f)

    #Set atomic species in correct order
    dp_params["model"]["type_map"] = species

    #Set training and validation data directories
    data_train_dir, data_valid_dir = npy_data_dir + '/Train', npy_data_dir + '/Valid'    

    #Load training dataset
    ms_train, num_train = load_dataset(data_train_dir, species)
    
    #Get number of training steps
    num_training_steps = int(num_epochs * num_train)

    #Check number of training steps
    if num_training_steps <= 0:
        fLOG.write(f"Number of training step is 0, check {data_train_dir} is not empty and 'N_epochs' > 0: stopping...\n")
        sys.exit()    
    else:
        fLOG.write(f"Training data {data_train_dir} has {num_train} frames\n")
        fLOG.write(f"Ensemble training for {num_epochs} epochs ({num_training_steps} steps)\n")
        dp_params["training"]["numb_steps"] = num_training_steps    

    #Set train and valid data path
    dp_params["training"]["training_data"]["systems"] = data_train_dir
    dp_params["training"]["validation_data"]["systems"] = data_valid_dir
    
    #Everything checked, updating log
    fLOG.write(f"Creating new training directories and training inputs...")
    
    #Close LOG file
    fLOG.close()
    return dp_params

def write_dp_inputs(temp_params, train_dir, num_models):
    #Loop over ensemble of models
    for nn in range(num_models):
        #Set all the seed to random values
        temp_params["model"]["descriptor"]["seed"] = random.randint(1, 100000)
        temp_params["model"]["fitting_net"]["seed"] = random.randint(1, 100000)
        temp_params["training"]["seed"] = random.randint(1, 100000)

        #Set working training dir
        nn_dir = train_dir + f"/NN{nn}"
        os.makedirs(nn_dir, exist_ok=True)     

        #Skip if already initialized
        if os.path.isfile(nn_dir+'/input.json'):
            continue

        #Write json training input
        with open(nn_dir+'/input.json', 'w') as f:
            json.dump(temp_params, f, sort_keys=False, indent=4)

def startup_training(scs_params, scs_iteration_dir):
    #Get scs main directory
    main_dir = scs_iteration_dir.split('/Iterations/')[0]

    #Get logfile
    fname_log = main_dir + f"/scs.{os.path.basename(scs_iteration_dir)}.log"

    #Read scs input parameters for ensemble training
    #Read atomic species
    if 'Atom_types' not in scs_params['Dataset']: sys.exit("Please provide atomic species in scs.input.yaml")
    else: atomic_species = scs_params['Dataset']['Atom_types']
    
    #Read number of models and dp input template
    if 'N_models' not in scs_params['Training']: number_of_models = 8 #Default ensemble size
    else: number_of_models = scs_params['Training']['N_models']

    #Read dp input template and check it
    if 'Reference' not in scs_params['Training']: sys.exit("Please provide a DP input template in scs.input.yaml")
    else: dp_train_temp = scs_params['Training']['Reference']

    #Read data directory
    if 'Dataset_path' not in scs_params['Training']: dp_data_dir = main_dir + f"/Reference/Dataset" #Default data directory
    else: dp_data_dir = scs_params['Training']['Dataset_path']

    #Read number of training epochs
    if 'N_epochs' not in scs_params['Training']: number_of_epochs = 75 #Default number of epochs
    else: number_of_epochs = scs_params['Training']['N_epochs']

    #Read dp input template and check it
    dp_train_parameters = read_dp_input(dp_train_temp, dp_data_dir, atomic_species, number_of_epochs, fname_log)

    #Get current training dir
    current_train_dir = scs_iteration_dir + '/Training'

    #Write dp inputs for ensemble of models
    write_dp_inputs(dp_train_parameters, current_train_dir, number_of_models)    