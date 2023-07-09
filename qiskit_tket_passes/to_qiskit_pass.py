import re
from collections import OrderedDict

from qiskit import QuantumCircuit
from qiskit.transpiler import TransformationPass
from qiskit.transpiler.target import Target, target_to_backend_properties
from pytket.architecture import Architecture
from pytket.circuit import OpType
from pytket.passes import BasePass
from pytket.passes._decompositions import _TK1_to_X_SX_Rz, _TK1_to_U
from pytket.transform import CXConfigType, PauliSynthStrat
from pytket.extensions.qiskit import qiskit_to_tk
from pytket.placement import GraphPlacement, LinePlacement, NoiseAwarePlacement

from .utils import get_arguments_from_doc, qiskit_dag_to_tk, tk_to_qiskit_dag

def ToQiskitPass(tket_pass, target: Target = None, **kwargs):
    class TketPassClass(TransformationPass):
        def __init__(self, target: Target = None, **kwargs):
            if isinstance(tket_pass, BasePass):
                self._pass = tket_pass
                _dict = tket_pass.to_dict()
                class_name = _dict[_dict['pass_class']]['name']

                self.requires = []
                self.preserves = []
            else:
                self.target = target
                super().__init__()
                class_name = tket_pass.__name__

                self._args_dict = OrderedDict()
                parsed_args = get_arguments_from_doc(tket_pass)
                for parsed_arg in parsed_args:
                    arg_name = parsed_arg[0]
                    arg_type = parsed_arg[1]
                    if arg_type.endswith('architecture.Architecture'):
                        if arg_name in kwargs:
                            arc = kwargs.pop(arg_name)
                            if type(arc) == list:
                                connections = []
                                for edge in arc:
                                    connections.append(tuple(edge))
                                arc = Architecture(connections)
                            self._args_dict[arg_name] = arc
                        elif self.target:
                            arc = self._arch_from_target()
                            self._args_dict[arg_name] = arc
                    elif arg_type.endswith('placement.Placement'):
                        if arg_name in kwargs:
                            placer_str = kwargs.pop(arg_name)
                        else:
                            placer_str = 'NoiseAware'

                        if placer_str == 'Graph':
                            placer = GraphPlacement(self._arch_from_target())
                            self._args_dict[arg_name] = placer
                        elif placer_str == 'Line':
                            placer = LinePlacement(self._arch_from_target())
                            self._args_dict[arg_name] = placer
                        elif placer_str == 'NoiseAware':
                            if self.target:
                                placer = self._noise_aware_placer_from_target()
                                self._args_dict[arg_name] = placer
                        else:
                            raise ValueError('Unsupported placer type:', placer_str)
                    elif arg_type.endswith('circuit.Circuit'):
                        if arg_name in kwargs:
                            circ = kwargs.pop(arg_name)
                            tkcirc = qiskit_to_tk(circ)
                            self._args_dict[arg_name] = tkcirc
                        elif self.target:
                            if class_name == 'DecomposeSwapsToCircuit' and arg_name == 'replacement_circuit':
                                # Construct SWAP replacement circuit based on target's gate set.
                                circ = self._swap_decomposition_from_target()
                                tkcirc = qiskit_to_tk(circ)
                                self._args_dict[arg_name] = tkcirc
                            elif class_name == 'RebaseCustom' and arg_name == 'cx_replacement':
                                # Construct CNOT replacement circuit based on target's gate set.
                                circ = self._cnot_decomposition_from_target()
                                tkcirc = qiskit_to_tk(circ)
                                self._args_dict[arg_name] = tkcirc
                    elif arg_type.endswith('circuit.OpType'):
                        if arg_name in kwargs:
                            op_str = kwargs.pop(arg_name)
                            op_type = self._optype_from_str(op_str)
                            self._args_dict[arg_name] = op_type
                    elif re.match("Set\[.+\.circuit\.OpType\]", arg_type) is not None:
                        if arg_name in kwargs:
                            _value = kwargs.pop(arg_name)
                            if all(isinstance(elem, str) for elem in _value):
                                op_types = set()
                                for op_str in _value:
                                    op_types.add(self._optype_from_str(op_str))

                                self._args_dict[arg_name] = op_types
                            elif isinstance(_value, set) and all(isinstance(elem, OpType) for elem in _value):
                                self._args_dict[arg_name] = _value
                        elif self.target and class_name == 'RebaseCustom' and arg_name == 'gateset':
                            # Get the target's gate set.
                            self._args_dict[arg_name] = self._gateset_from_target()
                    elif arg_type.endswith('transform.PauliSynthStrat'):
                        if arg_name in kwargs:
                            strategy = kwargs.pop(arg_name)
                            strategies_map = {
                                'Individual': PauliSynthStrat.Individual,
                                'Pairwise': PauliSynthStrat.Pairwise,
                                'Sets': PauliSynthStrat.Sets,
                            }
                            value = strategies_map[strategy]
                            self._args_dict[arg_name] = value
                    elif arg_type.endswith('transform.CXConfigType'):
                        if arg_name in kwargs:
                            cx_config = kwargs.pop(arg_name)
                            cx_config_map = {
                                'Snake': CXConfigType.Snake,
                                'Star': CXConfigType.Star,
                                'Tree': CXConfigType.Tree,
                                'MultiQGate': CXConfigType.MultiQGate
                            }
                            value = cx_config_map[cx_config]
                            self._args_dict[arg_name] = value
                    elif arg_name == 'tk1_replacement':
                        if self.target:
                            self._args_dict[arg_name] = self._tk1_replacement_from_target()
                        else:
                            self._args_dict[arg_name] = _TK1_to_U
                    else:
                        if arg_name in kwargs:
                            value = kwargs.pop(arg_name)
                            self._args_dict[arg_name] = value

                args =  self._args_dict.values()
                self._pass = tket_pass(*args, **kwargs)
            __class__.__name__ = 'TketPass_' + class_name

        def run(self, dag):
            tkcirc = qiskit_dag_to_tk(dag)
            self._pass.apply(tkcirc)
            return tk_to_qiskit_dag(tkcirc)

        def tket_argument(self, arg_name):
            if arg_name in self._args_dict:
                return self._args_dict[arg_name]
            else:
                raise ValueError(f"{__class__.__name__} has no argument with the name {arg_name}.")

        #TODO: May be we should move the following methods to utils file instead of having them as class methods
        def _optype_from_str(self, op_str):
            for op_type in dir(OpType):
                if op_str.upper() == op_type.upper():
                    return OpType.from_name(op_type)

            ops_map = {
                'id': 'noop',
                'u': 'U3',
                'cu': 'CU3',
                'iswap': 'ISWAPMax',
                'rxx': 'XXPhase',
                'ryy': 'YYPhase',
                'rzz': 'ZZPhase',
                'p': 'U1',
                'cp': 'CU1',
                'r': 'PhasedX',
            }
            return OpType.from_name(ops_map[op_str])

        def _gateset_from_target(self):

            operation_names = list(self.target.operation_names)
            for op in ['delay', 'if_else', 'rzx']:
                if op in operation_names:
                    operation_names.remove(op)

            return { self._optype_from_str(op_str) for op_str in operation_names }

        def _arch_from_target(self):
            _coupling_map = self.target.build_coupling_map()
            if _coupling_map is None:
                return Architecture([])
            else:
                return Architecture(_coupling_map.get_edges())

        def _cnot_decomposition_from_target(self):
            circ = QuantumCircuit(2)
            circ.cx(0, 1)
            if 'cx' not in self.target.operation_names:
                from qiskit import transpile
                circ = transpile(circ, basis_gates=list(self.target.operation_names))
            return circ

        def _swap_decomposition_from_target(self):
            from qiskit import transpile
            circ = QuantumCircuit(2)
            circ.swap(0, 1)
            return transpile(circ, basis_gates=list(self.target.operation_names))

        def _tk1_replacement_from_target(self):
            if {'x', 'sx', 'rz'}.issubset(self.target.operation_names):
                return _TK1_to_X_SX_Rz
            else:
                return _TK1_to_U

        def _noise_aware_placer_from_target(self):
            """
            Get noise data from target.
            This code is a modified copy from `process_characterisation` & `get_avg_characterisation` functions in pytket-qiskit module.
            """
            from collections import defaultdict
            from pytket.circuit import Node


            node_errors = defaultdict(dict)
            edge_errors = defaultdict(dict)
            readout_errors = {}

            coupling_map = target.build_coupling_map()
            arc = self._arch_from_target()
            properties = target_to_backend_properties(target)
            if properties is None:
                return None
            else:
                for gate in properties.gates:
                    for param in gate.parameters:
                        if param.name == 'gate_error':
                            optype = self._optype_from_str(gate.gate)
                            gate_error = param.value
                            if len(gate.qubits) == 1:
                                node_errors[Node(gate.qubits[0])].update({optype: gate_error})
                            else:
                                edge_errors[(Node(gate.qubits[0]), Node(gate.qubits[1]))].update({optype: gate_error})
                                if gate.qubits[::-1] not in coupling_map:
                                    edge_errors[(Node(gate.qubits[1]), Node(gate.qubits[0]))].update({optype: 2 * gate_error})

                props_dict = properties.to_dict()
                for n in range(target.num_qubits):
                    if len(props_dict['qubits']) > n:
                        readout_error = properties.readout_error(n)
                    else:
                        readout_error = 0

                    readout_errors[Node(n)] = [       
                        [1.0 - readout_error, readout_error],
                        [readout_error, 1.0 - readout_error],
                    ]

                avg = lambda xs: sum(xs.values()) / len(xs)
                avg_mat = (lambda xs: (xs[0][1] + xs[1][0]) / 2.0)
                map_values = lambda f, d: { k: f(v) for k, v in d.items() }

                avg_node_errors = map_values(avg, node_errors)
                avg_edge_errors = map_values(avg, edge_errors)
                avg_readout_errors = map_values(avg_mat, readout_errors)

                return NoiseAwarePlacement(
                    arc,
                    avg_node_errors,
                    avg_edge_errors,
                    avg_readout_errors
                )

    return TketPassClass(target, **kwargs)