#!/usr/bin/env python3

import os
import hashlib
from collections import defaultdict
import argparse
import sys

def calculate_file_hash(filepath, algorithm='md5', buffer_size=65536):
    """Calculate hash of a file using specified algorithm."""
    if algorithm == 'md5':
        hasher = hashlib.md5()
    elif algorithm == 'sha1':
        hasher = hashlib.sha1()
    elif algorithm == 'sha256':
        hasher = hashlib.sha256()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    with open(filepath, 'rb') as file:
        buffer = file.read(buffer_size)
        while len(buffer) > 0:
            hasher.update(buffer)
            buffer = file.read(buffer_size)
    
    return hasher.hexdigest()

def find_duplicate_files(directory, hash_algorithm='md5', exclude_extensions=None):
    """Find duplicate files in the given directory and its subdirectories.
    
    Args:
        directory: The root directory to scan
        hash_algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256')
        exclude_extensions: List of file extensions to exclude (e.g. ['.tmp', '.log'])
    """
    # First group files by size (files with different sizes can't be duplicates)
    print(f"Scanning directory: {directory}")
    size_to_files = defaultdict(list)
    
    # First pass: collect all files and their sizes
    print("Collecting file information...")
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            # Skip files with excluded extensions
            if exclude_extensions and any(filepath.lower().endswith(ext.lower()) for ext in exclude_extensions):
                continue
                
            try:
                size = os.path.getsize(filepath)
                size_to_files[size].append(filepath)
            except (IOError, OSError) as e:
                print(f"Error getting size of file {filepath}: {e}", file=sys.stderr)
    
    # Filter out sizes with only one file (these can't be duplicates)
    potential_duplicates = {size: file_list for size, file_list in size_to_files.items() 
                           if len(file_list) > 1}
    
    if not potential_duplicates:
        print("No duplicate files found based on file size.")
        return {}
    
    # Second pass: compare file hashes for potential duplicates
    print(f"Checking file hashes using {hash_algorithm}...")
    hash_to_files = defaultdict(list)
    
    total_checked = 0
    total_to_check = sum(len(files) for files in potential_duplicates.values())
    
    for size, file_list in potential_duplicates.items():
        for filepath in file_list:
            try:
                file_hash = calculate_file_hash(filepath, hash_algorithm)
                hash_to_files[file_hash].append(filepath)
                total_checked += 1
                if total_checked % 10 == 0 or total_checked == total_to_check:
                    print(f"Progress: {total_checked}/{total_to_check} files checked", end='\r')
            except (IOError, OSError) as e:
                print(f"Error processing file {filepath}: {e}", file=sys.stderr)
    
    print()  # New line after progress indicator
    
    # Filter out unique files
    duplicate_files = {file_hash: file_list for file_hash, file_list in hash_to_files.items() 
                      if len(file_list) > 1}
    
    return duplicate_files

def format_size(size_bytes):
    """Format size in bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024 or unit == 'TB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

def main():
    parser = argparse.ArgumentParser(description='Find duplicate files in a directory')
    parser.add_argument('directory', help='Directory to scan for duplicates')
    parser.add_argument('--algorithm', choices=['md5', 'sha1', 'sha256'], default='md5',
                        help='Hash algorithm to use (default: md5)')
    parser.add_argument('--output', help='Output file to write results (default: stdout)')
    parser.add_argument('--exclude', nargs='+', metavar='EXT',
                        help='File extensions to exclude (e.g. .tmp .log .cache)')
    args = parser.parse_args()
    
    # Process excluded extensions
    exclude_extensions = args.exclude
    if exclude_extensions:
        # Add dots to extensions if they don't have them
        exclude_extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in exclude_extensions]
        print(f"Excluding files with extensions: {', '.join(exclude_extensions)}")
    
    duplicates = find_duplicate_files(args.directory, args.algorithm, exclude_extensions)
    
    # Prepare output stream
    output_stream = open(args.output, 'w') if args.output else sys.stdout
    
    if not duplicates:
        print("No duplicate files found.", file=output_stream)
        if args.output:
            output_stream.close()
        return
    
    duplicate_count = sum(len(files) for files in duplicates.values()) - len(duplicates)
    print(f"\nFound {duplicate_count} duplicate files across {len(duplicates)} groups:", file=output_stream)
    
    # Calculate potential space savings
    space_savings = 0
    for file_hash, file_list in duplicates.items():
        if file_list:
            # Assume the size of the first file is the same for all duplicates
            file_size = os.path.getsize(file_list[0])
            # We could save space equal to (number of duplicates - 1) * file size
            space_savings += (len(file_list) - 1) * file_size
    
    print(f"Potential space savings: {format_size(space_savings)}", file=output_stream)
    
    for file_hash, file_list in duplicates.items():
        if file_list:
            size = os.path.getsize(file_list[0])
            print(f"\nDuplicate files with hash {file_hash} ({format_size(size)}):", file=output_stream)
            for filepath in file_list:
                print(f"  {filepath}", file=output_stream)
    
    if args.output:
        print(f"Results written to {args.output}")
        output_stream.close()

if __name__ == "__main__":
    main()