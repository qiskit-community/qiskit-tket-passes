import unittest

from qiskit.circuit.random import random_circuit
from pytket.passes import SequencePass
from pytket.extensions.qiskit import IBMQBackend
from qiskit_tket_passes import TketPassManager

class TestTketPassManager(unittest.TestCase):
    def setUp(self):
        super().setUp()
        
        self.backend = IBMQBackend('ibmq_quito')

    def test_tket_pass_manager_conatins_correct_passes(self):
        def _get_passes_in_tket_sequence(_pass):
            if isinstance(_pass, SequencePass):
                _list = []
                for _item in _pass.get_sequence():    
                    _list.append(_get_passes_in_tket_sequence(_item))
                return _list
            else:
                return _pass.to_dict()['StandardPass']['name']

        def _get_passes_in_qiskit_pm(_pass):
            if type(_pass) == dict:
                _list = []
                for _item in _pass['passes']:
                    _list.append(_get_passes_in_qiskit_pm(_item))
                return _list
            else:
                return _pass.name().replace('TketPass_', '')

        pm = TketPassManager(self.backend, optimization_level=2)    

        _pass = self.backend.default_compilation_pass(optimisation_level=2)
        self.assertEqual(_get_passes_in_qiskit_pm(pm.passes()[0]['passes'].dump_passes()), _get_passes_in_tket_sequence(_pass))

    def test_tket_pass_manager_run(self):
        circ = random_circuit(3, 10, seed=1)
        pm = TketPassManager(self.backend)
        tr_circ = pm.run(circ)

        basis_gates = self.backend._backend.configuration().basis_gates
        for op in tr_circ.count_ops():
            self.assertIn(op, basis_gates)

        coupling_map = self.backend._backend.configuration().coupling_map
        for _instruction in tr_circ.data:
            if _instruction.operation.name == 'cx':
                qubit_0 = tr_circ.find_bit(_instruction.qubits[0])[0]
                qubit_1 = tr_circ.find_bit(_instruction.qubits[1])[0]
                self.assertIn([qubit_0, qubit_1], coupling_map)

if __name__ == '__main__':
    unittest.main()