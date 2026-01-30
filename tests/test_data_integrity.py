import pytest
import os
import zlib

# Sizes in bytes
SIZES = [
    512,
    1024,              # 1KB
    128 * 1024,        # 128KB
    256 * 1024,        # 256KB
    512 * 1024,        # 512KB
    1024 * 1024,       # 1MB
    2 * 1024 * 1024,   # 2MB
    4 * 1024 * 1024,   # 4MB
]

# Patterns as (name, bytes)
# 0x0000 -> 2 bytes of zeros
# 0x1111 -> 2 bytes of 0x11
PATTERNS = [
    ("0x0000", b"\x00\x00"),
    ("0x1111", b"\x11\x11"),
    ("0x1010", b"\x10\x10"),
    ("0x0101", b"\x01\x01"),
    ("random", None),
]

def get_chunk_generator(pattern_bytes, total_size, chunk_size=65536):
    """Yields chunks of data based on the pattern."""
    bytes_generated = 0
    while bytes_generated < total_size:
        size_to_generate = min(chunk_size, total_size - bytes_generated)
        
        if pattern_bytes is None:
            # Random data
            chunk = os.urandom(size_to_generate)
        else:
            # Repeating pattern
            repeats = (size_to_generate + len(pattern_bytes) - 1) // len(pattern_bytes)
            full_pattern = pattern_bytes * repeats
            chunk = full_pattern[:size_to_generate]
            
        yield chunk
        bytes_generated += len(chunk)

def get_size_label(s):
    if s < 1024:
        return f"{s}b"
    elif s < 1024 * 1024:
        return f"{s//1024}kb"
    else:
        return f"{s//(1024*1024)}mb"

@pytest.mark.integrity
@pytest.mark.parametrize("size", SIZES, ids=[get_size_label(s) for s in SIZES])
@pytest.mark.parametrize("pattern_name,pattern_bytes", PATTERNS)
def test_data_integrity(test_dir, size, pattern_name, pattern_bytes):
    """
    Writes data of specific size and pattern to NFS, then reads verification.
    Uses CRC32 for speed and memory efficiency (calculates on the fly).
    """
    filename = f"integrity_{pattern_name}_{get_size_label(size)}.dat"
    filepath = os.path.join(test_dir, filename)
    
    # Write and calculate CRC
    write_crc = 0
    with open(filepath, "wb") as f:
        for chunk in get_chunk_generator(pattern_bytes, size):
            # zlib.crc32 computes checksum; passing previous result chains it
            write_crc = zlib.crc32(chunk, write_crc)
            f.write(chunk)
            
    # Force sync to ensure data is on server
    with open(filepath, "r+") as f:
        os.fsync(f.fileno())

    # Read and calculate CRC
    read_crc = 0
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            read_crc = zlib.crc32(chunk, read_crc)
            
    assert write_crc == read_crc, f"CRC mismatch for {pattern_name} size {get_size_label(size)}"
    
    # Explicit cleanup to save space during test run if many tests run
    try:
        os.remove(filepath)
    except OSError:
        pass
