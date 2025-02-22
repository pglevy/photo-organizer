import os
from PIL import Image
from PIL.ExifTags import TAGS
import shutil
import hashlib

def get_photo_year(file_path):
    """
    Extract the year a photo was taken from its EXIF metadata.
    
    Args:
        file_path (str): Path to the image file
    
    Returns:
        str: Year the photo was taken, or None if year cannot be determined
    """
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif()
            
            if exif_data:
                # Look for date/time original tag
                for tag_id, value in exif_data.items():
                    # Default tag_name in case the tag is not found in TAGS
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    
                    if tag_name in ['DateTimeOriginal', 'DateTime']:
                        # Extract year from date string (format: YYYY:MM:DD HH:MM:SS)
                        return value.split(':')[0]
    except (AttributeError, KeyError, IndexError):
        # Handle cases where EXIF data is missing or unreadable
        pass
    
    # Fallback: try to use file creation time
    try:
        return str(os.path.getctime(file_path)).split('.')[0][:4]
    except Exception:
        return None

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
    photo_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp', '.raw'}
    
    # Track processed file hashes to avoid duplicates
    processed_file_hashes = set()
    
    # Walk through source directory
    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            # Check if file is a photo
            if os.path.splitext(filename)[1].lower() in photo_extensions:
                file_path = os.path.join(root, filename)
                
                # Get the year of the photo
                photo_year = get_photo_year(file_path)
                
                # If year is found, organize the photo
                if photo_year:
                    year_dir = os.path.join(destination_dir, photo_year)
                    os.makedirs(year_dir, exist_ok=True)
                    
                    # Calculate file hash
                    file_hash = calculate_file_hash(file_path)
                    
                    # Check for duplicate files
                    if skip_duplicates and file_hash in processed_file_hashes:
                        print(f"Skipping duplicate file: {filename}")
                        continue
                    
                    # Generate unique filename
                    unique_filename = generate_unique_filename(year_dir, filename)
                    
                    # Copy photo to year folder
                    destination_path = os.path.join(year_dir, unique_filename)
                    shutil.copy2(file_path, destination_path)
                    
                    # Track processed file
                    processed_file_hashes.add(file_hash)
                    
                    print(f"Copied {filename} to {year_dir} as {unique_filename}")
                else:
                    print(f"Could not determine year for {filename}")

def main():
    # Example usage
    source_directory = "path/to/photos"
    destination_directory = "organized-photos"
    
    organize_photos(source_directory, destination_directory)

if __name__ == "__main__":
    main()