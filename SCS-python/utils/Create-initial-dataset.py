#Use ASE to read pwo and convert to NPY format for dp dataset initialization
from ase.io import read
import dpdata as dpd
from glob import glob
import os
import sys

usg_str = 'Create initial dataset in npy format from pwo and/or previous npy data.\nUsage:\npython Create-initial-dataset.py path/to/pwo/or/npy path/to/outdir A1:...:An\
\npath/to/pwo/or/npy is the path to pwo and/or npy data. It can be a path to a single directory or a bash regular expression enclosed by "..."\
\npath/to/outdir is the path where the dataset in .npy format will be stored\
\nA1:...:An is a string defining the order of the atomic species: A1 will be the first atomic specie, ..., An will be the last atomic specie'

if len(sys.argv) != 4:
    sys.exit(usg_str)

path_to_pwo_or_npy = sys.argv[1]
path_to_outdir = sys.argv[2]
atomic_species = sys.argv[3].split(':')

#Creating the dataset
data = dpd.MultiSystems(type_map=atomic_species)
#If QE pwos exist, add them to dataset
files = glob(path_to_pwo_or_npy + '/*.pwo')
if len(files) > 0:
    for file in files:
        atoms = read(file, index=":")
        for atom in atoms:
            atom.calc.results.pop('stress', None) #Remove info about virials
            Lab_data = dpd.LabeledSystem(atom, fmt='ase/structure')
            data.append(Lab_data)

#If dirs exist, add them to dataset
raws = glob(path_to_pwo_or_npy + '/*/type_map.raw')
if len(raws) > 0:
    for raw in raws:
        dir = os.path.dirname(raw)
        Lab_data = dpd.LabeledSystem(dir, fmt='deepmd/npy')    
        data.append(Lab_data)

#Dump dataset
print(data)

path_to_full_dataset = path_to_outdir + '/Initial'
os.makedirs(path_to_full_dataset, exist_ok=True)
data.to_deepmd_npy(path_to_full_dataset)

#Training-validation splitting 90-10
(data_training, data_validation, dict) = data.train_test_split(0.1, 11991)

#Training dataset
path_to_train_dataset = path_to_outdir + '/Train'
os.makedirs(path_to_train_dataset, exist_ok=True)
data_training.to_deepmd_npy(path_to_train_dataset)

#Validation dataset
path_to_valid_dataset = path_to_outdir + '/Valid'
os.makedirs(path_to_valid_dataset, exist_ok=True)
data_validation.to_deepmd_npy(path_to_valid_dataset)