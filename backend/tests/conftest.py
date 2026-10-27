import os, tempfile
_tmp = tempfile.mkdtemp(prefix="ais-test-")
os.environ["AIS_DATA_DIR"] = _tmp
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")
