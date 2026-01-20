import os
import time
import pytest

def test_file_create_read_write(test_dir):
    """Test basic file creation, writing, and reading."""
    file_path = os.path.join(test_dir, "hello.txt")
    content = "Hello, NFS World!"
    
    # Write
    with open(file_path, "w") as f:
        f.write(content)
    
    assert os.path.exists(file_path)
    
    # Read
    with open(file_path, "r") as f:
        read_content = f.read()
    
    assert read_content == content

def test_file_append(test_dir):
    """Test appending to a file."""
    file_path = os.path.join(test_dir, "append.txt")
    
    with open(file_path, "w") as f:
        f.write("Line 1\n")
        
    with open(file_path, "a") as f:
        f.write("Line 2\n")
        
    with open(file_path, "r") as f:
        lines = f.readlines()
        
    assert len(lines) == 2
    assert lines[0] == "Line 1\n"
    assert lines[1] == "Line 2\n"

def test_directory_operations(test_dir):
    """Test creating and removing subdirectories."""
    sub_dir = os.path.join(test_dir, "subdir")
    os.makedirs(sub_dir)
    assert os.path.isdir(sub_dir)
    
    nested_file = os.path.join(sub_dir, "nested.txt")
    with open(nested_file, "w") as f:
        f.write("nested")
    assert os.path.exists(nested_file)
    
    os.remove(nested_file)
    assert not os.path.exists(nested_file)
    
    os.rmdir(sub_dir)
    assert not os.path.exists(sub_dir)

def test_large_file_io(test_dir):
    """Test writing and reading a larger file (e.g. 1MB)."""
    file_path = os.path.join(test_dir, "large_file.bin")
    size = 1024 * 1024 # 1MB
    data = os.urandom(size)
    
    with open(file_path, "wb") as f:
        f.write(data)
        
    assert os.path.getsize(file_path) == size
    
    with open(file_path, "rb") as f:
        read_data = f.read()
        
    assert read_data == data
