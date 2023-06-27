import unittest

from qiskit.circuit import QuantumCircuit
from qiskit.providers.fake_provider import FakeQuitoV2
from qiskit.transpiler import PassManager, TransformationPass

import pytket.passes as tkps
from pytket.architecture import Architecture
from pytket.circuit import OpType
from pytket.placement import GraphPlacement, NoiseAwarePlacement
from pytket.transform import CXConfigType, PauliSynthStrat

import sys
import os
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
from qiskit_tket_passes import ToQiskitPass

class TestToQiskitPass(unittest.TestCase):

    def setUp(self):
        super().setUp()
        
        self.target = FakeQuitoV2().target

    def test_creation_from_tket_pass_class(self):
        _pass = ToQiskitPass(tkps.SynthesiseTket)
        self.assertIsInstance(_pass, TransformationPass)
        self.assertEqual(_pass.__class__.__name__, 'TketPass_SynthesiseTket')

    def test_creation_from_tket_pass_instance(self):
        tket_pass = tkps.FullPeepholeOptimise()
        _pass = ToQiskitPass(tket_pass)
        self.assertIsInstance(_pass, TransformationPass)
        self.assertEqual(_pass.__class__.__name__, 'TketPass_FullPeepholeOptimise')

    def test_architecture_from_target(self):
        coupling_map = self.target.build_coupling_map()

        _pass = ToQiskitPass(tkps.CXMappingPass, target=self.target)
        arc = _pass.tket_argument('arc')

        self.assertEqual(len(coupling_map.get_edges()), len(arc.coupling))

        for _item in arc.coupling:
            edge = (_item[0].index[0], _item[1].index[0])
            self.assertIn(edge, coupling_map)

    def test_noise_aware_placer_from_target(self):
        _pass = ToQiskitPass(tkps.CXMappingPass, target=self.target)
        self.assertIsInstance(_pass.tket_argument('placer'), NoiseAwarePlacement)

    def test_placer_from_str(self):
        _pass = ToQiskitPass(tkps.CXMappingPass, target=self.target, placer='Graph')
        self.assertIsInstance(_pass.tket_argument('placer'), GraphPlacement)

    def test_optype_from_str(self):
        _pass = ToQiskitPass(tkps.FullPeepholeOptimise, allow_swaps=True, target_2qb_gate='cx')
        self.assertEqual(_pass.tket_argument('target_2qb_gate'), OpType.CX)

    def test_swap_decomposition_from_target(self):
        circ = QuantumCircuit(2)
        circ.swap(0, 1)

        pm = PassManager([
            ToQiskitPass(tkps.DecomposeSwapsToCircuit, target=self.target)
        ])
        tr_circ = pm.run(circ)
        ops = tr_circ.count_ops()

        self.assertNotIn('swap', ops)
        self.assertEqual(ops['cx'], 3)

    def test_pauli_synthesis_strategy_from_str(self):
        _pass = ToQiskitPass(tkps.PauliSimp, strat='Pairwise')
        self.assertEqual(_pass.tket_argument('strat'), PauliSynthStrat.Pairwise)

    def test_cx_config_type_from_str(self):
        _pass = ToQiskitPass(tkps.OptimisePhaseGadgets, cx_config='Tree')
        self.assertEqual(_pass.tket_argument('cx_config'), CXConfigType.Tree)

if __name__ == '__main__':
    unittest.main()