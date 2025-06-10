#!/usr/bin/env python3
"""
Flask Web Application for Email Agent Asset Management

A user-friendly web interface for setting up and managing assets,
sender mappings, and document classification rules.
"""

import os
import sys
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from agents.asset_document_agent import (
    AssetDocumentAgent, Asset, AssetType, DocumentCategory,
    AssetSenderMapping, ConfidenceLevel
)
from utils.logging_system import get_logger, log_function, LogConfig, configure_logging

# Try to import Qdrant client
try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# Configure logging for the web UI
web_config = LogConfig(
    level="DEBUG",
    log_to_file=True,
    log_to_stdout=True,
    log_file="logs/web_ui.log",
    log_arguments=True,
    log_return_values=False,  # Don't log return values for web routes (can be large)
    log_execution_time=True,
    max_arg_length=200
)
configure_logging(web_config)

# Get logger for this module
logger = get_logger("web_ui")

app = Flask(__name__)
app.secret_key = 'email-agent-asset-management-2024'  # Change in production

# Global asset agent instance
asset_agent: Optional[AssetDocumentAgent] = None

@log_function()
def initialize_asset_agent():
    """Initialize the AssetDocumentAgent with Qdrant if available"""
    global asset_agent
    
    if QDRANT_AVAILABLE:
        try:
            # Try to connect to local Qdrant instance
            qdrant_client = QdrantClient(host="localhost", port=6333)
            asset_agent = AssetDocumentAgent(
                qdrant_client=qdrant_client,
                base_assets_path="./assets"
            )
            # Initialize collections asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(asset_agent.initialize_collections())
            loop.close()
            
            logger.info("AssetDocumentAgent initialized with Qdrant")
        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {e}")
            asset_agent = AssetDocumentAgent(base_assets_path="./assets")
            logger.info("AssetDocumentAgent initialized without Qdrant")
    else:
        asset_agent = AssetDocumentAgent(base_assets_path="./assets")
        logger.info("AssetDocumentAgent initialized without Qdrant (not installed)")

@app.route('/')
@log_function()
def index():
    """Main dashboard page"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html', 
                             error="Asset management system not initialized")
    
    # Get asset statistics
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        assets = loop.run_until_complete(asset_agent.list_assets())
        
        # Calculate statistics
        stats = {
            'total_assets': len(assets),
            'by_type': {},
            'recent_assets': assets[-5:] if assets else []  # Last 5 assets
        }
        
        # Count by asset type
        for asset in assets:
            asset_type = asset.asset_type.value
            stats['by_type'][asset_type] = stats['by_type'].get(asset_type, 0) + 1
        
        logger.info(f"Dashboard loaded with {len(assets)} assets")
        return render_template('dashboard.html', stats=stats, assets=assets)
    
    except Exception as e:
        logger.error(f"Failed to load dashboard: {e}")
        return render_template('error.html', error=f"Failed to load dashboard: {e}")
    finally:
        loop.close()

@app.route('/assets')
@log_function()
def list_assets():
    """List all assets page"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html', 
                             error="Asset management system not initialized")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        assets = loop.run_until_complete(asset_agent.list_assets())
        
        # Calculate type counts for the template
        type_counts = {}
        for asset in assets:
            asset_type = asset.asset_type.value
            type_counts[asset_type] = type_counts.get(asset_type, 0) + 1
        
        logger.info(f"Assets page loaded with {len(assets)} assets")
        return render_template('assets.html', assets=assets, asset_types=AssetType, type_counts=type_counts)
    
    except Exception as e:
        logger.error(f"Failed to load assets: {e}")
        return render_template('error.html', error=f"Failed to load assets: {e}")
    finally:
        loop.close()

@app.route('/assets/new', methods=['GET', 'POST'])
@log_function()
def create_asset():
    """Create new asset page"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html', 
                             error="Asset management system not initialized")
    
    if request.method == 'POST':
        try:
            # Get form data
            deal_name = request.form.get('deal_name', '').strip()
            asset_name = request.form.get('asset_name', '').strip()
            asset_type_str = request.form.get('asset_type', '')
            identifiers_str = request.form.get('identifiers', '').strip()
            
            logger.info(f"Creating asset: {deal_name} ({asset_type_str})")
            
            # Validate required fields
            if not deal_name or not asset_name or not asset_type_str:
                logger.warning("Asset creation failed: missing required fields")
                flash('Deal name, asset name, and asset type are required', 'error')
                return render_template('create_asset.html', 
                                     asset_types=AssetType,
                                     form_data=request.form)
            
            # Parse asset type
            try:
                asset_type = AssetType(asset_type_str)
            except ValueError:
                logger.warning(f"Invalid asset type selected: {asset_type_str}")
                flash('Invalid asset type selected', 'error')
                return render_template('create_asset.html', 
                                     asset_types=AssetType,
                                     form_data=request.form)
            
            # Parse identifiers
            identifiers = []
            if identifiers_str:
                identifiers = [id_.strip() for id_ in identifiers_str.split(',') if id_.strip()]
            
            # Create asset
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            deal_id = loop.run_until_complete(asset_agent.create_asset(
                deal_name=deal_name,
                asset_name=asset_name,
                asset_type=asset_type,
                identifiers=identifiers
            ))
            
            loop.close()
            
            logger.info(f"Asset created successfully: {deal_name} with ID: {deal_id[:8]}...")
            flash(f'Asset "{deal_name}" created successfully with ID: {deal_id[:8]}...', 'success')
            return redirect(url_for('list_assets'))
        
        except Exception as e:
            logger.error(f"Failed to create asset: {e}")
            flash(f'Failed to create asset: {e}', 'error')
            return render_template('create_asset.html', 
                                 asset_types=AssetType,
                                 form_data=request.form)
    
    return render_template('create_asset.html', 
                         asset_types=AssetType,
                         document_categories=DocumentCategory)

@app.route('/assets/<deal_id>')
@log_function()
def view_asset(deal_id: str):
    """View specific asset details"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html', 
                             error="Asset management system not initialized")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Get asset details
        asset = loop.run_until_complete(asset_agent.get_asset(deal_id))
        
        if not asset:
            logger.warning(f"Asset not found: {deal_id}")
            flash('Asset not found', 'error')
            return redirect(url_for('list_assets'))
        
        logger.info(f"Viewing asset: {asset.deal_name}")
        
        # Get sender mappings for this asset
        # Note: We'll need to implement a method to get mappings by asset_id
        sender_mappings = []  # Placeholder
        
        return render_template('asset_detail.html', 
                             asset=asset,
                             sender_mappings=sender_mappings,
                             document_categories=DocumentCategory)
    
    except Exception as e:
        logger.error(f"Failed to load asset {deal_id}: {e}")
        return render_template('error.html', error=f"Failed to load asset: {e}")
    finally:
        loop.close()

