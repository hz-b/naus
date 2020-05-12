from  naus.environment import Environment
import bluesky.plan_stubs as bps
from cart_pole_physics_model import CartPoleState
from gym.utils import seeding
from gym import spaces
import numpy as np
import functools
import copy

def plan_set_mode(detectors, motors, state_motors, *args, **kwargs):
    print('kwargs', kwargs)
    mode_var = kwargs['mode_var']
    mode = kwargs['mode']

    yield from bps.mv(mode_var, mode)


class CartPoleEnv(Environment):

    _observation_space = np.zeros((4,)) + np.nan
    _action_space = 2 # Why the hell 2?


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.theta_threshold_radians = 12 * 2 * np.pi / 360
        self.x_threshold = 2.4

        self.steps_beyond_done = None

        kwargs = copy.copy(self.user_kwargs)
        # Make sure it is a known keyword argument
        kwargs['mode_var']

         # Angle limit set to 2 * theta_threshold_radians so failing observation is still within bounds
        high = np.array([self.x_threshold * 2,
                         np.finfo(np.float32).max,
                         self.theta_threshold_radians * 2,
                         np.finfo(np.float32).max],
                        dtype=np.float32)

        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(-high, high, dtype=np.float32)

    def set_mode(self, mode):
    
        kwargs = copy.copy(self.user_kwargs)
        # Make sure it is a known keyword argument
        kwargs['mode_var']
        # Make sure it is a known keyword argument
        kwargs['mode'] = mode
        
        cmd = functools.partial(plan_set_mode, self.detectors, self.motors,
                                self.state_motors,
                                *self.user_args, **kwargs)
        self._submit(cmd)


    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        r = [seed]
        self.log.warning(f'Seed {r}')
        return r

    def extractState(self, dic):
        #print('measured', dic)

        dets = self.detectors
        assert(len(dets) == 1)
        det = dets[0]
        det_name = det.name
        try:
            x         = dic[f'{det_name}_x']['value']
        except Exception:
            self.log.error(f'Extraction of {det_name_x} failed from dic {dic}')

        x_dot     = dic[f'{det_name}_x_dot']['value']
        theta     = dic[f'{det_name}_theta']['value']
        theta_dot = dic[f'{det_name}_theta_dot']['value']

        state = CartPoleState(x=x, x_dot=x_dot, theta=theta, theta_dot=theta_dot)
        return state

    def storeInitialState(self, dic):
        state = self.extractState(dic)
        self.state_to_reset_to = state.values

    def getStateToResetTo(self):
        start = self.np_random.uniform(low=-0.05, high=0.05, size=(4,))
        return start

    def computeRewardTerminal(self, dic):

        state = self.extractState(dic)
        x = state.x
        theta = state.theta

        if False:
            done =  x < -self.x_threshold \
                    or x > self.x_threshold \
                    or theta < -self.theta_threshold_radians \
                    or theta > self.theta_threshold_radians
        else:
            done =  x > self.x_threshold \
                    or theta < -self.theta_threshold_radians \
                    or theta > self.theta_threshold_radians

        done = bool(done)

        if not done:
            reward = 1.0
        elif self.steps_beyond_done is None:
            # Pole just fell!
            self.steps_beyond_done = 0
            reward = 1.0
        else:
            if self.steps_beyond_done == 0:
                txt = (
                    """You are calling 'step()' even though this environment
 has already returned done = True. You should always call 'reset()' once you
 receive 'done = True' -- any further steps are undefined behavior."""
                )
                self.log.warn(txt)
            self.steps_beyond_done += 1
            reward = 0.0

        return reward, done

    def computeState(self, dic):
        return self.extractState(dic).values

