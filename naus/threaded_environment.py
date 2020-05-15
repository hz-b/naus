from bluesky import plan_stubs as bps, preprocessors as bpp
from bcib import CallbackIteratorBridge
from bcib.threaded_bridge import setup_threaded_callback_iterator_bridge
from bcib.bridge_plan import bridge_plan_stub
from queue import Queue
from threading import Thread
import logging
import itertools

logger = logging.getLogger('bact2')


def run_environement(env, partial, md=None, log=None, n_loops=1):
    '''Plan for executing environement.

    Args:
        env : a instanance of a subclass of
              :class:`naus.environment.Environment`
        n_loops : number of times to execute.
                  if negative run for ever

    This plan expects that env is used as an environement in an
    OpenAI or keras learning environment.

    Warning:
        The learning environment must be executed in an independent
        thread or process.


    Typical usage:

    ::

        bridge = setup_threaded_bridge()

        env = Environment(detectors, motors)
        env.bridge = bridge

        agent = SomeAgent(env)
        def run():
           agent.fit()
           return

        thread = threading.Thread(target=run)
        tread.start()
        RE(brige)
        thread.stop()
    '''


    if log is None:
        log = logger

    # 0 loops or no loops does not make sense ...
    assert(n_loops != 0)

    detectors = list(env.detectors)
    motors = list(env.motors)
    state_motors = list(env.state_motors)
    _md = {
        'detectors': [det.name for det in detectors],
        'plan_args': {
            'environent' : repr(env),
            # All arguments further down should be now in environment
            'detectors' : list(map(repr, detectors)),
            'motors' : list(map(repr, motors)),
            'state_motors' : list(map(repr, state_motors)),
            'per_step_plan' : repr(env.per_step_plan),
            'setup_plan' : repr(env.setup_plan),
            'teardown_plan' : repr(env.teardown_plan),
            'n_loops' : n_loops,
          },
        'plan_name' : 'environement_executor',
        'executor_type' : 'threaded',
        'hints' : {}
    }
    _md.update(md or {})

    clear_method = env.clearLinkToBridge

    objects_all = (detectors + motors + state_motors)
    @bpp.stage_decorator(objects_all)
    @bpp.run_decorator(md=_md)
    def run_inner():
        bridge = setup_threaded_callback_iterator_bridge()
        assert(bridge is not None)

        def run_partial(partial):
            return partial()

        try:
            env.bridge = bridge
            env.bridge

            thread = Thread(target=run_partial, args=[partial], name='run optimiser')
            thread.start()
            log.info(f'run_environement: thread evaluating partial, executing plan')
            for cnt in itertools.count():
                if n_loops < 0 or cnt < n_loops:
                    log.info(f'run_environement: running loop {cnt}')
                    r = (yield from bridge_plan_stub(bridge, log=log))
                    log.info(f'run_environement: loop {cnt} returned {r}')
                else:
                    log.info(f'Finshed evaluations after {cnt} loops')
                    break
        except Exception:
            log.error(f'run_environement: Failed to execute environment {env}')
            raise
        finally:
            log.info(f'run_environement: Finishing processing  {env}')
            thread.join()
            clear_method()
        # thread.join()

        return r

    return (yield from run_inner())
