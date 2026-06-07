from store import get_all_chunks, load_store

load_store()
chunks = get_all_chunks()
files = sorted(set(c['metadata']['filepath'] for c in chunks))

print(f"Total unique files indexed: {len(files)}\n")
for f in files:
    print(f)