import logging
# logging.basicConfig(level='DEBUG')

from keras.models import Sequential
from keras.layers import Dense, Activation, Flatten
from keras.optimizers import Adam

from rl.agents import SARSAAgent
from rl.policy import BoltzmannQPolicy

# from xmlrpc.client import ServerProxy
# from naus.environment_proxy import EnvironmentProxyForClient
from naus.environment_proxy_zmq import EnvironmentProxyForClient
ENV_NAME = 'CartPole-v0'

from zmq.utils.win32 import allow_interrupt

# Get the environment and extract the number of actions.
import numpy as np
import logging
# logging.basicConfig(level='INFO')

log = logging.getLogger('naus')



def run_test(actor, env, *, log=None):
    log.info('\nreset\n')
    env.reset()
    log.info('\nfit start\n')
    # Okay, now it's time to learn something! We visualize the training here for show, but this
    # slows down training quite a lot. You can always safely abort the training prematurely using
    # Ctrl + C.
    env.set_mode('fit')
    actor.fit(env, nb_steps=50000, visualize=False, verbose=2)
    #actor.fit(env, nb_steps=500, visualize=False, verbose=2)

    log.info('\nsaving weights\n')
    # After training is done, we save the final weights.
    actor.save_weights('sarsa_{}_weights.h5f'.format(ENV_NAME), overwrite=True)

    log.info('\ntesting evaluation\n')
    # Finally, evaluate our algorithm for 5 episodes.
    env.set_mode('test')
    actor.test(env, nb_episodes=5, visualize=False)

    # Closing down
    log.info('\nClosing down\n')
    env.done()
    log.info('\nDone succeded\n')

def main():
    # with ServerProxy("http://127.0.0.1:8000/", verbose=False, allow_none=True) as proxy:
    if True:
        pass

    #D:\Devel\github\keras-rl;D:\Devel\github\Devel\hz-b\naus
    # set PYTHONPATH=D:\Devel\github\keras-rl;D:\Devel\github\Devel\hz-b\naus
    # & python d:\Devel\github\Devel\hz-b\naus\examples\rl\cart_pole\sarsa_cartpole.py

    def stop_my_application():
        print('Stopping application')

    with allow_interrupt():
        # main polling loop.

        env = EnvironmentProxyForClient(receiver=None)
        np.random.seed(1974)
        env.seed(1974)

        env.reset()

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

        # SARSA does not require a memory.
        policy = BoltzmannQPolicy()
        sarsa = SARSAAgent(model=model, nb_actions=nb_actions, nb_steps_warmup=10, policy=policy)
        sarsa.compile(Adam(lr=1e-3), metrics=['mae'])

        run_test(sarsa, env, log=log)


if __name__ == '__main__':
    print("Starting")
    main()
    print("Done")
