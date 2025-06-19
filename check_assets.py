#!/usr/bin/env python3
"""Check what assets exist and their identifiers."""

import asyncio
from src.agents.asset_document_agent import AssetDocumentAgent


async def check_assets():
    """Check assets and their identifiers."""
    agent = AssetDocumentAgent()
    assets = await agent.list_assets()

    print(f"Found {len(assets)} assets:")
    print("=" * 60)

    for asset in assets:
        print(f"Asset ID: {asset.deal_id}")
        print(f"Deal Name: {asset.deal_name}")
        print(f"Asset Name: {asset.asset_name}")
        print(f"Asset Type: {asset.asset_type}")
        print(f"Identifiers: {asset.identifiers}")
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(check_assets())
