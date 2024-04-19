from __future__ import annotations

import contextlib

import pytest

deltalake = pytest.importorskip("deltalake")

import pyarrow as pa

import daft
from daft.logical.schema import Schema


@contextlib.contextmanager
def split_small_pq_files():
    old_config = daft.context.get_context().daft_execution_config
    daft.set_execution_config(
        # Splits any parquet files >100 bytes in size
        scan_tasks_min_size_bytes=1,
        scan_tasks_max_size_bytes=100,
    )
    yield
    daft.set_execution_config(config=old_config)


PYARROW_LE_8_0_0 = tuple(int(s) for s in pa.__version__.split(".") if s.isnumeric()) < (8, 0, 0)
pytestmark = pytest.mark.skipif(PYARROW_LE_8_0_0, reason="deltalake only supported if pyarrow >= 8.0.0")


def test_deltalake_write_basic(tmp_path, base_table):
    path = tmp_path / "some_table"
    df = daft.from_arrow(base_table)
    df.write_delta(str(path))
    read_delta = deltalake.DeltaTable(str(path))
    expected_schema = Schema.from_pyarrow_schema(read_delta.schema().to_pyarrow())
    assert df.schema() == expected_schema
    assert read_delta.to_pyarrow_table() == base_table


def test_deltalake_write_overwrite(tmp_path, base_table):
    path = tmp_path / "some_table"
    df = daft.from_arrow(base_table)
    df.write_delta(str(path))
    read_delta = deltalake.DeltaTable(str(path))
    expected_schema = Schema.from_pyarrow_schema(read_delta.schema().to_pyarrow())
    assert read_delta.version() == 0
    assert df.schema() == expected_schema
    assert read_delta.to_pyarrow_table() == base_table
    df = daft.from_arrow(base_table)
    df.write_delta(str(path), mode="overwrite")
    read_delta = deltalake.DeltaTable(str(path))
    expected_schema = Schema.from_pyarrow_schema(read_delta.schema().to_pyarrow())
    assert read_delta.version() == 1
    assert df.schema() == expected_schema
    assert read_delta.to_pyarrow_table() == base_table


def test_deltalake_write_parationby(tmp_path, base_table):
    path = tmp_path / "some_table"
    df = daft.from_arrow(base_table)
    df.write_delta(str(path), partition_by="c")
    read_delta = deltalake.DeltaTable(str(path))
    expected_schema = Schema.from_pyarrow_schema(read_delta.schema().to_pyarrow())
    assert df.schema() == expected_schema
    assert read_delta.metadata().partition_columns == ["c"]