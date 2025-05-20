from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_together import ChatTogether
from web3 import Web3
from web3.middleware import geth_poa_middleware
from alchemy import Alchemy, Network
import time
import random
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Configure Together API
# os.environ["TOGETHER_API_KEY"] = "tgp_v1_SZfy1HF_Y4Zg5eSBw5zWmypxegW0hgYEGeJ-fE5y09A"

# Create Together LLM instance
llm = ChatTogether(
    api_key=os.getenv("TOGETHER_API_KEY"),
    model_name="mistralai/Mixtral-8x7B-Instruct-v0.1"
)

# Constants
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
ETH_USD_PRICE_FEED = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"  # Chainlink ETH/USD Price Feed
TOKEN_TRADING_ADDRESS = "0x78b6ca4b4cc3cf7e5d9937e06a1b9ba534008ee5"
DUMMY_TOKEN_ADDRESS = "0x246f6857e5577abcabc5fa40bd017e8c4bf739cd"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
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

# Load contract ABIs from contract_data.json
with open("contract_data.json", "r") as f:
    contract_data = json.load(f)
TOKEN_TRADING_ABI = contract_data["TokenTrading"]["abi"]
DUMMY_TOKEN_ABI = contract_data["DummyToken"]["abi"]

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Trade Logger memory
trade_logs = []

@tool
def log_trade(action: str, details: str):
    """Log a trade action and its details to memory."""
    log_entry = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
        "action": action,
        "details": details
    }
    trade_logs.append(log_entry)
    return f"Trade logged: {log_entry}"

