"""File System Tools - Modified files tracking."""

_modified_files: set = set()


def get_modified_files() -> list:
    return list(_modified_files)


def reset_modified_files():
    _modified_files.clear()


def _track_modified(file_path: str):
    _modified_files.add(file_path)
