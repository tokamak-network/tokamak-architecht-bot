"""
Document Ingestion Script

Fetches documentation from Tokamak GitBook and other sources,
chunks it, and stores in the Chroma vector database.

Usage:
    python -m scripts.ingest
    python -m scripts.ingest --force  # Force re-ingestion
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.services.embedding_service import get_embedding_service
from app.services.rag_service import get_rag_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Documentation URLs to ingest
DOCS_URLS = [
    # Tokamak Rollup Hub Documentation
    "https://docs.tokamak.network/home/service-guide/tokamak-rollup-hub/tokamak-rollup-hub-platform",
    "https://docs.tokamak.network/home/service-guide/tokamak-rollup-hub/tokamak-rollup-hub-platform/deploy-new-rollup-chain",
    "https://docs.tokamak.network/home/service-guide/tokamak-rollup-hub/tokamak-rollup-hub-platform/manage-rollup-chain",
    # Add more URLs as needed
]

# Additional documentation content (inline for reliability)
ADDITIONAL_DOCS = [
    {
        "content": """
# Tokamak Rollup Hub - Key Configuration Parameters

## Network Configuration
- **Network Type**: Choose between Mainnet and Testnet. Testnet (Sepolia) is recommended for development.
- **Chain Name**: 1-63 alphanumeric characters. This identifies your rollup chain.

## L1 Connection
- **L1 RPC URL**: Ethereum execution layer endpoint (e.g., Infura, Alchemy, or your own node)
- **L1 Beacon URL**: Ethereum beacon chain endpoint for consensus layer data

## L2 Block Configuration
- **L2 Block Time**: Time between L2 blocks (1-255 seconds, default: 2 seconds)
  - Lower = faster transactions, higher costs
  - Higher = slower transactions, lower costs
  - Recommended: 2 seconds for most use cases

## Batch Configuration
- **Batch Submission Frequency**: How often to submit batches to L1 (must be multiple of 12)
  - Default: 1440 seconds (24 minutes)
  - Lower = faster finality, higher costs
  - Higher = slower finality, lower costs

- **Output Root Frequency**: How often to submit state roots to L1
  - Must be a multiple of L2 Block Time
  - Default: 240 seconds
  - Affects challenge period resolution

## Challenge Period
- **Challenge Period**: Time window for disputing invalid state transitions
  - Default: 12 seconds (testnet), 7 days (mainnet)
  - Longer = more secure, slower withdrawals
  - Shorter = less secure, faster withdrawals
  - Production recommendation: At least 7 days for mainnet

## Account Roles
1. **Admin Account**: System administrator, manages upgrades and configuration
2. **Proposer Account**: Submits state root proposals to L1
3. **Batcher Account**: Batches transactions and submits to L1
4. **Sequencer Account**: Orders and executes transactions on L2

Each account requires its own private key and sufficient ETH for gas fees.
        """,
        "source": "trh-config-parameters",
        "title": "TRH Configuration Parameters Guide",
    },
    {
        "content": """
# Tokamak Rollup Hub - Deployment Prerequisites

## Before You Start
1. **Ethereum Wallet**: You need a wallet with a seed phrase (12 BIP39 words)
2. **L1 ETH**: Sufficient ETH on L1 for deployment and operation
3. **AWS Account**: For infrastructure deployment
4. **RPC Endpoints**: Access to L1 execution and beacon nodes

## Seed Phrase Security
- NEVER share your seed phrase with anyone
- NEVER enter your seed phrase in untrusted applications
- The TRH platform uses your seed phrase to derive account keys
- Consider using a dedicated seed phrase for rollup operation

## Recommended ETH Amounts (Testnet)
- Admin Account: 0.1 ETH
- Proposer Account: 0.5 ETH
- Batcher Account: 1.0 ETH
- Sequencer Account: 0.1 ETH

## AWS Requirements
- AWS Access Key ID
- AWS Secret Access Key
- Recommended region: us-east-1 or ap-northeast-2
- Required permissions: EC2, VPC, EBS

## Getting Testnet ETH
For Sepolia testnet:
- Alchemy Faucet: https://sepoliafaucet.com/
- Infura Faucet: https://www.infura.io/faucet/sepolia
- PoW Faucet: https://sepolia-faucet.pk910.de/
        """,
        "source": "trh-prerequisites",
        "title": "TRH Deployment Prerequisites",
    },
    {
        "content": """
# Tokamak Rollup Hub - Integrations

## Available Integrations

### 1. Token Bridge
Cross-chain asset transfers between L1 and your L2 rollup.
- Deposit ETH and ERC20 tokens from L1 to L2
- Withdraw assets from L2 to L1
- Challenge period applies to withdrawals

### 2. Block Explorer (Blockscout)
Transaction viewer for your rollup chain.
- View transactions, blocks, and addresses
- Track token transfers
- Verify smart contracts

