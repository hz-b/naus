from cart_pole_physics_model import CartPoleState, CartPolePhysics
from ophyd import Component as Cpt, Device, Signal
from ophyd.status import AndStatus

from numpy import nan


class CartPole(Device):
    '''
    '''
    action    = Cpt(Signal, name='action',    value=nan)
    x         = Cpt(Signal, name='x',         value=nan)
    x_dot     = Cpt(Signal, name='x_dot',     value=nan)
    theta     = Cpt(Signal, name='theta',     value=nan)
    theta_dot = Cpt(Signal, name='theta_dot', value=nan)

    # Mode of evaluation
    rl_mode   = Cpt(Signal, name='mode', value='unknown')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.physics_model = CartPolePhysics()

    def set(self, action):
        self.log.debug(f'Setting cartpole to {action}')

        stat_a = self.action.set(action)
        state = CartPoleState(x=self.x.get(), x_dot=self.x_dot.get(),
                              theta=self.theta.get(),
                              theta_dot=self.theta_dot.get())
        n_state = self.physics_model(state, action)

        stat_set = AndStatus(
            AndStatus(
                self.x.set(n_state.x),
                self.x_dot.set(n_state.x_dot)
            ),
            AndStatus(
                self.theta.set(n_state.theta),
                self.theta_dot.set(n_state.theta_dot)
            )
        )
        status = AndStatus(stat_a, stat_set)
        self.log.debug(f'Cartpole finished {action}')
        return status

    def read(self):
        d = super().read()
        self.log.debug(f'Cart pool read {d}')
        return d
