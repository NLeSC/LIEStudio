cwlVersion: v1.0
class: Workflow
inputs:
  ligand_file:
    type: File
  topology_file:
    type: File
  protein_file:
    type: File?
  protein_top:
    type: File
  forcefield:
    type: string
    default: "amber99sb"    
  periodic_distance:
    type: double
    default: 1.8
  pressure:
    type: double
    default: 1.01325
  prfc:
    type: int[]
    default: [10000, 5000, 50, 0]
  ptau:
    type: double
    default: 0.5
  residues:
    type: int[]
  resolution:
    type: double
    default: 0.002
  salinity:
    type: double
    default: 0.1539976
  sim_time:
    type: double
    default: 1
  solvent:
    type: string
    default: "tip3p"
  temperature:
    type: int[]
    default: [100, 200, 300]
  ttau:
    type: double
    default: 0.1
    
outputs:
  gromitout_solvent_ligand:
    type: File
    outputSource: gromit_solvent_ligand/gromitout
  gromiterr_solvent_ligand:
    type: File
    outputSource: gromit_solvent_ligand/gromiterr
  gromacslog_solvent_ligand:
    type: File
    outputSource: gromit_solvent_ligand/gromacslog_step9
  trajectory_solvent_ligand:
    type: File
    outputSource: gromit_solvent_ligand/trajectory
  energy_solvent_ligand:
    type: File
    outputSource: gromit_solvent_ligand/energy
  energy_dataframe_solvent_ligand:
    type: File
    outputSource: energy_solvent_ligand/energy_dataframe
  energyout_solvent_ligand:
    type: File
    outputSource: energy_solvent_ligand/energyout
  energyerr_solvent_ligand:
    type: File
    outputSource: energy_protein_ligand/energyerr
  gromitout_protein_ligand:
    type: File
    outputSource: gromit_protein_ligand/gromitout
  gromiterr_protein_ligand:
    type: File
    outputSource: gromit_protein_ligand/gromiterr
  gromacslog_protein_ligand:
    type: File
    outputSource: gromit_protein_ligand/gromacslog_step9
  trajectory_protein_ligand:
    type: File
    outputSource: gromit_protein_ligand/trajectory
  gro_protein_ligand:
    type: File
    outputSource: gromit_protein_ligand/gro
  ndx_protein_ligand:
    type: File
    outputSource: gromit_protein_ligand/ndx
  top_protein_ligand:
    type: File
    outputSource: gromit_protein_ligand/top
  mdp_protein_ligand:
    type: File
    outputSource: gromit_protein_ligand/mdp
  energy_protein_ligand:
    type: File
    outputSource: gromit_protein_ligand/energy
  energy_dataframe_protein_ligand:
    type: File
    outputSource: energy_protein_ligand/energy_dataframe
  energyout_protein_ligand:
    type: File
    outputSource: energy_protein_ligand/energyout
  energyerr_protein_ligand:
    type: File
    outputSource: energy_protein_ligand/energyerr
  decompose_dataframe:
    type: File
    outputSource: decompose/decompose_dataframe
  decompose_err:
    type: File
    outputSource: decompose/decompose_err
  decompose_out:
    type: File
    outputSource: decompose/decompose_out
    
steps:
  gromit_solvent_ligand:
    run: mdstudio/gromit.cwl
    in:
      protein_top: protein_top
      ligand_file: ligand_file
      topology_file: topology_file
      forcefield: forcefield
      periodic_distance: periodic_distance
      pressure: pressure
      prfc: prfc
      ptau: ptau
      resolution: resolution
      salinity: salinity
      sim_time: sim_time
      solvent: solvent
      temperature: temperature
      ttau: ttau
    out: [gromitout,gromiterr,gromacslog_step9,trajectory, energy,
          gro, ndx, top, mdp]
  energy_solvent_ligand:
    run: mdstudio/energies.cwl
    in:
      edr:
        source: gromit_solvent_ligand/energy
    out: [energy_dataframe, energyout, energyerr]
  gromit_protein_ligand:
    run: mdstudio/gromit.cwl
    in:
      protein_file: protein_file
      protein_top: protein_top
      ligand_file: ligand_file
      topology_file: topology_file
      forcefield: forcefield
      periodic_distance: periodic_distance
      pressure: pressure
      prfc: prfc
      ptau: ptau
      resolution: resolution
      salinity: salinity
      sim_time: sim_time
      solvent: solvent
      temperature: temperature
      ttau: ttau
    out: [gromitout,gromiterr,gromacslog_step9,trajectory, energy,
          gro, ndx, top, mdp]
  energy_protein_ligand:
    run: mdstudio/energies.cwl
    in:
      edr:
        source: gromit_protein_ligand/energy
    out: [energy_dataframe, energyout, energyerr]
  decompose:
    run: mdstudio/decompose.cwl
    in:
      # secondary files
      topology_file: topology_file
      protein_top: protein_top
      # position binded parameters 
      res: residues
      gro:
        source: gromit_protein_ligand/gro
      ndx:
        source: gromit_protein_ligand/ndx
      trr:
        source: gromit_protein_ligand/trajectory
      top:
        source: gromit_protein_ligand/top
      mdp:
        source: gromit_protein_ligand/mdp      
    out: [decompose_dataframe, decompose_err, decompose_out]
