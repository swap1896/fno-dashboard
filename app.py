#!/usr/bin/env python3
"""
FNO Intelligence API Server
Flask backend for cloud deployment
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import json
from fno_analyzer import FNOAnalyzer
import threading
import time

app = Flask(__name__)
CORS(app)

# Global state
analyzer = None
last_analysis = None
last_update = None
update_lock = threading.Lock()

def init_analyzer():
    """Initialize analyzer with environment credentials"""
    global analyzer
    api_key = os.getenv('ZERODHA_API_KEY')
    api_secret = os.getenv('ZERODHA_API_SECRET')
    access_token = os.getenv('ZERODHA_ACCESS_TOKEN')
    
    if all([api_key, api_secret, access_token]):
        analyzer = FNOAnalyzer(api_key, api_secret, access_token)
        return True
    return False

def background_analyzer():
    """Background thread to refresh data periodically"""
    global last_analysis, last_update
    
    if not analyzer:
        return
    
    while True:
        try:
            with update_lock:
                last_analysis = analyzer.analyze_nifty_options()
                last_update = datetime.now()
            print(f"✓ Analysis updated at {last_update}")
        except Exception as e:
            print(f"❌ Error in background analysis: {e}")
        
        # Update every 5 minutes
        time.sleep(300)

# Routes
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_ready': analyzer is not None
    })

@app.route('/api/nifty-options', methods=['GET'])
def get_nifty_options():
    """Get current NIFTY options analysis"""
    global last_analysis, last_update
    
    if not last_analysis:
        if not analyzer:
            return jsonify({'error': 'API not configured'}), 500
        
        # Perform analysis on-demand
        try:
            with update_lock:
                last_analysis = analyzer.analyze_nifty_options()
                last_update = datetime.now()
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    response = last_analysis.copy()
    response['last_updated'] = last_update.isoformat()
    response['age_seconds'] = (datetime.now() - last_update).total_seconds()
    
    return jsonify(response)

@app.route('/api/refresh', methods=['POST'])
def refresh():
    """Manually trigger analysis refresh"""
    if not analyzer:
        return jsonify({'error': 'API not configured'}), 500
    
    try:
        with update_lock:
            global last_analysis, last_update
            last_analysis = analyzer.analyze_nifty_options()
            last_update = datetime.now()
        
        return jsonify({
            'status': 'success',
            'message': 'Analysis refreshed',
            'timestamp': last_update.isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/max-pain', methods=['GET'])
def get_max_pain():
    """Get max pain and related metrics"""
    if not last_analysis:
        return jsonify({'error': 'No data available'}), 404
    
    return jsonify({
        'max_pain': last_analysis['positioning']['max_pain'],
        'put_call_ratio': last_analysis['positioning']['put_call_ratio'],
        'directional_bias': last_analysis['positioning']['directional_bias'],
        'spot_price': last_analysis['spot_price'],
        'timestamp': last_update.isoformat()
    })

@app.route('/api/iv-analysis', methods=['GET'])
def get_iv_analysis():
    """Get IV skew and sentiment analysis"""
    if not last_analysis:
        return jsonify({'error': 'No data available'}), 404
    
    return jsonify(last_analysis['iv_analysis'])

@app.route('/api/signal', methods=['GET'])
def get_signal():
    """Get current trading signal"""
    if not last_analysis:
        return jsonify({'error': 'No data available'}), 404
    
    return jsonify(last_analysis['signal'])

@app.route('/api/top-strikes', methods=['GET'])
def get_top_strikes():
    """Get highest OI strikes"""
    if not last_analysis:
        return jsonify({'error': 'No data available'}), 404
    
    return jsonify({
        'strikes': last_analysis['highest_oi_strikes'],
        'timestamp': last_update.isoformat()
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get historical trades (if stored)"""
    history_file = 'trades_history.json'
    
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            trades = json.load(f)
        return jsonify(trades)
    
    return jsonify({'trades': []})

@app.route('/api/log-trade', methods=['POST'])
def log_trade():
    """Log a completed trade"""
    data = request.json
    history_file = 'trades_history.json'
    
    # Validate input
    required = ['entry', 'exit', 'type', 'strike']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Calculate P&L
    pnl = 0
    if data['type'] == 'PE':
        pnl = (data['entry'] - data['exit']) * 100
    elif data['type'] == 'CE':
        pnl = (data['exit'] - data['entry']) * 100
    
    # Load existing trades
    trades = []
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            trades = json.load(f)
    
    # Add new trade
    trade = {
        'timestamp': datetime.now().isoformat(),
        'entry': data['entry'],
        'exit': data['exit'],
        'type': data['type'],
        'strike': data['strike'],
        'pnl': round(pnl, 2),
        'notes': data.get('notes', '')
    }
    trades.append(trade)
    
    # Save
    with open(history_file, 'w') as f:
        json.dump(trades, f, indent=2)
    
    return jsonify({
        'status': 'success',
        'message': 'Trade logged',
        'pnl': round(pnl, 2),
        'trade': trade
    })

@app.route('/api/dashboard-data', methods=['GET'])
def get_dashboard_data():
    """Get all data needed for dashboard in one call"""
    if not last_analysis:
        return jsonify({'error': 'No data available'}), 404
    
    return jsonify({
        'overview': last_analysis['positioning'],
        'iv_analysis': last_analysis['iv_analysis'],
        'top_strikes': last_analysis['highest_oi_strikes'],
        'signal': last_analysis['signal'],
        'spot_price': last_analysis['spot_price'],
        'expiry': last_analysis['expiry'],
        'last_updated': last_update.isoformat(),
        'age_seconds': (datetime.now() - last_update).total_seconds()
    })

@app.route('/api/docs', methods=['GET'])
def get_docs():
    """API documentation"""
    return jsonify({
        'endpoints': {
            'GET /health': 'Health check',
            'GET /api/nifty-options': 'Full analysis data',
            'GET /api/max-pain': 'Max pain metrics',
            'GET /api/iv-analysis': 'IV skew analysis',
            'GET /api/signal': 'Current trading signal',
            'GET /api/top-strikes': 'Highest OI strikes',
            'GET /api/dashboard-data': 'All dashboard data',
            'GET /api/history': 'Trade history',
            'POST /api/log-trade': 'Log a new trade',
            'POST /api/refresh': 'Manually refresh data',
            'GET /api/docs': 'This documentation'
        },
        'notes': 'All endpoints return JSON. Use POST /api/log-trade with body: {"entry": X, "exit": Y, "type": "CE"/"PE", "strike": Z, "notes": "..."}'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Startup
if __name__ == '__main__':
    # Initialize analyzer
    if init_analyzer():
        print("✓ Analyzer initialized with API credentials")
        
        # Start background update thread
        bg_thread = threading.Thread(target=background_analyzer, daemon=True)
        bg_thread.start()
        print("✓ Background analyzer started (5 min refresh interval)")
    else:
        print("⚠ No API credentials found - running in demo mode")
        print("  Set ZERODHA_API_KEY, ZERODHA_API_SECRET, ZERODHA_ACCESS_TOKEN to enable")
    
    # Start Flask server
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"\n🚀 FNO Intelligence API Server")
    print(f"📍 http://localhost:{port}")
    print(f"📚 Docs: http://localhost:{port}/api/docs")
    print(f"❤️  Health: http://localhost:{port}/health")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
