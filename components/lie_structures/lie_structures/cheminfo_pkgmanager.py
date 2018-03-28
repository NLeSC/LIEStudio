# -*- coding: utf-8 -*-

"""
file: cheminfo_pkgmanager.py

Manage import of Cinfony supported cheminformatics software packages.

Currently supports the following 9 packages:

* webel: A cheminformatics toolkit built solely on webservices.
         All cheminformatics analysis is carried out using Rajarshi's REST
         services at http://rest.rguha.net (which use the CDK and are hosted
         at Uppsala) and the NIH's Chemical Identifier Resolver (by Markus
         Sitzmann, and which uses Cactvs for much of its backend).

         Dependencies: webel has no dependencies other than the Python
         standard library.

         Citation: X. Dong, K.E. Gilbert, R. Guha, R. Heiland, J. Kim,
         M.E. Pierce, G.C. Fox, and D.J. Wild, "Web Service Infrastructure
         for Chemoinformatics", Journal of Chemical Information and Modeling
         2007 47 (4), 1303-1307, DOI: 10.1021/ci6004349

* silverwebel: uses the same webservices backend as the 'webel' package but
         accessed through a .NET implementation.

         Dependencies: the Python 'pythonnet' package for nearly seamless
         integration with the .NET Common Language Runtime (CLR)

* pybel: Python bindings to the OpenBabel cheminformatics package.

         Dependencies: OpenBabel by default installed as part of cheminfo.

         Installation: If installed separately ensure that the python bindings
         are compiled by using the -DPYTHON_BINDINGS=ON argument to cmake.

         Citation: N.M. O'Boyle, M. Banck, C.A. James, C. Morley, T.
         Vandermeersch and G.R. Hutchison. "Open Babel: An open chemical toolbox."
         Journal of Cheminformatics (2011), 3, 33. DOI:10.1186/1758-2946-3-33

* cdk:   Binding to the Chemistry Development Kit (CDK) Java libraries using
         JPype Java-Python bridge.

         Dependencies: the self-contained CDK .jar file version 1.4.6
         downloadable at: https://sourceforge.net/projects/cdk/, the Python
         JPype package installed by default as part of the cheminfo.

         Installation: to correctly setup the bindings to CDK, add the
         following environment variables to your .bash_profile or equivalent
         shell setup script.

         export CLASSPATH=$HOME/Library/Java/cdk-1.4.7.jar:$CLASSPATH
         export JPYPE_JVM=/System/Library/Frameworks/JavaVM.framework/JavaVM
         export LD_LIBRARY_PATH=/System/Library/Frameworks/JavaVM.framework/Libraries:$LD_LIBRARY_PATH

         The CLASSPATH variable points to the location of the CDK .jar file.
         JPYPE_JVM points to the location of the Java Virtual Machine executable
         in this case the Mac OSX one. LD_LIBRARY_PATH to the Java libraries in
         this case also the Mac OSX one.

         Citation: C. Steinbeck, Y. Han, S. Kuhn, O. Horlacher, E. Luttmann and
         E.L. Willighagen, "The Chemistry Development Kit (CDK): An Open-Source
         Java Library for Chemo- and Bioinformatics" Journal of Chemical
         Information and Computer Sciences 2003 43 (2), 493-500
         DOI: 10.1021/ci025584y

         E.L. Willighagen, J.W. Mayfield, J. Alvarsson, A. Berg, L. Carlsson,
         N. Jeliazkova, S. Kuhn, T. Pluskal, M. Rojas-Chertó, O. Spjuth,
         G. Torrance, C.T. Evelo, R. Guha and C. Steinbeck "The Chemistry
         Development Kit (CDK) v2.0: atom typing, depiction, molecular formulas
         and substructure searching" Journal of Cheminformatics (2017) 9:33
         DOI: 10.1186/s13321-017-0220-4

* opsin: Open Parser for Systematic IUPAC Nomenclature. A Java package to
         convert chemical names to structures.

         Dependencies: the self-contained OPSIN .jar file version 1.3.0 or
         higher downloadable at: https://bitbucket.org/dan2097/opsin/downloads,
         the Python JPype package installed by default as part of the cheminfo.

         Installation: to correctly setup the bindings to OPSIN, add the
         following environment variables to your .bash_profile or equivalent
         shell setup script.

         export CLASSPATH=$HOME/Library/Java/opsin-1.3.0-jar-with-dependencies.jar:$CLASSPATH
         export JPYPE_JVM=/System/Library/Frameworks/JavaVM.framework/JavaVM
         export LD_LIBRARY_PATH=/System/Library/Frameworks/JavaVM.framework/Libraries:$LD_LIBRARY_PATH

         The CLASSPATH variable points to the location of the OPSIN .jar file.
         JPYPE_JVM points to the location of the Java Virtual Machine executable
         in this case the Mac OSX one. LD_LIBRARY_PATH to the Java libraries in
         this case also the Mac OSX one.

         Citation: D.M. Lowe, P.T. Corbett, P. Murray-Rust and R.C. Glen
         "Chemical Name to Structure: OPSIN, an Open Source Solution", Journal
         of Chemical Information and Modeling 2011 51 (3), 739-753
         DOI: 10.1021/ci100384d

* rdk:   RDKit is a collection of cheminformatics and machine-learning software
         written in C++ and Python.

         Dependencies: the RDKit library https://github.com/rdkit/rdkit. Requires
         the Boost libraries for compilation.

         Installation: to correctly setup the bindings to RDKit, add the
         following environment variables to your .bash_profile or equivalent
         shell setup script

         export RDBASE='$HOME/bin/RDkit'
         export DYLD_LIBRARY_PATH='$HOME/bin/RDkit/lib'

         Where RDBASE and DYLD_LIBRARY_PATH point to the installation directory
         of RDKit

* indy:  Indigo: universal cheminformatics API written in C++

         Dependencies: download a pre-compiled version of Indigo with Python
         language bindings for the appropriate platform or build from source
         from http://lifescience.opensource.epam.com/indigo/.

         Installation: add the Indigo installation directory to your Python
         path

         Citation: Pavlov, D., Rybalkin, M., Karulin, B., Kozhevnikov,
         M., Savelyev, A., & Churinov, A. "Indigo: universal cheminformatics API"
         Journal of Cheminformatics (2011), 3(Suppl 1), P4.
         DOI: 10.1186/1758-2946-3-S1-P4

* jchem: ChemAxon's JChem from CPython and Jython

* pydpi: A Python package for cheminformatics, Bioinformatics and Chemogenomics
         that uses RDKit as engine.

         Dependencies: an RDKit installation (see rdkit) and the Python pydpi
         package installed as part of cheminfo.

         Installation: follow the installation instructions of RDKit.

         Citation: D. Cao, Y. Liang, J. Yan, G. Tan, Q. Xu, and S. Liu "PyDPI:
         Freely Available Python Package for Chemoinformatics, Bioinformatics,
         and Chemogenomics Studies", Journal of Chemical Information and Modeling
         2013 53 (11), 3086-3096
         DOI: 10.1021/ci400127q
"""

