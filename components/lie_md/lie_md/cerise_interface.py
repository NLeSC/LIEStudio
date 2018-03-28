# -*- coding: utf-8 -*-
from collections import defaultdict
from mdstudio.deferred.chainable import chainable
from mdstudio.deferred.return_value import return_value
from os.path import join
from retrying import retry
from time import sleep
import cerise_client.service as cc
import docker
import hashlib
import json
import os


def create_cerise_config(input_session):
    """
    Creates a Cerise service using the path_to_config
    yaml file, together with the cwl_workflow to run
    and store the meta information in the session.

    :Param Input_dict: Object containing the cerise files.
    :returns: Dict containing the Cerise config.
    """
    with open(input_session['cerise_file'], 'r') as f:
        config = json.load(f)

    # Return None if key no in dict
    config = defaultdict(lambda: None, config)

    # Set Workflow
    protein_file = input_session['protein_file']
    config['cwl_workflow'] = choose_cwl_workflow(protein_file)
    config['log'] = join(input_session['workdir'], 'cerise.log')
    config['workdir'] = input_session['workdir']

    return config


@chainable
def call_cerise_gromit(
        gromacs_config, cerise_config, cerise_db):
    """
    Use cerise to run gromacs in a remote cluster, see:
    http://cerise-client.readthedocs.io/en/latest/

    :param gromacs_config: dict containing the gromacs parameters
    for the simulation.
    :param cerise_config: dict containing the settings to create
    and call a cerise-client process.
    :param cerise_db: MongoDB db to keep the information
    related to the Cerise services and jobs.
    :returns: Dict with the output paths.
    """
    print("Searching for pending jobs in DB")
    xs = cerise_db.insert_one("test", {"result": 42})
    r = cerise_db.extract(xs, 'id')
    return_value({"results": r})
    # srv_data = yield retrieve_service_from_db(
    #     cerise_config, gromacs_config, cerise_db)

    # if srv_data['result'] is None:
    #     print("There are no pending jobs!")
    #     # Create a new service if one is not already running
    #     srv = create_service(cerise_config)
    #     srv_data = yield submit_new_job(
    #         srv, gromacs_config, cerise_config, cerise_db)
    #     print("service: ", srv_data)

    # # is the job still running?
    # elif srv_data['job_state'] == 'Running':
    #     restart_srv_job(srv_data)

    # else:
    #     msg = "job is already done!"
    #     print(msg)

    # # Simulation information including cerise data
    # sim_dict = yield extract_simulation_info(
    #     srv_data, cerise_config, cerise_db)

    # print("results ", sim_dict)

    # # Shutdown Service if there are no other jobs running
    # yield try_to_close_service(srv_data, cerise_db)

    # return_value(sim_dict)


def retrieve_service_from_db(
        cerise_config, gromacs_config, cerise_db):
    """
    Check if there is an alive service in the db.

    :param cerise_config: Service metadata.
    :param gromacs_config: Path to the ligand geometry.
    :param cerise_db: Connector to the DB.
    """
    ligand_file = gromacs_config['ligand_file']
    query = {
        'job_type': gromacs_config['job_type'],
        'ligand_md5': compute_md5(ligand_file),
        'name': cerise_config['docker_name']}

    return cerise_db.find_one('cerise', query)


@retry(wait_random_min=500, wait_random_max=2000)
def create_service(cerise_config):
    """
    Create a Cerise service if one is not already running,
    using the `cerise_config` file.
    """
    try:
        srv = cc.require_managed_service(
                cerise_config['docker_name'],
                cerise_config.get('port', 29593),
                cerise_config['docker_image'],
                cerise_config['username'],
                cerise_config['password'])
        print("Created a new Cerise-client service")
    except docker.errors.APIError:
        pass

    return srv


