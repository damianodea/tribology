import dpdata as dpd
from glob import glob
from datetime import date
import numpy as np
import sys
import os

usg_str = "Merge multiple datasets to one single no duplicates dataset with unique type_map at1:...:atn.\nUsage: \npython Merge-datasets.py at1:...:atn dataset1_path ... datasetN_path"

if len(sys.argv) < 3:
    sys.exit(usg_str)
else:
    #Get user defined type_map
    usr_type_map = sys.argv[1].split(':')

    #Check that every path exists and it's not empty
    for path in sys.argv[2:]:
        if not os.path.isdir(path):
            sys.exit("Directory {} not found.\n{}".format(path, usg_str))
        elif not os.listdir(path):
            sys.exit("Directory {} is empty.\n{}".format(path, usg_str))
        else: continue

#Every argument is an existing non-empty path
#Print datasets info
for i, dataset_path in enumerate(sys.argv[2:]):
    dataset = dpd.MultiSystems()
    for sys_path in glob(dataset_path + '/*'):
        dataset.append(dpd.LabeledSystem(sys_path, fmt = 'deepmd/npy'))
    nframes = dataset.get_nframes()
    print("Dataset {} in {} contains {} frames.".format(i, dataset_path, nframes))
    del dataset

#Loading the datasets
merged_dataset = dpd.MultiSystems(type_map=usr_type_map)
for dataset_path in sys.argv[2:]:
    for sys_path in glob(dataset_path + '/*'):
        merged_dataset.append(dpd.LabeledSystem(sys_path, fmt = 'deepmd/npy'))

#If the datset contains duplicates, keep only the unique frames
unique_merged_dataset = dpd.MultiSystems(type_map=usr_type_map)        
for system in merged_dataset:
    uarr, idxs, counts = np.unique(system['energies'], return_index=True, return_counts=True)
    #If two or more energies are the same, check the coordinates
    if np.any(counts > 1):
        ucord, idxs, counts = np.unique(system['coords'], return_index=True, return_counts=True, axis=0)
        if np.any(counts > 1):
            unique_merged_dataset.append(system[idxs])
        else:
            unique_merged_dataset.append(system)
    else:
        unique_merged_dataset.append(system)
del merged_dataset

#Dump unique, merged dataset
final_dataset_path = './Merged-Dataset-' + str(date.today())
nframes = unique_merged_dataset.get_nframes()
print("Dumping {} frames merged dataset to directory {}".format(nframes, final_dataset_path))
os.makedirs(final_dataset_path, exist_ok=True)
unique_merged_dataset.to_deepmd_npy(final_dataset_path, set_size = 200)