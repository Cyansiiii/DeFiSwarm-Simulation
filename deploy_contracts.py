import solcx
from web3 import Web3
import json
import os
from solcx import compile_standard
from web3.middleware import ExtraDataToPOAMiddleware

# --- Solidity Compiler Version Management ---
required_solc_version = '0.8.20'
installed_versions = [str(v) for v in solcx.get_installed_solc_versions()]
if required_solc_version not in installed_versions:
    print(f"Solidity compiler version {required_solc_version} not found. Installing...")
    solcx.install_solc(required_solc_version)
    print(f"Successfully installed solc {required_solc_version}")
else:
    print(f"Solidity compiler version {required_solc_version} is already installed.")
solcx.set_solc_version(required_solc_version)
print(f"Successfully set solc version to {solcx.get_solc_version()}")
# --- End Solidity Compiler Version Management ---

# Ganache Configuration
GANACHE_URL = "http://192.168.1.12:8545"
GAS_PRICE = 20000000000
GAS_LIMIT = 6721975

# Initialize Web3 connection
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

def compile_contract(contract_path):
    with open(contract_path, "r") as file:
        source = file.read()
    
    print(f"\n=== Compiling {contract_path} ===")
    print("Source code preview:")
    print(source[:200] + "...\n" if len(source) > 200 else source)

    # Get the absolute path to node_modules
    node_modules_path = os.path.abspath('node_modules')
    
    compiled_sol = compile_standard({
        "language": "Solidity",
        "sources": {contract_path: {"content": source}},
        "settings": {
            "outputSelection": {
                "*": {
                    "*": ["abi", "evm.bytecode", "evm.deployedBytecode"]
                }
            },
            "optimizer": {
                "enabled": True,
                "runs": 200
            },
            "remappings": [
                f"@openzeppelin={node_modules_path}/@openzeppelin"
            ],
            "evmVersion": "london"
        }
    }, allow_paths=node_modules_path)

    contract_name = contract_path.split('.')[0]
    contract_data = compiled_sol['contracts'][contract_path][contract_name]
    
    if not contract_data['evm']['bytecode']['object']:
        print("❌ Error: Empty bytecode generated!")
        print("Possible reasons:")
        print("- Syntax errors in contract")
        print("- Missing imports (e.g. OpenZeppelin paths)")
        print("- Incorrect compiler version")
        print("\nFull compilation output:")
        print(json.dumps(compiled_sol, indent=2))
    else:
        bytecode = contract_data['evm']['bytecode']['object']
        print(f"✅ Success! Bytecode length: {len(bytecode)} bytes")
        print(f"First 100 chars: {bytecode[:100]}...")
    
    return compiled_sol

def deploy_contract(compiled_contract, contract_name, constructor_args=None):
    contract_key = f"{contract_name}:{contract_name.split('.')[0]}"
    bytecode = compiled_contract['contracts'][contract_name][contract_name.split('.')[0]]['evm']['bytecode']['object']
    abi = compiled_contract['contracts'][contract_name][contract_name.split('.')[0]]['abi']

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    account = w3.eth.accounts[0]

    # Build transaction with explicit gas parameters
    transaction = {
        'from': account,
        'gas': GAS_LIMIT,
        'gasPrice': GAS_PRICE,
        'nonce': w3.eth.get_transaction_count(account),
    }

    print(f"\nDeploying {contract_name}...")
    print(f"Using account: {account}")
    print(f"Gas limit: {GAS_LIMIT}")
    print(f"Gas price: {GAS_PRICE}")

    try:
        if constructor_args:
            tx_hash = contract.constructor(*constructor_args).transact(transaction)
        else:
            tx_hash = contract.constructor().transact(transaction)
        
        print(f"Transaction hash: {tx_hash.hex()}")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction receipt: {tx_receipt}")
        contract_address = tx_receipt.contractAddress
        return contract_address, abi
    except Exception as e:
        print(f"Error deploying contract: {str(e)}")
        raise

def main():
    # Compile contracts
    print("Compiling DummyToken contract...")
    dummy_token_compiled = compile_contract("DummyToken.sol")
    print("Compiling TokenTrading contract...")
    token_trading_compiled = compile_contract("TokenTrading.sol")

    # Deploy DummyToken
    print("Deploying DummyToken...")
    dummy_token_address, dummy_token_abi = deploy_contract(dummy_token_compiled, "DummyToken.sol")

    # Deploy TokenTrading with DummyToken address and initial price (1 ETH in wei)
    print("Deploying TokenTrading...")
    token_trading_address, token_trading_abi = deploy_contract(
        token_trading_compiled,
        "TokenTrading.sol",
        constructor_args=[dummy_token_address, Web3.to_wei(1, 'ether')]
    )

    # Save contract addresses and ABIs
    contract_data = {
        "DummyToken": {
            "address": dummy_token_address,
            "abi": dummy_token_abi
        },
        "TokenTrading": {
            "address": token_trading_address,
            "abi": token_trading_abi
        }
    }

    with open('contract_data.json', 'w') as f:
        json.dump(contract_data, f, indent=4)

    print("Contracts deployed and data saved to contract_data.json")

if __name__ == "__main__":
    main()