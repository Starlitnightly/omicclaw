"""
File Helpers - File Path and Type Utilities
============================================
Utility functions for file path resolution and type checking.
"""

from pathlib import Path


def resolve_browse_path(file_root, rel_path):
    """Resolve relative path within file root, preventing directory traversal.

    Args:
        file_root: Root directory path (Path object)
        rel_path: Relative path string

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path is outside file root
    """
    rel_path = rel_path or ''
    target = (file_root / rel_path).resolve()
    if target != file_root and file_root not in target.parents:
        raise ValueError('Invalid path')
    return target


def is_allowed_text_file(path_obj):
    """Check if file is an allowed text file type.

    Args:
        path_obj: Path object to check

    Returns:
        Boolean indicating if file type is allowed
    """
    allowed = {
        '.txt', '.py', '.md', '.json', '.csv', '.tsv', '.yaml', '.yml', '.log',
        '.ini', '.toml', '.js', '.css', '.html'
    }
    return path_obj.suffix.lower() in allowed


def is_image_file(path_obj):
    """Check if file is an image file.

    Args:
        path_obj: Path object to check

    Returns:
        Boolean indicating if file is an image
    """
    return path_obj.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp'}


def is_notebook_file(path_obj):
    """Check if file is a Jupyter notebook.

    Args:
        path_obj: Path object to check

    Returns:
        Boolean indicating if file is a notebook
    """
    return path_obj.suffix.lower() == '.ipynb'


def is_h5ad_file(path_obj):
    """Check if file is an h5ad AnnData file.

    Args:
        path_obj: Path object to check

    Returns:
        Boolean indicating if file is h5ad
    """
    return path_obj.suffix.lower() == '.h5ad'
