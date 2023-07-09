import unittest

from qiskit.transpiler.preset_passmanagers.plugin import (
    list_stage_plugins,
    passmanager_stage_plugins,
)
import qiskit_tket_passes.plugins as plgn
    
class TestPassManagerStagePlugins(unittest.TestCase):
    def test_plugins_are_installed(self):
        for stage_name in ['init', 'layout', 'routing', 'translation', 'optimization']:
            installed_plugins = list_stage_plugins(stage_name)
            self.assertIn('tket', installed_plugins)

    def test_plugins_are_used(self):
        plugins = passmanager_stage_plugins('init')
        self.assertIsInstance(isinstance(plugins['tket'], plgn.TketInitPassManager))

        plugins = passmanager_stage_plugins('layout')
        self.assertIsInstance(plugins['tket'], plgn.TketLayoutPassManager)

        plugins = passmanager_stage_plugins('routing')
        self.assertIsInstance(plugins['tket'], plgn.TketRoutingPassManager)

        plugins = passmanager_stage_plugins('translation')
        self.assertIsInstance(plugins['tket'], plgn.TketTranslationPassManager)

        plugins = passmanager_stage_plugins('optimization')
        self.assertIsInstance(plugins['tket'], plgn.TketOptimizationPassManager)


if __name__ == '__main__':
    unittest.main()