from dataclasses import dataclass


@dataclass
class Experiment:
    data: "Dataset"
    params: "Params"
    hypothesis: "Hypothesis"


@dataclass
class Dataset:
    train: "Data"
    test: "Data"

    @dataclass
    class Data:
        path: str


@dataclass
class Params:
    params: list["Param"]

    @dataclass
    class Param:
        key: str
        value: object


class Hypothesis:
    pipeline: "Pipeline"
    report: "Report"

    class Report:
        path: str


class Pipeline:
    start: "Start"
    jobs: list["Job"]
    finish: "Finish"


class Finish:
    pass


class Start:
    next: Finish | list["Job"]


class Job:
    next: Finish | list["Job"]
    export: "Export"

    class Export:
        path: str
