import dpdata as dp
import numpy as np
from ase.visualize.plot import plot_atoms
from matplotlib import pyplot as plt, colors

#Load test data as dict of numpy arrays
def load_parity_data(parity_data_fname, min_data_num=1):
    # Read parity data file
    with open(parity_data_fname, 'r') as f:
        data_str = f.readlines()

    # Read each block of data (system' s data) in a dictionary
    all_data = {}
    for line in data_str:
        tks = line.split()
        if '#' in line:
            system_name = tks[1].split('/')[-1].strip(':')
            all_data[system_name] = []
        
        else:
            all_data[system_name].append(tks)
    
    #Get system keys
    systems = list(all_data.keys())

    #Trasform data to dict of numpy array
    for system in systems:
        #Check if data is enough
        if len(all_data[system]) < min_data_num:
            del all_data[system]

        #Load data as numpy array
        else:
            data = all_data[system]
            all_data[system] = np.array(data, dtype=float)
    
    return all_data

def npy_to_ase(system_dataset_path, frame_idx=0):
    #Load data
    frame = dp.LabeledSystem(system_dataset_path, fmt='deepmd/npy')
    nframes_sys = frame.get_nframes()
    
    #Select idx frame
    frame = frame[frame_idx]
    atoms_sys = frame.to(fmt='ase/structure')[0]
    
    #Plot first frame
    atoms_sys.wrap(pretty_translation=True)

    return atoms_sys, nframes_sys


def parity_plot(parity_data, dataset_path, out_fname, width=5, height=5, ncols=6):
    # Set correct number of rows and columns
    if len(parity_data) <= ncols:
        ncols = len(parity_data)
        nrows = 1
    else:
        nrows = int(len(parity_data)/ncols)

    # Define canvas with nrows x ncols
    fig, axs = plt.subplots(nrows, ncols, figsize=(ncols*width, nrows*height))

    # Initialize num frames
    nframes = 0

    # Loop over canvas block to plot each system
    for i in range(nrows):
        for j in range(ncols):

            # Bind axis idxs to system idx
            idx = i*ncols + j
            if idx >= len(parity_data): break

            #Get system name and test data for that system
            system, parity_data_sys = list(parity_data.items())[idx]

            #Get data for parity plot
            DFT = parity_data_sys[:,:3].flatten()
            NNP = parity_data_sys[:,3:].flatten()
            x, y = DFT, NNP

            #Compute rmse and mae
            err = x - y
            rmse = np.sqrt(np.sum(err*err)/err.size)
            mae = np.abs(err).mean()

            #Get boundary data
            data_max = np.max([x.max(), y.max()])
            data_min = np.max([x.min(), y.min()])

            #Get axis for the system
            if nrows == 1:
                ax = axs[j]
            else:
                ax = axs[i, j]

            #histogram definition
            bins = [100, 100] # number of bins

            # # histogram the data
            # hh, locx, locy = np.histogram2d(x, y, bins=bins)

            #Create density plot
            s = ax.hist2d(x, y, bins=bins, cmin=1, cmap='jet', norm=colors.LogNorm())
            
            #Set bounds
            ax.set_xlim(left=data_min, right=data_max)
            ax.set_ylim(bottom=data_min, top=data_max)
            
            #Create parity line
            half_line = np.linspace(data_min, data_max, 1000)
            ax.plot(half_line, half_line, color='black', ls='-')

            #Show rmse and mae
            pos_x, pos_y = 0.9*data_min, 0.7*data_max
            stat_str = f"rmse = {rmse:.3f}\n mae = {mae:.2f}"
            ax.text(pos_x, pos_y, stat_str)

            #Get system dataset path
            dataset_system = dataset_path + '/' + system 

            #Pick one frame to create system rapresentative
            atoms, nframes_sys = npy_to_ase(dataset_system, frame_idx=0)

            #Create sub-axis for plotting atoms
            dim = data_max - data_min
            pos_x, pos_y = data_min + 0.7*dim , data_min
            aseax = ax.inset_axes(bounds=[pos_x, pos_y, dim*0.3, dim*0.5], transform=ax.transData)

            #Plot atoms via ase
            plot_atoms(atoms, aseax, rotation=('-90x,0y,0z'))
            aseax.set_xticks([])
            aseax.set_yticks([])

            #Show system axis title
            ax.set_title(system + ' ('+ str(nframes_sys)+')')

            #Update total frames counting
            nframes += nframes_sys            

    # Dump total number of frames     
    print(f"Total number of frames {nframes}")

    # Use tight layout
    fig.tight_layout()
    
    # Dump image
    fig.savefig(out_fname)


if __name__ == '__main__':
    import sys
    # Get command line arguments
    usg_str = "Usage:\npython parity_plot.py  /path/to/parity/data.out  /path/to/npy/dataset  /path/to/output/dir  min_data_for_plotting[default=1]"

    # Check arguments
    if len(sys.argv) != 4 and len(sys.argv) != 5:
        sys.exit(usg_str)
    
    # Get arguments
    elif len(sys.argv) == 4:
        parity_data_file = sys.argv[1]
        npy_dataset_path = sys.argv[2]
        output_fname = sys.argv[3]
        min_data_for_plotting = 1
    else:
        parity_data_file = sys.argv[1]
        npy_dataset_path = sys.argv[2]
        output_fname = sys.argv[3]
        min_data_for_plotting = int(sys.argv[4])
    
    # Load parity data for every system in dataset
    parity_data_per_system = load_parity_data(parity_data_file, min_data_num=min_data_for_plotting)

    # Dump parity plots per system
    parity_plot(parity_data_per_system, npy_dataset_path, output_fname)