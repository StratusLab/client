
from .BaseClient import BaseClient
from dirq.QueueSimple import QueueSimple

class DirectoryQueue(BaseClient):
    def __init__(self, configHolder):
        configHolder.assign(self)
        self.queue = QueueSimple(self.msg_queue)

    def send(self, message):
        self.queue.add(message)
