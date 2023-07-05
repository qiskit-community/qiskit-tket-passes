from qiskit.circuit.library import get_standard_gate_name_mapping
from qiskit.transpiler.preset_passmanagers.plugin import PassManagerStagePlugin
from qiskit.transpiler.preset_passmanagers import common
from qiskit.transpiler import PassManager, PassManagerConfig, Target
from pytket.passes import (
    DecomposeBoxes,
    RebaseCustom,
    SynthesiseTket,
    FullPeepholeOptimise,
    NaivePlacementPass,
    DecomposeSwapsToCXs,
    RoutingPass,
)
from pytket.passes import CXMappingPass, KAKDecomposition, CliffordSimp, RemoveRedundancies, SimplifyInitial

from .to_qiskit_pass import ToQiskitPass

def _target_from_pm_config(pm_config: PassManagerConfig):
    target = pm_config.target

    if target is None:
        target = Target.from_configuration(
            basis_gates=list(filter(lambda gate: gate in get_standard_gate_name_mapping(), pm_config.basis_gates)),
            coupling_map=pm_config.coupling_map,
            inst_map=pm_config.inst_map,
            backend_properties=pm_config.backend_properties,
            instruction_durations=pm_config.instruction_durations,
            timing_constraints=pm_config.timing_constraints,
        )

    return target

#TODO: Add support to Aer simulators
class TketInitPassManager(PassManagerStagePlugin):
    def pass_manager(self, pass_manager_config, optimization_level):

        passes = [
            ToQiskitPass(DecomposeBoxes),
        ]
        if optimization_level == 0:
            passes.append(ToQiskitPass(RebaseCustom, target=_target_from_pm_config(pass_manager_config)))
        elif optimization_level == 1 or optimization_level == 2:
            passes.append(ToQiskitPass(SynthesiseTket))
        elif passes == 3:
            passes.append(ToQiskitPass(FullPeepholeOptimise))

        return PassManager(passes)

class TketLayoutPassManager(PassManagerStagePlugin):
    def pass_manager(self, pass_manager_config, optimization_level):

        #TODO:The output from this stage is expected to have the layout property set field
        # set with a Layout object.
        return PassManager(
            [
                ToQiskitPass(NaivePlacementPass, target=_target_from_pm_config(pass_manager_config)),
                ToQiskitPass(DecomposeSwapsToCXs, target=_target_from_pm_config(pass_manager_config)),
                ToQiskitPass(NaivePlacementPass, target=_target_from_pm_config(pass_manager_config)),
            ]
        )

class TketRoutingPassManager(PassManagerStagePlugin):
    def pass_manager(self, pass_manager_config, optimization_level):

        return PassManager(
            [
                ToQiskitPass(RoutingPass, target=_target_from_pm_config(pass_manager_config)),
            ]
        )

class TketTranslationPassManager(PassManagerStagePlugin):
    def pass_manager(self, pass_manager_config, optimization_level):
  
        return PassManager(
            [
                ToQiskitPass(RebaseCustom, target=_target_from_pm_config(pass_manager_config))
            ]
        )

class TketOptimizationPassManager(PassManagerStagePlugin):
    def pass_manager(self, pass_manager_config, optimization_level):
        if optimization_level == 0:
            return None

        passes = []

        if optimization_level == 3:
            passes.append(ToQiskitPass(KAKDecomposition, target=_target_from_pm_config(pass_manager_config), target_2qb_gate='cx', allow_swaps=False))
            passes.append(ToQiskitPass(CliffordSimp, target=_target_from_pm_config(pass_manager_config), allow_swaps=False))
            # TODO: Why do we need this?
            passes.append(ToQiskitPass(CXMappingPass, target=_target_from_pm_config(pass_manager_config), directed_cx=False, delay_measures=False))

        if optimization_level > 1:
            passes.append(ToQiskitPass(SynthesiseTket))

        passes.append(ToQiskitPass(RebaseCustom, target=_target_from_pm_config(pass_manager_config)))
        passes.append(ToQiskitPass(RemoveRedundancies, target=_target_from_pm_config(pass_manager_config)))

        if optimization_level > 1:
            passes.append(ToQiskitPass(SimplifyInitial, allow_classical=False, create_all_qubits=True))

        return PassManager(passes)