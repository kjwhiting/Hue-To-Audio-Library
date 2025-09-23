import os

def rename_all_files(directory_path, prefix="new-"):
    """
    Use this util to rename all files in a given folder.

    Args:
        directory_path (str): The path to the directory containing the files.
        prefix (str): The prefix to add to each file name. Defaults to "new_".
    """
    try:
        count = 1
        # Get a list of all files and directories in the specified path
        for filename in os.listdir(directory_path):
            # Construct the full old file path
            old_file_path = os.path.join(directory_path, filename)

            # Check if it's a file (and not a directory)
            if os.path.isfile(old_file_path):
                # Construct the new file name with the prefix
                new_filename = f"{prefix}{count}.jpg"
                count+=1
                # Construct the full new file path
                new_file_path = os.path.join(directory_path, new_filename)

                # Rename the file
                os.rename(old_file_path, new_file_path)
                print(f"Renamed '{filename}' to '{new_filename}'")
    except FileNotFoundError:
        print(f"Error: Directory not found at '{directory_path}'")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage:
# Replace "path/to/your/directory" with the actual path to your directory
target_directory = "images/to-convert/"
rename_all_files(target_directory)