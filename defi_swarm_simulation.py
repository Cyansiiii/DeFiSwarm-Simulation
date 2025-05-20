import time
import random # To simulate price changes
import json
from alchemy import Alchemy, Network
from web3 import Web3
from web3.middleware import geth_poa_middleware
import requests
import os
from crewai import Agent, Task, Crew, Process
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from datetime import datetime, timedelta

# Set Together API configuration
os.environ["OPENAI_API_KEY"] = "tgp_v1_SZfy1HF_Y4Zg5eSBw5zWmypxegW0hgYEGeJ-fE5y09A"
os.environ["OPENAI_API_BASE"] = "https://api.together.xyz/v1"

# Initialize Together LLM
# Use Together's Mixtral model as before
from langchain_openai import ChatOpenAI
together_llm = ChatOpenAI(
    model="mistralai/Mixtral-8x7B-Instruct-v0.1",
    temperature=0.7,
    openai_api_base=os.environ["OPENAI_API_BASE"]
)

# CoinGecko API configuration
COINGECKO_API_KEY = "CG-98Tq5aJBzpgzkv21FLsWaxdf"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Load contract data
with open('contract_data.json', 'r') as f:
    contract_data = json.load(f)

# Contract addresses and ABIs
TOKEN_TRADING_ADDRESS = contract_data['TokenTrading']['address']
TOKEN_TRADING_ABI = contract_data['TokenTrading']['abi']
DUMMY_TOKEN_ADDRESS = contract_data['DummyToken']['address']
DUMMY_TOKEN_ABI = contract_data['DummyToken']['abi']

# Ganache Configuration
GANACHE_URL = "http://192.168.1.12:8545"
GAS_PRICE = 20000000000
GAS_LIMIT = 6721975

# Chainlink Price Feed ABI (minimal version for latestRoundData)
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

# Contract addresses
ETH_USD_PRICE_FEED = "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419"  # Mainnet Chainlink ETH/USD feed
VITALIK_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
USDC_CONTRACT = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"

# Alchemy API configuration
ALCHEMY_API_KEY = "CX-G7CvHwlDifhfPg-Uti8KCrQd8Vaze"
ALCHEMY_BASE_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# Initialize Alchemy
alchemy = Alchemy(
    api_key=ALCHEMY_API_KEY,
    network=Network.ETH_MAINNET
)

# Initialize Web3 connection with Ganache
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Get the first account from Ganache for transactions
ACCOUNT = w3.eth.accounts[0]
PRIVATE_KEY = w3.eth.account.create().key.hex()  # Create a new account for testing

print("Ganache accounts:", w3.eth.accounts)
balance = w3.eth.get_balance(w3.eth.accounts[0])
print("Balance of first account:", w3.from_wei(balance, 'ether'), "ETH")

def compile_contract(contract_path):
    # ... existing code ...
    compiled_sol = compile_standard(
        # ... existing code ...
    )
    # Print bytecode for debugging
    contract_key = f"{contract_path}:{contract_path.split('.')[0]}"
    bytecode = compiled_sol['contracts'][contract_path][contract_path.split('.')[0]]['evm']['bytecode']['object']
    print(f"Bytecode for {contract_path}:", bytecode[:60], "...")  # Print first 60 chars
    return compiled_sol

def deploy_contracts():
    """Deploy the TokenTrading and DummyToken contracts to Ganache."""
    try:
        # Deploy DummyToken contract
        dummy_token = w3.eth.contract(abi=DUMMY_TOKEN_ABI, bytecode=contract_data['DummyToken']['bytecode'])
        tx_hash = dummy_token.constructor().transact({'from': ACCOUNT})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        dummy_token_address = tx_receipt.contractAddress
        
        # Deploy TokenTrading contract
        token_trading = w3.eth.contract(abi=TOKEN_TRADING_ABI, bytecode=contract_data['TokenTrading']['bytecode'])
        tx_hash = token_trading.constructor(dummy_token_address).transact({'from': ACCOUNT})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        token_trading_address = tx_receipt.contractAddress
        
        # Update contract addresses
        contract_data['DummyToken']['address'] = dummy_token_address
        contract_data['TokenTrading']['address'] = token_trading_address
        
        # Save updated contract data
        with open('contract_data.json', 'w') as f:
            json.dump(contract_data, f, indent=4)
            
        return True
    except Exception as e:
        print(f"Error deploying contracts: {e}")
        return False

