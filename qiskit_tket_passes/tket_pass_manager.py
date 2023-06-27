from typing import Optional

from qiskit.transpiler import PassManager, FlowController
from qiskit.providers.backend import Backend
from pytket.passes import SequencePass
from .to_qiskit_pass import ToQiskitPass

class TketPassManager(PassManager):
    def __init__(self, backend: Backend, optimization_level: Optional[int] = None):

        super().__init__()

        if optimization_level is None:
            optimization_level = 1

        _pass = backend.default_compilation_pass(optimisation_level=optimization_level)
        self.append(self._visit_recursively(_pass))

    def _visit_recursively(self, _pass):
        if isinstance(_pass, SequencePass):
            _list = []
            for _item in _pass.get_sequence():    
                _list.append(self._visit_recursively(_item))
            return FlowController.controller_factory(_list, None)
        else:
            return ToQiskitPass(_pass)