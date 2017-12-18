#!/usr/bin/env bash

# LIEStudio installer script
# version 1.0
# Author: Marc van Dijk, VU University Amsterdam
# August 2016

# Get root directory of script
pushd `dirname $0` > /dev/null
ROOTDIR=`pwd -P`
popd > /dev/null

# CLI variables
SETUP=0
UPDATE=0
TEST=0
COMPILE_DOCS=0
FORCE=0
CERTIFICATE=0
VERBOSITY='debug'
PYTHON='python2.7'
VENVTOOL=
NO_VENV=0
USE_CONDA=0

# Internal variables
_PYTHON_PATH=
_PYV=
_PY_SUPPORTED=( 2\.7\* 3\.4\* 3\.5\* )
_PY_PACKAGES=( )
_PY_VENV=
_PY_VENV_ACTIVE=0
_VENV_NAME='venv'

USAGE="""LIEStudio setup script

This script installes or updates the LIEStudio 
software on your system.

Main options:
-s|--setup:         Install LIE Software package. Includes subroutines: -d, -c
-u|--update:        Update LIE Software package.
            
Subroutines:
-f|--force:         Force reinstall or update.
                    Default: $FORCE
-d|--documentation: Compile HTML documentation for the software and API.
                    documentation of the Python modules.
                    Default = $COMPILE_DOCS
-c|--certificate:   Create self-signed certificate for secure TLS transport.
                    Uses packaged certificate by default.
                    Default = $CERTIFICATE

Installation/update variables:
-p|--python:        Python version to use.
                    Default = $PYTHON
-e|--venv:          Python virtual environment tools to use.
                    Currently build-in venv module of Python 3.4> or Python 2.x virtualenv
-v|--verbosity:     verbosity level.
                    Default = $VERBOSITY
-l|--local-dev      Installs lie studio components inplace, making them easily editable.
-n|--no-venv        Do not use a virtual environment but system installed python packages
-c|--conda          Use Anaconda/Miniconda as Python virtual environment
                    
-h|--help:          This help message
"""

# Command line argument handling
for i in "$@"; do
    case $i in
        -h|--help)
        echo "$USAGE"
        exit 0
        shift # past argument with no value
        ;;
        -f|--force)
        FORCE=1
        shift # past argument with no value
        ;;
        -s|--setup)
        SETUP=1
        COMPILE_DOCS=1
        shift # past argument with no value
        ;;
        -u|--update)
        UPDATE=1
        shift # past argument with no value
        ;;
        -d|--documentation)
        COMPILE_DOCS=1
        shift # past argument with no value
        ;;
        -p=*|--python=*)
        PYTHON="${i#*=}"
        shift # past argument=value
        ;;
        -e=*|--venv=*)
        VENVTOOL="${i#*=}"
        shift # past argument=value
        ;;
        -v=*|--verbosity=*)
        VERBOSITY="${i#*=}"
        shift # past argument=value
        ;;
        -l|--local-dev)
        LOCALDEV=1
        shift # past argument with no value
        ;;
        -n|--no-venv)
        NO_VENV=1
        shift # past argument with no value
        ;;
        -c|--conda)
        USE_CONDA=1
        shift # past argument with no value
        ;;
        *)
        echo "$USAGE"
        exit 0 # unknown option
        ;;
    esac
done

# Check if array contains element
function containsElement () {
    local e
    for e in "${@:2}"; do [[ "$e" == "$1" ]] && return 0; done
    return 1
}

# Check if string is a valid path
# - actual path should contain at least one forward slash
# - path should exists
# - optionally check if file is executable
function _is_valid_path () {
    
    local FILE_TYPE=${2:-f}
    local IS_PATH=1
    [[ $( grep -o '/' <<<  $1 | wc -l ) -ne 0 ]] && $IS_PATH=0
    
    if [[ "$FILE_TYPE" == "-x" ]]; then
        if [[ $IS_PATH && -x $1 ]]; then
        return 0
        fi
    else
        if [[ $IS_PATH && -f $1 ]]; then
        return 0
        fi
    fi
    
    [[ $IS_PATH -eq 0 ]] && echo "ERROR: $1 seems to be a path but it is not valid"
    return 1
}

