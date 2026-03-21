"""
Utils Package - Utility Functions
==================================
Utility modules for OmicVerse web application.
"""

from .file_helpers import (
    resolve_browse_path,
    is_allowed_text_file,
    is_image_file,
    is_notebook_file,
    is_h5ad_file,
)

from .memory_helpers import (
    estimate_var_size,
    get_process_memory_mb,
    format_size,
)

from .variable_helpers import (
    summarize_var,
    resolve_var_path,
    filter_namespace_vars,
)

from .notebook_helpers import (
    ensure_default_notebook,
    read_notebook,
    write_notebook,
    create_code_cell,
    create_markdown_cell,
    extract_code_cells,
    extract_markdown_cells,
)

__all__ = [
    # File helpers
    'resolve_browse_path',
    'is_allowed_text_file',
    'is_image_file',
    'is_notebook_file',
    'is_h5ad_file',
    # Memory helpers
    'estimate_var_size',
    'get_process_memory_mb',
    'format_size',
    # Variable helpers
    'summarize_var',
    'resolve_var_path',
    'filter_namespace_vars',
    # Notebook helpers
    'ensure_default_notebook',
    'read_notebook',
    'write_notebook',
    'create_code_cell',
    'create_markdown_cell',
    'extract_code_cells',
    'extract_markdown_cells',
]
