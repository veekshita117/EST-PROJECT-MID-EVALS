import os
import time
import requests
from stream_unzip import stream_unzip

URL = "https://api.gbif.org/v1/occurrence/download/request/0007627-261110092616502.zip"
DEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw", "parquet_mammalia")
os.makedirs(DEST_DIR, exist_ok=True)

print(f"=== STREAMING EXTRACTION FOR MAMMALIA PARQUET ===")
print(f"Source URL: {URL}")
print(f"Destination: {DEST_DIR}")

def zipped_chunks():
    with requests.get(URL, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=131072):
            if chunk:
                yield chunk

t0 = time.time()
file_count = 0
total_bytes = 0
last_report = time.time()

for file_name, file_size, unzipped_chunks in stream_unzip(zipped_chunks()):
    fn = file_name.decode("utf-8")
    target_path = os.path.join(DEST_DIR, fn)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    file_bytes = 0
    with open(target_path, "wb") as f:
        for chunk in unzipped_chunks:
            f.write(chunk)
            file_bytes += len(chunk)
    
    # If 0-byte placeholder like occurrence.parquet/000000, remove it so DuckDB doesn't complain
    if file_bytes == 0 and os.path.basename(target_path) == "000000":
        os.remove(target_path)
    else:
        total_bytes += file_bytes
        file_count += 1
    
    if time.time() - last_report >= 15:
        elapsed = time.time() - t0
        mb = total_bytes / (1024 * 1024)
        rate = mb / elapsed if elapsed > 0 else 0
        print(f"Extracted {file_count} files, {mb:.1f} MB total ({rate:.2f} MB/s)")
        last_report = time.time()

elapsed = time.time() - t0
mb = total_bytes / (1024 * 1024)
print(f"\nExtraction completed successfully!")
print(f"Total files: {file_count}, Total size: {mb:.2f} MB ({mb/1024:.2f} GB) in {elapsed:.1f}s ({mb/elapsed:.2f} MB/s)")
