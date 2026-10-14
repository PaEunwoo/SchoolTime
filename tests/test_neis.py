import unittest
from unittest.mock import Mock

from services.neis import (
    NeisAuthenticationError,
    NeisClient,
    NeisResponseError,
)


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def json(self, content_type=None):
        return self.payload


class NeisClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_single_key_and_paginates(self):
        first = {
            "schoolInfo": [
                {"head": [{"list_total_count": 2}, {"RESULT": {"CODE": "INFO-000"}}]},
                {"row": [{"SCHUL_NM": "가학교"}]},
            ]
        }
        second = {
            "schoolInfo": [
                {"head": [{"list_total_count": 2}, {"RESULT": {"CODE": "INFO-000"}}]},
                {"row": [{"SCHUL_NM": "나학교"}]},
            ]
        }
        session = type("Session", (), {})()
        session.get = Mock(side_effect=[FakeResponse(first), FakeResponse(second)])
        client = NeisClient("one-key", session=session)
        results = await client.search_schools("학교")
        self.assertEqual([row["SCHUL_NM"] for row in results], ["가학교", "나학교"])
        calls = session.get.call_args_list
        self.assertEqual(calls[0].kwargs["params"]["KEY"], "one-key")
        self.assertEqual(calls[1].kwargs["params"]["pIndex"], 2)
        self.assertEqual(calls[0].kwargs["params"]["Type"], "json")

    async def test_no_result_code_returns_empty(self):
        payload = {"schoolInfo": [{"head": [{"RESULT": {"CODE": "INFO-200"}}]}]}
        client = NeisClient("key", session=type("Session", (), {
            "get": Mock(return_value=FakeResponse(payload))
        })())
        self.assertEqual(await client.search_schools("없는학교"), [])

    async def test_authentication_error_is_explicit(self):
        payload = {
            "schoolInfo": [
                {"head": [{"RESULT": {"CODE": "ERROR-290", "MESSAGE": "invalid"}}]}
            ]
        }
        client = NeisClient("key", session=type("Session", (), {
            "get": Mock(return_value=FakeResponse(payload))
        })())
        with self.assertRaises(NeisAuthenticationError):
            await client.search_schools("학교")

    def test_unknown_result_code_is_explicit(self):
        with self.assertRaises(NeisResponseError):
            NeisClient._parse_payload(
                {"schoolInfo": [{"head": [{"RESULT": {"CODE": "ERROR-999"}}]}]},
                "schoolInfo",
            )


if __name__ == "__main__":
    unittest.main()
