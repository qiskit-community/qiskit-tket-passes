import setuptools

def func():
    return [
        'tket = qiskit_tket_passes.optimization:RemoveRedundanciesPlugin',
    ]

setuptools.setup(
    name="qiskit-tket-passes",
    version='0.1.0',
    description="A python module to enable using TKET transpilation passes in Qiskit",
    packages=setuptools.find_packages(exclude=["test*"]),
    entry_points = {
        'qiskit.transpiler.init': [
            'tket = qiskit_tket_passes.plugins:TketInitPassManager',
        ],
        'qiskit.transpiler.layout': [
            'tket = qiskit_tket_passes.plugins:TketLayoutPassManager',
        ],
        'qiskit.transpiler.routing': [
            'tket = qiskit_tket_passes.plugins:TketRoutingPassManager',
        ],
        'qiskit.transpiler.translation': [
            'tket = qiskit_tket_passes.plugins:TketTranslationPassManager',
        ],
        'qiskit.transpiler.optimization': [
            'tket = qiskit_tket_passes.plugins:TketOptimizationPassManager',
        ]
    }
)