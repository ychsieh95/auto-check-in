import base64
import unittest
from unittest.mock import Mock, patch

from apktw.apktw import ApkTw


class ApkTwCaptchaTests(unittest.TestCase):
    def setUp(self):
        self.client = ApkTw("user", "password", "test-key")
        self.client.session = Mock()

    def test_extracts_sitekey_from_escaped_discuz_javascript(self):
        challenge = r"window.turnstile.render(box, {sitekey: \'0x-test\', theme: \'auto\'});"
        self.assertEqual("0x-test", self.client.extract_turnstile_sitekey(challenge))
        self.assertEqual(
            "0x-widget",
            self.client.extract_turnstile_sitekey(
                '<div class="cf-turnstile" data-sitekey="0x-widget"></div>'
            ),
        )

    def test_turnstile_without_sitekey_fails_explicitly(self):
        with self.assertRaisesRegex(RuntimeError, "sitekey is missing"):
            self.client.extract_turnstile_sitekey("window.turnstile.render(box, {});")

    @patch("apktw.apktw.requests.post")
    def test_invalid_images_are_never_uploaded(self, post):
        for image in (b"", b"<html>Access denied</html>"):
            with self.subTest(image=image):
                with self.assertRaisesRegex(RuntimeError, "empty or not a supported image"):
                    self.client.solve_captcha(image)
        post.assert_not_called()

    @patch("apktw.apktw.time.sleep")
    @patch("apktw.apktw.requests.get")
    @patch("apktw.apktw.requests.post")
    def test_turnstile_submission_and_polling(self, post, get, sleep):
        post.return_value.json.return_value = {"status": 1, "request": "task-id"}
        get.side_effect = [
            Mock(json=Mock(return_value={"status": 0, "request": "CAPCHA_NOT_READY"})),
            Mock(json=Mock(return_value={"status": 1, "request": "token"})),
        ]

        self.assertEqual("token", self.client.solve_turnstile("0x-test"))

        self.assertEqual({
            "key": "test-key", "json": "1", "method": "turnstile",
            "sitekey": "0x-test", "pageurl": self.client.LOGIN_URL,
        }, post.call_args.kwargs["data"])
        self.assertEqual("task-id", get.call_args.kwargs["params"]["id"])
        self.assertEqual(2, sleep.call_count)

    @patch("apktw.apktw.time.sleep")
    @patch("apktw.apktw.requests.get")
    @patch("apktw.apktw.requests.post")
    def test_image_solver_retains_base64_protocol(self, post, get, sleep):
        post.return_value.json.return_value = {"status": 1, "request": "task-id"}
        get.return_value.json.return_value = {"status": 1, "request": "Ab12"}
        image = b"GIF89a" + b"image-content"

        self.assertEqual("Ab12", self.client.solve_captcha(image))

        submitted = post.call_args.kwargs["data"]
        self.assertEqual("base64", submitted["method"])
        self.assertEqual(image, base64.b64decode(submitted["body"]))

    def test_login_submits_turnstile_token_without_fetching_image(self):
        self.client.session.get.side_effect = [
            Mock(text='<input name="formhash" value="abcd1234">'
                      "<script>updateseccode('hash')</script>"),
            Mock(text=r"window.turnstile.render(box, {sitekey: \'0x-test\'});"),
        ]
        self.client.session.post.return_value = Mock(url="https://apk.tw/forum.php")
        with patch.object(self.client, "solve_turnstile", return_value="token") as solve:
            with patch.object(self.client, "fetch_captcha_image") as fetch_image:
                self.assertTrue(self.client.login())

        solve.assert_called_once_with("0x-test")
        fetch_image.assert_not_called()
        challenge_request = self.client.session.get.call_args.kwargs["params"]
        self.assertEqual("update", challenge_request["action"])
        self.assertEqual("member::logging", challenge_request["modid"])
        payload = self.client.session.post.call_args.kwargs["data"]
        self.assertEqual("token", payload["cf-turnstile-response"])
        self.assertEqual("hash", payload["seccodehash"])
        self.assertEqual("", payload["seccodeverify"])

    def test_legacy_image_url_uses_server_update_token(self):
        self.client.session.get.return_value = Mock(content=b"GIF89aimage-content")
        challenge = '<img src="misc.php?mod=seccode&amp;update=12345&amp;idhash=hash">'

        self.assertEqual(
            b"GIF89aimage-content", self.client.fetch_captcha_image("hash", challenge)
        )

        self.client.session.get.assert_called_once_with(
            "https://apk.tw/misc.php?mod=seccode&update=12345&idhash=hash", timeout=15
        )

    def test_collector_does_not_treat_turnstile_as_an_image(self):
        self.client.session.get.return_value = Mock(
            text="window.turnstile.render(box, {sitekey: '0x-test'});"
        )
        with self.assertRaisesRegex(RuntimeError, "no image is available"):
            self.client.fetch_captcha_image("hash")
        self.assertEqual(1, self.client.session.get.call_count)


if __name__ == "__main__":
    unittest.main()
