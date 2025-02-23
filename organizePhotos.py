import os
from PIL import Image
from PIL.ExifTags import TAGS
import shutil
import hashlib
import re
from datetime import datetime

def extract_date_from_filename(filename):
    """
    Try to find a year in the filename using various common patterns.
    
    Args:
        filename (str): Name of the file
    
    Returns:
        str: Year if found, None otherwise
    """
    # Common patterns in photo filenames
    patterns = [
        r'20\d{2}',  # Matches years 2000-2099
        r'19\d{2}',  # Matches years 1900-1999
        r'IMG_(\d{4})',  # Common phone/camera format
        r'DSC_?(\d{4})',  # Common camera format
        r'P(\d{4})',  # Another common format
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            year = match.group(0)[-4:]  # Get last 4 digits if matched
            if 1900 <= int(year) <= datetime.now().year:
                return year
    return None

def extract_date_from_path(file_path):
    """
    Look for year patterns in the file path.
    
    Args:
        file_path (str): Full path to the file
    
    Returns:
        str: Year if found, None otherwise
    """
    path_parts = file_path.split(os.sep)
    for part in path_parts:
        # Look for directory names that are years
        if part.isdigit() and len(part) == 4:
            year = int(part)
            if 1900 <= year <= datetime.now().year:
                return part
    return None

def get_file_system_dates(file_path):
    """
    Get all available filesystem dates for the file.
    
    Args:
        file_path (str): Path to the file
    
    Returns:
        list: List of potential years from file system dates
    """
    dates = []
    try:
        # Get modification time
        mtime = os.path.getmtime(file_path)
        dates.append(datetime.fromtimestamp(mtime).year)
        
        # Get creation time
        ctime = os.path.getctime(file_path)
        dates.append(datetime.fromtimestamp(ctime).year)
        
        # Get access time
        atime = os.path.getatime(file_path)
        dates.append(datetime.fromtimestamp(atime).year)
    except Exception:
        pass
    
    return [str(year) for year in dates]

def get_exif_year(file_path):
    """
    Extract year from EXIF data with additional parsing.
    
    Args:
        file_path (str): Path to the image file
    
    Returns:
        str: Year if found, None otherwise
    """
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif()
            
            if exif_data:
                # Common EXIF date tags
                date_tags = ['DateTimeOriginal', 'DateTime', 'CreateDate', 'DateTimeDigitized']
                
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    
                    if tag_name in date_tags and value:
                        # Try different date formats
                        date_patterns = [
                            r'(\d{4})[:-]',  # Matches YYYY: or YYYY-
                            r'(\d{4})',      # Just matches YYYY
                        ]
                        
                        for pattern in date_patterns:
                            match = re.search(pattern, str(value))
                            if match:
                                year = match.group(1)
                                if 1900 <= int(year) <= datetime.now().year:
                                    return year
    except Exception:
        pass
    return None

def get_photo_year(file_path):
    """
    Try multiple methods to determine the year a photo was taken.
    
    Args:
        file_path (str): Path to the image file
    
    Returns:
        tuple: (year, source_description)
    """
    # 1. Try EXIF data first
    year = get_exif_year(file_path)
    if year:
        return year, "EXIF metadata"
    
    # 2. Try filename
    filename = os.path.basename(file_path)
    year = extract_date_from_filename(filename)
    if year:
        return year, "filename pattern"
    
    # 3. Try path
    year = extract_date_from_path(file_path)
    if year:
        return year, "folder name"
    
    # 4. Try file system dates
    fs_dates = get_file_system_dates(file_path)
    if fs_dates:
        # Use the oldest date as it's most likely to be the original
        year = str(min(int(y) for y in fs_dates))
        if year != "1970":  # Filter out Unix epoch
            return year, "file system date"
    
    return None, None

def generate_unique_filename(destination_path, original_filename):
    """
    Generate a unique filename to prevent overwrites.
    
    Args:
        destination_path (str): Directory where file will be saved
        original_filename (str): Original filename
    
    Returns:
        str: Unique filename
    """
    # Split filename into name and extension
    name, ext = os.path.splitext(original_filename)
    
    # Counter for unique filenames
    counter = 1
    
    # Generate unique filename
    while True:
        # If first attempt, use original filename
        if counter == 1:
            new_filename = original_filename
        else:
            # Add counter before extension
            new_filename = f"{name}_({counter}){ext}"
        
        # Full path of potential new file
        full_path = os.path.join(destination_path, new_filename)
        
        # If file doesn't exist, we can use this filename
        if not os.path.exists(full_path):
            return new_filename
        
        counter += 1

def calculate_file_hash(file_path):
    """
    Calculate MD5 hash of a file to detect exact duplicates.
    
    Args:
        file_path (str): Path to the file
    
    Returns:
        str: MD5 hash of the file
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def organize_photos(source_dir, destination_dir, skip_duplicates=True):
    """
    Organize photos from source directory into year-based folders in destination directory.
    
    Args:
        source_dir (str): Root directory containing photos in nested folders
        destination_dir (str): Root directory where organized photos will be saved
        skip_duplicates (bool): Whether to skip files that are exact duplicates
    """
    # Create destination directory if it doesn't exist
    os.makedirs(destination_dir, exist_ok=True)
    
    # Supported photo file extensions
    photo_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp', '.raw', '.heic', '.CR2'}
    
    # Track processed file hashes to avoid duplicates
    processed_file_hashes = set()
    
    # Statistics
    stats = {
        'total_processed': 0,
        'successfully_dated': 0,
        'date_sources': {},
        'undated': 0,
        'duplicates_skipped': 0
    }
    
    print(f"\nDebug: Starting to scan directory: {source_dir}")
    if not os.path.exists(source_dir):
        print(f"Error: Source directory '{source_dir}' does not exist!")
        return

    print(f"Debug: Looking for files with these extensions: {photo_extensions}")
    
    # Walk through source directory
    for root, dirs, files in os.walk(source_dir):
        print(f"\nDebug: Scanning directory: {root}")
        print(f"Debug: Found {len(files)} files in this directory")
        if len(files) > 0:
            print(f"Debug: First few files found: {files[:5]}")
        for filename in files:
            file_extension = os.path.splitext(filename)[1].lower()
            print(f"Debug: Checking file: {filename} (extension: {file_extension})")
            if file_extension in photo_extensions:
                file_path = os.path.join(root, filename)
                stats['total_processed'] += 1
                
                # Calculate file hash first to check for duplicates
                file_hash = calculate_file_hash(file_path)
                if skip_duplicates and file_hash in processed_file_hashes:
                    print(f"Skipping duplicate file: {filename}")
                    stats['duplicates_skipped'] += 1
                    continue
                
                # Get the year and method used
                photo_year, date_source = get_photo_year(file_path)
                
                if photo_year:
                    stats['successfully_dated'] += 1
                    stats['date_sources'][date_source] = stats['date_sources'].get(date_source, 0) + 1
                    
                    year_dir = os.path.join(destination_dir, photo_year)
                    os.makedirs(year_dir, exist_ok=True)
                    
                    # Generate unique filename
                    unique_filename = generate_unique_filename(year_dir, filename)
                    destination_path = os.path.join(year_dir, unique_filename)
                    
                    # Copy the file
                    shutil.copy2(file_path, destination_path)
                    processed_file_hashes.add(file_hash)
                    
                    print(f"Copied {filename} to {year_dir} as {unique_filename} (Date from: {date_source})")
                else:
                    stats['undated'] += 1
                    # Create and use unknown folder
                    unknown_dir = os.path.join(destination_dir, "unknown")
                    os.makedirs(unknown_dir, exist_ok=True)
                    
                    # Generate unique filename for unknown folder
                    unique_filename = generate_unique_filename(unknown_dir, filename)
                    destination_path = os.path.join(unknown_dir, unique_filename)
                    
                    # Copy the file
                    shutil.copy2(file_path, destination_path)
                    processed_file_hashes.add(file_hash)
                    
                    print(f"Moved {filename} to unknown folder as {unique_filename} (Date could not be determined)")
    
    # Print summary
    print("\nProcessing Summary:")
    print(f"Total files processed: {stats['total_processed']}")
    print(f"Successfully dated and organized: {stats['successfully_dated']}")
    print(f"Duplicates skipped: {stats['duplicates_skipped']}")
    print(f"Unable to determine date: {stats['undated']}")
    print("\nDate sources used:")
    for source, count in stats['date_sources'].items():
        print(f"  {source}: {count} files")

def main():
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Organize photos into folders by year taken.'
    )
    parser.add_argument(
        'source',
        help='Source directory containing photos to organize'
    )
    parser.add_argument(
        'destination',
        help='Destination directory where organized photos will be stored'
    )
    parser.add_argument(
        '--keep-duplicates',
        action='store_true',
        help='Keep duplicate files instead of skipping them'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if source directory exists
    if not os.path.exists(args.source):
        print(f"Error: Source directory '{args.source}' does not exist!")
        return
    
    # Organize photos
    organize_photos(
        args.source,
        args.destination,
        skip_duplicates=not args.keep_duplicates
    )

if __name__ == "__main__":
    main()