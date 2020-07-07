'''Proxies based on zmq

Purpose:
    See if xmlrpc is a performance bottleneck.
'''

import zmq
import numpy as np
import logging
import itertools

logger = logging.getLogger('naus')

#def array_metadata(A):
#    md = dict(
#        dtype = str(A.dtype),
#        shape = A.shape,
#    )
#    return md


#def send_array(socket, A, flags=0, copy=True, track=False):
#    """send a numpy array with metadata
#
#    Taken from pyzmq documentation
#    """
#    md = array_metadata(A)
#    socket.send_json(md, flags|zmq.SNDMORE)
#    return socket.send(A, flags, copy=copy, track=track)


def _recv_array(socket, metadata, flags=0, copy=False, track=False):
    msg = socket.recv(flags=flags, copy=copy, track=track)
    buf = memoryview(msg)
    A = np.frombuffer(buf, dtype=metadata['A_dtype'])
    return A.reshape(metadata['A_shape'])


#def recv_array(socket, flags=0, copy=True, track=False):
#    """recv a numpy array
#
#    Taken from pyzmq documentation
#    """
#    md = socket.recv_json(flags=flags)
#    return _recv_array(socket, md)


def time_to_expire(max_time, dt=.2, n_max=100):
    import time
    start = time.time()
    end = start + max_time

    for i in range(1, n_max):
        now = time.time()
        expire = start + i * dt

        if expire >= end:
            raise StopIteration

        to_wait = expire - now
        if to_wait < 0.0:
            yield 0.0
        yield to_wait
    else:
        raise AssertionError


