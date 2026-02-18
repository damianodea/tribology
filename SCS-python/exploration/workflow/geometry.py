import os
import sys
import subprocess
import numpy as np
from glob import glob
from ase import Atom, Atoms
from ase.io import read, write
from collections import Counter
from ase.build import surface, add_adsorbate
from scipy.sparse.csgraph import connected_components
from ase.neighborlist import NeighborList, natural_cutoffs


def build_random_bulk(bulk_info):
    #Choose randomly among the possible prompted structures
    structure_names = [structure_name for structure_name in bulk_info.keys() if 'Structure' in structure_name]
    structure_index = np.random.randint(0, len(structure_names))
    structure_name = structure_names[structure_index]

    #Load bulk structure, ase atoms
    bulk = bulk_info[structure_name]['Path']

    #Customize bulk: defects, substitutional, strain
    defects, strains = {}, {}
    
    #Get custom keys specifically for that structure
    if 'Defects' in bulk_info[structure_name] or 'Strain' in bulk_info[structure_name]:
        #Get bulk defects
        if 'Defects' in bulk_info[structure_name].keys():
            defects = bulk_info[structure_name]['Defects']
        
        #Get strain
        if 'Strain' in bulk_info[structure_name].keys():
            strains = bulk_info[structure_name]['Strain']

    #Get general custom keys for that system
    elif 'Defects' in bulk_info.keys() or 'Strain' in bulk_info.keys():
        #Get bulk defects
        if 'Defects' in bulk_info.keys():
            defects = bulk_info['Defects']
        
        #Get strain
        if 'Strain' in bulk_info.keys():
            strains = bulk_info['Strain']

    #Customize bulk structure
    bulk = build_custom_bulk(bulk, defects, strains)        

    return bulk

def build_custom_bulk(ase_atoms, bulk_def, deform):
    #Get atomic info
    nat = len(ase_atoms)
    cell = ase_atoms.get_cell()
    ase_atoms.set_pbc((True, True, True))

    #Strain the structure
    if bool(deform):
        #Get strain on axis
        deformations = [deform[axis] if axis in deform.keys() else 1.0 for axis in ['x', 'y', 'z']]
        deformations = np.array(deformations)

        #Get atomic positions relative to cell
        relative_positions = ase_atoms.get_scaled_positions(wrap=True)

        #Deform cell and atomic positions
        cell *= deformations
        absolute_positions = relative_positions@cell

        #Set new cell and atomic positions
        ase_atoms.positions = absolute_positions
        ase_atoms.cell = cell

    #Create bulk defects
    if bool(bulk_def):
        for def_type, def_prob in bulk_def.items():
            #Number of bulk defects
            def_num = int(nat*def_prob)
            
            #Extract random def_num indeces for creating defects
            def_idxs = np.random.choice(nat, size=def_num, replace=False)

            #Create vacancies
            if def_type == 'Void':
                ase_atoms = Atoms([atom for idx, atom in enumerate(ase_atoms) if not idx in def_idxs])
                nat = len(ase_atoms)
                
            #Create substitutional
            else:
                for def_idx in def_idxs:
                   ase_atoms[def_idx].symbol = def_type
    
    ase_atoms.set_cell(cell)
    return ase_atoms

#Building surface methods-----------------------------------------------------------------------------------------------------
def build_random_surface(surf_info, loc):
    #Choose randomly among the possible prompted structures
    structure_names = [structure_name for structure_name in surf_info.keys() if 'Structure' in structure_name]
    structure_index = np.random.randint(0, len(structure_names))
    structure_name = structure_names[structure_index]
    surface_info = surf_info[structure_name]

    #Build surface from bulk structure
    if 'Miller' in surface_info.keys():
        if 'Dimensions' not in surface_info.keys(): sys.exit("Please provide both 'Miller' and 'Dimensions' keywords to build surface from bulk, stopping...")
        #Load surface creation info
        bulk, miller = surface_info['Path'], surface_info['Miller']
        size = [[float(ele.strip('A')), 'angstrom'] if 'A' in ele else [int(ele.strip('L')), 'layers'] for ele in surface_info['Dimensions']]

        #Build surface
        surf = build_surface_from_bulk(bulk, miller, size)
    
    #Or load it directly
    else:
        surf = surface_info['Path']
    
    #Customize surface: defects, substitutional, passivating species
    bulk_defects, surface_defects, passivations = {}, {}, {}
    if 'Bulk_defects' in surface_info.keys():
        bulk_defects = surface_info['Bulk_defects']
    if 'Surface_defects' in surface_info.keys():
        surface_defects = surface_info['Surface_defects']
    if 'Passivation' in surface_info.keys():
        passivations = surface_info['Passivation']
    
    #Build custom surface
    surf = build_custom_slab(surf, loc, bulk_defects, surface_defects, passivations)

    #Add void
    if 'Void' in surface_info.keys():
        if loc == 'upper': sgn = -1
        elif loc == 'lower': sgn = +1
        surf.cell[2, 2] += sgn*float(surface_info['Void'])

    return surf

