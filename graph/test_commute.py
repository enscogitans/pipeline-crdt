import graph as g
import replica as r


def test_add_node_commute():
    broker = r.DataBroker(2)
    state = g.GraphState()
    replica_1 = r.Replica(0, broker, state.copy())
    replica_2 = r.Replica(1, broker, state.copy())

    replica_1.apply_local(g.AddNode(1))
    replica_2.apply_local(g.AddNode(2))

    assert replica_1.fetch_remote() == 1
    replica_1.apply_remote()
    assert replica_2.fetch_remote() == 1
    replica_2.apply_remote()

    assert replica_1.state == replica_2.state
    assert replica_1.state.get_nodes() == {1, 2}
    assert replica_1.state.get_edges() == set()


def test_add_edge_commute():
    broker = r.DataBroker(3)
    state = g.GraphState(node_keys=[1, 2, 3])
    replica_1 = r.Replica(0, broker, state.copy())
    replica_2 = r.Replica(1, broker, state.copy())
    replica_3 = r.Replica(2, broker, state.copy())

    replica_1.apply_local(g.AddEdge(1, 2))
    replica_2.apply_local(g.AddEdge(1, 2))
    replica_3.apply_local(g.AddEdge(3, 1))

    assert replica_1.fetch_remote() == 2
    assert replica_2.fetch_remote() == 2
    assert replica_3.fetch_remote() == 2
    replica_1.apply_remote()
    replica_2.apply_remote()
    replica_3.apply_remote()

    assert replica_1.state == replica_2.state == replica_3.state
    assert replica_1.state.get_nodes() == {1, 2, 3}
    assert replica_1.state.get_edges() == {(1, 2), (3, 1)}


def test_erase_node_commute():
    broker = r.DataBroker(2)
    state = g.GraphState(node_keys=[1, 2, 3])
    replica_1 = r.Replica(0, broker, state.copy())
    replica_2 = r.Replica(1, broker, state.copy())

    replica_1.apply_local(g.EraseNode(1))
    replica_1.apply_local(g.EraseNode(2))
    replica_2.apply_local(g.EraseNode(1))

    assert replica_1.fetch_remote() == 1
    assert replica_2.fetch_remote() == 2

    replica_1.apply_remote()
    replica_2.apply_remote()

    assert replica_1.state == replica_2.state
    assert replica_1.state.get_nodes() == {3}
    assert replica_1.state.get_edges() == set()


def test_erase_edge_commute():
    broker = r.DataBroker(2)
    state = g.GraphState(node_keys=[1, 2, 3], edges_keys=[(1, 2), (2, 3), (3, 1)])
    replica_1 = r.Replica(0, broker, state.copy())
    replica_2 = r.Replica(1, broker, state.copy())

    replica_1.apply_local(g.EraseEdge(1, 2))
    replica_1.apply_local(g.EraseEdge(2, 3))
    replica_2.apply_local(g.EraseEdge(1, 2))

    assert replica_1.fetch_remote() == 1
    assert replica_2.fetch_remote() == 2

    replica_1.apply_remote()
    replica_2.apply_remote()

    assert replica_1.state == replica_2.state
    assert replica_1.state.get_nodes() == {1, 2, 3}
    assert replica_1.state.get_edges() == {(3, 1)}


def test_add_node_erase_node():
    broker = r.DataBroker(2)
    state = g.GraphState(node_keys=[1])
    replica_1 = r.Replica(0, broker, state.copy())
    replica_2 = r.Replica(1, broker, state.copy())

    replica_1.apply_local(g.EraseNode(1))
    replica_2.apply_local(g.AddNode(2))

    assert replica_1.fetch_remote() == 1
    assert replica_2.fetch_remote() == 1

    replica_1.apply_remote()
    replica_2.apply_remote()

    assert replica_1.state == replica_2.state
    assert replica_1.state.get_nodes() == {2}
    assert replica_1.state.get_edges() == set()


def test_add_edge_erase_node():
    broker = r.DataBroker(2)
    state = g.GraphState(node_keys=[1, 2])
    replica_1 = r.Replica(0, broker, state.copy())
    replica_2 = r.Replica(1, broker, state.copy())

    replica_1.apply_local(g.AddEdge(1, 2))
    replica_2.apply_local(g.EraseNode(1))

    assert replica_1.fetch_remote() == 1
    assert replica_2.fetch_remote() == 1

    replica_1.apply_remote()
    replica_2.apply_remote()

    assert replica_1.state == replica_2.state
    assert replica_1.state.get_nodes() == {2}
    assert replica_1.state.get_edges() == set()
