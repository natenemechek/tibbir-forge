// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract ExpertToken is ERC721 {
    uint256 public nextId = 1;
    IERC20 public tibbir;  // $TIBBIR token

    mapping(uint256 => string) public tokenMetadata;

    constructor(address _tibbir) ERC721("ExpertToken", "EXP") {
        tibbir = IERC20(_tibbir);
    }

    function mint(address to, string memory metadata, uint256 stakeAmount) external {
        require(stakeAmount > 0, "Stake required");
        tibbir.transferFrom(msg.sender, address(this), stakeAmount);

        uint256 tokenId = nextId++;
        _safeMint(to, tokenId);
        tokenMetadata[tokenId] = metadata;
    }
}