def build_surface_from_bulk(bulk, miller, size):
    #Build surface with ase
    #Number of atomic layers is given
    if 'layers' in size[2][1]:
        num_layers = size[2][0]
    #Height of surface is given, find maximum number of atomic layers
    elif 'angstrom' in size[2][1]:
        surfmin = surface(bulk, miller, 2, vacuum=0.0)
        height = surfmin.positions.max(axis=0)[2] - surfmin.positions.min(axis=0)[2]
        num_layers = size[2][0]//height
        del surfmin
    if num_layers == 0: num_layers = 1
    
    #Build the general surface, center to origin
    surf = surface(bulk, miller, int(num_layers))
    surf.positions -= surf.positions.min(axis=0)

    #Orthorombize a non-orthorombic cell, assuming a // x
    surf_cell = surf.cell
    if surf_cell[1][0] > 1e-14:
        surf = surf.repeat((1, 2, 1))
        cell_y = surf.cell[1, 1]
        # surf.positions[:, 0] -= np.round(surf.positions[:, 0]/surf_cell[0][0])*surf_cell[0][0]
        surf.set_cell([surf_cell[0][0], cell_y, 0.0])
        surf.wrap()
    surf_cell = np.diag(surf.cell)

    #Adjust xy-dimension using the orthorombic cell
    if 'layers' in size[0][1]:
        num_layers_x = size[0][0]
    elif 'angstrom':
        num_layers_x = size[0][0]//surf_cell[0]
    if num_layers_x == 0: num_layers_x = 1

    if 'layers' in size[1][1]:
        num_layers_y = size[1][0]
    elif 'angstrom':
        num_layers_y = size[1][0]//surf_cell[1]
    if num_layers_y == 0: num_layers_y = 1

    #Get final surface
    surf = surf.repeat([int(num_layers_x), int(num_layers_y), 1])
    height = surf.positions.max(axis=0)[2] - surf.positions.min(axis=0)[2]
    surf.cell[2, 2] = height + 15

    return surf

def build_custom_slab(ase_atoms, kind, bulk_def, surf_def, pass_def):
    #Get atom info
    nat = len(ase_atoms)
    cell = ase_atoms.get_cell()
    ase_atoms.set_pbc((True, True, False))

    #Get bulk-boundary division
    if bool(bulk_def) or bool(surf_def) or bool(pass_def):
        lower, bulk, upper = boundary_bulk_split(ase_atoms)

        #Create bulk defects
        if bool(bulk_def):
            #Get number of bulk atoms
            nat = len(bulk)

            #Loop over bulk defect types
            for def_type, def_prob in bulk_def.items():
                #Number of bulk defects
                def_num = int(nat*def_prob)
                
                #Extract random def_num indeces for creating defects
                def_idxs = np.random.choice(nat, size=def_num, replace=False)

                #Create vacancies
                if def_type == 'Void':
                    bulk = Atoms([atom for idx, atom in enumerate(bulk) if not idx in def_idxs])
                    
                #Create substitutional
                else:
                    for def_idx in def_idxs:
                        bulk[def_idx].symbol = def_type

        #Get topmost atomic layer for lower surface
        if kind == 'lower':
            sgn = +1
            atomic_layer = upper
            bulk_layers = lower + bulk
        
        #Get lowermost atomic layer for upper surface
        elif kind == 'upper':
            sgn = -1
            atomic_layer = lower
            bulk_layers = bulk + upper
        
        #Get both upper and lower surfaces (slab)
        else:
            sgn = 0
            atomic_layer = lower + upper
            bulk_layers = bulk
                    
        #Surface defects
        if bool(surf_def):
            #Get number of surface atoms
            nat = len(atomic_layer)          

            #Create surface defects
            for def_type, def_prob in surf_def.items():

                #Number of defects
                def_num = int(nat*def_prob)

                #Extract random def_num indeces for creating defects
                def_idxs = np.random.choice(nat, size=def_num, replace=False)

                #Create vacancies
                if def_type == 'Void':
                    atomic_layer = Atoms([atom for idx, atom in enumerate(atomic_layer) if not idx in def_idxs])

                #Create substitutional
                else:
                    for def_idx in def_idxs:
                        atomic_layer[def_idx].symbol = def_type
    
        #Surface passivation
        if bool(pass_def):

            #Cumulative probability of passivation per site
            cum_prob_pass = []
            prob = 0.0
            for pass_prob in pass_def.values():
                prob += pass_prob
                cum_prob_pass.append(prob)
            tot_prob_pass = cum_prob_pass[-1]

            nat = len(atomic_layer)
            pRandoms = np.random.rand(nat)
            pass_types = list(pass_def.keys())
            #Passivating atomic species
            for idx, atom_layer in enumerate(atomic_layer):
                pRandom = pRandoms[idx]
                #No adsorbate
                if pRandom > tot_prob_pass: continue
                #Add adsorbate
                else:
                    for n, cum_prob in enumerate(cum_prob_pass):
                        #Get atomic type of adsorbate
                        if pRandom < cum_prob:
                            if len(pass_types[n]) > 1: #Molecule is complicated, not consider for now
                                sys.exit("Cannot handle passivation by molecules yet but only atoms, skipping...")
                                pass_atom = molecule(pass_types[n])
                            else: #Atom
                                pass_atom = Atom(pass_types[n])
                            
                            #Assign positions to addsorbate
                            pair = Atoms([pass_atom, atom_layer])
                            height = sum(natural_cutoffs(pair))
                            pos = atom_layer.position

                            #Add adsorbate
                            add_adsorbate(atomic_layer, pass_atom, sgn*height, pos[:2])
                            break
            
        #Final surface
        ase_atoms = bulk_layers + atomic_layer

    ase_atoms.set_cell(cell)
    return ase_atoms

