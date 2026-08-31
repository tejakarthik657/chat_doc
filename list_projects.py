import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Try different env file paths
for path in [".env", "rag-backend/.env", "../.env"]:
    if os.path.exists(path):
        load_dotenv(path)
        break

mongodb_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
db_name = os.environ.get("DB_NAME", "rag_db")

client = MongoClient(mongodb_url)
db = client[db_name]

print("\n==================== ACTIVE PROJECTS ====================")
projects = list(db["projects"].find())
if not projects:
    print("No projects found.")
else:
    for idx, p in enumerate(projects, 1):
        print(f"{idx}. Name:      {p.get('name')}")
        print(f"   Proj ID:   {p.get('_id')}")
        print(f"   User ID:   {p.get('user_id')}")
        print(f"   Status:    {p.get('status')}")
        print(f"   URL:       {p.get('website_url')}")
        print("-" * 57)
print("=========================================================\n")
client.close()
