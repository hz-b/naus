from keras.models import Sequential
from keras.layers import Dense, Activation, Flatten
from keras.optimizers import Adam

# from tensorflow.keras.model import Sequential
# from tensorflow.keras.layers import Dense, Activation, Flatten
# from tensorflow.keras.optimizers import Adam

import matplotlib
matplotlib.use('Qt5Agg')
import PyQt5

from rl.agents import SARSAAgent
from rl.policy import BoltzmannQPolicy

from naus.threaded_environment import run_environement
from naus.environment import Environment

from bluesky import RunEngine
from cart_pole_device import CartPole
from cart_pole_environment import CartPoleEnv

import numpy as np
import functools
import logging
logger = logging.getLogger('bact2')


def run_test(actor, env, *, log=None):
    log.info('\nfit start\n')
    # Okay, now it's time to learn something! We visualize the training here for show, but this
    # slows down training quite a lot. You can always safely abort the training prematurely using
    # Ctrl + C.
    actor.fit(env, nb_steps=50000, visualize=False, verbose=2)

    log.info('\nsaving weights\n')
    # After training is done, we save the final weights.
    actor.save_weights('sarsa_{}_weights.h5f'.format(ENV_NAME), overwrite=True)

    log.info('\ntesting evaluation\n')
    # Finally, evaluate our algorithm for 5 episodes.
    actor.test(env, nb_episodes=5, visualize=True)

    # Closing down 
    log.info('\nClosing down\n')
    env.done()
    log.info('\nDone succeded\n')


def main():

    # nb_actions = cpst._action_space
    nb_actions = 2
    # Next, we build a very simple model.
    model = Sequential()
    #n_os = cpst._observation_space.shape

    n_os = 4
    model.add(Flatten(input_shape=[1] +[n_os]))
    model.add(Dense(16))
    model.add(Activation('relu'))
    model.add(Dense(16))
    model.add(Activation('relu'))
    model.add(Dense(16))
    model.add(Activation('relu'))
    model.add(Dense(nb_actions))
    model.add(Activation('linear'))

    print(model.summary())
    model._make_predict_function()

    # SARSA does not require a memory.
    policy = BoltzmannQPolicy()
    sarsa = SARSAAgent(model=model, nb_actions=nb_actions, nb_steps_warmup=10, policy=policy)
    sarsa.compile(Adam(lr=1e-3), metrics=['mae'])

    cart_pole = CartPole(name = 'cp')

    log = logging.getLogger('bact2')

    RE = RunEngine({})
    RE.log.setLevel('DEBUG')
    cart_pole.log = RE.log

    stm = [cart_pole.x, cart_pole.x_dot, cart_pole.theta, cart_pole.theta_dot]
    cpst = CartPoleEnv(detectors=[cart_pole], motors=[cart_pole], 
    state_motors=stm, user_kwargs={'mode_var':cart_pole.rl_mode})

    np.random.seed(123)
    cpst.seed(123)

    partial = functools.partial(run_test, sarsa, cpst, log=RE.log)
    RE(run_environement(cpst, partial, log=RE.log))


if __name__ == '__main__':
    main()
