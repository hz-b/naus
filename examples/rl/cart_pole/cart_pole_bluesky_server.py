import matplotlib
matplotlib.use('Qt5Agg')
import PyQt5

import logging
# logging.basicConfig(level='INFO')
# logging.basicConfig(level='DEBUG')

# from bluesky.utils import install_qt_kicker
from naus.threaded_environment import run_environment
from naus.environment_proxy_zmq import EnvironmentProxyForServer
# from naus.xmlrpc_server import setup_xml_server

from bluesky import RunEngine
from bluesky.callbacks import LivePlot, LiveTable
from cart_pole_device import CartPole
from cart_pole_environment import CartPoleEnv

import matplotlib.pyplot as plt


class LivePlotTest(LivePlot):
    '''
    Todo:
        Separate module
        Learn mode level check based on a callback feeding
        Info to a 'standardised device'
    '''
    def __init__(self, *args, rl_learn_state_var='cp_rl_mode', **kwargs):
        super().__init__(*args, **kwargs)
        self.rl_learn_state_var = rl_learn_state_var

    def event(self, doc):
        rl_val = doc['data'][self.rl_learn_state_var]
        if rl_val == 'test':
            return super().event(doc)


def main():

    logger = logging.getLogger('bact2')

    cart_pole = CartPole(name='cp')

    RE = RunEngine({})
    # RE.log.setLevel('DEBUG')
    cart_pole.log = RE.log

    live_plots = True

    if live_plots:
        fig = plt.figure()
        ax = fig.add_subplot(211)
        ax2 = ax.twinx()
        ax3 = fig.add_subplot(212)
        ax4 = ax3.twinx()

    cbs = [
        LiveTable(['cp_rl_mode', 'cp_action', 'cp_x', 'cp_x_dot', 'cp_theta',
                   'cp_theta_dot'])
    ]
    if live_plots:
        cbs = [
            LivePlotTest('cp_action',    color='r', linestyle='-',  ax=ax),
            LivePlotTest('cp_x',         color='b', linestyle='-',  ax=ax2),
            LivePlotTest('cp_theta',     color='g', linestyle='-',  ax=ax3),
            LivePlotTest('cp_x_dot',     color='b', linestyle='--', ax=ax4),
            LivePlotTest('cp_theta_dot', color='g', linestyle='--', ax=ax4),
        ]

    stm = [cart_pole.x, cart_pole.x_dot, cart_pole.theta, cart_pole.theta_dot]
    cpst = CartPoleEnv(detectors=[cart_pole], motors=[cart_pole],
                       state_motors=stm, log=RE.log,
                       user_kwargs={'mode_var': cart_pole.rl_mode})

    server = EnvironmentProxyForServer(receiver=cpst)
    # partial = setup_xml_server(cpst)
    partial = server

    RE.log.info('Handling execution to bluesky')
    RE(
        run_environment(cpst, partial, log=RE.log, n_loops=-1)
        #, cbs
    )
    RE.log.info('Bluesky operation finished')


if __name__ == '__main__':
    plt.ion()
    try:
        main()
    finally:
        plt.ioff()
        plt.show()
        pass