# Tools for Price Checker Agent
@tool
def get_eth_price():
    """Get the current ETH/USD price from Chainlink price feed."""
    try:
        alchemy = Alchemy(api_key=ALCHEMY_API_KEY, network=Network.ETH_MAINNET)
        w3 = Web3(Web3.HTTPProvider(f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"))
        
        price_feed = w3.eth.contract(
            address=Web3.to_checksum_address(ETH_USD_PRICE_FEED),
            abi=PRICE_FEED_ABI
        )
        
        round_data = price_feed.functions.latestRoundData().call()
        price = round_data[1] / 10**8
        return f"Current ETH/USD price is ${price:.2f}"
    except Exception as e:
        return f"Error fetching price: {e}"

@tool
def get_simulated_price():
    """Get a simulated ETH/USD price for testing purposes."""
    change_percentage = random.uniform(-0.05, 0.05)
    current_price = getattr(get_simulated_price, 'current_price', 2000.0)
    current_price *= (1 + change_percentage)
    current_price = max(1500.0, round(current_price, 2))
    get_simulated_price.current_price = current_price
    return f"Simulated ETH/USD price is ${current_price:.2f}"

@tool
def get_historical_eth_price(days: int = 7):
    """Get historical ETH/USD prices for the past N days from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
            "interval": "daily",
            "x_cg_pro_api_key": COINGECKO_API_KEY
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        prices = data.get("prices", [])
        # Format: list of [timestamp, price]
        price_list = [(time.strftime('%Y-%m-%d', time.gmtime(int(p[0]//1000))), p[1]) for p in prices]
        return f"Historical ETH/USD prices (last {days} days): {price_list}"
    except Exception as e:
        return f"Error fetching historical prices: {e}"

@tool
def compare_eth_price(days: int = 7):
    """Compare current ETH/USD price to historical price from N days ago using CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
            "interval": "daily",
            "x_cg_pro_api_key": COINGECKO_API_KEY
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        prices = data.get("prices", [])
        if len(prices) < 2:
            return "Not enough data for comparison."
        old_price = prices[0][1]
        new_price = prices[-1][1]
        pct_change = ((new_price - old_price) / old_price) * 100
        return f"ETH/USD {days}d ago: ${old_price:.2f}, now: ${new_price:.2f}, change: {pct_change:.2f}%"
    except Exception as e:
        return f"Error comparing prices: {e}"

# Tools for Trade Maker Agent
@tool
def check_balance(address, token_contract):
    """Check the token balance for a specific address and token contract."""
    try:
        alchemy = Alchemy(api_key=ALCHEMY_API_KEY, network=Network.ETH_MAINNET)
        balances = alchemy.core.get_token_balances(address, [token_contract])
        return f"Token balances for {address}: {balances}"
    except Exception as e:
        return f"Error checking balance: {e}"

@tool
def execute_trade(decision, amount=100):
    """Execute a trade based on the decision (Buy/Sell) and amount."""
    try:
        w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
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
        
        # Get the first account from Ganache for transactions
        account = w3.eth.accounts[0]
        
        if decision == "Buy":
            price = trading_contract.functions.tokenPrice().call()
            cost = amount * price
            
            # Build transaction
            tx = trading_contract.functions.buyTokens(amount).build_transaction({
                'from': account,
                'value': cost,
                'gas': 6721975,
                'gasPrice': 20000000000,
                'nonce': w3.eth.get_transaction_count(account),
            })
            
            # Sign and send transaction
            signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return f"Executed BUY order for {amount} tokens. Transaction hash: {receipt.transactionHash.hex()}"
            
        elif decision == "Sell":
            # First approve the trading contract to spend tokens
            approve_tx = token_contract.functions.approve(
                TOKEN_TRADING_ADDRESS,
                amount
            ).build_transaction({
                'from': account,
                'gas': 6721975,
                'gasPrice': 20000000000,
                'nonce': w3.eth.get_transaction_count(account),
            })
            
            # Sign and send approval transaction
            signed_approve_tx = w3.eth.account.sign_transaction(approve_tx, private_key=PRIVATE_KEY)
            approve_tx_hash = w3.eth.send_raw_transaction(signed_approve_tx.rawTransaction)
            w3.eth.wait_for_transaction_receipt(approve_tx_hash)
            
            # Now sell the tokens
            price = trading_contract.functions.tokenPrice().call()
            revenue = amount * price
            
            sell_tx = trading_contract.functions.sellTokens(amount).build_transaction({
                'from': account,
                'gas': 6721975,
                'gasPrice': 20000000000,
                'nonce': w3.eth.get_transaction_count(account),
            })
            
            # Sign and send sell transaction
            signed_sell_tx = w3.eth.account.sign_transaction(sell_tx, private_key=PRIVATE_KEY)
            sell_tx_hash = w3.eth.send_raw_transaction(signed_sell_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(sell_tx_hash)
            
            return f"Executed SELL order for {amount} tokens. Transaction hash: {receipt.transactionHash.hex()}"
            
        else:
            return f"No trade action taken for decision: {decision}"
            
    except Exception as e:
        return f"Error executing trade: {str(e)}"

# Trade Maker: analyze prices and make trade decisions
@tool
def analyze_and_decide_trade():
    """Analyze CoinGecko and Chainlink prices and make a trade decision (Buy/Sell/Hold)."""
    try:
        cg_price = fetch_coingecko_price()
        chainlink_price = get_eth_price()
        # Simple logic: if CoinGecko price > Chainlink price by >1%, suggest Sell; if < -1%, suggest Buy; else Hold
        try:
            cg_val = float(cg_price.split('$')[1])
            cl_val = float(chainlink_price.split('$')[1])
            diff_pct = ((cg_val - cl_val) / cl_val) * 100
            if diff_pct > 1:
                decision = f"Sell (CoinGecko price is {diff_pct:.2f}% higher than Chainlink)"
            elif diff_pct < -1:
                decision = f"Buy (CoinGecko price is {abs(diff_pct):.2f}% lower than Chainlink)"
            else:
                decision = "Hold (Prices are similar)"
        except Exception:
            decision = "Unable to parse prices for decision."
        return f"Decision: {decision}\nCoinGecko: {cg_price}\nChainlink: {chainlink_price}"
    except Exception as e:
        return f"Error analyzing trade: {e}"

# Price Checker: fetch and report prices from CoinGecko
@tool
def fetch_coingecko_price():
    """Fetch the current ETH/USD price from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "ethereum",
            "vs_currencies": "usd",
            "x_cg_pro_api_key": COINGECKO_API_KEY
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        price = response.json()["ethereum"]["usd"]
        return f"CoinGecko ETH/USD price: ${price:.2f}"
    except Exception as e:
        return f"Error fetching CoinGecko price: {e}"

# Create prompts for agents
price_checker_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a specialized price monitoring agent that uses Chainlink's price feed and CoinGecko's historical price data to provide real-time and historical ETH/USD price information. Your primary goal is to ensure accurate and timely price data for trading decisions. Always compare the current ETH/USD price to the price from 7 days ago using CoinGecko and include this comparison in your analysis."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

trade_maker_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an experienced trading agent that analyzes price information 
    and makes trading decisions. You aim to maximize profits while managing risk 
    effectively. You use technical analysis and market trends to make informed decisions."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Add new tools to agents
price_checker_tools = [fetch_coingecko_price, get_eth_price, get_simulated_price, get_historical_eth_price, compare_eth_price]
trade_maker_tools = [analyze_and_decide_trade, check_balance, execute_trade, log_trade]

# Create agents
price_checker_agent = create_openai_functions_agent(llm, price_checker_tools, price_checker_prompt)
trade_maker_agent = create_openai_functions_agent(llm, trade_maker_tools, trade_maker_prompt)

price_checker_executor = AgentExecutor(agent=price_checker_agent, tools=price_checker_tools, verbose=True)
trade_maker_executor = AgentExecutor(agent=trade_maker_agent, tools=trade_maker_tools, verbose=True)

def run_defi_simulation():
    """Run the DeFi simulation."""
    print("\n--- Starting DeFi Simulation ---")
    
    # Price Checker Agent gets the price
    price_result = price_checker_executor.invoke({
        "input": "Get the current ETH/USD price and analyze the market conditions.",
        "chat_history": [],
        "agent_scratchpad": []
    })
    print("\nPrice Checker Result:", price_result)
    
    # Trade Maker Agent makes a decision
    trade_result = trade_maker_executor.invoke({
        "input": f"Based on the price information: {price_result['output']}, make a trading decision.",
        "chat_history": [],
        "agent_scratchpad": []
    })
    print("\nTrade Maker Result:", trade_result)

    # Automatically log the trade decision (use .invoke for @tool)
    log_trade.invoke({
        "action": "Trade Decision",
        "details": trade_result['output'] if 'output' in trade_result else str(trade_result)
    })
    print("\nTrade log updated:", trade_logs[-1])
    
    print("\n--- DeFi Simulation Results ---")

if __name__ == "__main__":
    run_defi_simulation()