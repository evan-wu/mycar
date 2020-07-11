# coding=utf-8
from components import CAN
import zmq
import types
import pickle
import typing
import logging

logger = logging.getLogger("ZmqCAN")


class ZmqCAN(CAN):
    """
    The ZMQ implementation of CAN.
    Server side: act as a broker to receive and broadcast messages. PUB + PULL
    Client side: subscribe to server side and push messages to server side. SUB + PUSH
    """

    def __init__(self, server_mode: bool):
        super(CAN, self).__init__()
        context = zmq.Context.instance()

        self.server_mode = server_mode
        if server_mode:  # server mode
            pub = context.socket(zmq.PUB)
            pub.bind("tcp://*:6000")
            self.pub = pub

            pull = context.socket(zmq.PULL)
            pull.bind("tcp://*:6001")
            self.pull = pull
        else:  # client mode
            sub = context.socket(zmq.SUB)
            sub.connect("tcp://localhost:6000")
            self.sub = sub

            push = context.socket(zmq.PUSH)
            push.connect("tcp://localhost:6001")
            self.push = push

            # dict of client listeners
            self.listeners = {}

    def start(self) -> bool:
        logger.info("ZMQ ({}) CAN started.".format('server' if self.server_mode else 'client'))
        return True

    def run(self, stop_event):
        if self.server_mode:
            while not stop_event.is_set():
                try:
                    received = self.pull.recv_multipart()
                    self.pub.send_multipart(received)
                except Exception as e:
                    logger.error('Failed to broadcast message', e)
        else:  # client
            while not stop_event.is_set():
                try:
                    events = self.sub.poll(timeout=0.005)
                    for i in range(events):
                        multipart = self.sub.recv_multipart()
                        channel = multipart[0].decode()
                        message = pickle.loads(multipart[1])
                        for listener in self.listeners[channel]:
                            try:
                                listener(channel, message)
                            except Exception as e1:
                                logger.error('{} failed to consume message'.format(listener), e1)
                except Exception as e:
                    logger.error('Failed to consume message', e)

    def publish(self, channel: str, message):
        """
        Publish a message to specified channel.
        """
        if self.server_mode:
            self.pub.send_multipart([channel.encode(), pickle.dumps(message)])
        else:
            self.push.send_multipart([channel.encode(), pickle.dumps(message)])

    def subscribe(self, channels: typing.Iterable, listener: types.MethodType):
        """
        Subscribe to a channel.
        """
        logger.info('subscribe to {}'.format(channels))
        for channel in channels:
            if channel not in self.listeners:
                self.listeners[channel] = [listener]
            else:
                self.listeners[channel].append(listener)
            self.sub.subscribe(channel)
