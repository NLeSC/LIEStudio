# -*- coding: utf-8 -*-

import os
import time
import json
import pickle

from autobahn.twisted.wamp import ApplicationRunner
from autobahn.twisted.util import sleep
from twisted.internet.defer import inlineCallbacks
from twisted.internet._sslverify import OpenSSLCertificateAuthorities
from twisted.internet.ssl import CertificateOptions
from OpenSSL import crypto

from lie_system import LieApplicationSession
from lie_workflow import Workflow


class LIEWorkflow(LieApplicationSession):
    
    """
    This workflow will perform a binding affinity prediction for CYP 1A2 with
    applicability domain analysis using the Linear Interaction Energy (LIE)
    method as described in:

    Capoferri L, Verkade-Vreeker MCA, Buitenhuis D, Commandeur JNM, Pastor M,
    Vermeulen NPE, et al. (2015) "Linear Interaction Energy Based Prediction
    of Cytochrome P450 1A2 Binding Affinities with Reliability Estimation."
    PLoS ONE 10(11): e0142232. https://doi.org/10.1371/journal.pone.0142232

    The workflow uses data from the pre-calibrated CYP1A2 model created using
    the eTOX ALLIES Linear Interaction Energy pipeline.
    """
    
    @inlineCallbacks
    def onRun(self, details):

        currdir = os.path.abspath(os.path.dirname(__file__))
        workdir = os.path.abspath(os.path.join(currdir, '../../lieproject'))
        liemodel = os.path.join(currdir, '1A2_model')

        # Ligand to make prediction for
        ligand = 'O1[C@@H](CCC1=O)CCC'
        ligand_format = 'smi'

        # CYP1A2 Model data
        with open(os.path.join(liemodel, 'model.dat'), 'r') as mdf:
            model = json.load(mdf)

        # CYP1A2 pre-calibrated model
        modelpicklefile = os.path.join(liemodel, 'params.pkl')
        modelfile = pickle.load(open(modelpicklefile))

        # MD settings
        forcefield = 'amber99SB'
        periodic_distance = 1.8
        temperature = '100,200,300'
        solvent = 'tip3p'
        ptau = 0.5
        prfc = '10000,5000,50,0'
        ttau = 0.1
        salinity = 0
        gromacs_vsite = True


        # Build Workflow
        wf = Workflow()
        
        # Load workflow if present else, build one
        workflow_file = os.path.join(workdir, 'workflow.json')
        if os.path.isfile(workflow_file):
            wf.load(workflow_file)
            wf.task_runner = self.call
            wf.set_wamp_session(session_data={'authid': self.session_config.authid})
        
        else:
            wf.task_runner = self.call
            wf.set_wamp_session(session_data={'authid': self.session_config.authid})
            
            # Set some workflow metadata in the start node
            project_dir = os.path.join(workdir, str(int(time.time())))
            start = wf.get_task(1)
            start.set('workdir', project_dir)

            # Stage 1: ligand pre-processing
            # Convert ligand to mol2 irrespective of input format.
            t2 = wf.add_task('Format conversion', task_type='WampTask', uri='liestudio.structure.convert',
                             store_output=True)
            wf.input(t2, input_format=ligand_format, output_format='mol2', mol=ligand)
            wf.connect_task(start.nid, t2)

            # Covert mol2 to 3D mol2 irrespective if input is 1D/2D or 3D mol2
            t3 = wf.add_task('Make 3D', task_type='WampTask', uri='liestudio.structure.make3d', store_output=True)
            wf.input(t3, input_format='mol2', from_file=True)
            wf.connect_task(t2, t3)

            # Adjust ligand protonation state to a given pH if applicable
            t4 = wf.add_task('Add hydrogens', task_type='WampTask', uri='liestudio.structure.addh', store_output=True)
            wf.input(t4, input_format='mol2', correctForPH=model['pHCorr'], pH=model['pH'], from_file=True)
            wf.connect_task(t3, t4)

            # Get the formal charge for the protonated mol2 to use as input for ACPYPE or ATB
            t5 = wf.add_task('Get charge', task_type='WampTask', uri='liestudio.structure.info')
            wf.input(t5, input_format='mol2', from_file=True)
            wf.connect_task(t4, t5)

            # STAGE 2. QUERY ATB FOR STRUCTURE
            # Query ATB for ligand using structure search
            t6 = wf.add_task('Query ATB', task_type='WampTask', uri='liestudio.atb.structure_query')
            wf.input(t6, structure_format='mol2', isfile=True)
            wf.connect_task(t4, t6)
            wf.connect_task(t5, t6, data_mapping={'charge': 'netcharge'})

            # Make a choice, if ATB match use it else go for ACPYPE
            # Choice 1: If matches, get exact match or one with lowest RMSD
            choice1 = wf.add_task('Select match', task_type='Task',
                                  custom_func='allies_workflow_helpers.pick_atb_query_match')

            # Choice 2: Run acpype on ligands
            choice2 = wf.add_task('ACPYPE', task_type='WampTask', uri='liestudio.amber.acpype', store_output=True,
                             retry_count=3)
            wf.input(choice2, from_file=True)
            wf.connect_task(t4, choice2, data_mapping={'mol': 'structure'})
            wf.connect_task(t5, choice2, data_mapping={'charge': 'net_charge'})

            # make the choice
            t7 = wf.add_task('ATB or ACPYPE', task_type='Choice', custom_func='allies_workflow_helpers.choose_atb_amber')
            wf.input(t7, pos=[choice2], neg=[choice1])
            wf.connect_task(t6, t7)
            wf.connect_task(t7, choice1)
            wf.connect_task(t7, choice2)

            # If ATB: fetch structure and force field files for best match
            t8 = wf.add_task('Fetch structure', task_type='WampTask', uri='liestudio.atb.get_structure',
                             store_output=True)
            wf.connect_task(choice1, t8)

            t9 = wf.add_task('Fetch top files', task_type='WampTask', uri='liestudio.atb.get_topology',
                             store_output=True)
            wf.input(t9, fformat='rtp_allatom', ffversion='54A7')
            wf.connect_task(choice1, t9)

            # Convert ATB ligand PDB tot mol2
            t10 = wf.add_task('Ligand PDB to mol2', task_type='WampTask', uri='liestudio.structure.convert',
                              store_output=True)
            wf.input(t10, input_format='pdb', output_format='mol2', from_file=True)
            wf.connect_task(t8, t10, data_mapping={'result': 'mol'})


            # STAGE 3. PLANTS DOCKING
            # Create rotations of the molecule for better sampling
            t11 = wf.add_task('Create 3D rotations', task_type='WampTask', uri='liestudio.structure.rotate',
                              store_output=True, continue_with_one=True)
            wf.input(t11, input_format='mol2', rotations=[[1, 0, 0, 90], [1, 0, 0, -90], [0, 1, 0, 90], [0, 1, 0, -90],
                                                          [0, 0, 1, 90], [0, 0, 1, -90]], from_file=True)
            wf.connect_task(t4, t11)
            wf.connect_task(t10, t11)

            # Run PLANTS on ligand and protein
            t12 = wf.add_task('Plants docking', task_type='WampTask', uri='liestudio.plants_docking.run_docking',
                              store_output=True)
            wf.input(t12, cluster_structures=100,
                     bindingsite_center=model['proteinParams'][0]['pocket'],
                     bindingsite_radius=model['proteinParams'][0]['radius'],
                     protein_file=os.path.join(liemodel, model['proteinParams'][0]['proteinDock']),
                     min_rmsd_tolerance=3.0)
            wf.connect_task(t11, t12, data_mapping={'mol': 'ligand_file'})

            # Get cluster median structures from docking
            t13 = wf.add_task('Get cluster medians', task_type='Task',
                              custom_func='allies_workflow_helpers.get_docking_medians')
            wf.connect_task(t12, t13)


            # STAGE 4. GROMACS MD
            # Ligand in solution
            t14 = wf.add_task('MD ligand in water', task_type='WampTask', uri='liestudio.gromacs.liemd',
                              store_output=True)
            wf.input(t14, sim_time=model['timeSim'], gromacs_lie=True, forcefield=forcefield,
                     periodic_distance=periodic_distance, temperature=temperature, solvent=solvent, ptau=ptau,
                     prfc=prfc, ttau=ttau, salinity=salinity, gromacs_vsite=gromacs_vsite)
            wf.connect_task(choice2, t14, data_mapping={'new_pdb': 'ligand_file', 'gmx_itp': 'topology_file'})

            # Map the ligand structures
            t15 = wf.add_task('Ligand mapper', task_type='Mapper')
            wf.connect_task(t13, t15, data_mapping={'medians': 'mapper'})

            # Run MD for protein + ligand
            t16 = wf.add_task('MD on protein-ligand system', task_type='WampTask', uri='liestudio.gromacs.liemd',
                              store_output=True)
            wf.input(t16, sim_time=model['timeSim'], gromacs_lie=True, forcefield=forcefield, charge=model['charge'],
                     periodic_distance=periodic_distance, temperature=temperature, solvent=solvent, ptau=ptau,
                     prfc=prfc, ttau=ttau, salinity=salinity, gromacs_vsite=gromacs_vsite,
                     protein_file=os.path.join(liemodel, model['proteinParams'][0]['proteinCoor']))
            wf.connect_task(t15, t16, data_mapping={'mapper': 'ligand_file'})
            wf.connect_task(choice2, t16, data_mapping={'gmx_itp': 'topology_file'})

            # Collect results
            t17 = wf.add_task('Collect MD results', task_type='Task', to_mapper=t15,
                              custom_func='allies_workflow_helpers.collect_md_enefiles')
            wf.input(t17, model_dir=liemodel)
            wf.connect_task(t14, t17, data_mapping={'output': 'unbound'})
            wf.connect_task(t16, t17, data_mapping={'output': 'bound'})


            # STAGE 5. PYLIE FILTERING, AD ANALYSIS AND BINDING-AFFINITY PREDICTION
            # Collect Gromacs bound and unbound MD energy trajectories in a dataframe
            t18 = wf.add_task('Create mdframe', task_type='WampTask',
                              uri='liestudio.pylie.collect_energy_trajectories', store_output=True)
            wf.connect_task(t17, t18)

            # Determine stable regions in MDFrame and filter
            t19 = wf.add_task('Detect stable regions', task_type='WampTask',
                              uri='liestudio.pylie.filter_stable_trajectory', store_output=True)
            wf.input(t19, do_plot=True)
            wf.connect_task(t18, t19)

            # Extract average LIE energy values from the trajectory
            t20 = wf.add_task('LIE averages', task_type='WampTask', uri='liestudio.pylie.calculate_lie_average',
                              store_output=True)
            wf.connect_task(t19, t20, data_mapping={'filtered_mdframe': 'mdframe'}, data_select=['filtered_mdframe'])

            # Calculate dG using pre-calibrated model parameters
            t21 = wf.add_task('Calc dG', task_type='WampTask', uri='liestudio.pylie.liedeltag', store_output=True)
            wf.input(t21,
                     alpha=modelfile['LIE']['params'][0],
                     beta=modelfile['LIE']['params'][1],
                     gamma=modelfile['LIE']['params'][2])
            wf.connect_task(t20, t21, data_mapping={'averaged': 'dataframe'})

            # Applicability domain: 1. Tanimoto similarity with training set
            t22 = wf.add_task('AD1, tanimoto simmilarity', task_type='WampTask',
                             uri='liestudio.cheminfo.chemical_similarity')
            wf.input(t22, test_set=[ligand], mol_format=ligand_format,
                     reference_set=modelfile['AD']['Tanimoto']['smi'],
                     ci_cutoff=modelfile['AD']['Tanimoto']['Furthest'])
            wf.connect_task(start.nid, t22)

            # Applicability domain: 2. residue decomposition
            t23 = wf.add_task('AD2, residue decomposition', task_type='WampTask',
                             uri='liestudio.pylie.adan_residue_decomp', store_output=True)
            wf.input(t23, model_pkl=modelpicklefile)
            wf.connect_task(t17, t23)

            # Applicability domain: 3. deltaG energy range
            t24 = wf.add_task('AD3, dene yrange', task_type='WampTask', uri='liestudio.pylie.adan_dene_yrange',
                             store_output=True)
            wf.input(t24, ymin=modelfile['AD']['Yrange']['min'], ymax=modelfile['AD']['Yrange']['max'])
            wf.connect_task(t21, t24, data_mapping={'liedeltag_file': 'dataframe'})

            # Applicability domain: 4. deltaG energy distribution
            t25 = wf.add_task('AD4, dene distribution', task_type='WampTask', uri='liestudio.pylie.adan_dene',
                              store_output=True)
            wf.input(t25, model_pkl=modelpicklefile,
                     center=list(modelfile['AD']['Dene']['Xmean']),
                     ci_cutoff=modelfile['AD']['Dene']['Maxdist'])
            wf.connect_task(t21, t25, data_mapping={'liedeltag_file': 'dataframe'})

        # Run the workflow
        wf.run()
        while wf.is_running:
            yield sleep(1)

        # Save the workflow to file
        project_dir = wf.get_task(1)['workdir']
        wf.save(path=os.path.join(project_dir, 'workflow.json'))

        self.leave()
        self.disconnect()
        return
        

if __name__ == '__main__':
    
    # load the self-signed cert the server is using
    #certpath = os.path.join(os.path.dirname(__file__), '../data/crossbar/server_cert.pem')
    #cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(certpath, 'r').read())
    
    # tell Twisted to use just the one certificate we loaded to verify connections
    #options = CertificateOptions(trustRoot=OpenSSLCertificateAuthorities([cert]))
        
    runner = ApplicationRunner(
        u"ws://localhost:8080/ws",
        u"liestudio",
        extra={'authid':u'lieadmin', 'password':u'liepw@#', 'authmethod':u'ticket'},
        #ssl=options
    )
    runner.run(LIEWorkflow, auto_reconnect=False)
