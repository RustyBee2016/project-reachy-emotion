from __future__ import annotations

from trainer.data_roots import resolve_training_data_roots


def test_resolve_training_data_roots_defaults(tmp_path) -> None:
    roots = resolve_training_data_roots(str(tmp_path))
    assert roots.train_root == tmp_path / "train"
    assert roots.val_root == tmp_path / "test"
    assert roots.uses_run_scoped_train is False
    assert roots.uses_run_scoped_val is False


def test_resolve_training_data_roots_prefers_run_scoped_paths(tmp_path) -> None:
    run_id = "run_0007"
    run_train = tmp_path / "train" / "run" / run_id
    run_val = tmp_path / "test" / run_id
    run_train.mkdir(parents=True, exist_ok=True)
    run_val.mkdir(parents=True, exist_ok=True)

    roots = resolve_training_data_roots(str(tmp_path), run_id=run_id)
    assert roots.train_root == run_train
    assert roots.val_root == run_val
    assert roots.uses_run_scoped_train is True
    assert roots.uses_run_scoped_val is True


def test_resolve_training_data_roots_falls_back_when_missing(tmp_path) -> None:
    run_id = "run_0009"
    roots = resolve_training_data_roots(str(tmp_path), run_id=run_id)
    assert roots.train_root == tmp_path / "train"
    assert roots.val_root == tmp_path / "test"
    assert roots.uses_run_scoped_train is False
    assert roots.uses_run_scoped_val is False
