import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY', 'YOUR_ALCHEMY_API_KEY')

# Contract Addresses
ETH_USD_PRICE_FEED = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"  # Chainlink ETH/USD Price Feed
TOKEN_TRADING_ADDRESS = os.getenv('TOKEN_TRADING_ADDRESS', 'YOUR_TOKEN_TRADING_ADDRESS')
DUMMY_TOKEN_ADDRESS = os.getenv('DUMMY_TOKEN_ADDRESS', 'YOUR_DUMMY_TOKEN_ADDRESS')

# Network Configuration
GANACHE_URL = "http://127.0.0.1:7545"
ETH_MAINNET_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# Gas Configuration
GAS_LIMIT = 6721975
GAS_PRICE = 20000000000

# Trading Parameters
DEFAULT_TRADE_AMOUNT = 100
BUY_THRESHOLD_PERCENTAGE = 0.95  # Buy when price drops 5%
SELL_THRESHOLD_PERCENTAGE = 1.05  # Sell when price rises 5%

# Contract ABIs
PRICE_FEED_ABI = [
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"internalType": "uint80", "name": "roundId", "type": "uint80"},
            {"internalType": "int256", "name": "answer", "type": "int256"},
            {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
            {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Load other contract ABIs from files
def load_contract_abi(contract_name):
    """Load contract ABI from JSON file."""
    import json
    try:
        with open(f'contracts/{contract_name}.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: ABI file for {contract_name} not found")
        return []

TOKEN_TRADING_ABI = load_contract_abi('TokenTrading')
DUMMY_TOKEN_ABI = load_contract_abi('DummyToken') 