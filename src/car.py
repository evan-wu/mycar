# coding=utf-8
import yaml
import importlib
import ast
from components import Component, CAN, ZmqCAN
import logging
import sys
import os
from threading import Thread
import typing


class Car:
    """
    The main class.
    """

    def __init__(self, config_file):
        """
        Args:
            config_file: YML config file.
        """
        self.components = {}
        self.can = None

        with open(config_file) as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)

        self._parse_config()

    def _parse_config(self):
        """
        Parse the YML config file and add components to the Car.
        """
        logging.info('Parsing config file to add car components...')

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
                comp_instance = self._initialize_component_class(component, classes[0])
                self._add_component(classes[0], comp_instance)
            else:
                for cls in classes:  # multiple classes with concrete class name
                    comp_instance = self._initialize_component_class(component, cls)
                    self._add_component(cls, comp_instance)

        # add 'can' to all components.
        if self.can is None:
            logging.warning('CAN(can) is not defined in config file, components will not be able to communicate!')
        else:
            for comp in self.components.values():
                if isinstance(self.can, ZmqCAN):
                    # add ZmqCAN client to component
                    comp_can = ZmqCAN(server_mode=False)
                    self._start_component(comp_can)
                    comp.can = comp_can
                else:
                    comp.can = self.can

    def _initialize_component_class(self, component_module, class_name):
        component_class = getattr(importlib.import_module('components.' + component_module), class_name)
        if not issubclass(component_class, Component):
            raise TypeError("{} is not a 'Component' subclass!".format(component_class))

        if self.config['components'][component_module] is None:  # empty args
            args = None
        elif class_name in self.config['components'][component_module]:
            args = self.config['components'][component_module][class_name]
        else:
            args = self.config['components'][component_module]

        if args is None:
            comp_instance = component_class()
        else:
            # set component's listening/publishing channels
            subscription = args.pop('subscription', None)
            publication = args.pop('publication', None)
            comp_instance = component_class(**args)
            if subscription is not None:
                comp_instance.subscription.extend(subscription) if isinstance(subscription, typing.Iterable) \
                    else comp_instance.subscription.append(subscription)
            if publication is not None:
                comp_instance.publication.extend(publication) if isinstance(publication, typing.Iterable) \
                    else comp_instance.subscription.append(publication)

        return comp_instance

    def _add_component(self, class_name, component_instance):
        self.components[class_name] = component_instance
        if isinstance(component_instance, CAN):
            if isinstance(component_instance, ZmqCAN):
                if not component_instance.server_mode:
                    raise TypeError('ZmqCAN should be defined as server_mode: True in config file!')

            self.can = component_instance
        logging.info('Added car component - ' + class_name)

    def _start_component(self, comp_instance):
        long_running = comp_instance.start()
        if long_running:
            t = Thread(target=comp_instance.run)
            t.daemon = True
            t.start()

    def start(self):
        """
        Start the Car, which starts all components.
        """
        for comp_instance in self.components.values():
            if comp_instance.can is not None and len(comp_instance.subscription) > 0:
                comp_instance.can.subscribe(comp_instance.subscription, comp_instance.on_message)
            self._start_component(comp_instance)

    def shutdown(self):
        """
        Shutdown the Car, which shutdowns all components.
        """
        for comp_instance in self.components.values():
            comp_instance.shutdown()


def main():
    logging.basicConfig(format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
                        level=logging.INFO)

    if len(sys.argv) < 3:
        print('required config file and ttl to run')
        sys.exit(-1)

    config = sys.argv[1]
    ttl = float(sys.argv[2])

    car = Car(config)
    car.start()
    import time

    time.sleep(ttl)
    car.shutdown()


if __name__ == '__main__':
    main()
