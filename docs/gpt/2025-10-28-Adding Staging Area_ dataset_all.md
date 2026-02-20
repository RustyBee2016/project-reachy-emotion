**Title: 2025-10-28-Adding Staging Area\_ dataset_all**

**Codex wrote:**

\[MEMORY BANK: ACTIVE\] I can't wire apps/api/app/routers/promote.py
yet---neither that path nor a promote_service module exists in the
workspace. Could you confirm the correct backend directory structure (or
point me to the service implementation) so I can proceed once the files
are in place? \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

**My response:**

We need to discuss the promotion workflow. As I understand it, the
videos move through the system as follows: Newly generated videos are
saved in the /temp folder. The user views and classify videos from the
/temp folder. Classified videos are stored in the /dataset_all folder.
Random videos (e.g. 70%) will be selected from /dataset_all and promoted
to the /train folder (used for model training/fine-tuning). Random
videos (e.g. 30%) will be selected from /dataset_all and promoted to the
/test folder (used for model testing/validation).

Do you agree with this summary of the promotion workflow?

you wrote: Could you confirm the correct backend directory structure (or
point me to the service implementation) so I can proceed once the files
are in place?

Do you need access to an Ubuntu 2 path in order to build a
promote_service module in the workspace?

Tell me in advance if you need access to Ubuntu 2 directories for
front-end development (of the promotion process, etc.). I will connect
the mounted drives and provide the required permissions.

If not, what is the process to construct the backend directory structure
or the (promotion) service implementation? \_\_\_\_\_\_\_\_\_\_\_\_

Note: Be careful accessing files from the
\'reachy_08.3_msi-ds_frontend\' directory. This directory serves as a
reference only because the web app was developed on Ubuntu 2. You can
sample files as required, but remember that paths will need to be
adjusted.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ -

**My prompt:** ADD: /videos/dataset_all

Before we move on to the scaffold, We should take a step back and
consider the promotion workflow. You wrote: Your summary is close, but
it doesn't quite match the architecture captured in the current
requirements: New clips land in /videos/temp/. After review and
labeling, accepted items are promoted directly from temp into either
/videos/train/ (with a label) or /videos/test/ (label must remain NULL)
while metadata is updated in Postgres via the promotion service. There
isn't a canonical /videos/dataset_all/ stage in the documented flow; the
train/test splits together effectively represent the curated dataset.
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ I agree with your comment that
the /videos/dataset_all folder configuration does not match the current
requirements. The point is the requirements should be updated for the
following purpose: /videos/dataset_all should store ALL of the
classified videos. Videos will be RANDOMLY selected from
/videos/dataset_all for training purposes. Since the dataset_all folder
will continue to grow over time, random selections will be different
during each training or fine-tuning run. Nonlabeled videos will be
randomly selected from videos/temp AND moved to /videos/test; the user
will never view these videos, so they cannot be stored in the
videos/train folder (and used for training/fine-tuning.) The important
point is that by using dataset_all as a staging area, the training set
(selected from videos/dataset_all) can have an infinite number of
different labeled videos each time the model needs to be fine-tuned. Do
you understand my explanation? Do you agree with the need and
effectiveness of /videos/dataset_all in the workflow?

CODEX RESPONSE:

\[MEMORY BANK: ACTIVE\] I understand your rationale, and introducing a
dedicated /videos/dataset_all/ stage can work---but it does change
several documented assumptions. To make it effective:

1\. **Ingest/label flow**

a\. After human review, accepted clips should move from /videos/temp/ →

/videos/dataset_all/ while preserving labels in Postgres.

b\. /videos/train/ and /videos/test/ become *derived* splits built by
selecting from

dataset_all instead of holding the long-lived canonical copies.

2\. **Promotion semantics**

a\. The promotion service now has two modes:

i\. **Dataset ingestion**: user-approved move into dataset_all (with
label).

ii\. **Training/Test selection**: randomly sample from dataset_all

(respecting class balance) and copy---or snapshot---to train/test for a

given training run.

b\. We still need to guarantee that /videos/test/ contains only
unlabeled clips if

the evaluation policy demands that, so the service should enforce label
IS

NULL for those copy targets.

**3. Workflow impacts**

a\. Tests and runbooks must codify the new staging step.

b\. Requirements (storage layout, promotion rules, manifest builder)
need

updates to reflect that train/test are regenerated for each training
cycle from

dataset_all.

c\. Manifests may need to parameterize the active training run so we
don't

brute-force rebuild the entire dataset unless requested.

**4. Next steps**

a\. Update requirements.md to capture the revised directories and

responsibilities.

b\. Adjust design docs/runbooks to describe dataset_all as the curated
source

of truth.

c\. When we scaffold the promotion service, add operations for:

i\. promote_to_dataset_all(video_id, label, ...)

ii\. select_for_training(run_id, strategy=balanced_random,

test_fraction=0.3, ...)

iii\. Potentially clear_split(run_id) or version existing train/test
splits.

I agree that having /videos/dataset_all/ as the stable, ever-growing
labeled corpus gives you maximal variability for fine-tuning, while
keeping train/test lean per run. We just need to reflect that change
across the docs and implementation so the new staging semantics are
explicit before we start building the service.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ -

=================== =

**My prompt:**

Yes, I agree. It\'s time to update the following documents: 2025-10-16-
requirements_08.4.2.md (docs/gpt/2025-10-16-requirements_08.4.2.md)
requirements_08.4.2.md (memory-bank/requirements_08.4.2.md)

**CODEX RESPONSE:**

\[MEMORY BANK: ACTIVE\] Updates applied to both requirement documents,
and the changelog entry has been added.

**Key changes:**

• Storage layout now includes /videos/dataset_all/ with per-run
regeneration of

train/test.

• Architecture, workflow, API contract, and DB schema all reflect the
new staging and

sampling process (including training_run and training_selection tables).

• Observability expectations flag sampling anomalies.

• memory-bank/requirements_08.4.2.md now logs a 2025‑10‑28 changelog
entry

documenting the dataset_all update.

Let me know if you'd like copy-ready diffs or further edits before we
move on to the promotion service scaffolding.

===================================

Moving on to the promotion scaffolding
