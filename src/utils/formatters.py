"""Utility functions for formatting data."""


def format_traffic(bytes_count: int) -> str:
    """Format bytes to human-readable string."""
    if bytes_count < 1024:
        return f"{bytes_count} B"

    kb = bytes_count / 1024
    if kb < 1024:
        return f"{kb:.2f} KB"

    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.2f} MB"

    gb = mb / 1024
    return f"{gb:.2f} GB"
