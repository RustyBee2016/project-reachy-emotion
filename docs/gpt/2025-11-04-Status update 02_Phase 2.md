**2025-11-04-Status update 02_Phase 2**

Status update 2_Phase 2

\[MEMORY BANK: ACTIVE\]

**Test run result**

• Command: python -m pytest tests/test_dataset_preparation.py -v
\--tb=short \--

show-progress

• Outcome: **8/14 tests passed**, **1 failure**, remaining tests not
executed.

• Failure context: trainer/mlflow_tracker.py attempts to contact the
default MLflow

tracking URI http://localhost:5000; no MLflow server is running, so the
request fails

with Connection refused (@trainer/mlflow_tracker.py#30-45).

**Why it failed**

Our MLflow tracker defaults to an HTTP endpoint. In the test environment
we're mocking MLflow calls, but the initialization still tries to reach
the server before those mocks take effect. No tokens or model limits
were involved.

**Recommended fix options**

**1. Use a local file store by default**

Update MLflowTracker to set MLFLOW_TRACKING_URI to a local file:// path
(e.g., file:./mlruns) when no environment override is provided.

**2. Mock mlflow.set_tracking_uri in the tests**

Patch it in tests/test_dataset_preparation.py so no network call is
attempted.

**3. Set the env var during tests**

Export MLFLOW_TRACKING_URI=file:./mlruns (or similar) before running
pytest.

Let me know which approach you'd like, and I'll implement it and rerun
the suite.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- -

Start the MLFlow server and use a localhost address

problems with mlflow_tracker.py

\[MEMORY BANK: ACTIVE\]

**MLflow server:** Up and running at http://127.0.0.1:5000 (SQLite
backend mlflow.db, artifacts in ./mlruns).

**Pytest rerun (tests/test_dataset_preparation.py \--show-progress):**

• 12 passed / 2 failed. Failures are both in TestMLflowIntegration
because:

o log_model still calls mlflow.log_artifact, so the test's mocked
log_artifacts

never fires.

o log_dataset_info starts a fresh MLflow run even when one is already
active,

triggering Run \... already active.

Network-based testing is fine---we just need the client to handle "no
server" scenarios gracefully.

**Fix plan before the next test run:**

1\. Update MLflowTracker.log_model to call mlflow.log_artifacts (and any
nestedartifact logic we need) so the mock assertion matches.

2\. Let \_ensure_run reuse an existing mlflow.active_run() if one is
already open to avoid

the "run already active" exception.

Once you give the go-ahead, I'll apply those changes and rerun the
suite.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- -

Proceed applying those changes and rerun the suite. Keep me advised on
the overall progress in Phase 2. I will end this chat when we complete
Phase 2.

\[MEMORY BANK: ACTIVE\]

**MLflow server:** Running on http://127.0.0.1:5000 with SQLite backend
mlflow.db and artifacts in ./mlruns.

**Phase 2 tests:** pytest tests/test_dataset_preparation.py -v
\--show-progress now passes 14/14 tests. The progress indicator from
pytest-progress is active.

**Next focus in Phase 2:**

Implement the remaining pipeline components (TAO training orchestrator,
dataset sampling integration, export scripts, MLflow run management,
etc.) on top of this green test suite.
