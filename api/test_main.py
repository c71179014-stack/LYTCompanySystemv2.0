import unittest

from fastapi.testclient import TestClient

from main import TOOLS, Tool, app, run_tool


class SmokeTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(TestClient(app).get("/api/health").json(), {"status": "ok"})

    def test_approval_defaults_to_deny(self):
        TOOLS["test"] = Tool(lambda: self.fail("Tool ran without approval"))
        try:
            with self.assertRaises(PermissionError):
                run_tool("test", {})
        finally:
            del TOOLS["test"]
