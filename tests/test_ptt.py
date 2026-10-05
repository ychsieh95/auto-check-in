import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PyPtt import connect_core, screens

from ptt.ptt import (
    _CURSOR_POSITION_QUERY,
    _AUTOWRAP_MARKERS,
    _UNSUPPORTED_TERMINAL_SEQUENCES,
    _patch_pyptt_synchronized_output,
    PttCheckin,
    _CURRENT_MAIN_MENU_TARGET,
    _STALE_MAIN_MENU_TARGET,
    _SYNC_OUTPUT_MARKERS,
    _strip_synchronized_output_markers,
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

    def test_current_markers_match_old_and_current_ptt_status_lines(self):
        full_status_line = (
            "[5/23 星期六 16:40] [ 射手時 ]  "
            "線上27866人, 我是CodingMan   [呼叫器]打開"
        )
        compact_status_line = (
            "8/19週三22:35   [ 七夕 ]   "
            "線上30721人,我是DeepLearning 呼叫器關閉  (h)說明"
        )
        current_status_line = "主選單 [ 牡羊時 ] 10/6 週二 0:40 | user | 線上22394人 (h)說明"

        for status_line in (full_status_line, compact_status_line, current_status_line):
            with self.subTest(status_line=status_line):
                main_menu_screen = f"【主功能表】\n離開，再見\n{status_line}"
                self.assertTrue(
                    all(marker in main_menu_screen for marker in _CURRENT_MAIN_MENU_TARGET)
                )

    def test_welcome_prompt_is_not_recognized_as_main_menu(self):
        welcome_screen = "密碼正確！歡迎光臨\n請按任意鍵繼續"
        self.assertFalse(
            all(marker in welcome_screen for marker in _CURRENT_MAIN_MENU_TARGET)
        )

    @patch("ptt.ptt.PTT.API")
    def test_client_does_not_override_a_future_upstream_parser(self, api):
        upstream_target = ["future", "main", "menu"]
        screens.Target.MainMenu = upstream_target.copy()
        screens.Target.CursorToGoodbye = upstream_target + ["cursor"]

        PttCheckin("user", "password")

        self.assertEqual(upstream_target, screens.Target.MainMenu)
        self.assertEqual(upstream_target + ["cursor"], screens.Target.CursorToGoodbye)
        api.assert_called_once_with()

    @patch("ptt.ptt.PTT.API")
    def test_login_can_remove_a_stale_server_session(self, api):
        client = PttCheckin("user", "password")

        self.assertTrue(client.login(kick_other_session=True))

        api.return_value.login.assert_called_once_with(
            "user", "password", kick_other_session=True
        )

    @patch("ptt.ptt.PTT.API")
    def test_failed_login_closes_the_connection(self, api):
        api.return_value.login.side_effect = RuntimeError("login failed")
        client = PttCheckin("user", "password")

        self.assertFalse(client.login())

        api.return_value.connect_core.close.assert_called_once_with()

    def test_synchronized_output_does_not_hide_continue_prompt(self):
        animated_prompt = (
            _SYNC_OUTPUT_MARKERS[0]
            + "請按任意鍵繼續".encode()
            + _SYNC_OUTPUT_MARKERS[1]
        )
        parser = screens.IncrementalScreen("utf-8")
        parser.feed(_strip_synchronized_output_markers(animated_prompt))

        self.assertIn("任意鍵", parser.screen)

    def test_cursor_position_query_does_not_freeze_welcome_screen(self):
        welcome_screen = (
            b"PTT welcome"
            + _CURSOR_POSITION_QUERY
            + "請按任意鍵繼續".encode()
        )
        parser = screens.IncrementalScreen("utf-8")
        parser.feed(_strip_synchronized_output_markers(welcome_screen))

        self.assertIn("任意鍵", parser.screen)

    def test_autowrap_switch_does_not_hide_post_password_prompt(self):
        parser = screens.IncrementalScreen("utf-8")
        parser.feed(_strip_synchronized_output_markers(
            _AUTOWRAP_MARKERS[1]
            + "請按任意鍵繼續".encode()
            + _AUTOWRAP_MARKERS[0]
        ))

        self.assertIn("任意鍵", parser.screen)

    def test_control_sequences_split_across_frames_do_not_freeze_parser(self):
        _patch_pyptt_synchronized_output()
        for marker in _UNSUPPORTED_TERMINAL_SEQUENCES:
            for split in range(1, len(marker)):
                with self.subTest(marker=marker, split=split):
                    core = SimpleNamespace(
                        _stream_parsers={}, config=SimpleNamespace(screen_height=24)
                    )
                    connect_core.API._stream_screen(core, "utf-8", b"before" + marker[:split])
                    screen = connect_core.API._stream_screen(
                        core, "utf-8", marker[split:] + "請按任意鍵繼續".encode()
                    )
                    self.assertIn("before", screen)
                    self.assertIn("任意鍵", screen)


if __name__ == "__main__":
    unittest.main()
