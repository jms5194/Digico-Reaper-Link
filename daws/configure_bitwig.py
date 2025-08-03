import pathlib
import shutil
import sys
from logger_config import logger
import hashlib
import os


def verify_markermatic_bridge_in_user_dir():
    # Copy the Markermatic Bridge to the Bitwig extensions directory
    bridge_full_path = get_bitwig_extensions_path() / "MarkerMatic-Bridge.bwextension"
    package_full_path = "/resources/MarkerMatic-Bridge.bwextension"
    if os.path.exists(bridge_full_path):
        current_file_checksum = calculate_md5_checksum(bridge_full_path)
        package_file_checksum = calculate_md5_checksum(package_full_path)
        if current_file_checksum == package_file_checksum:
            logger.info("Markermatic Bridge is already up to date.")
            return True
        else:
            logger.info("Markermatic Bridge is outdated, copying new version.")
            copy_markermatic_bridge_to_bitwig_extensions()
    else:
        logger.info("Markermatic Bridge not found, copying new version.")
        copy_markermatic_bridge_to_bitwig_extensions()

def copy_markermatic_bridge_to_bitwig_extensions():
    destination_directory = get_bitwig_extensions_path()
    source_file = "/resources/MarkerMatic-Bridge.bwextension"
    filename = os.path.basename(source_file)
    destination_path = os.path.join(destination_directory, filename)
    if os.path.exists(destination_path):
        os.remove(destination_path)
    shutil.move(source_file, destination_path)
    logger.info(f"Extension '{filename}' copied or replaced successfully.")
    logger.info("Copied Markermatic Bridge to Bitwig extensions directory.")

def get_bitwig_extensions_path() -> pathlib.Path:
    # Return the path to the Bitwig extensions directory based on the OS
    if is_apple():
        return pathlib.Path.home() / "Documents" / "Bitwig Studio" / "Extensions"
    elif is_windows():
        return pathlib.Path.home() / "Documents" / "Bitwig Studio" / "Extensions"
    elif is_linux():
        return pathlib.Path.home() / "Bitwig Studio" / "Extensions"
    else:
        return pathlib.Path.home()
    
def is_apple() -> bool:
    """Return whether OS is macOS or OSX."""
    return sys.platform == "darwin"

def is_windows() -> bool:
    """Return whether OS is Windows."""
    return sys.platform == "win32"

def is_linux() -> bool:
    """Return whether OS is Linux."""
    return sys.platform.startswith("linux")

def calculate_md5_checksum(file_path):
        """Calculates the MD5 checksum of a given file."""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:  # Open in binary read mode
            while True:
                chunk = f.read(8192)  # Read in chunks for large files
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()