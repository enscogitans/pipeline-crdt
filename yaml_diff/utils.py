import io
from copy import deepcopy

from ruamel.yaml import YAML, RoundTripLoader, RoundTripConstructor

yaml = YAML(typ="rt")


def _load_yaml_node(stream):
    return RoundTripLoader(stream).get_single_node()


def load_yaml(path: str):
    with open(path) as f:
        return yaml.load(f)


def load_yaml_node(path: str):
    with open(path) as f:
        return _load_yaml_node(f)


def parse_yaml_node(node):
    with io.StringIO("") as fake_stream:
        return RoundTripLoader(fake_stream).construct_document(deepcopy(node))  # construct_document modifies input


def dump_yaml(data, path: str):
    with open(path, "w") as f:
        yaml.dump(data, f)


def loads_yaml(yaml_text):
    with io.StringIO(yaml_text) as stream:
        return yaml.load(stream)


def loads_yaml_node(yaml_text: str):
    with io.StringIO(yaml_text) as stream:
        return _load_yaml_node(stream)


def dumps_yaml(yaml_data):
    with io.StringIO() as stream:
        yaml.dump(yaml_data, stream)
        stream.seek(0)
        return stream.read()


def assert_yaml_eq(yaml_1, yaml_2):
    text_1 = dumps_yaml(yaml_1)
    text_2 = dumps_yaml(yaml_2)
    assert text_1 == text_2