# Create a self-signed certificate to get basic TLS transport to work
# - Needs OpenSSL
# - Should be replaced by CA signed cert
function _create_self_signed_cert () {
  
    if [[ -z $( which openssl ) ]]; then
        CBDIR=${ROOTDIR}'/data/crossbar'
        openssl req -nodes -new -x509 -keyout ${CBDIR}/server_key.pem \
                -subj '/C=NL/ST=ZH/L=Amsterdam/O=VU/CN=LIEStudio/' \
                -out ${CBDIR}/server_cert.pem
    else
        echo "WARN: no 'openssl' implementation found. Unable to create basic self-signed certificate for TLS."
        echo "      If you wish to use secure communication over TLS, define your own certificate pair in ${CBDIR}/data/crossbar"    
    fi
}

# Check Python version
# - Check for prefered version, default $PYTHON
# - Check CLI defined python path or name
# - Check python version in users path
function _resolve_python_version () {
  
    # Check if $PYTHON is a known executable by name
    # else check if it is a valid path and is executable.
    _PYTHON_PATH=$( which ${PYTHON##*/} )
    if [[ -z $_PYTHON_PATH ]]; then 
        if _is_valid_path $PYTHON '-x'; then
        _PYTHON_PATH=$PYTHON
        else
        echo "ERROR: Python executable $PYTHON could not be resolved"
        exit 1
        fi
    fi
    echo "INFO: Python executable $PYTHON resolved to $_PYTHON_PATH"
    
    # Check if _PYTHON_PATH is actually Python.
    local IS_PYTHON="$( $_PYTHON_PATH --version 2>&1 | head -1 | awk '{print tolower($1)}' )"
    if [[ "$IS_PYTHON" != "python" ]]; then
        echo "ERROR: Executable does not seem to be python, $_PYTHON_PATH" 
        exit 1
    fi
    
    # Check if the python version is supported
    local SUPPORT_PYV=1
    if [[ "$IS_PYTHON" == "python" ]]; then
        
        _PYV=$( $_PYTHON_PATH --version 2>&1 | head -1 | awk '{print $2}')
        for pyv in "${_PY_SUPPORTED[@]}"; do
        if [[ $_PYV == $pyv ]]; then
            echo "INFO: Python version $_PYV supported"
            SUPPORT_PYV=0
            break
        fi
        done
        
    fi
    
    if [[ $SUPPORT_PYV -eq 1 ]]; then
        echo "ERROR: LIEStudio supports python version: "${_PY_SUPPORTED[@]}". Found: $_PYV"
        echo "ERROR: If you have one of the supported Python versions installed, supply the path using the -p/--python argument"
        exit 1
    fi
    
    echo "INFO: Using Python version $_PYV at $_PYTHON_PATH"
    return 0
}

# Check Python virtual environment options
# - If python version 3, use standard lib venv module
# - If python version 2.x then check if virtualenv is installed
function _resolve_python_venv () {
  
    # Python 3.4 or larger, use buildin venv module  
    if [[ $_PYV == 3\.* ]]; then
        echo "INFO: Using Python version $_PYV Virtual environment module (venv) part of standard library"
        _PY_VENV="$_PYTHON_PATH -m venv"
    
    # Python 2.x look for virtualenv tool
    else
        
        # If user provided path to virtualenv tool (-e/-venv), check
        if [[ -f $VENVTOOL ]]; then
            _PY_VENV="$VENVTOOL -p $_PYTHON_PATH"
        
        else   
            # Look for virtualenv tool that may be named differently
            local _virtualenv
            local _pyv_venv_options=( "virtualenv" "virtualenv-${_PYV%.*}" )
            for pyv_venv in "${_pyv_venv_options[@]}"; do
                _virtualenv=$( which $pyv_venv )
                if [[ ! -z $_virtualenv ]]; then
                    break
                fi
            done
        
            if [[ -z $_virtualenv ]]; then
                echo "ERROR: For Python version $_PYV the 'virtualenv' tool is required for installation of LIEstudio dependencies"
                echo "ERROR: It could not be found looking for: "${_pyv_venv_options[@]}" $VENVTOOL"
                echo "ERROR: If you have virtualenv installed, supply the path using the -e/--venv argument or"
                echo "ERROR: Install using 'pip install virtualenv' or similar"
                exit 1
            fi
        
            _PY_VENV="$_virtualenv -p $_PYTHON_PATH"
        fi
    fi
    
    [[ -z $_PY_VENV ]] && echo "ERROR: no Python venv tools defined", exit 1
    
    echo "INFO: Setup Python virtual environment using $_PY_VENV"
    return 0
}

# Check the directory structure
# - Create logs and temporary files directory
# - Change permissions /tmp to 
function _check_dir_structure () {
    
    for path in '/data/logs' '/tmp'; do
        if [ ! -d ${ROOTDIR}$path ]; then
        echo "INFO: Create directory ${ROOTDIR}$path"
        mkdir ${ROOTDIR}$path
        fi
    done
    
    chmod 755 ${ROOTDIR}/tmp
}

# Check if virtual environment is installed and activate
function _activate_py_venv () {
    
    if [[ $USE_CONDA -eq 0 ]]; then
    
        if [[ ! -e ${_VENVPATH}'/bin/activate' ]]; then
            echo "ERROR: Python virtual environment not installed (correctly)"
            echo "ERROR: Unable to activate it, not activation script at ${_VENVPATH}/bin/activate"
            exit 1
        fi
    
        if [[ $_PY_VENV_ACTIVE -eq 0 ]]; then
            source ${_VENVPATH}'/bin/activate'
            _PY_VENV_ACTIVE=1
        fi
    
    else
        source activate $_VENV_NAME
    fi
}

# Setup the Python virtual environment
# - No virtual environment path yet, create it
# - Already there, optionally force reinstall
function _setup_venv () {
    
    # Create or upgrade the Python virtual environment
    if [ ! -d $_VENVPATH ]; then
        
        # Remove and reinstall venv
        if [[ $FORCE -eq 1 ]]; then
            echo "INFO: Reinstall Python virtual environment at ${_VENVPATH}"
            rm -rf $_VENVPATH
            pipenv install
        else
            echo "INFO: Virtual environment present, not reinstalling"
        fi
        
    else
        echo "INFO: Create Python virtual environment"
        pipenv install
    fi
    
    return 0
}

# Setup the conda/miniconda managed virtual environment
function _setup_conda_venv () {
    
  local _CONDA=$( which conda )
  if [[ ! -z "$_CONDA" ]]; then
    
     # Create or upgrade the Anaconda virtual environment
     if [[ ! -z "$( $_CONDA info --envs | grep $_VENV_NAME )" ]]; then
        
         # Remove and reinstall venv
         if [[ $FORCE -eq 1 ]]; then
             echo "INFO: Reinstall Anaconda virtual environment"
             $_CONDA remove --name $_VENV_NAME --all
             $_CONDA create --name $_VENV_NAME
         else
             echo "INFO: Virtual environment present, not reinstalling"
         fi
        
     else
         echo "INFO: Create Anaconda/Miniconda managed virtual environment named $_VENV_NAME"
         $_CONDA create --name $_VENV_NAME
     fi
    
  else
     echo "ERROR: conda executable not found. Unable to install virtual environment"
     exit 1
  fi
  
  return 0
}

# Install python packages in virtual environment
function _install_update_packages () {
        
    # Activate venv
    _activate_py_venv

    # Download python packages not in pip
    cd ${ROOTDIR}/components
    for py_package in "${_PY_PACKAGES[@]}"; do
        echo "INFO: download Python package: " $py_package
        wget $py_package
        if [[ -f 'master.zip' ]]; then
        unzip 'master.zip'
        if [[ -d 'crossbar-master' ]]; then
            pip install $_force_reinstall "${ROOTDIR}/components/crossbar-master/"
            \rm -rf 'crossbar-master'
        fi
        \rm -f 'master.zip'  
        fi
    done
    cd ${ROOTDIR}
        
    # Update virtual environment
    if [[ $UPDATE -eq 1 ]]; then
        echo "INFO: Update Python virtual environment at $_VENVPATH"
        pipenv update
    else
        pipenv install
    fi

    # Install all LIEStudio component packages and their dependencies using pip
    local _force_reinstall=''
    [[  $UPDATE -eq 1 ]] && _force_reinstall='--upgrade'
    
    local _local_install=''
    [[  $LOCALDEV -eq 1 ]] && _local_install='-e'
    
    # Install LIEStudio components using pip
    for package in $( ls -d ${ROOTDIR}/components/*/ ); do
        if [[ -e ${package}/setup.py ]]; then
            echo "INFO: Install LIEStudio Python component ${package}"
            pip install $_force_reinstall $_local_install $package
        fi
    done
    
    return 0
}

# Compile LIEStudio and API documentation as HTML using Sphinx
function _compile_python_sphinx_docs () {
    
    # Build documentation
    echo "INFO: Compile LIEStudio and API documentation in HTML"
    rm -rf ${ROOTDIR}/docs/html
    cd ${ROOTDIR}/docs
    make html
    cd ${ROOTDIR}
    
    if [[ -d ${ROOTDIR}/docs/_build/html ]]; then
        mv -f ${ROOTDIR}/docs/_build/html ${ROOTDIR}/docs/html
        rm -rf ${ROOTDIR}/docs/_build
    fi
}

# ========== MAIN ========== 

echo ""
echo "==================== LIEStudio installer script ====================="
echo "Date: $( date )"
echo "User: $( whoami )  UID: $UID   GID: $GID"
echo "System: $( uname -mpnsr )"
echo "====================================================================="
echo ""

cd $ROOTDIR

export PIPENV_VENV_IN_PROJECT=1

# 1) Resolve Python version and virtual environment options
if [[ $NO_VENV -eq 0 ]]; then
    _resolve_python_version

    # 1.1) Use default Python venv tool or Anaconda managed virtual environment
    if [[ $USE_CONDA -eq 0 ]]; then
        _resolve_python_venv
    else
        echo "INFO: Use Anaconda/Miniconda managed virtual environment"
    fi

else
    echo "INFO: Skip setup of Python virtual environment."
    echo "INFO: Python package dependencies should be installed on the system."
fi

# 2) Check directory structure
_check_dir_structure

# 3) Install virtual environment
if [[ $SETUP -eq 1 && $NO_VENV -eq 0 ]]; then
     
    # 3.1) Install Python or Anaconda/Miniconda virtual environment
    if [[ $USE_CONDA -eq 0 ]]; then
        _setup_venv
    else
        _setup_conda_venv
    fi

fi

_VENVPATH=${ROOTDIR}/$_VENV_NAME

# 4) Install/update python packages
if [[ $NO_VENV -eq 0 ]]; then
    if [[ $SETUP -eq 1 || $UPDATE -eq 1 ]]; then
        _install_update_packages
    fi
fi

# 5) Create self-signed certificate
if [[ $CERTIFICATE -eq 1 ]]; then
    _create_self_signed_cert
else
    echo "INFO: use default certificate key pair for TLS"
    echo "      If you wish to use secure communication over TLS, define your own certificate pair in ${CBDIR}/data/crossbar"
fi

# 6) Install npm dependencies
if [[ $SETUP -eq 1 || ! -d ${ROOTDIR}/app/node_modules ]]; then
    echo 'Install NPM packages'
    mkdir -p ${ROOTDIR}/app/node_modules
    npm install --prefix ${ROOTDIR}/app --unsafe-perm
elif [[ $UPDATE -eq 1 ]]; then
    echo 'Updating NPM packages'
    mkdir -p ${ROOTDIR}/app/node_modules
    npm update --prefix ${ROOTDIR}/app --unsafe-perm
fi

# 7) Compile gulp 
if [[ $SETUP -eq 1 || $UPDATE -eq 1 ]]; then
    echo 'Compile gulp'
    cd ${ROOTDIR}/app
    gulp compile
    cd ${ROOTDIR}
fi

# 8) Compile software documentation
if [[ $COMPILE_DOCS -eq 1 ]]; then
    _activate_py_venv
    _compile_python_sphinx_docs
fi

# 9) Deactivate Python venv
if [[ $USE_CONDA -eq 0 ]]; then
    deactivate >/dev/null 2>&1
else
    source deactivate
fi

# 10) Finish
echo "NOTE: installation succesful"
exit 0
