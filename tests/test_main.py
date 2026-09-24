import unittest
from unittest.mock import MagicMock, call, patch

from main import run_ptt


class RunPttTests(unittest.TestCase):
    @patch("main.time.sleep")
    @patch("main.PttCheckin.from_config")
    def test_retry_uses_fresh_client_and_kicks_stale_session(self, from_config, sleep):
        first = MagicMock(lang="en")
        first.login.return_value = False
        second = MagicMock(lang="en")
        second.login.return_value = True
        second.check_status.return_value = "registered"
        from_config.side_effect = [first, second]

        result = run_ptt("config.json", None, login_retries=3, retry_delay=10)

        self.assertEqual("PTT Auto Check-in\nregistered", result)
        self.assertEqual([call("config.json"), call("config.json")], from_config.call_args_list)
        first.login.assert_called_once_with(kick_other_session=False)
        second.login.assert_called_once_with(kick_other_session=True)
        second.logout.assert_called_once_with()
        sleep.assert_called_once_with(10)


if __name__ == "__main__":
    unittest.main()
