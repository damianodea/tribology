from glob import glob
import dpdata as dp
import os

def wrap_lab_sys(labeled_system):
    """ Wrap a labeled system dataset"""

    #Dump labeled system as ase atoms
    ase_atoms = labeled_system.to_ase_structure()

    #Get atom map
    lab_type_map = labeled_system.get_atom_names()

    #Define wrapped labelled system
    wrapped_labeled_system = dp.LabeledSystem(type_map=lab_type_map)
    for id in range(len(ase_atoms)):
        #Get frame
        frame = ase_atoms[id]

        #Save calculation results
        calculator = frame.calc

        #Wrap frame atoms
        frame.wrap()

        #Save wrapped frame to calculator
        calculator.atoms = frame

        #Save calculator to wrapped frame
        frame.calc = calculator

        #Convert to dpdata object
        lab_frame = dp.LabeledSystem(frame, fmt='ase/structure')

        #Append to wrapped labeled system
        wrapped_labeled_system.append(lab_frame)

    return wrapped_labeled_system

def wrap_dataset_regex(regex_data_npy_path):
    """Wrap all datasets in a folder"""

    #Get all npy files
    npy_data_paths = glob(regex_data_npy_path)

    nframes = 0
    #Wrap all npy datasets
    for npy_data_path in npy_data_paths:
        #Load dataset
        lab_sys = dp.LabeledSystem(npy_data_path, fmt='deepmd/npy')

        #Wrap dataset
        wrapped_lab_sys = wrap_lab_sys(lab_sys)

        #Get dirname
        dirname, dataname = os.path.dirname(npy_data_path), os.path.basename(npy_data_path)
        wrapped_dirname = dirname + f"/{dataname}_wrapped"

        #Dump wrapped dataset
        wrapped_lab_sys.to_deepmd_npy(wrapped_dirname)

        #Inform user
        nframes_sys = wrapped_lab_sys.get_nframes()
        nframes += nframes_sys
        print(f"{wrapped_lab_sys.get_nframes()} frames in the wrapped dataset saved at {wrapped_dirname}")
    
    print(f"{nframes} total frames wrapped")

    return True


if __name__ == '__main__':
    usg_str = "Usage:\npython wrap_npy_dataset.py \"/path/to/dataset/*.npy\""

    import sys
    #Get input arguments
    if len(sys.argv) != 2: sys.exit(usg_str)

    regex_data_npy_path = sys.argv[1]

    #Wrap dataset
    wrap_dataset_regex(regex_data_npy_path)