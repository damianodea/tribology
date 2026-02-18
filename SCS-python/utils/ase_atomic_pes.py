from chgnet.model.dynamics import CHGNetCalculator
from deepmd.calculator import DP
import matplotlib.pyplot as plt
from ase import Atoms
import numpy as np
import itertools
import os


def load_model(model_path):
    #Use pre-trained CHGnet
    if model_path == 'CHGNET':
        prefix = 'chg'
        ase_calculator = CHGNetCalculator()
    
    #Use dp model
    elif os.path.basename(model_path).split('.')[-1] == 'pb':
        prefix = 'dp'
        ase_calculator = DP(model=model_path)
    
    else:
        sys.exit("Model not recognized!")    
    
    return ase_calculator

def ase_atomic_pes(model_path, atom_types, distance, num_bins):
    #Perform pes between each pair of atoms defined in 'atom_types' using the model in 'model_path'

    #Wrapper to load multiple models
    model = load_model(model_path)

    #Define ase atoms based on pair of atoms
    data = {}
    for at1, at2 in itertools.combinations_with_replacement(atom_types, 2):
        #Define ase atoms
        atoms = Atoms(f"{at1}{at2}", positions=[(0, 0, 0), (0, 0, distance)])
        
        #Attach model calculator
        atoms.calc = model

        #Distance loop: perform scf at each relative position and store energies and forces
        energies, forces = [], []
        for r in np.linspace(0, distance, num_bins):
            #Update last atom z-position
            atoms.positions[1, 2] = distance - r

            #Get energies and forces
            e = atoms.get_potential_energy()
            f = atoms.get_forces()

            #Store energy and forces
            energies.append(e)
            forces.append(e)
        
        #Reverse data, from 0 -> distance
        energies, forces = energies[::-1], forces[::-1]

        #Store data
        data[f"{at1}-{at2}"] = energies
    
    #Store positions of pes evaluation
    data['Distance'] = [distance - r for r in np.linspace(0, distance, num_bins)][::-1]

    return data

def plot_data(data, atom_types):
    #Get number of axis
    num_axes = len(data) - 1

    #Get distance values
    distances = data['Distance']

    #Define canvas
    fig, axs = plt.subplots(nrows=num_axes, sharex=True, figsize=(10, num_axes*5))
    for pair_label, pair_data, ax in zip(data.keys(), data.values(), axs):
        # #Get atomic pair pes
        # pair_label, pair_data = list(data.keys())[idx], list(data.values())[idx]

        #Normalization: zero energy at infinity
        Y = np.array(pair_data)
        Y -= Y[-1]

        #Plot on axis
        ax.plot(distances, Y)
        
        #Set title and axis label
        ax.set_title(f"{pair_label} dimer energy")
    
    #Set axes labels
    fig.text(0.5, 0.001, 'Distance (A)', ha='center')
    fig.text(0.001, 0.5, 'Energy (eV)', va='center', rotation='vertical')

    #Save figure
    fig.savefig(''.join(atom_types)+'_pair_pes.png')

    return True

def save_data(data):
    return

if __name__ == '__main__':
    import sys
    
    #Usage string info
    usg_str = "Usage:\npython ase_atomic_pes.py model_path at1:...:atN Rmax Nbins"
    if len(sys.argv) != 5: sys.exit(usg_str)

    model_path = sys.argv[1]
    atom_types = sys.argv[2].split(':')
    distance = float(sys.argv[3])
    num_bins = int(sys.argv[4])

    #Calculate pes between pairs of atoms
    energy_data = ase_atomic_pes(model_path, atom_types, distance, num_bins)

    #Plot calulcated data
    plotting = plot_data(energy_data, atom_types)