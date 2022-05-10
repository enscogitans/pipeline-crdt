class Topic:
    def __init__(self):
        self.messages = []
        self.curr_idx = 0

    def get_next_message(self):
        if self.curr_idx == len(self.messages):
            return None
        msg = self.messages[self.curr_idx]
        self.curr_idx += 1
        return msg

    def add_message(self, msg):
        self.messages.append(msg)


class DataBroker:
    def __init__(self, n_replicas):
        self.topics = [Topic() for _ in range(n_replicas)]

    def broadcast(self, replica_no, msg):
        for i, topic in enumerate(self.topics):
            if i != replica_no:
                topic.add_message(msg)

    def read_next(self, replica_no):
        topic = self.topics[replica_no]
        res = []
        while True:
            msg = topic.get_next_message()
            if msg is None:
                break
            res.append(msg)
        return res


class Replica:
    def __init__(self, replica_no, broker, graph_state):
        self.replica_no = replica_no
        self.broker = broker
        self.state = graph_state
        self.pending_updates = []

    def apply_local(self, upd):
        upd.prepare(self.state)
        upd.effect(self.state)
        self.broker.broadcast(self.replica_no, upd)

    def apply_remote(self):
        for i, upd in enumerate(self.pending_updates):
            upd.effect(self.state)
        self.pending_updates = []

    def fetch_remote(self):
        new_updates = [upd for upd in self.broker.read_next(self.replica_no)]
        self.pending_updates += new_updates
        return len(new_updates)
