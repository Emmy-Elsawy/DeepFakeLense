import os
import chromadb
from dotenv import load_dotenv

# Force the script to read the .env file and override manual terminal memory
load_dotenv(override=True)

# 1. Read your variable path
db_path = os.getenv("CHROMA_PERSIST_DIR", r"D:\DeepFakeLense-main\DeepFakeLense-main\my_chroma_db")

print(f"Connecting to database path: {db_path}")
client = chromadb.PersistentClient(path=db_path)

# 2. Open or create the collection
collection = client.get_or_create_collection(name="my_first_collection")

# 3. Quick test search to see if we are in the populated directory
if collection.count() > 0:
    print("\n--- DATABASE STATUS ---")
    print("📋 Active Collections:", client.list_collections())
    print("🔢 Total documents inside collection:", collection.count())
    
    print("\n🔎 Testing similarity search...")
    search_results = collection.query(
        query_texts=["Is the deepfake software working?"], 
        n_results=1 
    )
    print("📄 Found Document:", search_results['documents'])
    print("📏 Match Distance:", search_results['distances'])
else:
    print("\nThis folder is empty. Use collection.upsert() to add records to it.")
