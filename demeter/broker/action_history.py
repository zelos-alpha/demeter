from demeter.broker.types import BaseAction


class ActionRecorder(object):
    def __init__(self):
        self.history: [BaseAction] = []

    def add_history(self, action: BaseAction):
        self.history.append(action)
