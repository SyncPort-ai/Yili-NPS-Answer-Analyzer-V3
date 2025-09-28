"""
File utilities for NPS V3 system.

Provides file system operations, path management, and safe file handling.
"""

import os
import re
import shutil
import logging
from pathlib import Path
from typing import Union, Optional, List, Dict, Any
from datetime import datetime
import uuid
import json


logger = logging.getLogger(__name__)


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        directory: Directory path to ensure exists

    Returns:
        Path object for the directory

    Raises:
        OSError: If directory cannot be created
    """
    dir_path = Path(directory)
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory ensured: {dir_path}")
        return dir_path
    except Exception as e:
        logger.error(f"Failed to create directory {dir_path}: {e}")
        raise


def generate_safe_filename(
    base_name: str,
    extension: str = "",
    max_length: int = 100,
    add_timestamp: bool = False,
    add_uuid: bool = False
) -> str:
    """
    Generate safe filename for file system.

    Args:
        base_name: Base name for the file
        extension: File extension (with or without dot)
        max_length: Maximum filename length
        add_timestamp: Whether to add timestamp to filename
        add_uuid: Whether to add short UUID to filename

    Returns:
        Safe filename string
    """
    # Clean base name
    safe_name = re.sub(r'[^\w\s-]', '', base_name)
    safe_name = re.sub(r'[-\s]+', '-', safe_name)
    safe_name = safe_name.strip('-')

    # Add timestamp if requested
    if add_timestamp:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"{safe_name}_{timestamp}"

    # Add UUID if requested
    if add_uuid:
        short_uuid = uuid.uuid4().hex[:8]
        safe_name = f"{safe_name}_{short_uuid}"

    # Ensure extension starts with dot
    if extension and not extension.startswith('.'):
        extension = f".{extension}"

    # Combine and truncate if necessary
    full_name = f"{safe_name}{extension}"
    if len(full_name) > max_length:
        available_length = max_length - len(extension)
        safe_name = safe_name[:available_length]
        full_name = f"{safe_name}{extension}"

    return full_name


def safe_write_file(
    file_path: Union[str, Path],
    content: Union[str, bytes, Dict[str, Any]],
    encoding: str = 'utf-8',
    backup: bool = True
) -> Path:
    """
    Safely write content to file with optional backup.

    Args:
        file_path: Path to write file
        content: Content to write (str, bytes, or dict for JSON)
        encoding: Text encoding for string content
        backup: Whether to backup existing file

    Returns:
        Path to written file

    Raises:
        IOError: If file cannot be written
    """
    file_path = Path(file_path)

    try:
        # Create directory if needed
        ensure_directory_exists(file_path.parent)

        # Backup existing file if requested
        if backup and file_path.exists():
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")

        # Write content based on type
        if isinstance(content, dict):
            # JSON content
            with open(file_path, 'w', encoding=encoding) as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        elif isinstance(content, str):
            # Text content
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
        elif isinstance(content, bytes):
            # Binary content
            with open(file_path, 'wb') as f:
                f.write(content)
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")

        logger.info(f"File written successfully: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        raise


def safe_read_file(
    file_path: Union[str, Path],
    encoding: str = 'utf-8',
    json_content: bool = False
) -> Union[str, bytes, Dict[str, Any]]:
    """
    Safely read file content.

    Args:
        file_path: Path to read from
        encoding: Text encoding for string content
        json_content: Whether to parse as JSON

    Returns:
        File content as appropriate type

    Raises:
        IOError: If file cannot be read
        JSONDecodeError: If JSON parsing fails
    """
    file_path = Path(file_path)

    try:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if json_content:
            with open(file_path, 'r', encoding=encoding) as f:
                return json.load(f)
        else:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()

    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get comprehensive file information.

    Args:
        file_path: Path to analyze

    Returns:
        Dictionary with file information
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return {"exists": False, "path": str(file_path)}

    stat = file_path.stat()

    return {
        "exists": True,
        "path": str(file_path),
        "name": file_path.name,
        "stem": file_path.stem,
        "suffix": file_path.suffix,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
        "is_file": file_path.is_file(),
        "is_directory": file_path.is_dir(),
        "permissions": oct(stat.st_mode)[-3:]
    }


def clean_old_files(
    directory: Union[str, Path],
    pattern: str = "*",
    max_age_days: int = 7,
    max_count: Optional[int] = None,
    dry_run: bool = False
) -> List[Path]:
    """
    Clean old files from directory.

    Args:
        directory: Directory to clean
        pattern: File pattern to match
        max_age_days: Maximum age in days
        max_count: Maximum number of files to keep (None for no limit)
        dry_run: If True, only return files that would be deleted

    Returns:
        List of files that were (or would be) deleted
    """
    directory = Path(directory)
    deleted_files = []

    if not directory.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return deleted_files

    try:
        # Get files matching pattern
        files = list(directory.glob(pattern))

        # Sort by modification time (newest first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Calculate cutoff time
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)

        for file in files:
            should_delete = False

            # Check age
            if file.stat().st_mtime < cutoff_time:
                should_delete = True

            # Check count limit
            if max_count and len(files) - len(deleted_files) > max_count:
                should_delete = True

            if should_delete:
                if dry_run:
                    logger.info(f"Would delete: {file}")
                else:
                    try:
                        file.unlink()
                        logger.info(f"Deleted: {file}")
                    except Exception as e:
                        logger.error(f"Failed to delete {file}: {e}")
                        continue

                deleted_files.append(file)

        logger.info(f"Cleaned {len(deleted_files)} files from {directory}")
        return deleted_files

    except Exception as e:
        logger.error(f"Error cleaning directory {directory}: {e}")
        return deleted_files


def create_directory_structure(base_path: Union[str, Path], structure: Dict[str, Any]) -> Path:
    """
    Create directory structure from nested dictionary.

    Args:
        base_path: Base path for structure creation
        structure: Nested dictionary representing directory structure

    Returns:
        Path to created base directory

    Example:
        structure = {
            "reports": {
                "html": {},
                "json": {},
                "assets": {
                    "css": {},
                    "js": {}
                }
            },
            "logs": {}
        }
    """
    base_path = Path(base_path)

    def create_recursive(current_path: Path, struct: Dict[str, Any]):
        for name, sub_struct in struct.items():
            new_path = current_path / name
            ensure_directory_exists(new_path)

            if isinstance(sub_struct, dict):
                create_recursive(new_path, sub_struct)

    ensure_directory_exists(base_path)
    create_recursive(base_path, structure)

    logger.info(f"Created directory structure at: {base_path}")
    return base_path


def find_files(
    directory: Union[str, Path],
    pattern: str = "*",
    recursive: bool = True,
    max_depth: Optional[int] = None
) -> List[Path]:
    """
    Find files matching pattern in directory.

    Args:
        directory: Directory to search
        pattern: Glob pattern to match
        recursive: Whether to search recursively
        max_depth: Maximum recursion depth (None for unlimited)

    Returns:
        List of matching file paths
    """
    directory = Path(directory)
    found_files = []

    if not directory.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return found_files

    try:
        if recursive:
            if max_depth is None:
                found_files = list(directory.rglob(pattern))
            else:
                # Custom recursive search with depth limit
                def search_with_depth(path: Path, depth: int) -> List[Path]:
                    files = []
                    if depth >= max_depth:
                        return files

                    for item in path.iterdir():
                        if item.is_file() and item.match(pattern):
                            files.append(item)
                        elif item.is_dir():
                            files.extend(search_with_depth(item, depth + 1))

                    return files

                found_files = search_with_depth(directory, 0)
        else:
            found_files = list(directory.glob(pattern))

        # Filter to files only
        found_files = [f for f in found_files if f.is_file()]

        logger.debug(f"Found {len(found_files)} files matching '{pattern}' in {directory}")
        return found_files

    except Exception as e:
        logger.error(f"Error finding files in {directory}: {e}")
        return found_files


def copy_file_with_metadata(
    source: Union[str, Path],
    destination: Union[str, Path],
    preserve_timestamp: bool = True,
    create_dirs: bool = True
) -> Path:
    """
    Copy file preserving metadata.

    Args:
        source: Source file path
        destination: Destination file path
        preserve_timestamp: Whether to preserve timestamps
        create_dirs: Whether to create destination directories

    Returns:
        Path to copied file
    """
    source = Path(source)
    destination = Path(destination)

    try:
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if create_dirs:
            ensure_directory_exists(destination.parent)

        if preserve_timestamp:
            shutil.copy2(source, destination)
        else:
            shutil.copy(source, destination)

        logger.info(f"Copied file: {source} -> {destination}")
        return destination

    except Exception as e:
        logger.error(f"Failed to copy file {source} to {destination}: {e}")
        raise


def get_directory_size(directory: Union[str, Path]) -> Dict[str, Any]:
    """
    Calculate directory size and file count.

    Args:
        directory: Directory to analyze

    Returns:
        Dictionary with size information
    """
    directory = Path(directory)

    if not directory.exists() or not directory.is_dir():
        return {"exists": False, "path": str(directory)}

    total_size = 0
    file_count = 0
    dir_count = 0

    try:
        for item in directory.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
            elif item.is_dir():
                dir_count += 1

        return {
            "exists": True,
            "path": str(directory),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 3),
            "file_count": file_count,
            "directory_count": dir_count,
            "total_items": file_count + dir_count
        }

    except Exception as e:
        logger.error(f"Error calculating directory size for {directory}: {e}")
        return {"exists": True, "path": str(directory), "error": str(e)}


# Path validation utilities
def validate_file_path(file_path: Union[str, Path], must_exist: bool = False) -> bool:
    """
    Validate file path.

    Args:
        file_path: File path to validate
        must_exist: Whether file must exist

    Returns:
        True if path is valid
    """
    try:
        path = Path(file_path)

        # Check for invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in str(path) for char in invalid_chars):
            return False

        # Check if must exist
        if must_exist and not path.exists():
            return False

        # Check if parent directory is writable (if creating new file)
        if not must_exist and not path.exists():
            parent = path.parent
            if parent.exists() and not os.access(parent, os.W_OK):
                return False

        return True

    except Exception:
        return False


def is_safe_path(file_path: Union[str, Path], base_directory: Union[str, Path]) -> bool:
    """
    Check if file path is safe (no directory traversal).

    Args:
        file_path: File path to check
        base_directory: Base directory that path should be within

    Returns:
        True if path is safe
    """
    try:
        file_path = Path(file_path).resolve()
        base_directory = Path(base_directory).resolve()

        # Check if file path is within base directory
        return str(file_path).startswith(str(base_directory))

    except Exception:
        return False