# coding=utf-8
from components import Component
import types
import typing


class CAN(Component):
    """
    CAN - Controller Area Network.
    The message bus of the Car.
    """

    def publish(self, channel: str, message):
        """
        Publish a message to specified channel.
        message will be serialized and encoded.
        """
        raise TypeError("{} - publish not implemented!")

    def subscribe(self, channels: typing.Iterable, listener: types.MethodType):
        """
        Subscribe to a channel.
        message will be decoded and deserialized.
        """
        raise TypeError("{} - subscribe not implemented!")
