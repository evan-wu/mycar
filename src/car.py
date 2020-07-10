# coding=utf-8
import yaml
import importlib
import ast
from components import Component, CAN, ZmqCAN
import logging
import sys
import os
from threading import Thread, Event as TEvent
from multiprocessing import Process, Event as PEvent
import typing
import time

logger = logging.getLogger("Car")


class Car:
    """
    The main class.
    """

    def __init__(self, config_file, ttl):
        """
        Args:
            config_file: YML config file.
        """
        self.components = {}
        self.component_instances = []
        self.can = None
        self.parallel_process = False
        self.stop_event = None
        self.ttl = ttl

        with open(config_file) as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)

        self._parse_config()

    def _parse_config(self):
        """
        Parse the YML config file and add components to the Car.
        """
        logger.info('Parsing config file to add car components...')

        if 'parallel' in self.config and self.config['parallel'] == 'process':
            self.parallel_process = True
            self.stop_event = PEvent()
            logger.info('Using process level parallel for components.')
        else:
            self.parallel_process = False
            self.stop_event = TEvent()

        for component in self.config['components']:
            comp_module = str(component)
            pwd = os.path.abspath('.')
            if pwd.endswith('src'):
                pwd = os.path.abspath('components')
            else:
                pwd = os.path.abspath('src/components')

            with open(pwd + '/' + comp_module + '.py', 'r') as f:
                source = '\n'.join(f.readlines())
                p = ast.parse(source)
                classes = [node.name for node in ast.walk(p) if isinstance(node, ast.ClassDef)]
            if len(classes) == 0:
                raise ValueError("submodule '{}' contains no component class!".format(comp_module))

            if len(classes) == 1:  # only 1 class defined
                self._add_component(component, classes[0])
            else:
                for cls in classes:  # multiple classes within module
                    if cls in self.config['components'][component]:
                        self._add_component(component, cls)

    def _add_component(self, component_module, component_class_name):
        component_class = getattr(importlib.import_module('components.' + component_module), component_class_name)
        if not issubclass(component_class, Component):
            raise TypeError("{} is not a 'Component' subclass!".format(component_class))

        # get args dict
        if self.config['components'][component_module] is None:  # empty args
            args = {}
        elif component_class_name in self.config['components'][component_module]:
            args = self.config['components'][component_module][component_class_name]
        else:
            args = self.config['components'][component_module]

        self.components[component_class] = args

        if issubclass(component_class, CAN):
            self.can = component_class

        logger.info('Added car component - ' + component_class_name)

    @staticmethod
    def _inner_start_component(component_class, args, can_instance_or_class, can_args, stop_event):
        subscription = args.pop('subscription', [])
        publication = args.pop('publication', [])

        # create component instance
        comp_instance = component_class(**args)

        # do subscription
        if not issubclass(component_class, CAN) and can_instance_or_class is not None:
            if issubclass(can_instance_or_class, ZmqCAN):
                comp_instance.can = ZmqCAN(False)  # ZmqCAN client
                comp_instance.can.start()
                can_thread = Thread(name='{}-CAN_client-run'.format(component_class.__name__),
                                    target=comp_instance.can.run,
                                    args=(stop_event,))
                can_thread.start()
            elif isinstance(can_instance_or_class, CAN):  # object
                comp_instance.can = can_instance_or_class
            else:  # class
                comp_instance.can = can_instance_or_class(**can_args)
                comp_instance.can.start()
                can_thread = Thread(name='{}-CAN-run'.format(can_instance_or_class.__name__),
                                    target=comp_instance.can.run,
                                    args=(stop_event,))
                can_thread.start()

            # set component's listening/publishing channels
            comp_instance.subscription.extend(subscription) if isinstance(subscription, typing.Iterable) \
                else comp_instance.subscription.append(subscription)
            comp_instance.publication.extend(publication) if isinstance(publication, typing.Iterable) \
                else comp_instance.subscription.append(publication)

            if len(comp_instance.subscription) > 0:
                comp_instance.can.subscribe(comp_instance.subscription, comp_instance.on_message)

        if comp_instance.start():
            t = Thread(name='{}-run'.format(component_class.__name__),
                       target=comp_instance.run,
                       args=(stop_event,),
                       daemon=True)
            t.start()
        return comp_instance

    def _start_component(self, component_class, args, can_instance_or_class, can_args) -> object:
        logger.info('Starting {}'.format(component_class))

        if not self.parallel_process:
            return Car._inner_start_component(component_class, args, can_instance_or_class, can_args, self.stop_event)
        else:
            def run_in_process(comp_class, comp_args, can_class, can_args, stop_event):
                comp_instance = Car._inner_start_component(comp_class, comp_args, can_class, can_args, stop_event)
                time.sleep(self.ttl)
                comp_instance.shutdown()

            p = Process(name='{}'.format(component_class),
                        target=run_in_process,
                        args=(component_class, args, can_instance_or_class, can_args, self.stop_event,),
                        daemon=True)
            p.start()
            return None

    def start(self):
        """
        Start the Car, which starts all components.
        """
        # if a shared CAN, start it first
        can_args = None
        if self.can is not None:
            can_class = self.can
            can_args = self.components.pop(self.can)
            if issubclass(can_class, ZmqCAN):
                # ZmqCAN server
                if not can_args.get('server_mode'):
                    raise ValueError('ZmqCAN should be configured with server_mode: true')

                self._start_component(can_class, can_args, None, None)
            elif not self.parallel_process:
                # shared CAN
                self.can = self._start_component(can_class, can_args, None, None)

        for component_class, args in self.components.items():
            comp = self._start_component(component_class, args, self.can, can_args)
            if comp is not None:
                self.component_instances.append(comp)

    def shutdown(self):
        """
        Shutdown the Car, which shutdowns all components.
        """
        logger.info('Car shutdown...')
        self.stop_event.set()
        time.sleep(1)
        for comp in self.component_instances:
            comp.shutdown()


def main():
    logging.basicConfig(format='%(asctime)s:%(name)s:%(threadName)s:%(levelname)s: %(message)s',
                        level=logging.INFO)

    if len(sys.argv) < 3:
        print('required config file and ttl to run')
        sys.exit(-1)

    config = sys.argv[1]
    ttl = float(sys.argv[2])

    car = Car(config, ttl)
    car.start()

    time.sleep(ttl)
    car.shutdown()
    time.sleep(1)


if __name__ == '__main__':
    main()
