from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

try:
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
    # Force a connection test
    client.admin.command('ping')
    print("✅ MongoDB Connection: OK")
    
    db = client["veridoc"]
    collections = db.list_collection_names()
    print(f"\n📊 Collections in 'veridoc' DB: {collections}")
    
    # Check each collection
    for coll_name in ['users', 'documents', 'chunks', 'chat_history']:
        count = db[coll_name].count_documents({})
        print(f"  - {coll_name}: {count} documents")
    
    # Show any documents in "processing" state
    docs_processing = list(db['documents'].find({"status": "processing"}))
    if docs_processing:
        print(f"\n⏳ Documents being processed:")
        for doc in docs_processing:
            print(f"  - {doc.get('filename')} (ID: {doc.get('_id')})")
    else:
        print(f"\n✅ No documents in processing state")
    
    client.close()
except ConnectionFailure as e:
    print(f"❌ MongoDB Connection Failed: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
