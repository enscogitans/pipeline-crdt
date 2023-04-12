import io
from copy import deepcopy
from textwrap import dedent

from ruamel.yaml import YAML, RoundTripLoader

yaml = YAML(typ="rt")


def load_yaml(path: str):
    with open(path) as f:
        return yaml.load(f)


def dump_yaml(data, path: str):
    with open(path, "w") as f:
        yaml.dump(data, f)


def loads_yaml(yaml_text):
    with io.StringIO(yaml_text) as stream:
        return yaml.load(stream)


def dumps_yaml(yaml_data):
    with io.StringIO() as stream:
        yaml.dump(yaml_data, stream)
        stream.seek(0)
        return stream.read()


def parse_yaml_node(node):
    with io.StringIO("") as fake_stream:
        return RoundTripLoader(fake_stream).construct_document(deepcopy(node))  # construct_document modifies input


def _load_yaml_node(stream):
    return RoundTripLoader(stream).get_single_node()


def _dump_yaml_node(node, stream):
    document = parse_yaml_node(node)
    yaml.dump(document, stream)


def load_yaml_node(path: str):
    with open(path) as f:
        return _load_yaml_node(f)


def dump_yaml_node(yaml_data, path: str):
    with open(path, "w") as f:
        _dump_yaml_node(yaml_data, f)


def loads_yaml_node(yaml_text: str):
    with io.StringIO(yaml_text) as stream:
        return _load_yaml_node(stream)


def dumps_yaml_node(yaml_data):
    with io.StringIO() as stream:
        _dump_yaml_node(yaml_data, stream)
        stream.seek(0)
        return stream.read()


def my_dedent(text):
    text = dedent(text)
    text = text.lstrip("\n")
    text = text.rstrip()
    return text + "\n"
