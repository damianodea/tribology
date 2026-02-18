# SCS
Strategic Configuration Sampling or SCS in short, is a flexible and user-friendly program designed to generate compact dataset for machine learning interatomic potential (MLIP) training. Starting from an existing, often limited, dataset, SCS augments it by sampling new data employing an iterative active learning approach.
Each iteration of active learning workflow proceeds in steps. At firts an ensemble of MLIPs is trained on the available dataset. The MLIP ensemble is then used to explore the chemical configuration space of some systems of interest and a pool of candidate atomic configurations is extracted from the exploratory trajectories. Lastly, the sampled atomic configurations are computed using ab initio methods to collect new data. This procedure is iterated over until the MLIP ensemble is able to give confident predictions on the candidate data or when the user decides to stop the active learning workflow.

# Installation

## Requirements

Currently SCS interfaces three well-known softwares during the active learning workflow. They are required to be installed and their executable path must be visible by the user:
- [`DeePMD-kit`](https://docs.deepmodeling.com/projects/deepmd/en/stable/index.html), for MLIP training;
- [`Lammps`](https://www.lammps.org/) with DeePMD-kit plug-in, for explorative MLIP molecular dynamics;
- [`Quantum Espresso`](https://www.quantum-espresso.org/), for ab initio single point calculations;

The `packmol` package is required if one wants to work with molecular systems in addition to condensed phase systems.
- [`packmol`](https://m3g.github.io/packmol/), for random placing of molecular systems;

## Dependencies

SCS requires a python interpreter version >= 3.10 and the following python packages must be installed in the python environment:
- [`ase`](https://wiki.fysik.dtu.dk/ase/index.html)
- [`dpdata`](https://docs.deepmodeling.com/projects/dpdata/en/master/index.html)
- [`matplotlib`](https://matplotlib.org/)
- [`PyYAML`](https://pyyaml.org/)

## Download and installation

Before installing SCS it is recommended to create a python virtual environment containing the python packages mentioned.
Activate the virtual environment and download SCS by cloning this repository locally:  

`git clone https://github.com/41bY/SCS-python.git`

Once the download is completed, install the required python packages: 

`pip install -r SCS-python/requirements.txt`

## Program setup

To start a new instance of SCS, create a working directory:

`mkdir SCS-workdir`

To correctly setup the program, copy the `Reference` folder and the input files inside the SCS working directory:  

`cp -r SCS-python/Reference SCS-python/utils/*.sh SCS-workdir/`

Then move the SCS input file from the `Reference` folder to the SCS working directory:

`mv SCS-workdir/Reference/YAML-files/scs.input.yaml SCS-workdir/`

these files can be used as a starting template for the user.
After this procedure the user should have the SCS input file `scs.input.yaml`, SCS scripts `start_scs.sh`, `is_running.sh`, `stop_scs.sh` and the `Reference` folder inside the SCS working directory.

# Program usage

## Input preparation and folder structure

Once the new instance of SCS has been deployed (SCS working directory), the user can start SCS.
SCS requires its own input file in yaml format `scs.input.yaml` and one template input file and one jobscript for each software used in the active learning workflow: DeePMD-kit, Lammps and Quantum Espresso.
The `Reference` folder already contains all these files and the user can simply modify them or use them as template if working on different systems than bash and slurm.

Input file for DeePMD-kit training can be found inside `SCS-workdir/Reference/Training` while jobscripts for training and exploration workflow are inside `SCS-workdir/Reference/Jobscripts`. It is recommended to use these files as a template for the user.

Exploration and ab initio data generation steps require input files for each system the user wants to explore. Multiple systems can be explored and sampled at each active learning iteration. To explore a new system, create its reference folder inside `SCS-workdir/Reference/Systems/` with the name of the system. A working example for a system of water on iron can be found inside `SCS-workdir/Reference/Systems/H2O-Fe110`. It is recommended to use this folder and the files inside it as a template for the user.

Fill the system folder with the exploration input file `exploration.yaml` and ab initio input file and jobscripts: `input.pwi`, `dftinfo.yaml` and `job_qe.sh`. Users are strongly encouraged to seek support from the developers to collaborate on the use and further development of SCS!

## Starting dataset preparation

Before starting SCS the user must place an initial, starting dataset inside the corresponding reference folder `SCS-workdir/Reference/Dataset`. The user can easily perform such a task employing the utility script `SCS-python/utils/Create-initial-dataset.py` by command line:

`python Create-initial-dataset.py <path/to/initial/dataset> <path/to/SCS-workdir/Reference/Dataset> <A1:A2:...:An>`

where `<path/to/initial/dataset>` is the path to an initial dataset, `<path/to/SCS-workdir/Reference/Dataset>` corresponds to the reference folder of the new SCS instance and `<A1:A2:...:An>` is the order of the atomic symbols used within SCS.

Please keep the same order as the one used inside the reference training input `SCS-workdir/Reference/Training/input.json` (if given).
The initial dataset `<path/to/initial/dataset>` must be in `deepmd/npy` format or it can be a folder (or regex if enclosed by `"..."`) containing Quantum Espresso output files `.pwo`.

After this operation the user should find inside the dataset reference path `SCS-workdir/Reference/Dataset`, three sub-folders named `Initial`, `Train` and `Valid` containing the whole starting dataset and a 95%-5% train-valid split division.

## Running SCS

Once all the input files and jobscripts have been prepared inside the `Reference` folder, the user can start, stop and monitor SCS background execution using the three bash scripts: `start_scs.sh`, `stop_scs.sh`, `is_running.sh`.
Inside `start_scs.sh`, the user must set up the path to SCS's python environment and the path to the SCS's main program. 

From now on, the user can launch SCS inside its instance working directory `path/to/SCS-workdir` by running:

`bash start_scs.sh`

afterward SCS will run in background. 
To check the SCS background execution type inside the working directory:

`bash is_running.sh`

While running, SCS will produce a general output file `scs.1.log` containing the current iteration number, a restart file `scs.restart.yaml` that can be modified for custom restarts and the `Iterations` folder, storing each MLIP model, trajectories and Quantum Espresso files produced at every iteration.

To stop SCS background execution, type inside the working directory:

`bash stop_scs.sh`

this command will stop the SCS background execution but it will not affect scheduled jobs submitted by SCS that needs to be killed manually.