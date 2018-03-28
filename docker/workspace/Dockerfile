FROM python:3.6

RUN pip install --upgrade pip
RUN pip install --upgrade pipenv
RUN pip install --upgrade virtualenv

COPY docker-entrypoint.sh /docker-entrypoint.sh

VOLUME /app
WORKDIR /app

STOPSIGNAL SIGTERM

RUN echo "" >> ~/.bashrc && \
    echo 'source ~/.bashrc_mdstudio' >> ~/.bashrc

ENV PYENV_SHELL=/bin/bash

ADD .bashrc_mdstudio /root/.bashrc_mdstudio

CMD ["bash", "/docker-entrypoint.sh"]