@app.route('/senders')
@log_function()
def list_senders():
    """List all sender mappings"""
    logger.info("Loading sender mappings page")
    # This would require implementing a method to list all sender mappings
    return render_template('senders.html', mappings=[])

@app.route('/senders/new', methods=['GET', 'POST'])
@log_function()
def create_sender_mapping():
    """Create new sender-asset mapping"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html', 
                             error="Asset management system not initialized")
    
    if request.method == 'POST':
        try:
            # Get form data
            asset_id = request.form.get('asset_id', '').strip()
            sender_email = request.form.get('sender_email', '').strip().lower()
            confidence = float(request.form.get('confidence', 0.8))
            document_types_str = request.form.get('document_types', '').strip()
            
            logger.info(f"Creating sender mapping: {sender_email} -> {asset_id}")
            
            # Validate
            if not asset_id or not sender_email:
                logger.warning("Sender mapping creation failed: missing required fields")
                flash('Asset and sender email are required', 'error')
                return render_template('create_sender_mapping.html')
            
            # Parse document types
            document_types = []
            if document_types_str:
                document_types = [dt.strip() for dt in document_types_str.split(',') if dt.strip()]
            
            # Create mapping
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            mapping_id = loop.run_until_complete(asset_agent.create_asset_sender_mapping(
                asset_id=asset_id,
                sender_email=sender_email,
                confidence=confidence,
                document_types=document_types
            ))
            
            loop.close()
            
            logger.info(f"Sender mapping created successfully: {mapping_id[:8]}...")
            flash(f'Sender mapping created successfully: {mapping_id[:8]}...', 'success')
            return redirect(url_for('list_senders'))
        
        except Exception as e:
            logger.error(f"Failed to create sender mapping: {e}")
            flash(f'Failed to create sender mapping: {e}', 'error')
    
    # Get available assets for dropdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        assets = loop.run_until_complete(asset_agent.list_assets())
    except Exception as e:
        logger.error(f"Failed to load assets for sender mapping form: {e}")
        assets = []
    finally:
        loop.close()
    
    return render_template('create_sender_mapping.html', 
                         assets=assets,
                         document_categories=DocumentCategory)

@app.route('/api/assets')
@log_function()
def api_list_assets():
    """API endpoint to list assets (for AJAX calls)"""
    if not asset_agent:
        logger.error("Asset management system not initialized for API call")
        return jsonify({'error': 'Asset management system not initialized'}), 500
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        assets = loop.run_until_complete(asset_agent.list_assets())
        
        assets_data = []
        for asset in assets:
            assets_data.append({
                'deal_id': asset.deal_id,
                'deal_name': asset.deal_name,
                'asset_name': asset.asset_name,
                'asset_type': asset.asset_type.value,
                'identifiers': asset.identifiers,
                'created_date': asset.created_date.isoformat(),
                'folder_path': asset.folder_path
            })
        
        logger.info(f"API returned {len(assets_data)} assets")
        return jsonify({'assets': assets_data})
    
    except Exception as e:
        logger.error(f"API failed to list assets: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        loop.close()

@app.route('/api/health')
@log_function()
def api_health():
    """API health check endpoint"""
    if not asset_agent:
        logger.error("Asset agent not initialized for health check")
        return jsonify({'status': 'error', 'message': 'Asset agent not initialized'}), 500
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        health = loop.run_until_complete(asset_agent.health_check())
        logger.info("Health check completed successfully")
        return jsonify({'status': 'ok', 'health': health})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        loop.close()

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 error: {request.url}")
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return render_template('error.html', error='Internal server error'), 500

def create_app():
    """Application factory function"""
    # Initialize the asset agent
    initialize_asset_agent()
    return app

if __name__ == '__main__':
    # Initialize asset agent on startup
    initialize_asset_agent()
    
    logger.info("🌐 Starting Email Agent Asset Management Web UI")
    logger.info("📊 Dashboard: http://localhost:5000")
    logger.info("🏢 Assets: http://localhost:5000/assets")
    logger.info("📧 Senders: http://localhost:5000/senders")
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000) 