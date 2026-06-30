import pytest

from mcpdb.db.base import Connector, Context
from mcpdb.db.fake import FakeConnector


class MinimalConnector:
    async def connect(self, context: Context) -> None:
        return None


@pytest.mark.asyncio
async def test_connector_protocol_satisfied_by_fake() -> None:
    connector = FakeConnector()

    assert isinstance(connector, Connector)


def test_connector_protocol_unsatisfied_by_minimal_class() -> None:
    candidate = MinimalConnector()

    assert not isinstance(candidate, Connector)
