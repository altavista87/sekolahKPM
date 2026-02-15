#!/usr/bin/env python3
"""
Build script for Netlify deployment.
Prepares the codebase for serverless deployment.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path


def log(message):
    """Print build log message."""
    print(f"[BUILD] {message}")


def find_source_directory():
    """Find the edusync-evaluation source directory."""
    candidates = [
        Path("../edusync-evaluation"),  # Parent directory (local dev)
        Path("edusync-evaluation"),      # Current directory (Netlify)
        Path("/Users/sir/edusync-evaluation"),  # Absolute path
    ]
    
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    
    return None


def copy_source_files():
    """Copy necessary source files from edusync-evaluation."""
    source_dir = find_source_directory()
    
    if source_dir is None:
        log("WARNING: edusync-evaluation directory not found!")
        log("Searched in:")
        log("  - ../edusync-evaluation")
        log("  - ./edusync-evaluation")
        log("")
        log("Assuming source files are already present...")
        return
    
    log(f"Found source directory: {source_dir}")
    
    target_dirs = ["bot", "api", "database", "config", "services", "pipeline", "workers"]
    
    for dir_name in target_dirs:
        source = source_dir / dir_name
        if source.exists():
            target = Path(dir_name)
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
            log(f"Copied {dir_name}/")


def create_init_files():
    """Ensure __init__.py files exist."""
    for root, dirs, files in os.walk("."):
        if "__pycache__" in root:
            continue
        if dirs and "__init__.py" not in files:
            init_file = Path(root) / "__init__.py"
            init_file.touch()
            log(f"Created {init_file}")


def minify_for_serverless():
    """
    Remove unnecessary files to reduce function size.
    Netlify has size limits for serverless functions.
    """
    patterns_to_remove = [
        "**/*.pyc",
        "**/__pycache__",
        "**/test_*.py",
        "**/tests",
        "**/docs",
        "**/*.md",
        "**/alembic/versions/*.py",  # Keep only latest migration
    ]
    
    for pattern in patterns_to_remove:
        for path in Path(".").glob(pattern):
            if path.is_file():
                path.unlink()
                log(f"Removed {path}")
            elif path.is_dir():
                shutil.rmtree(path)
                log(f"Removed directory {path}")


def verify_structure():
    """Verify the build structure."""
    required_files = [
        "netlify/functions/telegram-webhook.py",
        "netlify/functions/health.py",
        "netlify.toml",
        "static/index.html",
    ]
    
    all_good = True
    for file_path in required_files:
        if Path(file_path).exists():
            log(f"✓ {file_path}")
        else:
            log(f"✗ MISSING: {file_path}")
            all_good = False
    
    return all_good


def main():
    """Main build process."""
    log("Starting Netlify build...")
    
    # Check if source exists (but don't fail - might be self-contained)
    source_dir = find_source_directory()
    if source_dir is None:
        log("Note: edusync-evaluation directory not found in parent.")
        log("Checking if source files are already present...")
        
        # Check if bot/ directory already exists
        if not Path("bot").exists():
            log("ERROR: Source files not found!")
            log("Please either:")
            log("  1. Place edusync-evaluation in the parent directory")
            log("  2. Run this script from a directory containing the source")
            sys.exit(1)
        else:
            log("Source files already present, skipping copy.")
    
    # Copy source files
    log("Copying source files...")
    copy_source_files()
    
    # Create __init__.py files
    log("Creating __init__.py files...")
    create_init_files()
    
    # Verify structure
    log("Verifying build structure...")
    if verify_structure():
        log("✓ Build verification passed")
    else:
        log("✗ Build verification failed")
        sys.exit(1)
    
    # Note about function size
    log("Build complete!")
    log("NOTE: Netlify Functions have a size limit.")
    log("If deployment fails due to size:")
    log("  1. Remove unused dependencies from requirements-netlify.txt")
    log("  2. Use Netlify's Large Functions addon")
    log("  3. Consider splitting into smaller functions")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