def get_eth_price():
    """Get the current ETH/USD price from CoinGecko, fallback to public endpoint if Pro fails."""
    try:
        # Try Pro endpoint first
        url_pro = "https://pro-api.coingecko.com/api/v3/simple/price"
        params = {'ids': 'ethereum', 'vs_currencies': 'usd'}
        headers = {'x-cg-pro-api-key': COINGECKO_API_KEY}
        response = requests.get(url_pro, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            price = data['ethereum']['usd']
            return f"Current ETH/USD price is ${price:.2f}"
        # If 400 error, try public endpoint
        url_pub = "https://api.coingecko.com/api/v3/simple/price"
        response = requests.get(url_pub, params=params)
        if response.status_code == 200:
            data = response.json()
            price = data['ethereum']['usd']
            return f"Current ETH/USD price is ${price:.2f} (public API)"
        return f"Error fetching price: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error fetching price: {e}"

def get_simulated_price():
    """Get a simulated ETH/USD price for testing purposes."""
    try:
        change_percentage = random.uniform(-0.05, 0.05)
        if not hasattr(get_simulated_price, 'current_price'):
            get_simulated_price.current_price = 2000.0
        current_price = get_simulated_price.current_price
        current_price *= (1 + change_percentage)
        current_price = max(1500.0, round(current_price, 2))
        get_simulated_price.current_price = current_price
        return f"Simulated ETH/USD price is ${current_price:.2f}"
    except Exception as e:
        return f"Error generating simulated price: {e}"

def get_historical_prices(days=30):
    """Get historical ETH/USD prices from CoinGecko, fallback to public endpoint if Pro fails."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        params = {
            'vs_currency': 'usd',
            'from': start_timestamp,
            'to': end_timestamp
        }
        # Try Pro endpoint first
        url_pro = "https://pro-api.coingecko.com/api/v3/coins/ethereum/market_chart/range"
        headers = {'x-cg-pro-api-key': COINGECKO_API_KEY}
        response = requests.get(url_pro, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
        else:
            # Try public endpoint
            url_pub = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range"
            response = requests.get(url_pub, params=params)
            if response.status_code != 200:
                error_data = response.json()
                error_message = error_data.get('status', {}).get('error_message', response.text)
                print(f"CoinGecko API error: {response.status_code} - {error_message}")
                return f"Error fetching historical prices: {response.status_code} - {error_message}"
            data = response.json()
        prices = data.get('prices', [])
        if not prices:
            return "No historical price data available"
        price_changes = []
        for i in range(1, len(prices)):
            prev_price = prices[i-1][1]
            curr_price = prices[i][1]
            change = ((curr_price - prev_price) / prev_price) * 100
            price_changes.append(change)
        avg_price = sum(p[1] for p in prices) / len(prices)
        max_price = max(p[1] for p in prices)
        min_price = min(p[1] for p in prices)
        avg_change = sum(price_changes) / len(price_changes)
        price_levels = [p[1] for p in prices]
        price_levels.sort()
        support_level = price_levels[int(len(price_levels) * 0.2)]
        resistance_level = price_levels[int(len(price_levels) * 0.8)]
        volatility = (sum((x - avg_change) ** 2 for x in price_changes) / len(price_changes)) ** 0.5
        analysis = f"""Historical ETH/USD Price Analysis (Last {days} days):\n- Average Price: ${avg_price:.2f}\n- Highest Price: ${max_price:.2f}\n- Lowest Price: ${min_price:.2f}\n- Average Daily Change: {avg_change:.2f}%\n- Current Price: ${prices[-1][1]:.2f}\n- Price Trend: {'Upward' if avg_change > 0 else 'Downward'} trend with {abs(avg_change):.2f}% average daily change\n- Support Level: ${support_level:.2f}\n- Resistance Level: ${resistance_level:.2f}\n- Market Volatility: {volatility:.2f}%"""
        return analysis
    except Exception as e:
        print(f"Error in get_historical_prices: {str(e)}")
        return f"Error fetching historical prices: {e}"

def check_balance(address, token_contract):
    """Check the token balance for a specific address and token contract."""
    try:
        # Validate addresses
        if not Web3.is_address(address):
            return f"Invalid address: {address}"
        if not Web3.is_address(token_contract):
            return f"Invalid token contract: {token_contract}"
            
        # Use the global alchemy instance
        balances = alchemy.core.get_token_balances(address, [token_contract])
        return f"Token balances: {balances}"
    except Exception as e:
        return f"Error checking balance: {e}"

def execute_trade(decision, amount=100):
    """Execute a trade based on the decision (Buy/Sell) and amount."""
    try:
        if not w3.is_connected():
            return "Failed to connect to Ganache"
            
        # Initialize contracts
        trading_contract = w3.eth.contract(
            address=Web3.to_checksum_address(TOKEN_TRADING_ADDRESS),
            abi=TOKEN_TRADING_ABI
        )
        token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(DUMMY_TOKEN_ADDRESS),
            abi=DUMMY_TOKEN_ABI
        )
        
        if decision == "Buy":
            price = trading_contract.functions.tokenPrice().call()
            cost = amount * price
            
            # Build transaction
            tx = trading_contract.functions.buyTokens(amount).build_transaction({
                'from': ACCOUNT,
                'value': cost,
                'gas': GAS_LIMIT,
                'gasPrice': GAS_PRICE,
                'nonce': w3.eth.get_transaction_count(ACCOUNT),
            })
            
            # Sign and send transaction
            signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return f"Successfully bought {amount} tokens. Transaction hash: {receipt.transactionHash.hex()}"
            
        elif decision == "Sell":
            # First approve the trading contract to spend tokens
            approve_tx = token_contract.functions.approve(
                TOKEN_TRADING_ADDRESS,
                amount
            ).build_transaction({
                'from': ACCOUNT,
                'gas': GAS_LIMIT,
                'gasPrice': GAS_PRICE,
                'nonce': w3.eth.get_transaction_count(ACCOUNT),
            })
            
            # Sign and send approval transaction
            signed_approve_tx = w3.eth.account.sign_transaction(approve_tx, private_key=PRIVATE_KEY)
            approve_tx_hash = w3.eth.send_raw_transaction(signed_approve_tx.rawTransaction)
            w3.eth.wait_for_transaction_receipt(approve_tx_hash)
            
            # Now sell the tokens
            price = trading_contract.functions.tokenPrice().call()
            revenue = amount * price
            
            sell_tx = trading_contract.functions.sellTokens(amount).build_transaction({
                'from': ACCOUNT,
                'gas': GAS_LIMIT,
                'gasPrice': GAS_PRICE,
                'nonce': w3.eth.get_transaction_count(ACCOUNT),
            })
            
            # Sign and send sell transaction
            signed_sell_tx = w3.eth.account.sign_transaction(sell_tx, private_key=PRIVATE_KEY)
            sell_tx_hash = w3.eth.send_raw_transaction(signed_sell_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(sell_tx_hash)
            
            return f"Successfully sold {amount} tokens. Transaction hash: {receipt.transactionHash.hex()}"
            
        else:
            return f"No trade action taken for decision: {decision}"

    except Exception as e:
        return f"Error executing trade: {e}"

def log_trade_decision(context, decision):
    """Append the trade decision and context to a log file."""
    with open("trade_log.txt", "a") as f:
        f.write(f"{datetime.now().isoformat()}\nContext: {context}\nDecision: {decision}\n{'-'*40}\n")

def run_simulation(duration_seconds, check_interval_seconds):
    """
    Runs a simulation of the DeFiSwarm agents using CrewAI, passing real data as context.
    """
    print("\n--- Starting DeFiSwarm Simulation with CrewAI ---")

    # Initialize Web3 connection
    if not w3.is_connected():
        raise Exception("Failed to connect to Alchemy")
        
    # Verify contract addresses
    try:
        dummy_token = w3.eth.contract(
            address=Web3.to_checksum_address(DUMMY_TOKEN_ADDRESS),
            abi=DUMMY_TOKEN_ABI
        )
        token_trading = w3.eth.contract(
            address=Web3.to_checksum_address(TOKEN_TRADING_ADDRESS),
            abi=TOKEN_TRADING_ABI
        )
        dummy_token.functions.name().call()
        token_trading.functions.tokenPrice().call()
    except Exception as e:
        print(f"Error verifying contracts: {e}")
        raise Exception("Contracts are not properly deployed. Please run deploy_contracts.py first.")

    # Create CrewAI Agents (no tools)
    price_checker = Agent(
        role='Price Checker',
        goal='Monitor and provide accurate ETH/USD price information',
        backstory="""You are a specialized price monitoring agent that uses Chainlink's \
        price feed and CoinGecko's historical data to provide comprehensive ETH/USD price \
        information. Your primary goal is to ensure accurate and timely price data for \
        trading decisions. Use the provided context for all analysis.""",
        verbose=True,
        llm=together_llm
    )

    trade_maker = Agent(
        role='Trade Maker',
        goal='Make profitable trading decisions based on price information',
        backstory="""You are an experienced trading agent that analyzes price information \
        and makes trading decisions. You aim to maximize profits while managing risk \
        effectively. You use technical analysis, historical price data, and market trends \
        to make informed decisions. Use the provided context for all analysis.""",
        verbose=True,
        llm=together_llm
    )

    # Run the simulation
    start_time = time.time()
    try:
        while time.time() - start_time < duration_seconds:
            print(f"\n--- Cycle at {time.strftime('%H:%M:%S')} ---")

            # Get real data from tools
            eth_price = get_eth_price()
            historical = get_historical_prices(30)

            # Create Tasks with real data as context
            price_check_task = Task(
                description=f"""Get the current ETH/USD price and analyze market conditions.\n\nContext:\nETH Price: {eth_price}\nHistorical Data: {historical}\n\nProvide a detailed analysis of the current market situation, including:\n1. Current price and its relation to historical averages\n2. Price trends and momentum\n3. Support and resistance levels based on historical data\n4. Market volatility indicators""",
                agent=price_checker
            )

            trading_task = Task(
                description=f"""Based on the price information and market analysis, make a trading decision.\n\nContext:\nETH Price: {eth_price}\nHistorical Data: {historical}\n\nMake a decision to either Buy, Sell, or Hold, with clear reasoning based on the historical price analysis and context above.""",
                agent=trade_maker
            )

            # Create Crew
            crew = Crew(
                agents=[price_checker, trade_maker],
                tasks=[price_check_task, trading_task],
                process=Process.sequential,
                verbose=True
            )

            # Execute the crew's tasks
            result = crew.kickoff()
            print("\nCrew Execution Result:", result)

            # Automatic trade logging after each trade decision
            log_trade_decision(
                context=f"ETH Price: {eth_price}\nHistorical Data: {historical}",
                decision=result
            )
            time.sleep(check_interval_seconds)

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        print("\n--- DeFiSwarm Simulation Ended ---")

if __name__ == "__main__":
    # Run the simulation
    simulation_duration = 60  # seconds
    price_check_interval = 5  # seconds
    run_simulation(simulation_duration, price_check_interval)