# Copyright 2022 Avaiga Private Limited
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from importlib import util
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from src.taipy.core.common.alias import DataNodeId
from src.taipy.core.data.sql import SQLDataNode
from src.taipy.core.exceptions.exceptions import MissingRequiredProperty
from taipy.config.common.scope import Scope


if not util.find_spec("pyodbc"):
    pytest.skip("skipping tests because PyODBC is not installed", allow_module_level=True)


class TestSQLDataNode:
    __properties = [
        {
            "db_username": "sa",
            "db_password": "Passw0rd",
            "db_name": "taipy",
            "db_engine": "mssql",
            "read_query": "SELECT * from daily_min_example",
            "write_table": "foo",
            "db_extra_args": {
                "TrustServerCertificate": "yes",
            },
        },
        {
            "db_name": "taipy",
            "db_engine": "sqlite",
            "read_query": "SELECT * from daily_min_example",
            "write_table": "foo",
            "db_extra_args": {
                "TrustServerCertificate": "yes",
                "other": "value",
            },
        },
    ]

    @pytest.mark.parametrize("properties", __properties)
    def test_create(self, properties):
        dn = SQLDataNode(
            "foo_bar",
            Scope.PIPELINE,
            properties=properties,
        )
        assert isinstance(dn, SQLDataNode)
        assert dn.storage_type() == "sql"
        assert dn.config_id == "foo_bar"
        assert dn.scope == Scope.PIPELINE
        assert dn.id is not None
        assert dn.parent_id is None
        assert dn.job_ids == []
        assert dn.is_ready_for_reading
        assert dn.read_query != ""

    @pytest.mark.parametrize(
        "properties",
        [
            {},
            {"db_username": "foo"},
            {"db_username": "foo", "db_password": "foo"},
            {"db_username": "foo", "db_password": "foo", "db_name": "foo"},
        ],
    )
    def test_create_with_missing_parameters(self, properties):
        with pytest.raises(MissingRequiredProperty):
            SQLDataNode("foo", Scope.PIPELINE, DataNodeId("dn_id"))
        with pytest.raises(MissingRequiredProperty):
            SQLDataNode("foo", Scope.PIPELINE, DataNodeId("dn_id"), properties=properties)

    @mock.patch("src.taipy.core.data.sql.SQLDataNode._read_as", return_value="custom")
    @mock.patch("src.taipy.core.data.sql.SQLDataNode._read_as_pandas_dataframe", return_value="pandas")
    @mock.patch("src.taipy.core.data.sql.SQLDataNode._read_as_numpy", return_value="numpy")
    @pytest.mark.parametrize("properties", __properties)
    def test_read(self, mock_read_as, mock_read_as_pandas_dataframe, mock_read_as_numpy, properties):

        # Create SQLDataNode without exposed_type (Default is pandas.DataFrame)
        sql_data_node_as_pandas = SQLDataNode(
            "foo",
            Scope.PIPELINE,
            properties=properties,
        )

        assert sql_data_node_as_pandas._read() == "pandas"

        # Create the same SQLDataNode but with custom exposed_type
        sql_data_node_as_custom_object = SQLDataNode(
            "foo",
            Scope.PIPELINE,
            properties={
                "db_username": "a",
                "db_password": "a",
                "db_name": "a",
                "db_engine": "mssql",
                "read_query": "SELECT * from table_name",
                "write_table": "foo",
                "exposed_type": "Whatever",
            },
        )
        assert sql_data_node_as_custom_object._read() == "custom"

        # Create the same SQLDataSource but with numpy exposed_type
        sql_data_source_as_numpy_object = SQLDataNode(
            "foo",
            Scope.PIPELINE,
            properties={
                "db_username": "a",
                "db_password": "a",
                "db_name": "a",
                "db_engine": "mssql",
                "read_query": "SELECT * from table_name",
                "write_table": "foo",
                "exposed_type": "numpy",
            },
        )

        assert sql_data_source_as_numpy_object._read() == "numpy"

    @pytest.mark.parametrize("properties", __properties)
    def test_read_as(self, properties):
        class MyCustomObject:
            def __init__(self, foo=None, bar=None, *args, **kwargs):
                self.foo = foo
                self.bar = bar
                self.args = args
                self.kwargs = kwargs

        sql_data_node = SQLDataNode(
            "foo",
            Scope.PIPELINE,
            properties={
                "db_username": "sa",
                "db_password": "foobar",
                "db_name": "datanode",
                "db_engine": "mssql",
                "read_query": "SELECT * from table_name",
                "write_table": "foo",
            },
        )

        with mock.patch("sqlalchemy.engine.Engine.connect") as engine_mock:
            cursor_mock = engine_mock.return_value.__enter__.return_value
            cursor_mock.execute.return_value = [
                {"foo": "baz", "bar": "qux"},
                {"foo": "quux", "bar": "quuz"},
                {"foo": "corge"},
                {"bar": "grault"},
                {"KWARGS_KEY": "KWARGS_VALUE"},
                {},
            ]
            data = sql_data_node._read_as("fake query", MyCustomObject)

        assert isinstance(data, list)
        assert isinstance(data[0], MyCustomObject)
        assert isinstance(data[1], MyCustomObject)
        assert isinstance(data[2], MyCustomObject)
        assert isinstance(data[3], MyCustomObject)
        assert isinstance(data[4], MyCustomObject)
        assert isinstance(data[5], MyCustomObject)

        assert data[0].foo == "baz"
        assert data[0].bar == "qux"
        assert data[1].foo == "quux"
        assert data[1].bar == "quuz"
        assert data[2].foo == "corge"
        assert data[2].bar is None
        assert data[3].foo is None
        assert data[3].bar == "grault"
        assert data[4].foo is None
        assert data[4].bar is None
        assert data[4].kwargs["KWARGS_KEY"] == "KWARGS_VALUE"
        assert data[5].foo is None
        assert data[5].bar is None
        assert len(data[5].args) == 0
        assert len(data[5].kwargs) == 0

        with mock.patch("sqlalchemy.engine.Engine.connect") as engine_mock:
            cursor_mock = engine_mock.return_value.__enter__.return_value
            cursor_mock.execute.return_value = []
            data_2 = sql_data_node._read_as("fake query", MyCustomObject)
        assert isinstance(data_2, list)
        assert len(data_2) == 0

    @pytest.mark.parametrize(
        "data,written_data,called_func",
        [
            (pd.DataFrame([{"a": 1, "b": 2}, {"a": 3, "b": 4}]), [{"a": 1, "b": 2}, {"a": 3, "b": 4}], "_insert_dicts"),
            ([{"a": 1, "b": 2}, {"a": 3, "b": 4}], [{"a": 1, "b": 2}, {"a": 3, "b": 4}], "_insert_dicts"),
            ({"a": 1, "b": 2}, [{"a": 1, "b": 2}], "_insert_dicts"),
            ([(1, 2), (3, 4)], [(1, 2), (3, 4)], "_insert_tuples"),
            ([[1, 2], [3, 4]], [[1, 2], [3, 4]], "_insert_tuples"),
            ((1, 2), [(1, 2)], "_insert_tuples"),
            ([1, 2, 3, 4], [(1,), (2,), (3,), (4,)], "_insert_tuples"),
            ("foo", [("foo",)], "_insert_tuples"),
            (None, [(None,)], "_insert_tuples"),
            (np.array([1, 2, 3, 4]), [(1,), (2,), (3,), (4,)], "_insert_tuples"),
            (np.array([np.array([1, 2]), np.array([3, 4])]), [[1, 2], [3, 4]], "_insert_tuples"),
            ([], None, None),
            (pd.DataFrame([]), None, None),
            (np.array([]), None, None),
        ],
    )
    def test_write(self, data, written_data, called_func):
        dn = SQLDataNode(
            "foo",
            Scope.PIPELINE,
            properties={
                "db_username": "sa",
                "db_password": "foobar",
                "db_name": "datanode",
                "db_engine": "mssql",
                "read_query": "SELECT * from foo",
                "write_table": "foo",
            },
        )

        dn2 = SQLDataNode(
            "foo",
            Scope.PIPELINE,
            properties={
                "db_name": "datanode",
                "db_engine": "sqlite",
                "read_query": "SELECT * from foo",
                "write_table": "foo",
            },
        )

        with mock.patch("sqlalchemy.engine.Engine.connect") as engine_mock, mock.patch(
            "src.taipy.core.data.sql.SQLDataNode._create_table"
        ) as create_table_mock:
            cursor_mock = engine_mock.return_value.__enter__.return_value
            cursor_mock.execute.side_effect = None

            # Test write empty list
            if called_func is None:
                with mock.patch("src.taipy.core.data.sql.SQLDataNode._insert_dicts") as insert_dicts_mock, mock.patch(
                    "src.taipy.core.data.sql.SQLDataNode._insert_tuples"
                ) as insert_tuples_mock:
                    dn._write(data)
                    dn2._write(data)
                    insert_dicts_mock.assert_not_called()
                    insert_tuples_mock.assert_not_called()
                    engine_mock.assert_not_called()
                    create_table_mock.assert_not_called()
                return

            with mock.patch(f"src.taipy.core.data.sql.SQLDataNode.{called_func}") as insert_mock:
                dn._write(data)
                insert_mock.assert_called_once_with(written_data, create_table_mock.return_value, cursor_mock)
            with mock.patch(f"src.taipy.core.data.sql.SQLDataNode.{called_func}") as insert_mock:
                dn2._write(data)
                insert_mock.assert_called_once_with(written_data, create_table_mock.return_value, cursor_mock)
