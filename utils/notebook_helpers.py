"""
Notebook Helpers - Jupyter Notebook Utilities
==============================================
Utility functions for Jupyter notebook operations.
"""

import json
import logging
from pathlib import Path


def ensure_default_notebook(file_root):
    """Ensure default.ipynb exists in file root.

    Args:
        file_root: Root directory path (Path object)
    """
    default_path = file_root / 'default.ipynb'
    if default_path.exists():
        return

    try:
        # Try using nbformat if available
        try:
            import nbformat
            nb = nbformat.v4.new_notebook()
            nb.cells = [nbformat.v4.new_code_cell(source='')]
            with open(default_path, 'w', encoding='utf-8') as handle:
                nbformat.write(nb, handle)
        except ImportError:
            # Fallback to minimal JSON structure
            minimal = {
                "cells": [{
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": []
                }],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5
            }
            with open(default_path, 'w', encoding='utf-8') as handle:
                handle.write(json.dumps(minimal))
    except Exception as e:
        logging.error(f"Default notebook creation failed: {e}")


def read_notebook(notebook_path):
    """Read a Jupyter notebook file.

    Args:
        notebook_path: Path to notebook file

    Returns:
        Notebook dictionary

    Raises:
        FileNotFoundError: If notebook doesn't exist
        json.JSONDecodeError: If notebook is invalid JSON
    """
    with open(notebook_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_notebook(notebook_path, notebook_data):
    """Write a Jupyter notebook file.

    Args:
        notebook_path: Path to notebook file
        notebook_data: Notebook dictionary
    """
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook_data, f, indent=2)


def create_code_cell(source='', execution_count=None, outputs=None):
    """Create a code cell dictionary.

    Args:
        source: Cell source code (string or list of strings)
        execution_count: Execution count (int or None)
        outputs: Cell outputs (list or None)

    Returns:
        Code cell dictionary
    """
    return {
        "cell_type": "code",
        "execution_count": execution_count,
        "metadata": {},
        "outputs": outputs or [],
        "source": source
    }


def create_markdown_cell(source=''):
    """Create a markdown cell dictionary.

    Args:
        source: Cell source markdown (string or list of strings)

    Returns:
        Markdown cell dictionary
    """
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source
    }


def extract_code_cells(notebook_data):
    """Extract all code cells from notebook.

    Args:
        notebook_data: Notebook dictionary

    Returns:
        List of code cell dictionaries
    """
    return [cell for cell in notebook_data.get('cells', [])
            if cell.get('cell_type') == 'code']


def extract_markdown_cells(notebook_data):
    """Extract all markdown cells from notebook.

    Args:
        notebook_data: Notebook dictionary

    Returns:
        List of markdown cell dictionaries
    """
    return [cell for cell in notebook_data.get('cells', [])
            if cell.get('cell_type') == 'markdown']
