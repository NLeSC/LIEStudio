# -*- coding: utf-8 -*-

from autobahn.twisted.wamp import ApplicationRunner
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor

from lie_system import LieApplicationSession


class LIEWorkflow(LieApplicationSession):

    @inlineCallbacks
    def onRun(self, details):

        mol = yield self.call(u'liestudio.structure.convert', input_format='smi', output_format='mol2',
                        mol='O1[C@@H](CCC1=O)CCC')
        pdb = yield self.call(u'liestudio.structure.make3d', input_format='mol2', mol=mol['mol'])

        print pdb['mol']

        self.disconnect()
        reactor.stop()

        yield True


if __name__ == '__main__':

    runner = ApplicationRunner(
        u"ws://localhost:8080/ws",
        u"liestudio",
        extra={'authid': u'lieadmin', 'password': u'liepw@#', 'authmethod': u'ticket'},
    )
    runner.run(LIEWorkflow, auto_reconnect=False)
