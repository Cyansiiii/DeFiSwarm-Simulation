# DeFi Trading Crew

A CrewAI-based implementation of automated DeFi trading agents that monitor ETH/USD prices and execute trades based on market conditions.

## Features

- Real-time ETH/USD price monitoring using Chainlink price feed
- Automated trading decisions based on technical analysis
- Integration with Ganache for local blockchain testing
- Fallback to simulated price data when needed
- Detailed trading analysis and reporting

## Prerequisites

- Python 3.8+
- Ganache running locally on port 7545
- Alchemy API key
- Deployed TokenTrading and DummyToken contracts

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd defi-trading-crew
```

2. Create and activate a virtual environment:
```bash
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```env
ALCHEMY_API_KEY=your_alchemy_api_key_here
TOKEN_TRADING_ADDRESS=your_token_trading_contract_address_here
DUMMY_TOKEN_ADDRESS=your_dummy_token_contract_address_here
PRIVATE_KEY=your_private_key_here
```

## Usage

1. Start Ganache:
```bash
ganache --networkId 5777 --gasPrice 20000000000 --gasLimit 6721975
```

2. Run the DeFi crew simulation:
```bash
python defi_crew.py
```

## Project Structure

- `defi_crew.py`: Main implementation of CrewAI agents and tasks
- `config.py`: Configuration and constants
- `contracts/`: Smart contract ABIs and deployment scripts
- `.env`: Environment variables (not tracked in git)

## Agents

### Price Checker Agent
- Monitors ETH/USD price using Chainlink price feed
- Provides real-time price information
- Tracks price trends and volatility
- Falls back to simulated data when needed

### Trade Maker Agent
- Analyzes price information for trading opportunities
- Makes buy/sell decisions based on technical analysis
- Executes trades on the blockchain
- Provides detailed trading analysis

## Tasks

1. Price Check Task
   - Monitor current ETH/USD price
   - Track price trends and volatility
   - Provide clear price information

2. Trade Decision Task
   - Analyze market conditions
   - Check account balances
   - Execute trades when favorable
   - Provide detailed analysis

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 