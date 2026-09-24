import os
import unittest

from utils.virtualenv import activate_current_virtualenv


class ActivateCurrentVirtualenvTests(unittest.TestCase):
    def test_direct_virtualenv_interpreter_gets_activation_environment(self):
        environ = {"PATH": "/usr/local/bin:/usr/bin"}

        activated = activate_current_virtualenv(
            executable="/project/.venv/bin/python3",
            prefix="/project/.venv",
            base_prefix="/usr",
            environ=environ,
        )

        self.assertTrue(activated)
        self.assertEqual("/project/.venv", environ["VIRTUAL_ENV"])
        self.assertEqual(
            os.pathsep.join(["/project/.venv/bin", "/usr/local/bin", "/usr/bin"]),
            environ["PATH"],
        )

    def test_existing_virtualenv_bin_is_not_duplicated(self):
        environ = {"PATH": "/project/.venv/bin:/usr/bin"}

        activate_current_virtualenv(
            executable="/project/.venv/bin/python3",
            prefix="/project/.venv",
            base_prefix="/usr",
            environ=environ,
        )

        self.assertEqual("/project/.venv/bin:/usr/bin", environ["PATH"])

    def test_system_interpreter_is_unchanged(self):
        environ = {"PATH": "/usr/bin"}

        activated = activate_current_virtualenv(
            executable="/usr/bin/python3",
            prefix="/usr",
            base_prefix="/usr",
            environ=environ,
        )

        self.assertFalse(activated)
        self.assertEqual({"PATH": "/usr/bin"}, environ)


if __name__ == "__main__":
    unittest.main()
