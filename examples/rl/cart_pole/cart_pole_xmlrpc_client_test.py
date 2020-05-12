import logging
logging.basicConfig(level='DEBUG')
from xmlrpc.client import ServerProxy, Fault
from naus.environment_proxy import EnvironmentProxyForClient

log = logging.getLogger('naus')


class MyServerProxy(ServerProxy):
    def close(self, *args, **kwargs):
        try:
            r = super().close(*args, **kwargs)
        except Fault as fault:
            for cnt, entry in enumerate(self.__stack):
                log.error(f'stack frame {cnt}: {entry}')
            raise fault


def main():
    

    with MyServerProxy("http://localhost:8000/", verbose=True) as proxy:
        env = EnvironmentProxyForClient(proxy)
        try:
            env.seed()
            log.info('\nSetup start\n')
            env.setup()
            log.info('\nSetup succeded\n')
            env.reset()
            log.info('\nReset succeded\n')
            r = env.step(.2)
            log.info(f'\nStep succeded {r}\n')
            env.done()
            #log.info('\nDone succeded\n')
        finally:
            log.info('Closing Proxy')
        #    proxy.close()

if __name__ == '__main__':
    main()
