import unittest
from unittest.mock import patch

from PyPtt import screens

from ptt.ptt import (
    PttCheckin,
    _CURRENT_MAIN_MENU_TARGET,
    _STALE_MAIN_MENU_TARGET,
)


class PttMainMenuCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.main_menu = screens.Target.MainMenu
        self.cursor_to_goodbye = screens.Target.CursorToGoodbye

    def tearDown(self):
        screens.Target.MainMenu = self.main_menu
        screens.Target.CursorToGoodbye = self.cursor_to_goodbye

    @patch("ptt.ptt.PTT.API")
    def test_client_updates_stale_pyptt_main_menu_markers(self, api):
        screens.Target.MainMenu = _STALE_MAIN_MENU_TARGET.copy()
        screens.Target.CursorToGoodbye = _STALE_MAIN_MENU_TARGET + ["> (G)oodbye"]

        PttCheckin("user", "password")

        self.assertEqual(_CURRENT_MAIN_MENU_TARGET, screens.Target.MainMenu)
        self.assertEqual(
            _CURRENT_MAIN_MENU_TARGET + ["> (G)oodbye"],
            screens.Target.CursorToGoodbye,
        )
        api.assert_called_once_with()

    @patch("ptt.ptt.PTT.API")
    def test_client_does_not_override_a_future_upstream_parser(self, api):
        upstream_target = ["future", "main", "menu"]
        screens.Target.MainMenu = upstream_target.copy()
        screens.Target.CursorToGoodbye = upstream_target + ["cursor"]

        PttCheckin("user", "password")

        self.assertEqual(upstream_target, screens.Target.MainMenu)
        self.assertEqual(upstream_target + ["cursor"], screens.Target.CursorToGoodbye)
        api.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
