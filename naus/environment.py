'''OpenAI compatible environment

Todo:
    This module does not need to depend on bluesky if the plans
    are put in a separate module
'''

from bluesky import plan_stubs as bps, preprocessors as bpp
import super_state_machine.machines

from abc import abstractmethod
import functools
import enum
import logging
logger = logging.getLogger('naus')


def per_step_plan(detectors, motors, actions, *args, log=None, **kwargs):
    '''execute one step and return detecors readings

    Applies the actions to the motors and reads the detectors.

    Args:
        detectors: detectors to read from
        motors:    motors to apply the actions to
        actions:   keras-rl requested actions

    Returns:
        the detector readings.
    '''
    if log is None:
        log = logger

    motors = list(motors)
    action = list(actions)

    # There should be a func
    ml = []
    for m, a in zip(motors, action):
        ml.extend([m, a])
    args = tuple(ml)

    log.debug(f'Executing move (bps.mv) {args}')
    yield from bps.mv(*args)

    r = (yield from bps.trigger_and_read(detectors))
    log.debug(f'Read {detectors} to {r}')

    return r


def setup_plan(detectors, motors, *args, log=None, **kwargs):
    '''retrieve the actual status

    Reads the detectors and returns the state

    Args:
        detectors: detectors to read from

    Motors are passed for convenience for a user that intends to
    implement his own plan.
    '''
    if log is None:
        log = logger

    yield from bps.checkpoint()
    log.info(f'Reading detectors {detectors}')
    r = (yield from bps.trigger_and_read(detectors))
    log.info(f'setup returned {r}')
    return r


def reset_plan(detectors, state_motors, saved_state, *args, log=None,
               **kwargs):
    '''plan to revert environment to original state

    Uses :func:`per_step_plan`. Passes the `state_motors`
    as motors and the `saved_state` as actions.
    '''
    if log is None:
        log = logger

    log.info(
        f'Executing reset plan on {state_motors} and saved_state {saved_state}'
    )
    r = (yield from per_step_plan(detectors, state_motors, saved_state))
    log.info(f'Reset plan read {r}')
    return r


def teardown_plan(detectors, motors, actions, state_motors, state_actions,
                  *args, log=None, **kwargs):
    '''Typically: nothing to do

    Args:
        detectors: the detectors registered to the environment

    Todo:
        Consider resetting to original state
    '''
    if log is None:
        log = logger


class EnvironmentState(super_state_machine.machines.StateMachine):
    '''State the environment is currently in.

    Mainly used for cross checking purposes.
    '''
    class States(enum.Enum):
        UNDEFINED = 'undefined'
        SETUP = 'setting_up'
        TEARDOWN = 'tearing_down'
        RESETTING = 'resetting'
        INITIALISED = 'initialised'
        STEPPING = 'stepping'
        DONE = 'done'
        FAILED = 'failed'

    class Meta:
        initial_state = 'undefined'
        transitions = {
            'undefined':    ['resetting', 'setting_up', 'tearing_down', 'failed'],
            'setting_up':   ['initialised', 'tearing_down', 'failed'],
            'resetting':    ['initialised', 'tearing_down', 'failed'],
            'initialised':  ['stepping',   'done', 'resetting', 'tearing_down', 'failed'],
            'stepping':     ['stepping',   'done', 'resetting', 'tearing_down', 'failed'],
            'done':         ['setting_up', 'done', 'resetting', 'tearing_down', 'failed'],
            'tearing_down': ['undefined', 'failed'],
            'failed':       ['undefined', 'resetting', 'tearing_down', 'failed'],
        }


