from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["veridoc"]

# Check collections and counts
print("=== Database Status ===")
print(f"Users: {db['users'].count_documents({})}")
print(f"Documents: {db['documents'].count_documents({})}")
print(f"Chunks: {db['chunks'].count_documents({})}")
print(f"Chat History: {db['chat_history'].count_documents({})}")

# Show sample document if exists
docs = list(db['documents'].find().limit(1))
if docs:
    print("\n=== Sample Document ===")
    for doc in docs:
        print(f"ID: {doc.get('_id')}")
        print(f"Filename: {doc.get('filename')}")
        print(f"Upload Date: {doc.get('upload_date')}")

# Show chunk count per document
chunks = list(db['chunks'].aggregate([
    {"$group": {"_id": "$document_id", "count": {"$sum": 1}}},
    {"$limit": 5}
]))
if chunks:
    print("\n=== Chunks per Document (sample) ===")
    for c in chunks:
        print(f"Document {c['_id']}: {c['count']} chunks")
else:
    print("\n⚠️  WARNING: No chunks found! Documents may not be ingested properly.")

client.close()
