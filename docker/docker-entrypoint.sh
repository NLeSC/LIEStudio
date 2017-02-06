echo 'Running installer' &>> docker/.INSTALLING

_VENV_NAME=$(basename $(pwd))

if ! [[ $(pew ls | grep "^${_VENV_NAME}$") -eq "${_VENV_NAME}" ]]; then
    bash installer.sh --setup --local-dev &>> docker/.INSTALLING

    echo 'Install IDE bindings' &>> docker/.INSTALLING
    # make sure we have the bindings for our IDE
    pipenv run pip freeze --local | grep -v '^\-e' > .requirements.txt
    pip install -r .requirements.txt &>> docker/.INSTALLING
    rm ./.requirements.txt
fi

echo 'Enabling debugging code' &>> docker/.INSTALLING
# disable the debugger disabling code which spews a LOT of warnings
sed -i 's/ sys.settrace(None)/ #sys.settrace(None)/g' ${_VENVPATH}/lib/python2.7/site-packages/twisted/internet/process.py

echo 'Set mongo connection' &>> docker/.INSTALLING
sed -i 's/"host": "localhost",/"host": "mongo",/g' /app/data/settings.json

_VENVPATH="/root/.local/share/virtualenvs/app"
grep -q "source ${_VENVPATH}/bin/activate" ~/.bashrc || echo "source ${_VENVPATH}/bin/activate" >> ~/.bashrc
grep -q "export MONGO_HOST=mongo" ~/.bashrc || echo "export MONGO_HOST=mongo" >> ~/.bashrc
grep -q "export IS_DOCKER=1" ~/.bashrc || echo "export IS_DOCKER=1" >> ~/.bashrc

echo 'Compiling pycharm helpers' &>> docker/.INSTALLING
if [ -d /app/.pycharm_helpers/pydev/ ]; then
    python /app/.pycharm_helpers/pydev/setup_cython.py build_ext --inplace &>> docker/.INSTALLING
fi

# notify the installation has been completed
echo '<<<<COMPLETED>>>>' >> docker/.INSTALLING

#execute the default phusion script
/sbin/my_init