### 3. Grafana Monitoring
Performance metrics and system monitoring.
- Real-time chain metrics
- Resource usage graphs
- Alert configuration

### 4. System Pulse
Uptime monitoring for your rollup infrastructure.
- Health checks
- Downtime alerts
- Performance tracking

### 5. DAO Candidate Registration
Participate in Tokamak Network governance.
- Register as a DAO candidate
- Minimum stake: 1000.1 TON
- Requires memo and optional name info

## Backup & Restore (Testnet Only)
- Create snapshots of your rollup state
- Restore from previous checkpoints
- Schedule automatic backups
- Attach external storage for backups
        """,
        "source": "trh-integrations",
        "title": "TRH Integrations Guide",
    },
]


def clean_html_content(html_content: str) -> str:
    """Clean HTML content for better text extraction."""
    soup = BeautifulSoup(html_content, "lxml")

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    # Get text
    text = soup.get_text(separator="\n")

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    text = "\n".join(line for line in lines if line)

    return text


def ingest_urls(urls: list[str], rag_service) -> int:
    """Ingest documents from URLs."""
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    total_chunks = 0

    for url in urls:
        try:
            logger.info(f"Loading: {url}")
            loader = WebBaseLoader(url)
            documents = loader.load()

            for doc in documents:
                # Clean the content
                clean_content = clean_html_content(doc.page_content)

                # Split into chunks
                chunks = splitter.split_text(clean_content)

                # Prepare metadata
                metadatas = [
                    {"source": url, "chunk_index": i}
                    for i in range(len(chunks))
                ]

                # Add to vector store
                rag_service.add_documents(chunks, metadatas)
                total_chunks += len(chunks)
                logger.info(f"  Added {len(chunks)} chunks from {url}")

        except Exception as e:
            logger.error(f"Failed to ingest {url}: {e}")

    return total_chunks


def ingest_additional_docs(docs: list[dict], rag_service) -> int:
    """Ingest additional inline documentation."""
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    total_chunks = 0

    for doc in docs:
        try:
            logger.info(f"Processing: {doc['title']}")

            # Split into chunks
            chunks = splitter.split_text(doc["content"])

            # Prepare metadata
            metadatas = [
                {
                    "source": doc["source"],
                    "title": doc["title"],
                    "chunk_index": i,
                }
                for i in range(len(chunks))
            ]

            # Add to vector store
            rag_service.add_documents(chunks, metadatas)
            total_chunks += len(chunks)
            logger.info(f"  Added {len(chunks)} chunks from {doc['title']}")

        except Exception as e:
            logger.error(f"Failed to ingest {doc['title']}: {e}")

    return total_chunks


def main():
    parser = argparse.ArgumentParser(description="Ingest documentation into vector store")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingestion (clears existing documents)",
    )
    parser.add_argument(
        "--urls-only",
        action="store_true",
        help="Only ingest from URLs, skip inline docs",
    )
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Tokamak Architect Bot - Document Ingestion")
    logger.info("=" * 50)

    # Initialize services
    settings = get_settings()
    logger.info(f"Embedding provider: {settings.embedding_provider}")

    # Initialize embedding service first (loads model)
    logger.info("Initializing embedding service...")
    embedding_service = get_embedding_service()
    logger.info(f"Embedding dimension: {embedding_service.dimension}")

    # Initialize RAG service
    logger.info("Initializing RAG service...")
    rag_service = get_rag_service()

    # Check existing documents
    stats = rag_service.get_stats()
    logger.info(f"Current documents in store: {stats['document_count']}")

    if stats["document_count"] > 0 and not args.force:
        logger.info("Documents already exist. Use --force to re-ingest.")
        logger.info("Skipping ingestion.")
        return

    if args.force and stats["document_count"] > 0:
        logger.info("Force flag set. Clearing existing documents...")
        # Delete and recreate collection
        rag_service.chroma_client.delete_collection(settings.chroma_collection_name)
        rag_service.collection = rag_service.chroma_client.create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Collection cleared.")

    total_chunks = 0

    # Ingest from URLs
    logger.info("\n--- Ingesting from URLs ---")
    url_chunks = ingest_urls(DOCS_URLS, rag_service)
    total_chunks += url_chunks
    logger.info(f"URL ingestion complete: {url_chunks} chunks")

    # Ingest additional docs
    if not args.urls_only:
        logger.info("\n--- Ingesting Additional Documentation ---")
        additional_chunks = ingest_additional_docs(ADDITIONAL_DOCS, rag_service)
        total_chunks += additional_chunks
        logger.info(f"Additional docs ingestion complete: {additional_chunks} chunks")

    # Final stats
    logger.info("\n" + "=" * 50)
    logger.info("Ingestion Complete!")
    logger.info(f"Total chunks added: {total_chunks}")
    stats = rag_service.get_stats()
    logger.info(f"Total documents in store: {stats['document_count']}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
