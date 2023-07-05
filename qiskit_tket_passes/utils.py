import pydoc
import re

import pytket.passes as tkps

def get_arguments_from_doc(tket_pass):
    arguments = []

    _doc = pydoc.getdoc(tket_pass)
    if 'Overloaded function.' in _doc:
        #Return the first signature
        #TODO: We should return all possible signatures. This would requires changes in ToQiskitPass also.
        matches = re.findall("[1-9]\. (" + tket_pass.__name__ + '[^\n]+)', _doc)
        synopsis_line = matches[0]
    else:
        synopsis_line = pydoc.splitdoc(_doc)[0]

    # To avoid issue caused by callable parentheses:
    synopsis_line = re.sub('Callable\[\[[^\[]+\][^\[]+\]', 'Callable', synopsis_line)

    match = re.search("\(([^(]+)\)", synopsis_line)
    if match is not None:
        splitted_args = match.group(1).split(', ')
        for arg_str in splitted_args:
            if arg_str == '**kwargs':
                continue
            else:
                argument = arg_str.split(': ')
                eq_index = argument[1].find('=')
                if eq_index > 0:
                    (_type, _default) = argument[1].split(' = ')
                    arguments.append((argument[0], _type, _default))
                else:
                    arguments.append(tuple(argument))

    return arguments

# This is **temp**. Conversion should be done in a better way
# https://github.com/CQCL/pytket-qiskit/blob/develop/pytket/extensions/qiskit/qiskit_convert.py

from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
from qiskit.converters import dag_to_circuit, circuit_to_dag

from pytket.circuit import Circuit
from qiskit.dagcircuit import DAGCircuit

def qiskit_dag_to_tk(dag: DAGCircuit):
    # Replace any gate that is not known to pyket by its definition
    from pytket.extensions.qiskit.qiskit_convert import _known_qiskit_gate
    for node in dag.op_nodes():
        if not type(node.op) in _known_qiskit_gate:
            dag.substitute_node_with_dag(node, circuit_to_dag(node.op.definition))

    return qiskit_to_tk(dag_to_circuit(dag))

def tk_to_qiskit_dag(tkcirc: Circuit):
    return circuit_to_dag(tk_to_qiskit(tkcirc))