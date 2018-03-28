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
  gromitout:
    type: File
    outputSource: gromit/gromitout
  gromiterr:
    type: File
    outputSource: gromit/gromiterr
  gromacslog2:
    type: File
    outputSource: gromit/gromacslog_step2
  gromacslog3:
    type: File
    outputSource: gromit/gromacslog_step3
  gromacslog4:
    type: File
    outputSource: gromit/gromacslog_step4
  gromacslog5:
    type: File
    outputSource: gromit/gromacslog_step5
  gromacslog6:
    type: File
    outputSource: gromit/gromacslog_step6
  gromacslog7:
    type: File
    outputSource: gromit/gromacslog_step7
  gromacslog8:
    type: File
    outputSource: gromit/gromacslog_step8
  gromacslog9:
    type: File
    outputSource: gromit/gromacslog_step9
  trajectory:
    type: File
    outputSource: gromit/trajectory
  gro:
    type: File
    outputSource: gromit/gro
  ndx:
    type: File
    outputSource: gromit/ndx
  top:
    type: File
    outputSource: gromit/top
  mdp:
    type: File
    outputSource: gromit/mdp
  energy_edr:
    type: File
    outputSource: gromit/energy
  energy_dataframe:
    type: File
    outputSource: energy/energy_dataframe
  energyout:
    type: File
    outputSource: energy/energyout
  energyerr:
    type: File
    outputSource: energy/energyerr
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
  gromit:
    run: mdstudio/gromit.cwl
    in:
      protein_top: protein_top
      protein_file: protein_file
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
    out: [gromacslog_step2, gromacslog_step3, gromacslog_step4,
    gromacslog_step5, gromacslog_step6, gromacslog_step7,
    gromacslog_step8, gromacslog_step9, gromitout, gromiterr,
    trajectory, energy, gro, ndx, top, mdp]
  energy:
    run: mdstudio/energies.cwl
    in:
      edr:
        source: gromit/energy
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
        source: gromit/gro
      ndx:
        source: gromit/ndx
      trr:
        source: gromit/trajectory
      top:
        source: gromit/top
      mdp:
        source: gromit/mdp      
    out: [decompose_dataframe, decompose_err, decompose_out]
