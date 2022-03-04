from unittest import TestCase
from routes.src.common import get_return_envelope


class TestCommon(TestCase):
    def test_get_return_envelope(self):
        msg = "Test message 1"
        data = [1, 2, 3]
        envelope = get_return_envelope(success=True, message=msg, data=data)
        self.assertTrue(envelope["success"])
        self.assertEqual(msg, envelope["message"])
        self.assertEqual(data, envelope["results"])
