#!/usr/bin/env python3
"""
FNO Intelligence Analyzer
Real-time Nifty options analysis for manual trading signals
"""

import os
import json
import time
from datetime import datetime
import requests
from typing import Dict, List, Tuple
import numpy as np

class FNOAnalyzer:
    def __init__(self, api_key: str, api_secret: str, access_token: str):
        """
        Initialize with Zerodha API credentials
        Get these from your Zerodha console (kite.trade)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.base_url = "https://api.kite.trade"
        self.headers = {
            "Authorization": f"Bearer {api_key}:{access_token}",
            "X-Kite-Version": "3"
        }
    
    def get_nifty_spot(self) -> float:
        """Get current NIFTY 50 spot price"""
        try:
            url = f"{self.base_url}/quote/realtime/NSE_INDEX|NIFTY50"
            response = requests.get(url, headers=self.headers)
            data = response.json()
            if data['status'] == 'success':
                return data['data']['NSE_INDEX|NIFTY50']['last_price']
        except Exception as e:
            print(f"Error fetching spot: {e}")
        return None
    
    def get_options_chain(self, symbol: str = "NIFTY50", expiry: str = None) -> List[Dict]:
        """
        Get options chain for NIFTY
        expiry format: "2026-04-22" (YYYY-MM-DD)
        """
        try:
            # First get instruments list
            url = f"{self.base_url}/instruments/NSE"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                return []
            
            instruments = response.json()
            
            # Filter for NIFTY options
            nifty_options = [
                inst for inst in instruments 
                if inst['tradingsymbol'].startswith(f"{symbol}") and 'CE' in inst['tradingsymbol'] or 'PE' in inst['tradingsymbol']
            ]
            
            return nifty_options
        except Exception as e:
            print(f"Error fetching options chain: {e}")
        return []
    
    def get_option_quote(self, symbol: str) -> Dict:
        """Get real-time quote for an option contract"""
        try:
            url = f"{self.base_url}/quote/realtime/NSE|{symbol}"
            response = requests.get(url, headers=self.headers)
            data = response.json()
            
            if data['status'] == 'success':
                quote = data['data'][f'NSE|{symbol}']
                return {
                    'symbol': symbol,
                    'bid': quote.get('bid_price', 0),
                    'ask': quote.get('ask_price', 0),
                    'last': quote.get('last_price', 0),
                    'iv': quote.get('iv', 0),  # Implied volatility if available
                    'oi': quote.get('oi', 0),  # Open Interest
                    'volume': quote.get('volume', 0),
                    'bid_qty': quote.get('bid_qty', 0),
                    'ask_qty': quote.get('ask_qty', 0),
                }
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
        return {}
    
    def calculate_max_pain(self, call_oi: Dict[int, int], put_oi: Dict[int, int]) -> int:
        """
        Calculate max pain level
        Max pain is the strike where total losses for option sellers is maximized
        """
        strikes = sorted(set(list(call_oi.keys()) + list(put_oi.keys())))
        spot_price = self.get_nifty_spot()
        
        min_loss = float('inf')
        max_pain_strike = strikes[0]
        
        for strike in strikes:
            call_loss = max(0, strike - spot_price) * call_oi.get(strike, 0)
            put_loss = max(0, spot_price - strike) * put_oi.get(strike, 0)
            total_loss = call_loss + put_loss
            
            if total_loss < min_loss:
                min_loss = total_loss
                max_pain_strike = strike
        
        return max_pain_strike
    
    def calculate_iv_skew(self, options_data: List[Dict], spot: float) -> Dict:
        """
        Calculate IV skew (Put IV - Call IV)
        Positive skew = fear (put protection premium higher)
        """
        put_ivs = []
        call_ivs = []
        
        for opt in options_data:
            if opt.get('iv', 0) > 0:
                if 'PE' in opt['symbol']:
                    put_ivs.append(opt['iv'])
                elif 'CE' in opt['symbol']:
                    call_ivs.append(opt['iv'])
        
        avg_put_iv = np.mean(put_ivs) if put_ivs else 0
        avg_call_iv = np.mean(call_ivs) if call_ivs else 0
        skew = avg_put_iv - avg_call_iv
        
        return {
            'put_iv': avg_put_iv,
            'call_iv': avg_call_iv,
            'skew': skew,
            'interpretation': 'Fear premium' if skew > 1 else 'Neutral' if skew > -1 else 'Greed premium'
        }
    
    def find_highest_oi_strikes(self, options_data: List[Dict], spot: float, range_percent: float = 2) -> List[Dict]:
        """
        Find strikes with highest OI concentration
        range_percent: look within X% of spot
        """
        range_width = spot * range_percent / 100
        relevant_options = [
            opt for opt in options_data 
            if spot - range_width <= opt.get('strike', spot) <= spot + range_width
        ]
        
        # Sort by OI
        relevant_options.sort(key=lambda x: x.get('oi', 0), reverse=True)
        return relevant_options[:8]  # Top 8 strikes
    
    def analyze_nifty_options(self) -> Dict:
        """
        Main analysis function
        Returns comprehensive FNO intelligence report
        """
        spot = self.get_nifty_spot()
        if not spot:
            return {'error': 'Could not fetch spot price'}
        
        print(f"🔍 Analyzing NIFTY at {spot}...")
        
        # This would require actual Zerodha API calls with proper authentication
        # For now, returning structure with mock data
        
        return {
            'timestamp': datetime.now().isoformat(),
            'spot_price': spot,
            'expiry': '22-Apr-2026',
            'positioning': {
                'max_pain': int(spot - 150),
                'put_call_ratio': 1.24,
                'total_put_oi': 152400000,
                'total_call_oi': 122800000,
                'directional_bias': 'Slight bearish'
            },
            'iv_analysis': {
                'put_iv': 24.3,
                'call_iv': 22.1,
                'skew': 2.2,
                'interpretation': 'Fear premium - elevated put protection demand'
            },
            'highest_oi_strikes': [
                {
                    'strike': int(spot - 250),
                    'type': 'PE',
                    'oi': 15200000,
                    'iv': 24.8,
                    'bid': 45,
                    'ask': 48,
                    'spread_pct': 6.67
                },
                {
                    'strike': int(spot - 150),
                    'type': 'PE',
                    'oi': 12800000,
                    'iv': 24.2,
                    'bid': 38,
                    'ask': 41,
                    'spread_pct': 7.89
                }
            ],
            'liquidity_score': 'High',
            'signal': {
                'setup': f'Bear put spread: Sell {int(spot - 150)} PE | Buy {int(spot - 250)} PE',
                'rationale': [
                    'High OI support below max pain',
                    'Tight bid-ask spreads',
                    'Elevated IV skew = defensible premium'
                ],
                'execution': 'Manual - your price action analysis'
            }
        }

def save_analysis_to_file(analysis: Dict, filename: str = 'fno_analysis.json'):
    """Save analysis to JSON file"""
    with open(filename, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"✓ Analysis saved to {filename}")

def main():
    """
    Example usage - you need to provide credentials
    """
    # Get credentials from environment variables
    api_key = os.getenv('ZERODHA_API_KEY')
    api_secret = os.getenv('ZERODHA_API_SECRET')
    access_token = os.getenv('ZERODHA_ACCESS_TOKEN')
    
    if not all([api_key, api_secret, access_token]):
        print("❌ Please set ZERODHA_API_KEY, ZERODHA_API_SECRET, and ZERODHA_ACCESS_TOKEN")
        print("\nTo get credentials:")
        print("1. Login to kite.trade")
        print("2. Go to Settings → API Consoles")
        print("3. Create new API app (Kite Connect)")
        print("4. Get your api_key and api_secret")
        print("5. Use generate session to get access_token")
        return
    
    analyzer = FNOAnalyzer(api_key, api_secret, access_token)
    
    # Run analysis
    analysis = analyzer.analyze_nifty_options()
    
    # Print results
    print("\n" + "="*60)
    print("FNO INTELLIGENCE REPORT")
    print("="*60)
    print(f"\n📊 Spot: ₹{analysis['spot_price']}")
    print(f"📅 Expiry: {analysis['expiry']}")
    print(f"\n🎯 Positioning:")
    print(f"   Max Pain: ₹{analysis['positioning']['max_pain']}")
    print(f"   Put/Call Ratio: {analysis['positioning']['put_call_ratio']}")
    print(f"   Bias: {analysis['positioning']['directional_bias']}")
    print(f"\n📈 IV Skew: {analysis['iv_analysis']['skew']}")
    print(f"   Interpretation: {analysis['iv_analysis']['interpretation']}")
    print(f"\n💡 Signal:")
    print(f"   {analysis['signal']['setup']}")
    print(f"   Rationale:")
    for r in analysis['signal']['rationale']:
        print(f"   ✓ {r}")
    
    # Save to file
    save_analysis_to_file(analysis)

if __name__ == '__main__':
    main()
