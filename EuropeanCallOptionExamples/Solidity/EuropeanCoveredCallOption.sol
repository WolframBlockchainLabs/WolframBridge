// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/ConfirmedOwner.sol";

contract EuropeanCoveredCallOption is ChainlinkClient, ConfirmedOwner {
    /**
     ** Chainlink Variables
     *
     * Chainlink to make request
     * jobID - return value (string now)
     * fee - Varies by network and job
     */
    using Chainlink for Chainlink.Request; 
    bytes32 private jobId; 
    uint256 private fee; 

    string public ethPrice; 

    ERC20 public stableCoin;
    address payable private buyer;
    address payable private seller;
    uint256 public strikePrice;
    uint256 public expirationTime;
    uint256 public contractPremium;
    uint256 private escrowAmount = 1000 ether; // 1000 XTZ equivalent in wei - test
    uint256 public currentPrice;

    enum ContractState { Waiting, Active, Executed }
    ContractState public state;

    /** 
    * @notice Initialize the link token and target oracle
    *
    * Goerli Testnet details: 
    * Link Token: 0x326C977E6efc84E512bB9C30f76E30c160eD06FB 
    * Oracle: 0xCC79157eb46F5624204f47AB42b3906cAA40eaB7 
    * jobId: 7d80a6386ef543a3abb52817f6707e3b 
    *
    * Milkomeda Mainnet details:
    * Link Token: 0xf390830DF829cf22c53c8840554B98eafC5dCBc2
    * Oracle: 0x49484Ae8646C12A8A68DfE2c978E9d4Fa5b01D16
    * jobId: 7d80a6386ef543a3abb52817f6707e3b
    */ 
    constructor () ConfirmedOwner(msg.sender) {
        // chainlink settings
        setChainlinkToken(0x326C977E6efc84E512bB9C30f76E30c160eD06FB); 
        setChainlinkOracle(0xCC79157eb46F5624204f47AB42b3906cAA40eaB7); 
        jobId = "7d80a6386ef543a3abb52817f6707e3b"; 
        fee = (1 * LINK_DIVISIBILITY) / 10; // 0,1 * 10**18 (Varies by network and job) 
    }

    function initContract(
        address _stableCoin,
        address payable _seller,
        uint256 _strikePrice,
        uint256 _expirationTime,
        uint256 _contractPremium
    ) external payable {
        require(
            msg.sender.balance >= escrowAmount,
            "Insufficient balance in seller account"
        );
        require(
            msg.value == escrowAmount,
            "Please send exact XTZ amount"
        );
        
        // main settings    
        stableCoin = ERC20(_stableCoin);
        seller = _seller;
        strikePrice = _strikePrice;
        expirationTime = _expirationTime;
        contractPremium = _contractPremium;
        state = ContractState.Waiting;
    }

    /**
     * Create a Chainlink request to retrieve API response, find the target
     * data which is located in a list
     *
     * API return value
       {
        "queryresult":{
            "success":true,
            "error":false,
            "numpods":1,
            ...
            "pods":[
                {
                    "title":"Result",
                    "scanner":"Money",
                    "id":"Result",
                    ...
                    "subpods":[
                        {
                            "title":"",
                            "plaintext":"$1843.49 (US dollars) (24\/07\/2023)"
                        }
                    ],
                    ...
                }
            ],
            ...
        }
       }
     * 
     * How to get eth price - "queryresult,pods,0,subpods,0,plaintext" (0 is the index of array)
     */
    function requestOffChainData() public { 
        Chainlink.Request memory req = buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfill.selector
        );
        // Set the URL to perform the GET request on
        req.add(
            "get",
            "https://api.wolframalpha.com/v2/query?input=ethereum+price+in+usd&output=JSON&includepodid=Result&format=plaintext&appid=6RKXJQ-W8TE9W3PTH"
        );
        req.add("path", "queryresult,pods,0,subpods,0,plaintext");
        // Sends the request
        sendChainlinkRequest(req, fee);  
    } 

    /**
     * Receive the response in the form of uint256
     * This is the callback function so currentPrice is automatically updated.
     */
    function fulfill(bytes32 _requestId, bytes memory data) public recordChainlinkFulfillment(_requestId) {
        ethPrice = string(data);
        ethPrice = getSlice(1, 7, ethPrice);

        currentPrice = strToUint(ethPrice) * 10 ** 14;
    }
    
    function getSlice(uint256 begin, uint256 end, string memory text) public pure returns (string memory) {
        bytes memory a = new bytes(end-begin);
        uint j = 0;
        for(uint i=0;i<end-begin;i++){
            if (bytes(text)[i+begin] == ".")
                j++;

            a[i] = bytes(text)[i+begin+j];
        }
        return string(a);    
    }  

    function strToUint(string memory _str) public pure returns(uint256 res) {
        for (uint256 i = 0; i < bytes(_str).length; i++) {
            if ((uint8(bytes(_str)[i]) - 48) < 0 || (uint8(bytes(_str)[i]) - 48) > 9) {
                return 0;
            }
            res += (uint8(bytes(_str)[i]) - 48) * 10**(bytes(_str).length - i - 1);
        }
        
        return res;
    }  

    /** 
    * Allow withdraw of Link tokens from the contract 
    */ 
    function withdrawLink() public onlyOwner { 
        LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress()); 
        require(link.transfer(msg.sender, link.balanceOf(address(this))), 'Unable to transfer'); 
    }     

    function enterContract() external payable {
        require(state == ContractState.Waiting, "Invalid state");
        require(msg.value == contractPremium, "Please send exact XTZ amount");
        require(
            stableCoin.balanceOf(msg.sender) >= strikePrice * 1000,
            "Insufficient stablecoin in buyer account"
        );

        buyer = payable(msg.sender);
        state = ContractState.Active;

        (bool sent,) = seller.call{value: contractPremium}(""); //transfer XTZ to contract
        require(sent, "Failed to send ETH");
        stableCoin.transferFrom(buyer, address(this), strikePrice * 1000); // transfer stablecoin to contract
    }

    function executeContract() external {
        require(state == ContractState.Active, "Invalid state");
        require(block.timestamp >= expirationTime, "Contract not at expiration");
        require(currentPrice >= strikePrice, "Current price is less than strike price");

        state = ContractState.Executed;

        stableCoin.transfer(seller, strikePrice * 1000); // transfer stablecoin to seller
        buyer.transfer(escrowAmount); // transfer XTZ to buyer
    }
}