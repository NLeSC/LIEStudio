# -*- coding: utf-8 -*-

PYLIE_MASTER_CONFIG = {

    # Global settings
    'Global.kBt': 2.49,
    'Global.R': 8.3144621,  # Gasconstant in J K-1 mol-1
    'Global.temp': 305,  # Temperature, degrees Kelvin
    'Global.plotFileType': 'pdf',  # Filetype for plots saved to disk
    'Global.rlm_outlier_cutoff': 0.8,  # Outlier detection limit for Robust Linear Regression weights

    # LIEScanDataFrame:
    'LIEScanDataFrame.max_combinations': 100000000,
    'LIEScanDataFrame.alpha': [0, 1.01, 0.01],
    'LIEScanDataFrame.beta': [0, 1.01, 0.01],
    'LIEScanDataFrame.gamma': 0,
    'LIEScanDataFrame.pdist_metric': 'euclidean',
    'LIEScanDataFrame.linkage_metric': 'euclidean',
    'LIEScanDataFrame.linkage_method': 'complete',
    'LIEScanDataFrame.cluster_method': 'vector',
    'LIEScanDataFrame.outlier_cutoff': 0.75,
    'LIEScanDataFrame.inlier_cutoff': 0.75,
    'LIEScanDataFrame.prob_insignif_cutoff': 0.05,
    'LIEScanDataFrame.prob_report_insignif': True,
    'LIEScanDataFrame.grad_desc_cutoff': -0.0001,
    'LIEScanDataFrame.grad_ascn_cutoff': 0.0001,

    # LIEModelBuilder:
    'LIEModelBuilder.def_params': [0.5, 0.5],
    'LIEModelBuilder.conv_cutoff': 1.0e-10,
    'LIEModelBuilder.maxiter': 500,
    'LIEModelBuilder.minclustersize': 8,
    'LIEModelBuilder.model_cols': ['vdw', 'coul'],
    'LIEModelBuilder.window_size': 4,
    'LIEModelBuilder.param_scale': 0.1,
    'LIEModelBuilder.max_error_steps': 50,
    'LIEModelBuilder.max_dw_cutoff': 0.1,
    'LIEModelBuilder.max_iter_steps': 500,
    'LIEModelBuilder.mc_rand_sample_draw': 0.2,
    'LIEModelBuilder.mc_filter_tol': 0.9,
    'LIEModelBuilder.random_add': True,
    'LIEModelBuilder.max_deviation': 0.8,
    'LIEModelBuilder.usefilter': True,
    'LIEModelBuilder.filter.param_ltol': [0, 0, -100],
    'LIEModelBuilder.filter.param_utol': [1, 1, 100],
    'LIEModelBuilder.filter.rmsd': [0, 5],
    'LIEModelBuilder.filter.rsquared': [0.6, 1],

    # LIEMDFrame:
    'LIEMDFrame.inlierFilterMethod': 'pair',
    'LIEMDFrame.filetype': 'gromacs',
    'LIEMDFrame.lie_vdw_header': 'vdwLIE',
    'LIEMDFrame.lie_ele_header': 'EleLIE',

    # FilterSplines class: FFT based spline filtering of MD (energy) trajectories
    'FilterSplines.fftfreq': 15,  # Filter frequencies higher than X. The higher the number, the more bumps.
    'FilterSplines.gradco': 0.2,  # Gradient cutoff: if value higher than X, the gradient is high enough, there is a change
    'FilterSplines.gradco_mult': 100,  # Gradient multiplication factor for plotting
    'FilterSplines.gradcl': 0.0,  # Clean 0.1*length from start and end (0 means no cleaning, recommended. Only use with FFTfreq ~5 and lower)
    'FilterSplines.minlength': 100,  # Minimal length of stable data (in datapoints, not time!)
    'FilterSplines.extend': True,  # If stable stretch is longer then minlength, use full stretch if TRUE
    'FilterSplines.doublespline': True,  # Perform double spline fitting on FFT output (recommended)
    'FilterSplines.splinesmooth': 999,  # Smoothness of the spline (low is smoother, 0 gives the orig data back)

    # FilterGaussian class: Multivariate Gaussian based filtering of the Van der Waals - Coulomb energy pairs in the dataset
    'FilterGaussian.confidence': 0.975,

    # FilterWorkflow
    'FilterWorkflow.doFilterSplines': True,
    'FilterWorkflow.FilterSplinesInlierMethod': 'pair',
    'FilterWorkflow.plotFilterSplines': False,
    'FilterWorkflow.doFilterGaussian': True,
    'FilterWorkflow.plotFilterGaussian': False,
    'FilterWorkflow.doFilterAlphaBetaScan': True,
    'FilterWorkflow.plotFilterAlphaBetaScan': False,
    'FilterWorkflow.stable_unbound_md_tolerance': 0.05,
    'FilterWorkflow.plot_results': False,

    # PoseWorkflow
    'PoseWorkflow.plotClusterResults': False,

    # ModelWorkflow
    'ModelWorkflow.rmsd_tolerance': 3,
    'ModelWorkflow.plotClusterResults': False,
    'ModelWorkflow.cluster_method': 'vector',
    'ModelWorkflow.pdist_metric': 'euclidean',
    'ModelWorkflow.linkage_metric': 'euclidean',
    'ModelWorkflow.linkage_method': 'complete',
}
