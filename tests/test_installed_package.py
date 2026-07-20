import importlib.metadata
import os
import unittest
from unittest.mock import Mock, patch


class InstalledPackageTest(unittest.TestCase):
    def test_plugin_entry_point_loads_without_credentials_or_processes(self):
        distribution = importlib.metadata.distribution("hermes-agent-council")
        entry_points = [
            entry_point
            for entry_point in importlib.metadata.entry_points(
                group="hermes_agent.plugins"
            )
        ]

        self.assertEqual(1, len(entry_points))
        entry_point = entry_points[0]
        self.assertIn(entry_point, distribution.entry_points)
        self.assertEqual("hermes-council", entry_point.name)
        self.assertEqual("hermes_council", entry_point.value)

        with patch.dict(os.environ, {}, clear=True):
            with patch("subprocess.Popen") as popen:
                plugin = entry_point.load()
                plugin.register(Mock())

        self.assertEqual("hermes_council", plugin.__name__)
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
