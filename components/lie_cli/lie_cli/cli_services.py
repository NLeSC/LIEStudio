# -*- coding: utf-8 -*-

from autobahn.twisted.wamp import ApplicationRunner

from lie_cli.cli_parser import lie_cli_parser
from lie_cli.wamp_services import CliWampApi

def main():
    """
    Main function for enabling mdstudio_cli command line script functionality
    """

    # Parse command line arguments
    cliparser = lie_cli_parser()

    # Connect to MDStudio and call method
    runner = ApplicationRunner(
        u"ws://localhost:8080/ws",
        u"liestudio",
        extra=cliparser,
    )
    runner.run(CliWampApi, auto_reconnect=False, log_level='error')