@chainable
def submit_new_job(srv, gromacs_config, cerise_config, cerise_db):
    """
    Create a new job using the provided `srv` and `cerise_config`.
    The job's input is extracted from the `gromacs_config`  and
    the job metadata is stored in the DB using `cerise_db`.
    """
    print("Creating Cerise-client job")
    job = create_lie_job(srv, gromacs_config, cerise_config)

    # Associate a CWL workflow with the job
    job.set_workflow(cerise_config['cwl_workflow'])
    print("CWL worflow is: {}".format(cerise_config['cwl_workflow']))

    # run the job in   the remote
    msg = "Running the job in a remote machine using docker: {}".format(
        cerise_config['docker_image'])
    print(msg)

    # submit the job and register it
    job.run()

    # Store data in the DB
    srv_data = collect_srv_data(
        job.id, cc.service_to_dict(srv), gromacs_config,
        cerise_config['username'])

    # wait until the job is running
    while job.state == 'Waiting':
        sleep(2)

    # Add srv_dict to database
    srv_data['job_state'] = 'Running'
    s = yield register_srv_job(
        job, srv_data, cerise_db)
    print("register: ", s)
    
    return_value(srv_data)


def restart_srv_job(srv_data):
    """
    Use a dictionary to restart a Cerise service.

    :param srv_data: dict containing the cerise service information.
    """
    srv = cc.service_from_dict(srv_data)
    cc.start_managed_service(srv)

    job = srv.get_job_by_id(srv_data['job_id'])

    print("Job {} already running".format(job.id))


@chainable
def extract_simulation_info(
        srv_data, cerise_config, cerise_db):
    """
    Wait for a job to finish, if the job is already done
    return the information retrieved from the db.

    :param srv_data: dict containing the meta information
    of the cerise service.
    :param srv_data: dict containing the data use to create
    a new cerise service.
    : param cerise_db: Mongo db collection to store data
    related to the cerise service.
    """
    print("Extracting output from: {}".format(
        cerise_config['workdir']))

    if cc.managed_service_exists(srv_data['name']):
        srv = cc.service_from_dict(srv_data)
        job = srv.get_job_by_id(srv_data['job_id'])
        output = wait_extract_clean(
            job, srv, cerise_config, cerise_db)

        # Update data in the db
        srv_data.update(output)
        srv_data['job_state'] = job.state
        update_srv_info_at_db(srv_data, cerise_db)

    # remove mongoDB object id
    srv_data.pop('_id', None)

    return_value(srv_data)


def wait_extract_clean(job, srv, cerise_config, cerise_db):
    """
    Wait for the `job` to finish, extract the output and cleanup.
    """
    job = wait_for_job(job, cerise_config['log'])
    output = get_output(job, cerise_config)
    cleanup(job, srv, cerise_db)

    return output


def update_srv_info_at_db(srv_data, cerise_db):
    """
    Update the service-job data store in the `cerise_db`.
    """
    query = {'ligand_md5': srv_data['ligand_md5']}
    cerise_db.update_one('cerise', query, {"$set": srv_data})


def collect_srv_data(
        job_id, srv_data, gromacs_config, username):
    """
    Add all the relevant information for the job and
    service to the service dictionary
    """
    # Save id of the current job in the dict
    srv_data['job_id'] = job_id

    # create a unique ID for the ligand
    ligand_file = gromacs_config['ligand_file']

    srv_data['ligand_md5'] = compute_md5(ligand_file)
    srv_data['username'] = username
    srv_data['job_type'] = gromacs_config['job_type']

    return srv_data


def create_lie_job(srv, gromacs_config, cerise_config):
    """
    Create a Cerise job using the cerise `srv` and set gromacs
    parameters using `gromacs_config`.
    """
    job_name = 'job_{}'.format(cerise_config['task_id'])
    job = srv.create_job(job_name)

    # Copy gromacs input files
    job = add_input_files_lie(job, gromacs_config)

    return set_input_parameters_lie(job, gromacs_config)


def add_input_files_lie(job, gromacs_config):
    """
    Tell to Cerise which files are associated to a `job`.
    """
    # Add files to cerise job
    for name in ['protein_top', 'ligand_file', 'topology_file']:
        job.add_input_file(name, gromacs_config[name])

    protein_file = gromacs_config.get('protein_file')
    if protein_file is not None:
        job.add_input_file('protein_file', protein_file)
    else:
        msg = "There is not protein_file then a SOLVENT-LIGAND MD will be performed"
        print(msg)

    # Secondary files are all include as part of the protein
    # topology. Just to include them whenever the protein topology
    # is used
    if gromacs_config['include']:
        for file_path in gromacs_config['include']:
            job.add_secondary_file('protein_top', file_path)

    return job


