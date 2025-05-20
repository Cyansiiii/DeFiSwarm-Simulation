// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract TokenTrading is Ownable {
    IERC20 public token;
    uint256 public tokenPrice; // Price in wei (1 ETH = 10^18 wei)
    
    event TokensBought(address buyer, uint256 amount, uint256 cost);
    event TokensSold(address seller, uint256 amount, uint256 revenue);
    
    constructor(address _tokenAddress, uint256 _initialPrice) Ownable(msg.sender) {
        token = IERC20(_tokenAddress);
        tokenPrice = _initialPrice;
    }
    
    function setTokenPrice(uint256 _newPrice) external onlyOwner {
        tokenPrice = _newPrice;
    }
    
    function buyTokens(uint256 _amount) external payable {
        require(msg.value >= _amount * tokenPrice, "Insufficient ETH sent");
        
        uint256 cost = _amount * tokenPrice;
        require(token.transfer(msg.sender, _amount), "Token transfer failed");
        
        // Refund excess ETH
        if (msg.value > cost) {
            payable(msg.sender).transfer(msg.value - cost);
        }
        
        emit TokensBought(msg.sender, _amount, cost);
    }
    
    function sellTokens(uint256 _amount) external {
        require(_amount > 0, "Amount must be greater than 0");
        
        uint256 revenue = _amount * tokenPrice;
        require(token.transferFrom(msg.sender, address(this), _amount), "Token transfer failed");
        
        payable(msg.sender).transfer(revenue);
        emit TokensSold(msg.sender, _amount, revenue);
    }
    
    // Function to withdraw ETH from contract (only owner)
    function withdrawETH() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }
    
    // Function to withdraw tokens from contract (only owner)
    function withdrawTokens() external onlyOwner {
        token.transfer(owner(), token.balanceOf(address(this)));
    }
} 