from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["veridoc"]

# Check all collections
print("=== Full Database Status ===")
print(f"Users: {db['users'].count_documents({})}")
print(f"Documents: {db['documents'].count_documents({})}")
print(f"Chunks: {db['chunks'].count_documents({})}")

# List all documents
if db['documents'].count_documents({}) > 0:
    print("\n=== All Documents ===")
    for doc in db['documents'].find():
        print(f"\nDoc ID: {doc['_id']}")
        print(f"  Filename: {doc.get('filename')}")
        print(f"  Status: {doc.get('status')}")
        print(f"  Page Count: {doc.get('page_count')}")
        print(f"  Uploaded: {doc.get('uploaded_at')}")
else:
    print("\n⚠️ No documents found in database")

# Check if there are documents on disk
import os
uploads_dir = "storage/uploads"
if os.path.exists(uploads_dir):
    print(f"\n=== Files on Disk ===")
    for root, dirs, files in os.walk(uploads_dir):
        for file in files:
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            print(f"{filepath} ({size} bytes)")
else:
    print(f"\n⚠️ Storage directory not found: {uploads_dir}")

client.close()