def set_input_parameters_lie(job, gromacs_config):
    """
    Set input variables for gromit `job`
    and residues to compute the lie energy.
    """
    # Key to run the MD simulation
    md_keys = [x.split('.')[1] for x in gromacs_config.keys()
               if 'lie_md' in x]

    # Pass parameters to cerise job
    for k in md_keys:
        job.set_input(k, gromacs_config[k])

    # Finally set residues
    residues = gromacs_config['residues']
    job.set_input('residues', residues)

    return job


def register_srv_job(job, srv_data, cerise_db):
    """
    Once the `job` is running in the queue system register
    it in the `cerise_db`.
    """
    xs = cerise_db.insert_one('cerise', srv_data)
    print("Added service to mongoDB")
    return xs


def wait_for_job(job, cerise_log):
    """
    Wait until job is done.
    """
    # Wait for job to finish
    while job.is_running():
        sleep(30)

    # Process output
    if job.state != 'Success':
        print('There was an error: {}'.format(job.state))

    print('Cerise log stored at: {}'.format(
        cerise_log))

    with open(cerise_log, 'w') as f:
        json.dump(job.log, f, indent=2)

    return job


def cleanup(job, srv, cerise_db, remove_job_from_db=False):
    """
    Clean up the job and the service.
    """
    print("removing job: {} from Cerise-client".format(job.id))
    srv.destroy_job(job)

    # Remove job from DB
    if remove_job_from_db:
        remove_srv_job_from_db(srv, job.id, cerise_db)


def remove_srv_job_from_db(srv, job_id, cerise_db):
    """
    Remove the service and job information from DB
     """
    query = {'job_id': job_id}
    cerise_db.delete_one(query)
    print('Removed job: {} from database'.format(job_id))


@chainable
def try_to_close_service(srv_data, cerise_db):
    """
    Close service it There are no more jobs and
    the service is still running.
    """
    try:
        srv = cc.service_from_dict(srv_data)

        # Search for other running jobs
        query = {'username': srv_data['username'], 'job_state': 'Running'}
        counts = yield cerise_db.count('cerise', query)

        if counts == 0:
            print("Shutting down Cerise-client service")
            cc.stop_managed_service(srv)
            cc.destroy_managed_service(srv)

    except cc.errors.ServiceNotFound:
        print("There is not Cerise Service running")
        pass


def get_output(job, config):
    """
    retrieve output information from the `job`.
    """
    file_formats = {
        "gromitout": "{}_{}.out",
        "gromiterr": "{}_{}.err",
        "gromacslog2": "{}_{}.out",
        "gromacslog3": "{}_{}.out",
        "gromacslog4": "{}_{}.out",
        "gromacslog5": "{}_{}.out",
        "gromacslog6": "{}_{}.out",
        "gromacslog7": "{}_{}.out",
        "gromacslog8": "{}_{}.out",
        "gromacslog9": "{}_{}.out",
        "energy_edr":  "{}_{}.edr",
        "energy_dataframe": "{}_{}.ene",
        "energyout": "{}_{}.out",
        "energyerr": "{}_{}.err",
        "decompose_dataframe": "{}_{}.ene",
        "decompose_err": "{}_{}.err",
        "decompose_out": "{}_{}.out"}

    # Save all data about the simulation
    outputs = job.outputs
    results = {
        key: copy_output_from_remote(
            outputs[key], key, config, fmt)
        for key, fmt in file_formats.items() if key in outputs}

    return results


def copy_output_from_remote(file_object, file_name, config, fmt):
    """
    Copy output files to the localhost.
    """
    task_id = config['task_id']
    workdir = config['workdir']

    path = join(workdir, fmt.format(file_name, task_id))
    file_object.save_as(path)

    return path


def compute_md5(file_name):
    """
    Compute the md5 for a given `file_name`.
    """
    with open(file_name) as f:
        xs = f.read()

    return hashlib.md5(xs.encode()).hexdigest()


def choose_cwl_workflow(protein_file):
    """
    If there is not a `protein_file`
    perform a solvent-ligand simulation.
    """
    root = os.path.dirname(__file__)
    if protein_file is not None:
        return join(root, 'data/protein_ligand.cwl')
    else:
        return join(root, 'data/solvent_ligand.cwl')
