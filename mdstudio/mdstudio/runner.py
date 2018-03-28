# coding=utf-8

import os

import twisted
from autobahn.twisted.wamp import ApplicationRunner
from twisted.python.logfile import DailyLogFile

from mdstudio.component.impl.common import CommonSession
from twisted.internet import reactor, ssl
from twisted.internet.ssl import CertificateOptions

from mdstudio.logging.brand import ascii_brand
from mdstudio.logging.impl.printing_observer import PrintingLogObserver


def main(component, auto_reconnect=True):
    crossbar_host = os.getenv('CROSSBAR_HOST', 'localhost')

    with open(os.path.join(CommonSession.mdstudio_root_path(), '../data/crossbar/server_cert.pem'), 'r') as f:
        cert_data = f.read().encode('utf-8')

    cert = ssl.Certificate.loadPEM(cert_data)
    options = CertificateOptions(caCerts=[cert])

    runner = ApplicationRunner(
        u"wss://{}:8080/ws".format(crossbar_host),
        u"mdstudio",
        ssl=options
    )

    def start_component(config):
        logdir = os.path.join(component.component_root_path(), 'logs')
        if not os.path.exists(logdir):
            os.makedirs(logdir)

        gitignorepath = os.path.join(logdir, '.gitignore')
        if not os.path.isfile(gitignorepath):
            with open(gitignorepath, 'w') as f:
                f.write('*')

        log_file = DailyLogFile('daily.log', logdir)
        twisted.python.log.addObserver(PrintingLogObserver(log_file))

        print(ascii_brand)

        print('Crossbar host is: {}'.format(crossbar_host))
        session = component(config)  # type: CommonSession
        return session

    try:
        runner.run(start_component, auto_reconnect=auto_reconnect, start_reactor=not reactor.running, log_level='info')
    finally:
        if reactor.running:
            reactor.stop()