def boundary_bulk_split(ase_atoms):
    #Get number of atoms
    nat = len(ase_atoms)

    #Assume surface: disable PBC along z
    ase_atoms.set_pbc((True, True, False))
    
    #Define atom natural cutoffs
    cutoffs = natural_cutoffs(ase_atoms)
    nl = NeighborList(cutoffs, self_interaction=False, bothways=True)
    nl.update(ase_atoms)

    #Get coordination number (CN) of each atom
    CNs = []
    for i, atom in enumerate(ase_atoms):
        #Neighbors count
        indices, _ = nl.get_neighbors(i)
        num_neighbors = len(indices)

        #Get coordination number per atom index
        CNs.append(num_neighbors)
    
    # #TODO: New way to split boundary-bulk atoms
    # #Get sorted atoms
    # z_ordered_atom_idxs = np.argsort(ase_atoms.positions[:,2])

    # #Get 10% lowermost and uppermost atoms
    # idx_10_percent = int(nat*0.1)
    # z_ordered_atom_idxs = np.argsort(ase_atoms.positions[:,2])
    # lowest_atom_idxs = z_ordered_atom_idxs[:idx_10_percent]
    # highest_atom_idxs = z_ordered_atom_idxs[-idx_10_percent:]

    #Get lowermost and uppermost z-coordinate
    z_min, z_max = ase_atoms.positions[:,2].min(), ase_atoms.positions[:,2].max()

    #Define safe threshodls for lower and upper atoms
    # z_thr = 2.0 #Angstrom
    z_thr = 0.33*(z_max - z_min) #Divide slab in 3 equal parts by height

    #Get lowermost and uppermost atoms
    lowest_atom_idxs, highest_atom_idxs = [], []
    for idx, atom in enumerate(ase_atoms):
        #Lower atoms
        if atom.position[2] < z_min + z_thr:
            lowest_atom_idxs.append(idx)
        
        #Upper atoms
        elif atom.position[2] > z_max - z_thr:
            highest_atom_idxs.append(idx)

    #Classify atoms with lowest CN among highest and lowest
    lower_boundary_idxs, higher_boundary_idxs = [], []
    #Atoms ordered with increasing CN
    for idx in np.argsort(CNs):
        #Get lower boundary atom
        if idx in lowest_atom_idxs:
            lower_boundary_idxs.append(idx)
        #Get higher boundary atom
        elif idx in highest_atom_idxs:
            higher_boundary_idxs.append(idx)
    
    # #Reduce classification to 5% of atoms
    # idx_5_percent = int(nat*0.05)
    # lower_boundary_idxs = lower_boundary_idxs[:idx_5_percent]
    # higher_boundary_idxs = higher_boundary_idxs[-idx_5_percent:]
    
    #From idx to atoms
    lower_boundary_atoms, upper_boundary_atoms, bulk_atoms = [], [], []
    for idx, atom in enumerate(ase_atoms):
        #Get lower boundary atom
        if idx in lower_boundary_idxs:
            lower_boundary_atoms.append(atom)
        #Get higher boundary atom
        elif idx in higher_boundary_idxs:
            upper_boundary_atoms.append(atom)            
        #Get bulk atom
        else:
            bulk_atoms.append(atom)

    #Get ase atoms object
    lower_boundary_atoms = Atoms(lower_boundary_atoms)
    upper_boundary_atoms = Atoms(upper_boundary_atoms)
    bulk_atoms = Atoms(bulk_atoms)    

    #Get division between bulk and superficial atoms
    return lower_boundary_atoms, bulk_atoms, upper_boundary_atoms
#-----------------------------------------------------------------------------------------------------------------------------

#Buildining molecules methods-------------------------------------------------------------------------------------------------
def build_random_molecules(mol_info, start_box, packmol):
    #Get user defined box of molecules
    mol_box = mol_info['Box']
    
    #Assign starting box for placing molecules
    if start_box is None:
        #Box given in input for molecules
        if len(mol_box) == 1: box = [mol_box[0] for n in range(3)]
        else: box = mol_box
    
    #Use minimum dimension box possible if molecule box is fully assigned
    elif len(mol_box) == 3:
        box = [mol_ax if mol_ax <= start_ax else start_ax for mol_ax, start_ax in zip(mol_box, start_box)]

    #Use XY-surface and Z for molecules
    else:
        box = [ax for ax in start_box[:2]] + [mol_box[-1]]
    box = np.array(box, dtype=float)

    #Get path to molecular structures and their numbers
    mol_and_numbers = [[obj['Path'], obj['Number']] for key, obj in mol_info.items() if 'Structure' in key]

    #If density given, create random molecule compositions based on their numbers
    if 'Density' in mol_info.keys():
        density = mol_info['Density']
        mol_and_numbers = get_random_composition(mol_and_numbers, density, box)

    #Write xyz molecules data as temporary files for packmol
    molpath_and_numbers = []
    for idx, molnum in enumerate(mol_and_numbers):
        molpath = 'Mol' + str(idx) + '.xyz'
        mol = molnum[0]
        num = molnum[1]
        write(molpath, mol)
        molpath_and_numbers.append([molpath, num])
    del mol_and_numbers
    
    #Write packmol input
    packmol_input = write_packmol_input(molpath_and_numbers, box)

    #Launch packmol loop until convergence
    for iteration in range(3):
        convergence = run_packmol(packmol, packmol_input)
        if not convergence:
            #Increase z dimension by 10% | other method: remove random molecules
            box[2] *= 1.1
            packmol_input = write_packmol_input(molpath_and_numbers, box)
        else: break
    if not convergence: sys.exit("Packmol did not run succesfully, stopping...")

    #Load molecules
    mols = read('molecules.xyz')
    mols.set_cell(box)    

    #Print out molecules density
    density = np.sum(mols.get_masses())/np.prod(box) #aum/angstrom^3
    density /= 0.6022137 #g/cm^3

    print(f"Molecules density: {density} g/cm^3", flush=True)
    return mols

def get_random_composition(mol_and_nums, density, box):
    #Convert density from g/cm^3 to amu/ang^3
    gcm2amuang = 0.6022137
    density *= gcm2amuang #amu/ang^3
    volume = np.prod(box) #ang^3

    update_mol_and_numbers = []
    assigned_mass = 0
    num_molecules = len(mol_and_nums)
    for idx, mol_list in enumerate(mol_and_nums):
        mol = mol_list[0] #Ase atoms
        symbols = mol.get_chemical_symbols()
        type_nums = Counter(symbols)

        #Get molecule mass
        mol_mass = np.sum(mol.get_masses())

        #Remaining mass
        remain_mass = density*volume - assigned_mass

        #Get maximum molecule number
        maxN = remain_mass//mol_mass
        userN = int(mol_list[1])

        #Maximum molecule number between 1 and userN
        if maxN > userN: maxN = userN
        elif maxN < 1: maxN = 1
        else: maxN = int(maxN)

        #Get molecule number
        #If last molecule, saturate its number
        if idx == (num_molecules - 1):
            N = maxN
        else:
            N = np.random.randint(1, maxN + 1)
            
        #Add molecule numbers and assigned mass
        update_mol_and_numbers.append([mol, N])
        assigned_mass += N*mol_mass
    
    return update_mol_and_numbers

