"""Image management utilities."""

import os
import hashlib
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from PIL import Image

logger = logging.getLogger(__name__)


class ImageManager:
    """Manage uploaded and processed images."""
    
    def __init__(
        self,
        upload_dir: str = "./uploads",
        temp_dir: str = "./tmp",
        max_file_size_mb: int = 20,
        allowed_extensions: tuple = (".jpg", ".jpeg", ".png", ".pdf"),
    ):
        self.upload_dir = Path(upload_dir)
        self.temp_dir = Path(temp_dir)
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_extensions
        
        # Create directories
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def save_upload(
        self,
        file_data: bytes,
        original_filename: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Save uploaded file."""
        # Validate extension
        ext = Path(original_filename).suffix.lower()
        if ext not in self.allowed_extensions:
            raise ValueError(f"Invalid file extension: {ext}")
        
        # Validate size
        if len(file_data) > self.max_file_size:
            raise ValueError(f"File too large: {len(file_data)} bytes")
        
        # Generate unique filename
        hash_id = hashlib.md5(file_data).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_id}_{timestamp}_{hash_id}{ext}"
        
        # Save file
        filepath = self.upload_dir / filename
        with open(filepath, "wb") as f:
            f.write(file_data)
        
        # Get image info
        info = self._get_image_info(filepath)
        
        return {
            "filename": filename,
            "filepath": str(filepath),
            "original_name": original_filename,
            "size_bytes": len(file_data),
            "hash": hash_id,
            "uploaded_at": datetime.now().isoformat(),
            **info,
        }
    
    def _get_image_info(self, filepath: Path) -> Dict[str, Any]:
        """Get image metadata."""
        try:
            with Image.open(filepath) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                }
        except Exception as e:
            logger.warning(f"Could not get image info: {e}")
            return {
                "width": None,
                "height": None,
                "format": None,
                "mode": None,
            }
    
    def create_thumbnail(
        self,
        filepath: str,
        size: tuple = (300, 300),
    ) -> str:
        """Create thumbnail image."""
        path = Path(filepath)
        thumb_path = self.temp_dir / f"thumb_{path.stem}.jpg"
        
        try:
            with Image.open(path) as img:
                img.thumbnail(size)
                img = img.convert("RGB")
                img.save(thumb_path, "JPEG", quality=85)
            return str(thumb_path)
        except Exception as e:
            logger.error(f"Thumbnail creation failed: {e}")
            return filepath
    
    def cleanup_old_files(self, max_age_days: int = 7):
        """Remove old temporary files."""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        
        for filepath in self.temp_dir.iterdir():
            if filepath.is_file():
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                if mtime < cutoff:
                    try:
                        filepath.unlink()
                        logger.info(f"Deleted old file: {filepath}")
                    except Exception as e:
                        logger.error(f"Failed to delete {filepath}: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        stats = {
            "upload_dir": str(self.upload_dir),
            "temp_dir": str(self.temp_dir),
            "upload_count": 0,
            "upload_size_mb": 0,
            "temp_count": 0,
            "temp_size_mb": 0,
        }
        
        # Upload dir stats
        for filepath in self.upload_dir.iterdir():
            if filepath.is_file():
                stats["upload_count"] += 1
                stats["upload_size_mb"] += filepath.stat().st_size / (1024 * 1024)
        
        # Temp dir stats
        for filepath in self.temp_dir.iterdir():
            if filepath.is_file():
                stats["temp_count"] += 1
                stats["temp_size_mb"] += filepath.stat().st_size / (1024 * 1024)
        
        stats["upload_size_mb"] = round(stats["upload_size_mb"], 2)
        stats["temp_size_mb"] = round(stats["temp_size_mb"], 2)
        
        return stats
    
    def delete_file(self, filepath: str) -> bool:
        """Delete a file."""
        try:
            path = Path(filepath)
            if path.exists():
                path.unlink()
                return True
        except Exception as e:
            logger.error(f"Failed to delete {filepath}: {e}")
        return False
