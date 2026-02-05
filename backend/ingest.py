import os
from dotenv import load_dotenv
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# Configuration: Add all relevant Tokamak GitBook URLs here
DOCS_URLS = [
    "https://docs.tokamak.network/home/service-guide/tokamak-rollup-hub/tokamak-rollup-hub-platform",
    "https://docs.tokamak.network/home/service-guide/tokamak-rollup-hub/tokamak-rollup-hub-platform/deploy-new-rollup-chain",
]
DB_DIR = "./chroma_db"

def ingest_docs():
    print(f"🔄 Loading documentation from {len(DOCS_URLS)} sources...")
    
    docs = []
    for url in DOCS_URLS:
        try:
            print(f"   - Fetching {url}...")
            loader = WebBaseLoader(url)
            docs.extend(loader.load())
        except Exception as e:
            print(f"   ⚠️ Failed to load {url}: {e}")

    if not docs:
        print("❌ No documents loaded. Check your URLs.")
        return

    print(f"📄 Loaded {len(docs)} documents. Splitting...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(docs)

    print(f"💾 Saving {len(splits)} chunks to Vector DB...")
    
    Chroma.from_documents(
        documents=splits,
        embedding=OpenAIEmbeddings(),
        persist_directory=DB_DIR
    )
    
    print("✅ Ingestion Complete! The Architect is ready.")

if __name__ == "__main__":
    ingest_docs()