import os
import sys
import collections
import importlib
import logging

from retrying import retry
from twisted.logger import Logger

logging = Logger()

# Cheminformatics packages supported by cheminfo, the order matters!
SUPPORTED_PACKAGES = ('webel', 'silverwebel', 'pybel', 'jchem', 'cdk', 'indy', 'opsin', 'rdk', 'pydpi')


def retry_if_Index_Exception(exception):
    """
    There is a bug when importing pybel that triggers this error:
    https://github.com/MD-Studio/MDStudio/issues/29
    """
    return isinstance(exception, IndexError)


class CinfonyPackageManager(collections.MutableMapping):
    """
    Package import manager

    Manages the import of cheminformatics software supported by cheminfo
    provided they have been installed in accordance with the installation
    instructions mentioned above.
    """

    def __init__(self, package_config, *args, **kwargs):
        self.__dict__.update(*args, **kwargs)

        # Try import of supported packages
        for package in SUPPORTED_PACKAGES:
            self._import_pkg(package, package_config)

        logging.info('Imported packages: {0}'.format(', '.join(self.keys())))
        not_imported = [p for p in SUPPORTED_PACKAGES if p not in self]
        if not_imported:
            logging.info('Packages not imported: {0}. Check the installation instructions '
                         'if this was unexpected'.format(', '.join(not_imported)))

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getitem__(self, key):
        return self.__dict__[key]

    def __delitem__(self, key):
        del self.__dict__[key]

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    @retry(retry_on_exception=retry_if_Index_Exception, stop_max_attempt_number=10)
    def _import_pkg(self, package, package_config):
        """
        Import packages by name or path and register in self.
        Log relevant import errors

        :param package:        package name
        :type package:         :py:str
        :param package_config: package specific configuration
        :type package_config:  :py:dict
        """

        # If package path defined, add to Python path
        path = '{0}_path'.format(package)
        if path in package_config:
            if not os.path.exists(package_config[path]):
                logging.error('No such path to package {0}: {1}'.format(package, package_config[path]))
                return
            if path not in sys.path:
                sys.path.append(package_config[path])

        # Prepare import. PyDPI is not in Cinfony
        package_name = 'cinfony.{0}'.format(package)
        if package == 'pydpi':

            # RDKit needed for pydpi
            if 'rdk' not in self:
                logging.info('Cannot load PyDPI, RDKit not available')
                return
            package_name = 'cheminfo_pydpi'

        # Try package import, report errors
        try:
            self[package] = importlib.import_module(package_name)
        except ImportError as e:
            logging.debug('Import error for package {0}: {1}'.format(package, e))
        except SyntaxError as e:
            logging.error('Syntax error on import of package {0}: {1}'.format(package, e))
        except KeyError as e:
            logging.error('Package {0}: not found.'.format(package))
        # except:
        #     logging.error('Unexpected error for package {0}: {1}'.format(package, sys.exc_info()[0]))
