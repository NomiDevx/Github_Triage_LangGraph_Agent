from myapp.processor import process_items

def run():
    items = []
    result = process_items(items)
    print("Processed:", result)
