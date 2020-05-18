from .environment_proxy import EnvironmentProxyForServer
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import logging
import functools

logger = logging.getLogger('naus')


# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)


def setup_xml_server(environment, log=None, server_log_requests=False):
    '''Returns a closure for setting up the xmlrpc server

    Args:
       environment:         an instance of
                            :class:`naus.environment.Environment`
       log:                 a :class:`logging.Logger` instance
       server_log_requests: shall server requests be logged

    Returns:
       a :any:`functools.partial` lambda function for starting and
       running the server.
    '''
    if log is None:
        log = logger

    proxy = EnvironmentProxyForServer(environment)

    def run_test(proxy, *, log=None):
        '''run proxy server

        Todo:
            allow self shutdown on server request
            Separate implementation in an independent module
        '''

        with SimpleXMLRPCServer(('127.0.0.1', 8000),
                                logRequests=server_log_requests,
                                allow_none=True,
                                # requestHandler=RequestHandler
                                ) as server:
            server.register_introspection_functions()
            server.register_instance(proxy)
            server.allow_none = True

            log.info(f'XML Server running env = {proxy.__class__.__name__}')
            # Run the server's main loop
            server.serve_forever()
        log.info('XML Server stopped')

    partial = functools.partial(run_test, proxy, log=log)
    return partial
