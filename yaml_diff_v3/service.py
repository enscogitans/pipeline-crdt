from yaml_diff_v3 import crdt_graph, utils, yaml_graph, converter
from yaml_diff_v3.crdt_graph import Timestamp, SessionId


class Service:
    def make_initial_crdt_graph(self, yaml_text: str, ts: Timestamp) -> crdt_graph.Graph:
        yaml_node = yaml_graph.deserialize(utils.loads_yaml_node(yaml_text))
        crdt_node = converter.make_new_crdt_node_from_yaml(yaml_node, ts)
        return crdt_graph.Graph(root=crdt_node)

    def build_local_updates(self, old_graph: crdt_graph.Graph,
                            old_yaml_text: str, new_yaml_text: str,
                            session_id: SessionId, ts: Timestamp) -> list[crdt_graph.Update]:
        old_yaml_node = yaml_graph.deserialize(utils.loads_yaml_node(old_yaml_text))
        new_yaml_node = yaml_graph.deserialize(utils.loads_yaml_node(new_yaml_text))
        yaml_updates = yaml_graph.build_updates(old_yaml_node, new_yaml_node)
        return converter.make_crdt_updates_from_yaml_updates(yaml_updates, session_id, ts, old_graph)

    def apply_updates(self, graph: crdt_graph.Graph, updates: list[crdt_graph.Update],
                      applied_updates: set[crdt_graph.UpdateId]) -> None:
        applier = crdt_graph.UpdatesApplier(applied_updates)
        applier.apply_updates(graph, updates)

    def convert_to_yaml(self, graph: crdt_graph.Graph) -> str:
        yaml_node = converter.crdt_graph_to_yaml_node(graph)
        return utils.dumps_yaml_node(yaml_graph.serialize(yaml_node))

    def merge_with_empty_graph(self, base_yaml_text: str, yaml_text_1: str, yaml_text_2: str) -> str:
        graph = self.make_initial_crdt_graph(base_yaml_text, Timestamp(0))
        updates_1 = self.build_local_updates(graph, base_yaml_text, yaml_text_1, SessionId("session_1"), Timestamp(1))
        updates_2 = self.build_local_updates(graph, base_yaml_text, yaml_text_2, SessionId("session_2"), Timestamp(2))
        self.apply_updates(graph, updates_1 + updates_2, applied_updates=set())
        return self.convert_to_yaml(graph)
