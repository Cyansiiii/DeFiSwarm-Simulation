import json
from web3 import Web3
from solcx import compile_standard, install_solc, set_solc_version
from web3.middleware import ExtraDataToPOAMiddleware

# Install and set Solidity compiler version
required_solc_version = '0.8.20'
try:
    set_solc_version(required_solc_version)
except:
    print(f"Installing Solidity compiler version {required_solc_version}...")
    install_solc(required_solc_version)
    set_solc_version(required_solc_version)
print(f"Using Solidity compiler version: {required_solc_version}")

# Ganache Configuration
GANACHE_URL = "http://127.0.0.1:8545"  # Use localhost instead of IP
GAS_PRICE = 20000000000
GAS_LIMIT = 6721975
CHAIN_ID = 1337  # Ganache's default chain ID

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

print(f"\nGanache Configuration:")
print(f"URL: {GANACHE_URL}")
print(f"Chain ID: {CHAIN_ID}")
print(f"Gas Price: {GAS_PRICE}")
print(f"Gas Limit: {GAS_LIMIT}")

# Check Ganache connection and configuration
print("\nChecking Ganache connection...")
print(f"Connected: {w3.is_connected()}")
print(f"Chain ID: {w3.eth.chain_id}")
print(f"Block Number: {w3.eth.block_number}")
print(f"Gas Price: {w3.eth.gas_price}")
print(f"Node Version: {w3.client_version}")

# Get first account
account = w3.eth.accounts[0]
print(f"\nFirst Account: {account}")
print(f"Balance: {w3.from_wei(w3.eth.get_balance(account), 'ether')} ETH")

def compile_contract():
    with open("TestContract.sol", "r") as file:
        source = file.read()
    
    print("\nCompiling contract...")
    compiled_sol = compile_standard({
        "language": "Solidity",
        "sources": {"TestContract.sol": {"content": source}},
        "settings": {
            "outputSelection": {
                "*": {
                    "*": ["abi", "evm.bytecode"]
                }
            }
        }
    })
    
    bytecode = compiled_sol['contracts']['TestContract.sol']['TestContract']['evm']['bytecode']['object']
    print(f"Bytecode length: {len(bytecode)} bytes")
    print(f"First 100 chars: {bytecode[:100]}...")
    
    return compiled_sol

def deploy_contract():
    # Compile contract
    compiled_sol = compile_contract()
    bytecode = compiled_sol['contracts']['TestContract.sol']['TestContract']['evm']['bytecode']['object']
    abi = compiled_sol['contracts']['TestContract.sol']['TestContract']['abi']
    
    # Get account
    account = w3.eth.accounts[0]
    print(f"\nUsing account: {account}")
    balance = w3.eth.get_balance(account)
    print(f"Account balance: {w3.from_wei(balance, 'ether')} ETH")
    
    # Create contract instance
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Build transaction
    transaction = {
        'from': account,
        'gas': GAS_LIMIT,
        'gasPrice': GAS_PRICE,
        'nonce': w3.eth.get_transaction_count(account),
        'chainId': CHAIN_ID
    }
    
    # Deploy contract
    print("\nDeploying contract...")
    print(f"Gas limit: {GAS_LIMIT}")
    print(f"Gas price: {GAS_PRICE}")
    
    try:
        # Estimate gas first
        gas_estimate = contract.constructor().estimate_gas(transaction)
        print(f"Estimated gas: {gas_estimate}")
        transaction['gas'] = gas_estimate
        
        tx_hash = contract.constructor().transact(transaction)
        print(f"Transaction hash: {tx_hash.hex()}")
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Contract deployed at: {tx_receipt.contractAddress}")
        
        return tx_receipt.contractAddress, abi
    except Exception as e:
        print(f"\nError deploying contract: {str(e)}")
        if hasattr(e, 'args') and len(e.args) > 0:
            print(f"Error details: {e.args[0]}")
        raise

if __name__ == "__main__":
    deploy_contract() 