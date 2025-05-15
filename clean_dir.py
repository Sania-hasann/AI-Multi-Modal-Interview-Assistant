import os
import sys

def clear_files(directory):
    """
    Remove all files in the specified directory and its subdirectories
    while keeping the directory structure intact.
    """
    count = 0
    
    # Check if the directory exists
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        return count
    
    # Walk through all directories and files
    for root, dirs, files in os.walk(directory):
        # Remove each file
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
                print(f"Removed: {file_path}")
                count += 1
            except Exception as e:
                print(f"Error removing {file_path}: {e}")
    
    return count

if __name__ == "__main__":
    # Get directory from command line argument or use current directory
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = 'session/'
        print(f"No directory specified, using current directory: {target_dir}")
    
    # Ask for confirmation
    confirmation = input(f"This will delete ALL files in {target_dir} and its subdirectories. Continue? (y/n): ")
    
    if confirmation.lower() == 'y':
        deleted = clear_files(target_dir)
        print(f"Operation complete. {deleted} files removed.")
    else:
        print("Operation canceled.")