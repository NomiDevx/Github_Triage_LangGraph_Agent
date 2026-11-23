def process_items(items):
    # Notice: crashes if items contains None or is malformed
    results = []
    for item in items:
        result = item.strip()
        results.append(result)
    return results
