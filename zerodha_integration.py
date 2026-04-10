#!/usr/bin/env python3
"""
Zerodha Kite Connect Integration Module
Handles live authentication and real-time options data fetching
"""

import os
import json
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ZerodhaAuthenticator:
    """Handle Zerodha API authentication flow"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.kite.trade"
        self.login_url = "https://kite.zerodha.com/connect/login"
        self.access_token = None
        self.userid = None
        
    def get_login_url(self) -> str:
        """Get the login URL for user authentication"""
        return f"{self.login_url}?api_key={self.api_key}&v=3"
    
    def generate_session(self, request_token: str) -> bool:
        """
        Generate access token using request token
        This is called AFTER user completes login
        """
        try:
            # Create checksum
            data = f"{self.api_key}{request_token}{self.api_secret}"
            checksum = hashlib.sha256(data.encode()).hexdigest()
            
            # Get session
            url = f"{self.base_url}/session/token"
            payload = {
                "api_key": self.api_key,
                "request_token": request_token,
                "checksum": checksum
            }
            
            response = requests.post(url, data=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'success':
                self.access_token = data['data']['access_token']
                self.userid = data['data']['user_id']
                logger.info(f"✓ Session generated for {self.userid}")
                return True
            else:
                logger.error(f"✗ Session generation failed: {data.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error generating session: {e}")
            return False
    
    def get_headers(self) -> Dict:
        """Get authorization headers for API requests"""
        if not self.access_token:
            raise ValueError("Access token not set. Call generate_session() first.")
        
        return {
            "Authorization": f"Bearer {self.api_key}:{self.access_token}",
            "X-Kite-Version": "3"
        }


class ZerodhaOptionsData:
    """Fetch and analyze live NIFTY options data"""
    
    def __init__(self, access_token: str, api_key: str):
        self.access_token = access_token
        self.api_key = api_key
        self.base_url = "https://api.kite.trade"
        self.headers = {
            "Authorization": f"Bearer {api_key}:{access_token}",
            "X-Kite-Version": "3"
        }
    
    def get_quote(self, instrument_token: str) -> Optional[Dict]:
        """Get real-time quote for an instrument"""
        try:
            url = f"{self.base_url}/quote/realtime/{instrument_token}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'success':
                return data['data']
            return None
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            return None
    
    def get_ltp(self, instrument_token: str) -> Optional[float]:
        """Get last traded price"""
        quote = self.get_quote(instrument_token)
        if quote:
            return quote.get('last_price')
        return None
    
    def get_option_chain(self, symbol: str = "NIFTY50") -> List[Dict]:
        """
        Get options chain for symbol
        Returns list of option contracts with pricing
        """
        try:
            # Get instruments list
            url = f"{self.base_url}/instruments"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse CSV format response
            lines = response.text.split('\n')
            headers = lines[0].split(',')
            
            options = []
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                parts = line.split(',')
                if len(parts) < len(headers):
                    continue
                
                record = dict(zip(headers, parts))
                
                # Filter for NIFTY options
                if symbol in record.get('tradingsymbol', ''):
                    if 'PE' in record['tradingsymbol'] or 'CE' in record['tradingsymbol']:
                        options.append({
                            'instrument_token': record.get('instrument_token'),
                            'tradingsymbol': record.get('tradingsymbol'),
                            'strike': float(record.get('strike', 0)),
                            'expiry': record.get('expiry'),
                            'option_type': record.get('option_type'),
                        })
            
            return options
        except Exception as e:
            logger.error(f"Error fetching options chain: {e}")
            return []
    
    def get_holdings(self) -> Optional[List[Dict]]:
        """Get user's holdings"""
        try:
            url = f"{self.base_url}/portfolio/holdings"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'success':
                return data['data']
            return None
        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return None
    
    def get_orders(self) -> Optional[List[Dict]]:
        """Get user's orders"""
        try:
            url = f"{self.base_url}/orders"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'success':
                return data['data']
            return None
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return None
    
    def place_order(self, tradingsymbol: str, quantity: int, price: float = 0, 
                   order_type: str = "MARKET", direction: str = "BUY") -> Optional[Dict]:
        """
        Place an order
        order_type: MARKET, LIMIT
        direction: BUY, SELL
        """
        try:
            url = f"{self.base_url}/orders/regular"
            
            payload = {
                "tradingsymbol": tradingsymbol,
                "quantity": quantity,
                "order_type": order_type,
                "transaction_type": direction,
            }
            
            if order_type == "LIMIT":
                payload["price"] = price
            
            response = requests.post(url, data=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'success':
                logger.info(f"✓ Order placed: {tradingsymbol} {direction} x{quantity}")
                return data['data']
            else:
                logger.error(f"✗ Order failed: {data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None


class ZerodhaService:
    """Complete Zerodha integration service"""
    
    def __init__(self):
        self.api_key = os.getenv('ZERODHA_API_KEY')
        self.api_secret = os.getenv('ZERODHA_API_SECRET')
        self.access_token = os.getenv('ZERODHA_ACCESS_TOKEN')
        
        self.authenticator = None
        self.data_client = None
        self.initialized = False
        
        if self.api_key and self.api_secret:
            self.authenticator = ZerodhaAuthenticator(self.api_key, self.api_secret)
        
        if self.access_token:
            self.data_client = ZerodhaOptionsData(self.access_token, self.api_key)
            self.initialized = True
    
    def is_ready(self) -> bool:
        """Check if service is ready to use"""
        return self.initialized
    
    def get_nifty_spot(self) -> Optional[float]:
        """Get NIFTY 50 spot price"""
        if not self.data_client:
            return None
        
        # NIFTY 50 index token (NSE_INDEX|NIFTY50)
        # Common tokens: NIFTY50 = 256265475
        try:
            url = f"{self.data_client.base_url}/instruments"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            lines = response.text.split('\n')
            for line in lines[1:]:
                if not line.strip():
                    continue
                parts = line.split(',')
                if len(parts) >= 4:
                    if parts[2] == 'NIFTY50' and parts[3] == 'INDEX':
                        # Found NIFTY50, get its price
                        token = parts[0]
                        quote = self.data_client.get_quote(token)
                        if quote:
                            return quote.get('last_price')
            
            return None
        except Exception as e:
            logger.error(f"Error getting NIFTY spot: {e}")
            return None
    
    def get_expiry_dates(self) -> List[str]:
        """Get available expiry dates for NIFTY options"""
        if not self.data_client:
            return []
        
        options = self.data_client.get_option_chain("NIFTY50")
        expiries = set()
        for opt in options:
            if opt.get('expiry'):
                expiries.add(opt['expiry'])
        
        return sorted(list(expiries))
    
    def get_nifty_options_snapshot(self) -> Dict:
        """Get complete snapshot of NIFTY options data"""
        if not self.data_client:
            return {'error': 'Data client not initialized'}
        
        spot = self.get_nifty_spot()
        if not spot:
            return {'error': 'Could not fetch spot price'}
        
        options = self.data_client.get_option_chain("NIFTY50")
        if not options:
            return {'error': 'Could not fetch options chain'}
        
        # Get nearest expiry (usually weekly)
        expiries = set(opt.get('expiry') for opt in options)
        nearest_expiry = sorted(expiries)[0] if expiries else None
        
        # Filter options for nearest expiry
        expiry_options = [opt for opt in options if opt.get('expiry') == nearest_expiry]
        
        # Get quotes for top strikes
        pe_oi = {}
        ce_oi = {}
        
        for opt in expiry_options:
            try:
                quote = self.data_client.get_quote(opt['instrument_token'])
                if quote:
                    strike = opt.get('strike', 0)
                    oi = quote.get('oi', 0)
                    
                    if opt.get('option_type') == 'PE':
                        pe_oi[strike] = oi
                    elif opt.get('option_type') == 'CE':
                        ce_oi[strike] = oi
            except Exception as e:
                logger.warning(f"Error getting quote for {opt['tradingsymbol']}: {e}")
                continue
        
        # Calculate metrics
        total_pe_oi = sum(pe_oi.values())
        total_ce_oi = sum(ce_oi.values())
        put_call_ratio = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
        
        # Find max pain (simplified)
        max_pain = max(pe_oi.keys()) if pe_oi else spot
        
        return {
            'timestamp': datetime.now().isoformat(),
            'spot_price': spot,
            'expiry': nearest_expiry,
            'positioning': {
                'max_pain': int(max_pain),
                'put_call_ratio': round(put_call_ratio, 2),
                'total_put_oi': total_pe_oi,
                'total_call_oi': total_ce_oi,
            },
            'pe_oi': dict(sorted(pe_oi.items())),
            'ce_oi': dict(sorted(ce_oi.items())),
        }


if __name__ == '__main__':
    service = ZerodhaService()
    
    if service.is_ready():
        print("✓ Zerodha service initialized")
        snapshot = service.get_nifty_options_snapshot()
        print(json.dumps(snapshot, indent=2))
    else:
        if service.authenticator:
            print("⚠ Zerodha service not authenticated")
            print(f"📍 Login URL: {service.authenticator.get_login_url()}")
            print("\nAfter login, you'll get a request_token in the redirect URL")
            print("Use it to generate an access token")
        else:
            print("❌ ZERODHA_API_KEY or ZERODHA_API_SECRET not set")
            print("\nSet environment variables:")
            print("  export ZERODHA_API_KEY=your_key")
            print("  export ZERODHA_API_SECRET=your_secret")
            print("  export ZERODHA_ACCESS_TOKEN=your_token")
