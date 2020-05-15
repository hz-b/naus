'''Proxies for xmlrpc server/clients

Todo:
    review if xmlrpc is an appropriate choice
'''


import logging


logger = logging.getLogger('naus')


class _EnvironmentProxy:
    '''

    Waring:
        review if __getattr__ should check for allowable
        attributes
    '''
    def __init__(self, receiver, *, log=None):
        self._rec = receiver
        if log is None:
            log = logger
        self.log = logger

    @property
    def receiver(self):
        return self._rec

    @receiver.setter
    def receiver(self, rec):
        self._rec = rec

    def __getattr__(self, name):
        return getattr(self._rec, name)


class EnvironmentProxyForServer(_EnvironmentProxy):
    '''Proxy of the environment for the XMLRPC server

    This makes the different method calls, that keras-rl requies
    compatible with xmlrpc.
    '''

    def setup(self, *args, **kwargs):
        self.log.info(f'Setup called with {args} {kwargs}')
        r = self._rec.setup(*args, **kwargs)
        self.log.info(f'Setup called with {args} {kwargs} returned {r}')

    def seed(self, *args, **kwargs):
        '''32 bit integer limit of xml rpc circumvented
        '''
        seed = self._rec.seed(*args, **kwargs)
        assert(len(seed) == 1)
        seed = seed[0]
        r = f'{seed:d}'
        return r

    def reset(self, *args, **kwargs):
        '''
        Sequences to lists
        '''
        r = self._rec.reset(*args, **kwargs)
        r = [float(x) for x in r]
        self.log.debug(f'Reset returned {r}')
        return r

    def step(self, *args, **kwargs):
        '''
        
        Sequences to lists
        '''
        r = self._rec.step(*args, **kwargs)
        state, action, done, info = r
        self.log.debug(f'step returned unconverted {r}')
        state = [float(x) for x in state]
        r = state, action, done, info
        self.log.debug(f'step returned {r}')
        return r

    #def close(self, *args, **kwargs):
    #    r = self._env.close(*args, **kwargs)
    #    self.log.debug(f'close returned {r}')
    #    return r

class EnvironmentProxyForClient(_EnvironmentProxy):
    '''Proxy of the environment for the XMLRPC client

    This makes the different method calls, that keras-rl requies
    compatible with xmlrpc.
    '''
    def seed(self, *args, **kwargs):
        seed = self._rec.seed(*args, **kwargs)
        r = int(seed)
        return r

    def reset(self):
        return self._rec.reset()

    def step(self, actions):
        actions = int(actions)
        return self._rec.step(actions)
    
    def steps_beyond_done(self, *args, **kwargs):
        self.log.debug('Executing steps_beyond_done with {args} {kwargs}')
        return self._rec.steps_beyond_done(*args, **kwargs)


