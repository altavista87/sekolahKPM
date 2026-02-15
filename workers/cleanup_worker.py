"""Cleanup worker for maintenance tasks."""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_temp_files(temp_dir: str = "./tmp", max_age_hours: int = 24):
    """Clean up old temporary files."""
    temp_path = Path(temp_dir)
    if not temp_path.exists():
        return
    
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    deleted = 0
    
    for file_path in temp_path.iterdir():
        if file_path.is_file():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime < cutoff:
                try:
                    file_path.unlink()
                    deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
    
    logger.info(f"Cleaned up {deleted} temp files")
    return deleted


def cleanup_old_uploads(upload_dir: str = "./uploads", max_age_days: int = 30):
    """Clean up old uploaded files."""
    upload_path = Path(upload_dir)
    if not upload_path.exists():
        return
    
    cutoff = datetime.now() - timedelta(days=max_age_days)
    deleted = 0
    
    for file_path in upload_path.iterdir():
        if file_path.is_file():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime < cutoff:
                try:
                    file_path.unlink()
                    deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
    
    logger.info(f"Cleaned up {deleted} upload files")
    return deleted


def run_cleanup():
    """Run all cleanup tasks."""
    logger.info("Starting cleanup worker")
    
    cleanup_temp_files()
    cleanup_old_uploads()
    
    logger.info("Cleanup complete")


if __name__ == "__main__":
    run_cleanup()
