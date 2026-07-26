"""
============================================================================
  HuggingFace Model Cache Cleanup Utility
  Scans all local drives (C:, D:, E:, F:, etc.) for HuggingFace model
  caches, reports total disk space usage, and deletes on confirmation.
============================================================================
  Project: Decentralized Tamper-Resistant Civic Issue Reporting System
  Usage:   python cleanup_huggingface_cache.py
============================================================================
"""

import os
import sys
import glob
import shutil
import string
from pathlib import Path


def get_available_drives():
    """Detect all available drive letters on this Windows system."""
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append(drive)
    return drives


def get_size_bytes(path: str) -> int:
    """Recursively calculate total size of a directory in bytes."""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def format_size(size_bytes: int) -> str:
    """Format bytes into a human-readable string (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


def find_huggingface_caches(drives: list) -> list:
    """
    Search all drives for HuggingFace model cache directories.
    
    Standard HuggingFace cache locations on Windows:
      - C:\\Users\\<user>\\.cache\\huggingface\\
      - C:\\Users\\<user>\\.cache\\torch\\hub\\checkpoints\\
      - Any directory matching *\\.cache\\huggingface\\
    """
    found_caches = []
    seen_paths = set()

    # ── Standard HuggingFace cache patterns ──
    search_patterns = [
        # Primary HuggingFace Hub cache (models, datasets, tokenizers)
        os.path.join("Users", "*", ".cache", "huggingface"),
        # PyTorch Hub cache (torchvision model weights, etc.)
        os.path.join("Users", "*", ".cache", "torch"),
        # Standalone huggingface directories
        os.path.join("Users", "*", "huggingface"),
        # Broader fallback: any .cache/huggingface anywhere on the drive
        os.path.join("**", ".cache", "huggingface"),
    ]

    # ── Also check the HF_HOME and TRANSFORMERS_CACHE env vars ──
    env_paths = [
        os.environ.get("HF_HOME"),
        os.environ.get("TRANSFORMERS_CACHE"),
        os.environ.get("HUGGINGFACE_HUB_CACHE"),
        os.environ.get("TORCH_HOME"),
    ]

    for env_path in env_paths:
        if env_path and os.path.isdir(env_path):
            real = os.path.realpath(env_path)
            if real not in seen_paths:
                seen_paths.add(real)
                found_caches.append(real)

    for drive in drives:
        print(f"  Scanning {drive} ...", end="", flush=True)
        drive_found = 0

        for pattern in search_patterns:
            full_pattern = os.path.join(drive, pattern)
            try:
                # Use glob for standard patterns (non-recursive)
                if "**" not in pattern:
                    matches = glob.glob(full_pattern)
                else:
                    # Recursive glob — limit depth to avoid excessive scanning
                    # Only search top-level directories + Users
                    matches = glob.glob(full_pattern, recursive=True)

                for match in matches:
                    if os.path.isdir(match):
                        real = os.path.realpath(match)
                        if real not in seen_paths:
                            seen_paths.add(real)
                            found_caches.append(real)
                            drive_found += 1
            except (OSError, PermissionError):
                pass

        if drive_found > 0:
            print(f" found {drive_found} cache(s)")
        else:
            print(f" no caches found")

    return found_caches


def main():
    print("=" * 70)
    print("   HuggingFace Model Cache Cleanup Utility")
    print("   Scans all local drives for HuggingFace cached models")
    print("=" * 70)
    print()

    # ── Step 1: Detect available drives ──
    drives = get_available_drives()
    print(f"Detected drives: {', '.join(drives)}")
    print()

    # ── Step 2: Scan for HuggingFace caches ──
    print("Scanning for HuggingFace model caches...")
    print("-" * 70)
    caches = find_huggingface_caches(drives)
    print("-" * 70)
    print()

    if not caches:
        print("No HuggingFace model caches found on any drive.")
        print("Your system is clean!")
        return

    # ── Step 3: Calculate sizes and report ──
    print(f"Found {len(caches)} HuggingFace cache location(s):\n")
    print(f"{'#':<4} {'Path':<55} {'Size':>12}")
    print("-" * 73)

    total_bytes = 0
    cache_details = []

    for i, cache_path in enumerate(caches, 1):
        size = get_size_bytes(cache_path)
        total_bytes += size
        cache_details.append({"path": cache_path, "size": size})
        print(f"{i:<4} {cache_path:<55} {format_size(size):>12}")

    print("-" * 73)
    print(f"{'':>4} {'TOTAL SPACE OCCUPIED:':<55} {format_size(total_bytes):>12}")
    print()

    if total_bytes == 0:
        print("All cache directories are empty. Nothing to delete.")
        return

    # ── Step 4: Ask for confirmation ──
    print("=" * 70)
    print(f"  WARNING: This will permanently delete {format_size(total_bytes)}")
    print(f"  of HuggingFace cached models from {len(caches)} location(s).")
    print(f"  Models will be re-downloaded when needed by your projects.")
    print("=" * 70)
    print()

    confirmation = input("Type 'yes' to proceed with deletion: ").strip().lower()

    if confirmation != "yes":
        print("\nAborted. No files were deleted.")
        return

    # ── Step 5: Delete caches ──
    print("\nDeleting HuggingFace caches...\n")
    deleted_count = 0
    deleted_bytes = 0
    errors = []

    for detail in cache_details:
        path = detail["path"]
        size = detail["size"]
        try:
            shutil.rmtree(path)
            deleted_count += 1
            deleted_bytes += size
            print(f"  ✓ Deleted: {path} ({format_size(size)})")
        except PermissionError:
            errors.append(f"  ✗ Permission denied: {path}")
            print(f"  ✗ Permission denied: {path}")
        except Exception as e:
            errors.append(f"  ✗ Error deleting {path}: {e}")
            print(f"  ✗ Error deleting {path}: {e}")

    print()
    print("=" * 70)
    print(f"  Cleanup Complete!")
    print(f"  Deleted: {deleted_count}/{len(caches)} cache(s)")
    print(f"  Space freed: {format_size(deleted_bytes)}")
    if errors:
        print(f"  Errors: {len(errors)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
