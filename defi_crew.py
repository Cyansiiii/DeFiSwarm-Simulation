from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from web3 import Web3
from alchemy import Alchemy, Network
import time
import random
import os

# Configure Grok API
os.environ["GROQ_API_KEY"] = "sk-85ff0db0bd8a457c96f7c15ccf23cd29"

# Create Grok LLM instance
llm = ChatGroq(
    api_key="sk-85ff0db0bd8a457c96f7c15ccf23cd29",
    model_name="mixtral-8x7b-32768"
)

# Constants
ALCHEMY_API_KEY = "CX-G7CvHwlDifhfPg-Uti8KCrQd8Vaze"
ETH_USD_PRICE_FEED = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"  # Chainlink ETH/USD Price Feed
TOKEN_TRADING_ADDRESS = "0x78b6ca4b4cc3cf7e5d9937e06a1b9ba534008ee5"
DUMMY_TOKEN_ADDRESS = "0x246f6857e5577abcabc5fa40bd017e8c4bf739cd"
PRIVATE_KEY = "0xde18f385d8a7127738fcb84879781cfc1abcbdbf63ff2a014150746f13edac21"
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

# Create prompts for agents
price_checker_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a specialized price monitoring agent that uses Chainlink's 
    price feed to provide real-time ETH/USD price information. Your primary goal is 
    to ensure accurate and timely price data for trading decisions."""),
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

# Create agents
price_checker_tools = [get_eth_price, get_simulated_price]
trade_maker_tools = [check_balance, execute_trade]

price_checker_agent = create_openai_functions_agent(llm, price_checker_tools, price_checker_prompt)
trade_maker_agent = create_openai_functions_agent(llm, trade_maker_tools, trade_maker_prompt)

price_checker_executor = AgentExecutor(agent=price_checker_agent, tools=price_checker_tools, verbose=True)
trade_maker_executor = AgentExecutor(agent=trade_maker_agent, tools=trade_maker_tools, verbose=True)

def run_defi_simulation():
    """Run the DeFi simulation."""
    print("\n--- Starting DeFi Simulation ---")
    
    # Price Checker Agent gets the price
    price_result = price_checker_executor.invoke({
        "input": "Get the current ETH/USD price and analyze the market conditions."
    })
    print("\nPrice Checker Result:", price_result)
    
    # Trade Maker Agent makes a decision
    trade_result = trade_maker_executor.invoke({
        "input": f"Based on the price information: {price_result['output']}, make a trading decision."
    })
    print("\nTrade Maker Result:", trade_result)
    
    print("\n--- DeFi Simulation Results ---")

if __name__ == "__main__":
    run_defi_simulation() 