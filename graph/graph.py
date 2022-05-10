import abc
import uuid


class Node:
    def __init__(self, key):
        self.key = key
        self.node_id = uuid.uuid4()

    def __eq__(self, other):
        return (self.key, self.node_id) == (other.key, other.node_id)

    def __hash__(self):
        return hash(self.node_id)


class Edge:
    def __init__(self, src_key, dst_key):
        self.src_key = src_key
        self.dst_key = dst_key
        self.edge_id = uuid.uuid4()

    def __eq__(self, other):
        return (self.src_key, self.dst_key, self.edge_id) == (other.src_key, other.dst_key, other.edge_id)

    def __hash__(self):
        return hash(self.edge_id)


class GraphState:
    def __init__(self, *, node_keys=None, edges_keys=None):
        self.nodes = set()
        self.edges = set()
        if node_keys is not None:
            self.nodes = {Node(key) for key in node_keys}
        if edges_keys is not None:
            self.edges = {Edge(src_key, dst_key) for (src_key, dst_key) in edges_keys}

    def copy(self):
        state = GraphState()
        state.nodes = set(self.nodes)
        state.edges = set(self.edges)
        return state

    def has_node(self, key):
        return any(node.key == key for node in self.nodes)

    def has_edge(self, src_key, dst_key):
        return (
            self.has_node(src_key) and self.has_node(dst_key)
            and any((edge.src_key, edge.dst_key) == (src_key, dst_key) for edge in self.edges)
        )

    def has_outgoing_edge(self, src_key):
        return any(src_key == edge.src_key for edge in self.edges)

    def get_nodes(self):
        return {node.key for node in self.nodes}

    def get_edges(self):
        nodes = self.get_nodes()
        return {
            (edge.src_key, edge.dst_key) for edge in self.edges if edge.src_key in nodes and edge.dst_key in nodes
        }

    def __eq__(self, other):
        return (self.get_nodes(), self.get_edges()) == (other.get_nodes(), other.get_edges())


class Update(abc.ABC):
    @abc.abstractmethod
    def prepare(self, graph_state) -> None: ...

    @abc.abstractmethod
    def effect(self, graph_state) -> None: ...


class AddNode(Update):
    def __init__(self, key):
        super().__init__()
        self.key = key
        self._node = None

    def prepare(self, graph_state) -> None:
        assert self._node is None
        self._node = Node(self.key)

    def effect(self, graph_state) -> None:
        graph_state.nodes.add(self._node)


class EraseNode(Update):
    def __init__(self, key):
        super().__init__()
        self.key = key
        self._nodes = None

    def prepare(self, graph_state) -> None:
        assert graph_state.has_node(self.key)
        assert not graph_state.has_outgoing_edge(self.key)
        assert self._nodes is None
        self._nodes = {node for node in graph_state.nodes if node.key == self.key}

    def effect(self, graph_state) -> None:
        graph_state.nodes -= self._nodes


class AddEdge(Update):
    def __init__(self, src_key, dst_key):
        super().__init__()
        self.src_key = src_key
        self.dst_key = dst_key
        self._edge = None

    def prepare(self, graph_state) -> None:
        assert graph_state.has_node(self.src_key)
        assert self._edge is None
        self._edge = Edge(self.src_key, self.dst_key)

    def effect(self, graph_state) -> None:
        graph_state.edges.add(self._edge)


class EraseEdge(Update):
    def __init__(self, src_key, dst_key):
        super().__init__()
        self.src_key = src_key
        self.dst_key = dst_key
        self._edges = None

    def prepare(self, graph_state) -> None:
        assert graph_state.has_edge(self.src_key, self.dst_key)
        assert self._edges is None
        self._edges = {
            edge for edge in graph_state.edges if (edge.src_key, edge.dst_key) == (self.src_key, self.dst_key)
        }

    def effect(self, graph_state) -> None:
        graph_state.edges -= self._edges
