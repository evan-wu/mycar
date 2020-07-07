# coding=utf-8
import logging


class Component(object):
    """
    Super class of all Car components.
    All components can receive interested messages and publish output messages.
    """

    def __init__(self):
        self.subscription = []
        self.publication = []
        self.can = None
        self._channel_num_warned = False

    def start(self) -> bool:
        """
        Start the component. If the component has long running job to do,
        it should return True, and the 'run()' method will be run in separated thread/process.
        """
        raise TypeError("{} - 'start' method not implemented!".format(self))

    def run(self):
        """
        [Optional] Long running job.
        """
        pass

    def shutdown(self):
        raise TypeError("{} - 'shutdown' method not implemented!".format(self))

    def on_message(self, channel, content):
        """
        Message received from subscribed CAN channel.
        The implementation should not block or take too long to execute.
        """
        raise TypeError(
            "{} - subscribed to channel: '{}', but 'on_message' method not implemented!".format(self, channel))

    def publish_message(self, *content):
        """
        Publish message(s) to the pre-defined channel(s).
        Note: If publish to multiple channels, the content order should be the same as the output channels' name
        """
        if self.can is None:
            raise ValueError("{} - can not publish message without 'CAN' defined in config file.".format(self))

        if len(self.publication) != len(content) and not self._channel_num_warned:
            logging.warning("{} - {} of message(s) to publish, but there is {} pre-defined publication channel(s)."
                            .format(self, len(content), len(self.publication)))
            self._channel_num_warned = True

        for i in range(len(self.publication)):
            self.can.publish(self.publication[i], content[i])
