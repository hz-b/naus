Using naus
==========

Using naus is considered by the author more complex than it should be.
It depends on the following non standard module:

    * bcib

Typically a user will define his own environment by subclassing from
:class:`naus.environment.Environment`. Typically one has to overload
the abstract methods. Then an instance is created using the required

* detectors
* motors
* state_motors

Each action is applied to one motor. If this is not compliant to the
use case, a per_step_plan needs to be implemented. See
:func:`naus.environment.Environment` for the signature of the function.
The `state_motors` are used for resetting the state at the (beginning ?)
of each epoc.

The bluesky run engine has to run in a different processes than the
keras-rl agent. These have to be started by the user.

Typical usage for the bluesky engine is then :

::

    from naus.threaded_environment import run_environment
    from naus.environment import Environment
    from naus.xmlrpc_server import setup_xml_server

    class UserENV(Environment):
        '''
        Required implementations of overloaded abstract methods not
        shown
        '''

    partial = setup_xml_server(cpst)

    RE.log.info('Handling execution to bluesky')
    RE(run_environment(cpst, partial, log=RE.log, n_loops=-1), cbs)


On the server side keras-rl has to be set up. This is not described here.
The following steps are required to be able to call to the xmlrpc server

::

    from xmlrpc.client import ServerProxy
    from naus.environment_proxy import EnvironmentProxyForClient

    with ServerProxy("http://127.0.0.1:8000/", verbose=False, allow_none=True) as proxy:
        env = EnvironmentProxyForClient(proxy)

        # pass environment to agent
        # make your agent calls

Todo:
    Consider if the setup of the server could be done automatically by the
    bluesky compatible plan stub :func:`naus.threaded_environment.run_environment`