class _EnvironmentProxy:

    def __init__(self, receiver, *, port=9998, flags=0, copy=False, track=False,
                 max_time=10,  log=None):
        self._rec = receiver
        if log is None:
            log = logger
        self.log = logger

        self.context = None
        self.socket = None
        self.flags = flags
        self.copy = copy
        self.track = track
        self.port = int(port)
        self.poller_in = None
        self.poller_out = None
        self.max_time = max_time
        self._initConnection()

    def _initConnection(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.poller_in =  zmq.Poller()
        self.poller_in.register(self.socket, zmq.POLLIN)
        self.poller_out =  zmq.Poller()
        self.poller_out.register(self.socket, zmq.POLLOUT)

    @property
    def receiver(self):
        return self._rec

    @receiver.setter
    def receiver(self, rec):
        self._rec = rec

    # def __getattr__(self, name):
    #    return getattr(self._rec, name)

    def sendData(self, md, A):
        flags = self.flags
        if A is None:
            t_flags = flags
            md['has_A'] = False
        else:
            A = np.asarray(A)
            t_flags = flags|zmq.SNDMORE
            md['has_A'] = True
            md['A_dtype'] = str(A.dtype)
            md['A_shape'] = A.shape

        copy = self.copy
        track = self.track
        socket = self.socket

        cls_name = self.__class__.__name__
        self.log.info(f'{cls_name}: Sending data: checking poller {md}')
        max_time = 10
        for dt in time_to_expire(max_time=max_time):
            # self.log.info(f'timeout {dt:.1f} seconds')
            events = self.poller_out.poll(timeout=dt * 1000)
            if len(events) > 0:
                # self.log.info(f'treating send events {events}')
                break
        else:
            raise TimeoutError(f'Poller not ready within {max_time} seconds')

        # self.log.info(f'{cls_name}: sending metadata {md}')
        socket.send_json(md, t_flags)
        # self.log.info(f'{cls_name}: sent metadata {md}')
        if A is not None:
            # self.log.info(f'{cls_name}: sending array {md}')
            socket.send(A, flags, copy=copy, track=track)
            # self.log.info(f'{cls_name}: sent array {md}')

    def receiveData(self):
        flags = self.flags
        copy = self.copy
        track = self.track
        socket = self.socket

        max_time = self.max_time
        for dt in time_to_expire(max_time=max_time):
            # self.log.info(f'timeout {dt:.1f} seconds')
            events = self.poller_in.poll(timeout=dt * 1000)
            if len(events) > 0:
                # self.log.info(f'treating recv events {events}')
                break
        else:
            raise TimeoutError(f'Poller not ready within {max_time} seconds')

        md = socket.recv_json(flags=flags)
        has_A = md['has_A']
        if has_A:
            A = _recv_array(socket, md, flags=flags, track=track, copy=copy)
        else:
            A = None
        return md, A


class EnvironmentProxyForServer(_EnvironmentProxy):
    '''make method calls return xmlrpc compatible
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.command_dic = self._buildCommandDict()

    def _initConnection(self):
        super()._initConnection()
        txt = f"tcp://*:{self.port}"
        cls_name = self.__class__.__name__
        self.log.info(f'{cls_name}: Opening port @ {txt}')
        self.socket.bind(txt)

    def _buildCommandDict(self):
        commands = ['setup', 'step', 'seed', 'reset', 'set_mode']
        d = {cmd : getattr(self, cmd) for cmd in commands}
        return d

    def commandToMethod(self, name):
        '''

        Warning:
            safety critical method
        '''
        method = self.command_dic[name]
        return method

    def process_single(self):
        """
        """
        # Get next command request with metadata
        cls_name = self.__class__.__name__
        md, A = self.receiveData()
        cmd = md['cmd']
        # self.log.info(f'{cls_name}: processing command {cmd}')
        method = self.commandToMethod(cmd)
        try:
            r_md, r_A = method(md, A)
        except Exception as ex:
            txt = f'{cls_name}: command {cmd} raise exeception {ex}'
            self.log.error(txt)
            r_md = dict(exception = ex.__class__.__name__, args=ex.args)
            self.sendData(r_md, None)

        else:
            # self.log.info(f'{cls_name}: command {cmd} returned {r_md}, {r_A}')
            self.sendData(r_md, r_A)

    def loop(self):
        self.log.info('Starting to process commands')
        for cnt in itertools.count():
            # self.log.info(f'Running command No. {cnt}')
            self.process_single()

    def set_mode(self, md, A):
        set_mode = md['set_mode']
        self._rec.set_mode(set_mode)
        return {}, None

    def setup(self, md, A):
        self.log.info(f'Setup')
        assert(A is None)
        r = self._rec.setup()
        A = np.asarray(r)
        self.log.info(f'Setup called with {md} {A} returned {r}')
        return {}, A

    def seed(self, md, A):
        '''
        '''
        assert(A is not None)
        self.log.info(f'seed {A} type {type(A)}')
        seed = int(A)
        seed = self._rec.seed(seed)
        A = np.asarray(seed)
        return {}, seed

    def reset(self, md, A):
        '''

        Sequences to lists
        '''
        assert(A is None)
        r = self._rec.reset()
        A = np.asarray(r)
        # self.log.debug(f'Reset returned {r}')
        return {}, A

    def step(self, md, A):
        '''
        Sequences to lists
        '''
        assert(A is not None)
        actions = A
        r = self._rec.step(actions)
        state, reward, done, info = r
        # self.log.debug(f'step returned unconverted {r}')
        A = np.asarray(state)
        md = dict(done=done, reward=reward, info=info)
        # self.log.debug(f'step returned {r}')
        return md, A

    #def close(self, *args, **kwargs):
    #    r = self._env.close(*args, **kwargs)
    #    self.log.debug(f'close returned {r}')
    #    return r

    def __call__(self):
        return self.loop()

class EnvironmentProxyForClient(_EnvironmentProxy):
    def __init__(self, *args, hostname='127.0.0.1', **kwargs):
        self.hostname = hostname
        super().__init__(*args, **kwargs)

    def _initConnection(self):
        super()._initConnection()
        txt = f"tcp://{self.hostname}:{self.port}"
        cls_name = self.__class__.__name__
        self.log.info(f'{cls_name}: Opening port @ {txt}')
        self.socket.connect(txt)

    def processCommand(self, md, A):
        cls_name = self.__class__.__name__
        # self.log.info(f'{cls_name}: sending command with meta data {md}')
        self.sendData(md, A)

        # self.log.info(f'{cls_name}: waiting for answer')
        md, A = self.receiveData()
        # self.log.info(f'{cls_name}: got answer with meta data {md}')

        try:
            recv_exception = md['exception']
        except KeyError:
            recv_exception = None

        if recv_exception:
            args = md['args']
            txt = f'{cls_name}: received exception {recv_exception} with args {args}'
            self.log.error(txt)
            raise Exception(txt)

        return md, A

    def seed(self, num):
        md = dict(cmd='seed')
        A = np.asarray(num)
        md, A = self.processCommand(md, A)
        return A

    def reset(self):
        md = dict(cmd='reset')
        md, A = self.processCommand(md, None)
        return A

    def step(self, actions):
        md = dict(cmd='step')
        md, A = self.processCommand(md, actions)
        state = A
        reward = md['reward']
        info = md['info']
        done = md['done']
        return state, reward, done, info

    def set_mode(self, val):
        md = dict(cmd='set_mode', set_mode=val)
        md, _ = self.processCommand(md, None)

    #@set_mode.setter
    #def set_mode(self, val):
    #    md = dict(cmd = 'set_mode_put', set_mode=val)
    #    md, _ = self.processCommand(md, None)

    # def steps_beyond_done(self, *args, **kwargs):
    #    self.log.debug('Executing steps_beyond_done with {args} {kwargs}')
    #    return self._rec.steps_beyond_done(*args, **kwargs)
