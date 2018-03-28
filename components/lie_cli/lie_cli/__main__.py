from mdstudio.runner import main
from lie_cli.wamp_services import CliWampApi

if __name__ == '__main__':
    main(CliWampApi,  auto_reconnect=False)