class Environment:
    '''OpenAI environment emitting bluesky plans for real measurements

    Args:
        detectors :    detectors to use in the plan
        motors :       motors (or actuators) to use in each step.
                    (see also argument per_step_plan)
        state_motors : motors (or actuators) to reset the state to
                    the original state (see reset_plan)

    It uses the motors to execute the actions requested. At each
    step it hands the motors and detectors to the per_step plan.
    From the retrieved documents reward and terminus have to be
    extracted (see appropriate methods which have to be
    overloaded below).

    Every time an epoc shall be reset, the reset_plan is
    executed. Appropriate methods are provided for defining this
    state and passing it to the reset_plan.

    Furthermore a tear_down plan can be provided. This can be used
    for shutting off any devices at the end in a controlled
    fashion.

    A user has to derive its own environment by overloading the
    following methods:

    * :meth:`storeInitialState`: this shall store the state the
      environement shall be reset for every epoch. When a reset is
      requested, the reset_plan is executed. This defaults to
      :func:`reset_plan`. It will be passed the declared detectors
      and motors.

    * :meth:`getStateToResetTo`: this shall provide the info of
      the reset state. ITs return value will be handed over to
      :func:`reset_plan` as `saved_state` argument.

    * :meth:`computeState`: It gets the information acquired
      during the per_step_plan. This method needs to extract the
      values as required by keras-rl.

    * :meth:`computeRewardTerminal`: This is called after each
      step. It must return the reward of the last step and if the
      epoch has terminated.

    Finally the user has to assign a
    :class:`bcib.CallbackIteratorBridge` to the .bridge attribute
    unless you use
    :func:`naus.threaded_environment.run_environment`.
    '''
    def __init__(self, *, detectors, motors, state_motors, log=None,
                 per_step_plan=per_step_plan,
                 reset_plan=reset_plan,
                 setup_plan=setup_plan,
                 teardown_plan=teardown_plan,
                 user_args=(),
                 user_kwargs={},
                 plan_bridge=None,
    ):
        '''
        Todo:
           Ensure that all motors are also in the detectors
        '''

        self.detectors = detectors
        self.motors = motors
        self.state_motors = state_motors

        if log is None:
            log = logger
        self.log = log

        self.per_step_plan = per_step_plan
        self.reset_plan = reset_plan
        self.setup_plan = setup_plan
        self.teardown_plan = teardown_plan

        user_kwargs.setdefault('log', log)
        self.user_args = user_args
        self.user_kwargs = user_kwargs

        self.state_to_reset_to = None

        self._bridge = plan_bridge

        self.state = EnvironmentState()

    #-------------------------------------------------------------------------
    # Methods to override in a derived class
    @abstractmethod
    def storeInitialState(self, dic):
        '''Extract the initial state read back from the device

        dic :
            the dictonary as read from the devices

        Typical implementation: identify the set values of the motors in the
        devices. Store them in the order as found in self.motors
        '''
        cls_name = self.__class__.__name__
        m_name = 'storeInitialState'
        raise NotImplementedError(f'{cls_name}.{m_name} implement in derived class')
        # Extract the data you require to reset to
        self.state_to_reset_to

    @abstractmethod
    def getStateToResetTo(self):
        '''State to reset environment to

        Typically returns the state stored by storeInitialState
        Please note that the diconary returned by storeInitialState
        will contain much more information than just the settings
        of the motors
        '''
        cls_name = self.__class__.__name__
        m_name = 'getStateToResetTo'
        raise NotImplementedError(f'{cls_name}.{m_name} implement in derived class')
        return self.state_to_reset_to

    @abstractmethod
    def computeState(self, dic):
        '''Compute state from data obtained in Dictonary

        Args:
            dic : a dictionary passed back by the sink of the
                per_step_plan

        Returns:
            state: current state to be returned to OpenAI
                typically a vector of floats.

        If the default per_step_plan is used dic will contain the
        data read back from all detectors
        '''
        cls_name = self.__class__.__name__
        m_name = 'computeState'
        raise NotImplementedError(f'{cls_name}.{m_name} implement in derived class')
        state = None
        return state

    @abstractmethod
    def computeRewardTerminal(self, d):
        '''Compute reward and terminal from state d

        Args:
            d: a dictionary containing the result

        Returns:
            reward (float): The reward of the observer
            terminal (bool): Whether the observation ends the episode.

        If the default per_step_plan is used dic will contain the
        data read back from all detectors
        '''
        cls_name = self.__class__.__name__
        m_name = 'computeRewardTerminal'
        raise NotImplementedError(f'{cls_name}.{m_name} implement in derived class')

        reward = None
        terminal = None
        return reward, reward

    def checkOnStart(self):
        '''

        Todo:
            What must be done here?
        '''

    # -------------------------------------------------------------------------
    # Methods expected by the OpenAI solvers
    def setup(self):
        '''Execute start plan and store the state

        Will read the device and handle the output dictionary to
        :meth:`storeInitialState`.

        '''
        self.state.set_setting_up()
        cmd = functools.partial(self.setup_plan, self.detectors, self.motors,
                                self.user_args, self.user_kwargs)
        cls_name = self.__class__.__name__
        # self.log.debug(f'{cls_name}.setup: submitting command {cmd}')
        r = self._submit(cmd)
        self.storeInitialState(r)
        self.state.set_initialised()

    def close(self):
        '''What to emit to the run engine?
        '''
        self.state.set_tearing_down()
        reset_state = self.getStateToResetTo()
        cmd = functools.partial(self.teardown_plan, self.detectors, self.motors,
                                self.state_motors, reset_state,
                                self.user_args, self.user_kwargs)
        self._submit(cmd)

        # Inform bluesky that we are done ...
        self._bridge.stopDelegation()
        self.state.set_undefined()

    def done(self):
        self._bridge.stopDelegation()
        self.state.set_done()

    def step(self, actions):
        """Run one time step of the environment's dynamics.

        Accepts an action and returns a tuple
        (observation, reward, done, info).

        Args:
            action (object): An action provided by the environment.

        Returns:
            observation (object): Agent's observation of the
                                  current environment.

            reward (float):       Amount of reward returned after
                                  previous action.

            done (boolean):       Whether the episode has ended,
                                  in which case further step()
                                  calls will return undefined
                                  results.

            info (dict):          Contains auxiliary diagnostic
                                  information (helpful for
                                  debugging, and sometimes
                                  learning).
        """

        self.state.set_stepping()

        lm = len(self.motors)
        try:
            if lm == 1:
                # Should be float compatible
                float(actions)
                actions = [actions]

            la = len(actions)
            lm = len(self.motors)

            if la != lm:
                txt = (
                    f'At each step I expect {lm} = number of motors actions'
                    f' but got only {la} actions'
                    )
                raise AssertionError(txt)
        except Exception:
            self.state.set_stepping()
            self.bridge.stopDelegation()
            raise

        cmd = functools.partial(self.per_step_plan, self.detectors,
                                self.motors, actions,
                                *self.user_args, **self.user_kwargs)
        # self.log.debug(f'step executing command {cmd}')
        r_dic = self._submit(cmd)

        # Process result
        state = self.computeState(r_dic)
        reward, done = self.computeRewardTerminal(r_dic)
        info = {}
        if done:
            self.state.set_done()
        return state, reward, done, info

    def reset(self):
        '''

        Todo:
            The device should now what its inital state was.
            What's the bluesky equivalent to this call
        '''
        self.state.set_resetting()
        reset_state = self.getStateToResetTo()

        assert(self.state_motors is not None)
        assert(self.detectors is not None)

        # self.log.warning(f'reset: Starting to apply plan {self.user_kwargs}')
        cmd = functools.partial(self.reset_plan, self.detectors,
                                self.state_motors, reset_state,
                                *self.user_args, **self.user_kwargs)
        # Process result
        r_dic = self._submit(cmd)
        # self.log.warning('reset: Applied plan')

        # Translate it to a state
        #self.log.warning(f'reset: computing state {r_dic}')
        state = self.computeState(r_dic)
        # self.log.warning(f'reset: computed state {state}')
        assert(state is not None)
        self.state.set_initialised()
        return state

    def __enter__(self):
        """Support with-statement for the environment. """
        self.checkOnStart()
        return self

    def __exit__(self, *args):
        """Support with-statement for the environment. """
        self.close()
        # propagate exception
        return False

    def __repr__(self):
        cls_name = self.__class__.__name__
        txt = (
            f'{cls_name}('
            f'detectors={self.detectors}, motors={self.motors}'
            f' per_step_plan={self.per_step_plan},'
            f' reset_plan={self.reset_plan},'
            f' setup_plan={self.setup_plan},'
            f' teardown_plan={self.teardown_plan},'
            f' bridge={self._bridge},'
            f' user_args={self.user_args}'
            f' user_kwargs={self.user_kwargs}'
            ')'
        )
        return txt

    def _submit(self, cmd):
        assert(not self.state.is_failed)
        if self._bridge is None:
            raise AssertionError('bridge obj is None')
        try:
            r = self._bridge.submit(cmd)
        except Exception:
            self.state.set_failed()
            self._bridge.stopDelegation()
            raise
        return r

    @property
    def bridge(self):
        assert(self._bridge is not None)
        return self._bridge

    @bridge.setter
    def bridge(self, obj):
        assert(obj is not None)
        assert(callable(obj.submit))
        assert(callable(obj.stopDelegation))
        self.log.info(f'Replacing bridge {self._bridge} with {obj}')
        self._bridge = obj

    def clearLinkToBridge(self):
        self.log.info(f'Clearing link to bridge {self._bridge}')
        self._bridge = None
