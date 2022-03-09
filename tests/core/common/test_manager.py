import dataclasses
import pathlib
from dataclasses import dataclass
from typing import Any, Dict

from taipy.core.common._manager import _Manager
from taipy.core.config.config import Config
from taipy.core.repository import _FileSystemRepository


@dataclass
class MockModel:
    id: str
    name: str

    def to_dict(self):
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return MockModel(id=data["id"], name=data["name"])


@dataclass
class MockEntity:
    id: str
    name: str


class MockRepository(_FileSystemRepository):
    def _to_model(self, obj: MockEntity):
        return MockModel(obj.id, obj.name)

    def _from_model(self, model: MockModel):
        return MockEntity(model.id, model.name)

    @property
    def _storage_folder(self) -> pathlib.Path:
        return pathlib.Path(Config.global_config.storage_folder)  # type: ignore


class MockManager(_Manager[MockEntity]):
    _ENTITY_NAME = MockEntity.__name__
    _repository = MockRepository(model=MockModel, dir_name="foo")


class TestManager:
    def test_save_and_fetch_model(self):
        m = MockEntity("uuid", "foo")
        MockManager._set(m)

        fetched_model = MockManager._get(m.id)
        assert m == fetched_model

    def test_get(self):
        m = MockEntity("uuid", "foo")
        MockManager._set(m)
        assert MockManager._get(m.id) == m

    def test_get_all(self):
        objs = []
        for i in range(5):
            m = MockEntity(f"uuid-{i}", f"Foo{i}")
            objs.append(m)
            MockManager._set(m)
        _objs = MockManager._get_all()

        assert len(_objs) == 5

    def test_delete(self):
        m = MockEntity("uuid", "foo")
        MockManager._set(m)
        MockManager._delete(m.id)
        assert MockManager._get(m.id) is None

    def test_delete_all(self):
        objs = []
        for i in range(5):
            m = MockEntity(f"uuid-{i}", f"Foo{i}")
            objs.append(m)
            MockManager._set(m)
        MockManager._delete_all()
        assert MockManager._get_all() == []
