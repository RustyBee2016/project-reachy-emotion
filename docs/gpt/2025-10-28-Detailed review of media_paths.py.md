**2025-10-28-Detailed review of media_paths.py**

**media_paths.py**

path:
/media/rusty_admin/project_data/reachy_emotion/apps/api/app/services

\[MEMORY BANK: ACTIVE\]

Here's a guided tour of media_paths.py, highlighting purpose and syntax
section by section.

1\. **Module header & imports**
(@apps/api/app/services/media_paths.py#1-12)

a\. The docstring states the module's role: filesystem helpers for media
assets.

b\. from \_\_future\_\_ import annotations lets annotations be

referenced as strings (reduces circular import issues).

c\. Standard-library imports: dataclass (lightweight data container),
Path (path

arithmetic), Iterator (type hint).

d\. The module imports Settings from our dependency layer, so helper
functions

can read video_root, base_media_url, etc.

e\. Two module-level constants define valid splits and file extensions;
storing

them centrally keeps comparisons cheap and consistent.

2\. **Error and data types**
(@apps/api/app/services/media_paths.py#14-27)

a\. InvalidSplitError subclasses ValueError. Raising this allows callers
to catch a

specific error and translate it into an HTTP 400.

b\. \@dataclass(slots=True) on VideoFile auto-generates \_\_init\_\_,
**repr**, etc.,

while slots=True keeps instances memory-efficient by predefining
attributes.

Fields capture normalized metadata about a single file (ID, split,

absolute/relative paths, size, modification timestamp).

3\. **Split validation** (@apps/api/app/services/media_paths.py#30-40)

a\. \_validate_split(split: str) -\> str: normalizes input to lowercase
and checks

membership in ALLOWED_SPLITS. Raising InvalidSplitError prevents

downstream code from wandering outside controlled directories.

b\. get_split_dir(settings, split) applies \_validate_split, then
constructs an

absolute path: Path(settings.video_root).expanduser().resolve() anchors
us

at VIDEO_ROOT, and / split_lower appends the validated subdirectory.
Using

Path arithmetic avoids manual string concatenation and resolves
symlinks.

4\. **Enumerating files** (@apps/api/app/services/media_paths.py#42-68)

a\. iter_split_files(\...) first resolves the root and target directory,
early-returning

an empty iterator if the directory doesn't exist.

b\. The nested generator \_generator() loops through sorted directory
entries. It

filters out anything that isn't a file and enforces extension rules.

c\. For each qualifying file, it calls path.stat() to capture size and
modification

time, then yields a VideoFile instance.

d\. list_split(\...) simply materializes that iterator into a list,
which is useful for

pagination or further aggregation.

5\. **Response metadata helpers**

a\. describe_video(\...) (@apps/api/app/services/media_paths.py#71-80)

transforms a VideoFile into the dict returned to API clients, including
URLs

constructed from the settings' media/thumb prefixes. Trimming trailing

slashes with rstrip(\"/\") prevents duplicated separators in the final
URLs.

b\. find_video(\...) (@apps/api/app/services/media_paths.py#83-105)
searches

across all splits. It reuses get_split_dir and the extension filter,
returning the

first matching VideoFile. This is essential for promotion/relabel flows
that

don't know where a video currently resides.

c\. split_stats(\...) (@apps/api/app/services/media_paths.py#108-115)

aggregates count and total bytes for a split, feeding the health
endpoint's

dashboard.

All of these helpers live in one module because they share the same
concerns:

• mapping logical concepts (temp, train, test) to concrete filesystem
paths,

• enforcing file hygiene rules,

• preparing API-friendly metadata.

Keeping them together ensures every router/service---whether listing
videos, promoting them, or computing health stats---applies the same
validation and formatting logic.