def write_packmol_input(mol_infos, cell):
    input_packmol_name = 'molecules_input.inp'
    with open(input_packmol_name, 'w') as f:
        #Write header
        f.write(f"tolerance 2.0\n")
        f.write(f"seed -1\n")
        f.write(f"randominitialpoint\n")
        f.write(f"filetype xyz\n")
        f.write(f"output molecules.xyz\n")

        pbc_cell = [float(axis) - 2 for axis in cell]
        for mol_info in mol_infos:
            mol_path = mol_info[0]
            mol_num = int(mol_info[1])

            if mol_num <= 0: continue

            f.write(f"\nstructure {mol_path}\n")
            f.write(f"  number {mol_num}\n")
            f.write(f"  inside box 0. 0. 0. {pbc_cell[0]} {pbc_cell[1]} {pbc_cell[2]}\n")
            f.write(f"end structure\n")
    return input_packmol_name

def run_packmol(packmol_path, packmol_input):
    try:
        result = subprocess.check_output(packmol_path + ' < ' + packmol_input, shell = True, executable = "/bin/bash", stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        out = str(e.output)
        with open('packmol.err', 'w') as f:
            f.write(out)
        return False
    return True
#-----------------------------------------------------------------------------------------------------------------------------

#Build interface methods------------------------------------------------------------------------------------------------------
def build_interface(lower_surf, upper_surf, molecules):
    #Real interface
    if lower_surf is not None and upper_surf is not None:
        #Get lower surface cell
        cell = lower_surf.get_cell()
        
        #Get lower surface dimensions
        lower_surf.positions -= lower_surf.positions.min(axis=0)
        dim = lower_surf.positions.max(axis=0) - lower_surf.positions.min(axis=0)
        
        #Get number of boundary/bulk atoms for group indexing
        low, bulk, up = boundary_bulk_split(lower_surf)
        nat_dw_low, nat_dw_bulk, nat_dw_hig = len(low), len(bulk), len(up)
        
        #Re-order lower surface accounting for group index
        lower_surf = low + bulk + up
        nat_lower_surf = len(lower_surf)
        
        #With molecules
        nat_molecules = 0
        if molecules is not None:
            #Get molecules' dimensions
            dim_mols = molecules.positions.max(axis=0) - molecules.positions.min(axis=0)

            #Shift molecules over lower surface
            molecules.positions += np.array([0.0, 0.0, dim[2] + 2.0]) - molecules.positions.min(axis=0)

            #Update geometry dimensions
            dim += np.array([0.0, 0.0, dim_mols[2] + 2.0])
            nat_molecules = len(molecules)

        #Shift upper surface over lower surface or molecules
        upper_surf.positions += np.array([0.0, 0.0, dim[2] + 2.0]) - upper_surf.positions.min(axis=0)

        #Get number of boundary/bulk atoms for group indexing
        low, bulk, up = boundary_bulk_split(upper_surf)
        nat_up_low, nat_up_bulk, nat_up_hig = len(low), len(bulk), len(up)

        #Re-order upper surface accounting for group index
        upper_surf = low + bulk + up
        nat_upper_surf = len(upper_surf)

        #Assemble final interface, keep group order
        interface = lower_surf + upper_surf

        #Assign correct cell
        dim = interface.positions.max(axis=0) - interface.positions.min(axis=0)
        interface.set_cell(cell)
        interface.cell[2, 2] = dim[2] + 10        

        #Assign interface group indeces
        group_idxs = {'Surface_down'  : [n for n in range(1, nat_lower_surf + 1)],
                      'FIX_down' : [n for n in range(1, nat_dw_low + 1)],
                      'NVT_down' : [n for n in range(nat_dw_low + 1, nat_dw_low + nat_dw_bulk + 1)],
                      'NVE_down' : [n for n in range(nat_dw_low + nat_dw_bulk + 1, nat_dw_low + nat_dw_bulk + nat_dw_hig + 1)],
                      'NVE_up'   : [n for n in range(nat_lower_surf + 1, nat_lower_surf + nat_up_low + 1)],
                      'NVT_up'   : [n for n in range(nat_lower_surf + nat_up_low + 1, nat_lower_surf + nat_up_low + nat_up_bulk + 1)],
                      'FIX_up'   : [n for n in range(nat_lower_surf + nat_up_low + nat_up_bulk + 1, nat_lower_surf + nat_up_low + nat_up_bulk + nat_up_hig + 1)],
                      'Surface_up'  : [n for n in range(nat_lower_surf + 1, nat_lower_surf + nat_upper_surf + 1)]
                       }
        
        #With molecules
        if nat_molecules > 0:
            interface += molecules
            group_idxs['Molecules'] = [n for n in range(nat_lower_surf + nat_upper_surf + 1, nat_lower_surf + nat_upper_surf + nat_molecules + 1)]

        
    #Surface only
    elif lower_surf is not None or upper_surf is not None:
        #Assign surface correctly
        if lower_surf is not None: surf = lower_surf
        elif upper_surf is not None: surf = upper_surf  

        #Shift surface to origin
        surf.positions -= surf.positions.min(axis=0)

        #Get surface cell and surface dimension
        cell = surf.get_cell()
        dim = surf.positions.max(axis=0) - surf.positions.min(axis=0)

        #Get surface division
        low, bulk, up = boundary_bulk_split(surf)
        nat_surf_low, nat_surf_bulk, nat_surf_hig = len(low), len(bulk), len(up)            

        # print("Method build_interface:Begin", flush=True)
        # print(nat_surf_low, nat_surf_bulk, nat_surf_hig, flush=True)
        # print("Method build_interface:End", flush=True)        

        #Re-order surface accounting for group index
        surf = low + bulk + up
        nat_surf = len(surf)

        #With molecules
        nat_molecules = 0
        if molecules is not None:
            #Get molecules' dimensions
            dim_mols = molecules.positions.max(axis=0) - molecules.positions.min(axis=0)            

            #Shift molecules over lower surface
            if lower_surf is not None:
                molecules.positions += np.array([0.0, 0.0, dim[2] + 2.0]) - molecules.positions.min(axis=0)
            
            #Or shift molecules over upper surface
            elif upper_surf is not None:
                molecules.positions += np.array([0.0, 0.0, -2.0]) - molecules.positions.min(axis=0)

            #Update system' dimension
            dim += np.array([0, 0, dim_mols[2] + 2.0])
            nat_molecules = len(molecules)

        #Assemble final surface
        interface = surf

        #Assign atomic indexes
        if lower_surf is not None: #Lower surface
            group_idxs = {'Surface_down'    : [n for n in range(1, nat_surf + 1)],
                          'FIX_surf'   : [n for n in range(1, nat_surf_low + 1)],
                          'NVT_surf'   : [n for n in range(nat_surf_low + 1, nat_surf_low + nat_surf_bulk + 1)],
                          'NVE_surf'   : [n for n in range(nat_surf_low + nat_surf_bulk + 1, nat_surf_low + nat_surf_bulk + nat_surf_hig + 1)],
                        }
        else: #Upper surface
            group_idxs = {'Surface_up'    : [n for n in range(1, nat_surf + 1)],
                          'NVT_surf'   : [n for n in range(1, nat_surf_low + 1)],
                          'NVT_surf'   : [n for n in range(nat_surf_low + 1, nat_surf_low + nat_surf_bulk + 1)],
                          'FIX_surf'   : [n for n in range(nat_surf_low + nat_surf_bulk + 1, nat_surf_low + nat_surf_bulk + nat_surf_hig + 1)],
                        }          
              
        #With molecules
        if nat_molecules > 0:
            interface += molecules
            group_idxs['Molecules'] = [n for n in range(nat_surf + 1, nat_surf + nat_molecules + 1)]     

        #Assign correct cell
        dim = interface.positions.max(axis=0) - interface.positions.min(axis=0)
        interface.positions -= interface.positions.min(axis=0)
        interface.set_cell(cell)
        if dim[2] > interface.cell[2, 2]:
            interface.cell[2, 2] = dim[2] + 2 #Fake interface with PBC

    #Molecules only
    else:
        #Shift molecules to center
        molecules.positions -= molecules.positions.min(axis=0)

        #Set molecules' dimension
        dim_mols = molecules.positions.max(axis=0) - molecules.positions.min(axis=0)
        molecules.set_cell(dim_mols + 2.0)
        
        #Assign molecule' s group
        nat_molecules = len(molecules)
        interface = molecules
        group_idxs = {'Molecules' : [n for n in range(1, nat_molecules + 1)]}               

    return interface, group_idxs
#-----------------------------------------------------------------------------------------------------------------------------

#Lammps read/write methods----------------------------------------------------------------------------------------------------
def get_group_idx_from_lmpinput(lmp_input_ref):
    #Get group index from lammps input
    group_ids = []
    group_names = []
    with open(lmp_input_ref, 'r') as f:
        for line in f:
            tks = line.split()
            if len(tks) < 2: continue
            #group Molecules id 2:5 (or 2 3 4 5)
            if tks[0] == 'group' and tks[2] == 'id':
                group_names.append(tks[1])
                group_ids.append(tks[3:])

    #Get group ids as list of int
    group_ids_int = []
    for group_id in group_ids:
        if len(group_id) == 1:
            Startid, Stopid = group_id[0].split(':')[0], group_id[0].split(':')[1]
            group_id_int = [idx for idx in range(int(Startid), int(Stopid)+1)]
        
        else:
            group_id_int = [int(idx) for idx in group_id]
        group_ids_int.append(group_id_int)
    
    #Build dictionary of group names and indeces
    group_dict = dict([(group_name, group_id_int) for group_name, group_id_int in zip(group_names, group_ids_int)])

    return group_dict

def get_atoms_from_traj(lmp_traj, grp_idx=None):
    #Load last frame of trajectory as ase atoms
    atoms = read(lmp_traj, index=-1, format='lammps-dump-text')
    nat = len(atoms)

    #Group indeces is specified -> get the group and its (new) connected atoms
    if grp_idx is not None:
        #Set pbc in every direction
        atoms.set_pbc((True, True, True))
        
        #Get atoms' neighbor list
        cutoffs = natural_cutoffs(atoms)
        nl = NeighborList(cutoffs, self_interaction=False, bothways=True)
        nl.update(atoms)

        #Get atoms connectivity matrix and atoms' connected components
        matrix = nl.get_connectivity_matrix()
        n_components, component_list = connected_components(matrix)

        #Get indeces of atom group and connected atoms
        connected_component_idxs = [component_list[n] for n in grp_idx]
        atom_idxs = [n for n in range(nat) if component_list[n] in connected_component_idxs or n in grp_idx]

        #Get group and connected atoms
        structure = atoms[atom_idxs]
    
    #Else get all atoms
    else:
        structure = atoms

    return structure

def structure_from_lmp(ref_phase, ref_struc):
    #Get lmp reference input and correspoinding trajectory
    lmp_input_ref = 'input' + str(ref_phase) + '.in'
    lmp_traj = 'dyn' + str(ref_phase) + '.lammpstrj'

    #Get groups indeces from reference run
    group_and_idxs = get_group_idx_from_lmpinput(lmp_input_ref)

    #Get group indeces of reference structure: start from 0 -> indeces for ase atoms
    grp_idx = group_and_idxs[ref_struc]

    #Convert from lmp to ase indeces
    grp_idx = [idx - 1 for idx in grp_idx]

    #Get ase structure from previous lammpstrj using group index
    structure = get_atoms_from_traj(lmp_traj, grp_idx)
    structure.wrap(pretty_translation=True)

    return structure

def write_lmp_data(ase_atoms, atomic_dict, step):
    #Define output files to be written
    fname_xyz = 'pos' + str(step) + '.xyz'
    fname_pos = 'pos' + str(step) + '.data'

    #Write ase xyz format geometry
    write(fname_xyz, ase_atoms)

    #Get atomic info to write lmp 
    nat = len(ase_atoms)
    ntyp = len(atomic_dict.keys())
    cell = np.diag(ase_atoms.get_cell())

    #Write pos.data file
    with open(fname_pos, 'w') as f:
        #Write header
        f.write("Generated by SCS: exploration routine\n")
        f.write(f"\n{nat}    atoms\n")
        f.write(f"{ntyp}    atom types\n")

        #Write atomic box
        for axis, cord in zip(cell, ['x', 'y', 'z']):
            f.write(f"0.0     {axis}     {cord}lo {cord}hi\n")
        
        #Write atomic masses
        f.write("\nMasses\n\n")
        atom_orders = {}
        for idx, symb in enumerate(atomic_dict.keys()):
            atom_orders[symb] = idx + 1
            f.write(f"{idx + 1}    {atomic_dict[symb]}\n")

        #Write atomic coordinates
        f.write("\nAtoms\n\n")
        for idx, atom in enumerate(ase_atoms):
            idx += 1
            symb = atom.symbol
            coord = atom.position
            f.write("%-5d   %2d     %12.9f   %12.9f   %12.9f\n" %(idx, atom_orders[symb], coord[0], coord[1], coord[2]))

def write_lmp_input(info, species, lmp_groups, idx=0):
    #Slice dictionary with correct Phase
    run_info = info[f"Phase{idx}"]["Run"]

    #Get info to write lmp input
    run_type = run_info["Type"]
    if run_type != 'Relax':
        run_steps = run_info['Steps']

    #Get file names
    fname_input = 'input' + str(idx) + '.in'
    fname_pos = 'pos' + str(idx) + '.data'
    fname_xyz = 'pos' + str(idx) + '.xyz'
    fname_trajectory = 'dyn' + str(idx) + '.lammpstrj'
    fname_restart = 'Phase' + str(idx) + '.restart'

    #No geometry file has been created -> write a restart input
    if lmp_groups is None:
        #Read groups info from previous run
        lmp_groups = {}
        old_input = 'input' + str(idx - 1) + '.in'
        with open(old_input, 'r') as f:
            for line in f:
                tks = line.split()
                if len(tks) < 4: continue
                #Get groups only if defined by atomic id
                if tks[0] == 'group' and tks[2] == 'id':                 
                    lmp_groups[tks[1]] = tks[3:]
        
        #Ensure lmp_groups dictionary is a dict of list containing atomic indeces
        for group_name, group_idxs in lmp_groups.items():
            if len(group_idxs) == 1:
                if ':' in group_idxs[0]: #12:34
                    iStart, iStop = group_idxs[0].split(':')[0], group_idxs[0].split(':')[1]
                
                else: #One atom group
                    iStart = iStop = group_idxs[0]

            else:
                iStart, iStop = group_idxs[0], group_idxs[-1]
            #Define group as a list of atomic indeces
            group_idxs = [n for n in range(iStart, iStop+1)]

    #Define to_write dictionary
    to_write = {}

    #Get Timestep
    if "Timestep" in run_info.keys():
        timestep_ps = run_info["Timestep"]*0.001 #fs*0.001 = ps(lmp metal unit)
        to_write["Timestep"] = [f"timestep  {timestep_ps}\n"]
    else:
        timestep_ps = 0.0001 #ps(lmp metal unit) = 0.1fs
        to_write['Timestep'] = [f"timestep  {timestep_ps}\n"]    

    #Get pair_stlye line
    to_write["Pair_style"] = "pair_style  deepmd  " + " ".join(glob('../../Training/NN*/compressed.pb'))

    #Get relative model devi
    if 'relative' in run_info.keys():
        to_write["Pair_style"] += f"  relative  {run_info['Relative']}"

    #Get out_frequency style
    if "Out_freq" in run_info.keys():
        to_write["Pair_style"] += f"  out_freq  {run_info['Out_freq']}"
        to_write["Thermo"] = [f"thermo  {run_info['Out_freq']}\n", "thermo_style  custom  step  time  etotal  fmax  fnorm  press\n"]
        to_write["Dump"] = [f"\ndump  dump_pos  all  custom  {run_info['Out_freq']}  {fname_trajectory}  element  xu  yu  zu\n",
                            f"dump_modify  dump_pos  format  float  %15.12g  element  {' '.join(list(species.keys()))}  sort  id\n"]
    #Default value
    else:
        to_write["Pair_style"] += f"  out_freq  100"
        to_write["Thermo"] = [f"thermo  100\n", "thermo_style  custom  step  time  etotal  fmax  fnorm  press\n"]
        to_write["Dump"] = [f"\ndump  dump_pos  all  custom  100  {fname_trajectory}  element  xu  yu  zu\n",
                            f"dump_modify  dump_pos  format  float  %15.12g  element  {' '.join(list(species.keys()))}  sort  id\n"] 

    #Finish pair_style line
    to_write["Pair_style"] += f"  out_file  mdevi{idx}.out\n"

    #Get pair_coeff line
    to_write["Pair_coeff"] = [f"pair_coeff * * {' '.join(list(species.keys()))}\n", "newton  on\n"]

    #Get groups line
    to_write["Group"] = []
    # print("Method write_lmp_input:Begin", flush=True)
    # print(lmp_groups, flush=True)
    # print("Method write_lmp_input:End", flush=True)
    for group_name, group_idxs in lmp_groups.items():
        start_idx, stop_idx = group_idxs[0], group_idxs[-1]
        line = f"group  {group_name}  id  {start_idx}:{stop_idx}\n"
        to_write["Group"].append(line)        

    #Get atomic force from load
    if 'Load' in run_info.keys():
        #Get normal area
        atoms = read(fname_xyz)
        area = atoms.cell[0, 0]*atoms.cell[1, 1]

        #Get number of upper layer atoms
        nat_lay_up = lmp_groups['FIX_up'][-1] - lmp_groups['FIX_up'][0] + 1

        #Compute atomic force
        toeVang = 0.00624151
        Load = toeVang*run_info['Load']*area/nat_lay_up        

        #Get load line
        load_line = f" addforce  0.0  0.0  {-Load}"
    
    #Get temperature
    if 'Temperature' in run_info.keys():
        Temp = run_info["Temperature"] #{Tstart : 300, Tstop : 1300}

        #Get temperature line
        temp_line = f" temp  {Temp['Tstart']}  {Temp['Tstop']} $(100.*dt)"

    #Get pressure
    if 'Pressure' in run_info.keys():
        Press = run_info["Pressure"] #{x : {'Pstart' : 1, 'Pstop' : 5}, ...}

        #Get pressure line
        press_line = ""
        for cord in ['x', 'y', 'z']:
            if cord not in Press.keys(): continue
            else: press_line += f" {cord}  {Press[cord]['Pstart']*10000}  {Press[cord]['Pstop']*10000}  $(1000.*dt)" #bar
    
    #Get sliding speed
    if 'Sliding' in run_info.keys():
        Slide = run_info["Sliding"] #{x : Vx, y : Vy}

        #Get slide line
        slide_line = " move  linear"
        for cord in ['x', 'y', 'z']:
            if cord in Slide.keys(): speed = Slide[cord]/100 #A/ps
            else: speed = "NULL"
            slide_line += f" {speed}"       
    
    #Get run lines based on run type
    to_write['Run'] = []

    #Relax simulation
    if run_type == 'Relax':
        #Get load for minimization
        if 'Load' in run_info.keys():
            to_write["Run"] = [f"fix  load_up  FIX_up {load_line}\n",
                                "fix_modify  load_up  energy  yes\n",
                                "fix  load_dw  FIX_down  setforce  0.0  0.0  0.0\n"]
        to_write["Run"].append("minimize  0.0  1e-03  100000  10000000\n")
        
    #NVT simulation
    elif run_type == 'NVT':
        # NVT under load
        if 'Load' in run_info.keys():
            #Define temperature computation
            to_write["Compute"] = ["compute  temp_dw  NVT_down  temp/com\n", "compute  temp_up  NVT_up  temp/com\n"]
            #Define interfacial NVE group
            group_nve = "group  NVE_int  union  NVE_down  NVE_up"
            if 'Molecules' in lmp_groups.keys(): 
                to_write["Compute"].append("compute  temp_int  NVE_int  temp/com\n")
                group_nve += "  Molecules\n"
            else: group_nve += "\n"
            to_write["Group"].append(group_nve)

            #Under sliding
            if 'Sliding' in run_info.keys():
                #Get Run lines
                to_write["Run"] = [f"fix  load_up  FIX_up   {load_line}\n",
                                   f"fix  sliding  FIX_up   {slide_line}\n",
                                   f"fix  nvt_dw   NVT_down nvt  {temp_line}\n",
                                    "fix_modify  nvt_dw  temp  temp_dw\n",
                                   f"fix  nvt_up  NVT_up  nvt  {temp_line}\n",
                                    "fix_modify  nvt_up  temp  temp_up\n",
                                   f"fix  nve_int  NVE_int   nve\n"
                                    "fix  nve_dw   FIX_down  nve\n",
                                    "fix  load_dw  FIX_down  recenter INIT INIT INIT\n"]                

            #Only under load
            else:
                #Get Run lines
                to_write["Run"] = [f"fix  load_up  FIX_up   {load_line}\n",
                                   f"fix  nosliding  FIX_up  nve\n",
                                   f"fix  nvt_dw   NVT_down nvt  {temp_line}\n",
                                    "fix_modify  nvt_dw  temp  temp_dw\n",
                                   f"fix  nvt_up  NVT_up  nvt  {temp_line}\n",
                                    "fix_modify  nvt_up  temp  temp_up\n",
                                   f"fix  nve_int  NVE_int   nve\n"
                                    "fix  nve_dw   FIX_down  nve\n",
                                    "fix  load_dw  FIX_down  recenter INIT INIT INIT\n"]                

        # NVT only
        else:
            #Get Run lines
            to_write["Run"] = [f"fix  nvt_all   all nvt  {temp_line}\n"]      

    #NPT simulation
    elif run_type == 'NPT':
        #Get Run lines
        to_write["Run"] = [f"fix  npt_all   all  npt  {temp_line}  {press_line}\n"]

    #NVE simulation
    elif run_type == 'NVE':
        #Get Run lines
        to_write["Run"] = [f"fix  nve_all   all  nve\n"]         

    #Get initial velocities and run steps
    if run_type != 'Relax':
        to_write["Run"] += [f"velocity  all  create  {run_info['Temperature']['Tstart']}  {np.random.randint(0, 10000)}  dist  gaussian\n",
                            f"run  {run_steps}\n"]

    #Write lammps input
    with open(fname_input, 'w') as f:
        #Units & pbc & initial geometry
        f.write("units  metal\n")
        f.write("boundary  p p p\n")
        f.write("atom_style  atomic\n")
        f.write(f"read_data  {fname_pos}\n")
        
        #Pair style & pair_coeff & newton
        f.write("\n")
        f.writelines(to_write["Pair_style"])
        f.writelines(to_write["Pair_coeff"])

        #Groups
        f.write("\n")
        f.writelines(to_write["Group"])
        
        #Computes
        if 'Compute' in to_write.keys():
            f.write("\n")
            f.writelines(to_write['Compute'])

        #Dump
        f.write("\n")
        f.writelines(to_write["Dump"])
        
        #Thermo
        f.write("\n")
        f.writelines(to_write["Thermo"])

        #Timestep
        f.write("\n")
        f.writelines(to_write["Timestep"])
        
        #Fixes, Velocity and Run
        f.write("\n")
        f.writelines(to_write["Run"])        
        
        #Restart
        f.write(f"\nwrite_restart  {fname_restart}")
#-----------------------------------------------------------------------------------------------------------------------------

#Wrapper methods for initialization------------------------------------------------------------------------------------------------------
def get_atomic_info(exploration_info, phase_id):
    #Iteratively search for last definition of atomic species and masses
    species_and_masses = None
    for n in range(phase_id+1)[::-1]:
        exp_phase_info = exploration_info[f"Phase{n}"]
        if 'Geometry' in exp_phase_info.keys():
            if 'Species' in exp_phase_info['Geometry']:
                species_and_masses = exp_phase_info['Geometry']['Species']
                break
    
    #Dictionary of atomic symbols and their masses
    return species_and_masses

def get_building_blocks_ase(building_block_paths):
    #Convert each structure path in an ase atoms object
    building_block_ase = building_block_paths.copy()

    #Loop over system in geometry and get ase atoms
    for system, system_info in building_block_paths.items():
        if system in ['Bulk', 'Surface_down', 'Surface_up', 'Molecules']:
            for structure, structure_info in system_info.items():
                #This element describes a structure (i.e. not 'box' or 'number' for example)
                if 'Structure' in structure:
                    #Get structure path
                    structure_path = structure_info["Path"]
                    
                    #If path exist, load as ase atoms
                    if os.path.isfile(structure_path):
                        building_block_ase[system][structure]["Path"] = read(structure_path)
                    
                    #If 'Phase' is in structure_path -> load ase atoms from previous run
                    elif 'Phase' in structure_path:
                        ref_phase, ref_system = int(structure_path.split('/')[0].strip('Phase')), structure_path.split('/')[-1]
                        building_block_ase[system][structure]["Path"] = structure_from_lmp(ref_phase, ref_system)                    
                    
                    #Else TODO:load from mpj
                    else:
                        sys.exit(f"{structure_path} not found and loading structures from mpj is not supported yet, stopping...")
    
    #Every structure in current geometry info is an ase atoms object
    return building_block_ase

def customize_building_blocks_ase(building_blocks_as_ase, path_to_packmol):
    #Customize loaded ase atoms

    #If bulk this is the only system in the geometry (pbc along every direction)
    if 'Bulk' in building_blocks_as_ase.keys():
        atoms = build_random_bulk(building_blocks_as_ase['Bulk'])
        groups = {'Bulk' : [n for n in range(1, len(atoms) + 1)]}
    
    #Else it can be more complex system: surf/int + molecules
    else:
        #Assume no box for molecules
        starting_mol_box = None

        #Build surface down
        surf_dw = None
        if 'Surface_down' in building_blocks_as_ase.keys():
            surf_dw = build_random_surface(building_blocks_as_ase['Surface_down'], loc='lower')
            if starting_mol_box is None: starting_mol_box = np.diag(surf_dw.get_cell())

        #Build surface up
        surf_up = None
        if 'Surface_up' in building_blocks_as_ase.keys():
            surf_up = build_random_surface(building_blocks_as_ase['Surface_up'], loc='upper')
            if starting_mol_box is None: starting_mol_box = np.diag(surf_up.get_cell())

        #Build molecules box
        mols = None
        if 'Molecules' in building_blocks_as_ase.keys():
            mols = build_random_molecules(building_blocks_as_ase['Molecules'], starting_mol_box, path_to_packmol)

        #Assemble final composite system
        atoms, groups = build_interface(surf_dw, surf_up, mols)

        # print("Method customize_building_blocks_ase:Begin", flush=True)
        # print(groups, flush=True)
        # print("Method customize_building_blocks_ase:End", flush=True)
    
    return atoms, groups

def get_current_geometry(exp_info, num_phase, packmol_path):
    #Current phase geometry
    current_systems = exp_info[f"Phase{num_phase}"]["Geometry"]

    #Get ase atoms for each specified geometry of current phase
    building_blocks_as_ase = get_building_blocks_ase(current_systems)

    #Customize each ase atoms as specified in its structure info
    atoms, groups_dict = customize_building_blocks_ase(building_blocks_as_ase, packmol_path)

    return atoms, groups_dict
    
def get_last_geometry(num_phase):
    #Get last lammps input and trajectory
    last_lmp_in = 'input' + str(num_phase - 1) + '.in'
    last_lmp_traj = 'dyn' + str(num_phase - 1) + '.lammpstrj'

    #Get lmp atomic groups and ase atoms
    group_and_idxs = get_group_idx_from_lmpinput(last_lmp_in)
    atoms = get_atoms_from_traj(last_lmp_traj, grp_idx=None)

    return atoms, group_and_idxs
#----------------------------------------------------------------------------------------------------------------------------------------