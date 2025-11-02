const fs = require('fs');
const path = require('path');

async function main() {
  const [deployer] = await ethers.getSigners();
  const Staking = await ethers.getContractFactory("TibbirStaking");
  const abi = Staking.interface.format(ethers.utils.FormatTypes.json);

  const outPath = path.join(__dirname, "../abis/staking.json");
  fs.writeFileSync(outPath, abi);
  console.log("ABI exported to", outPath);
}

main().catch(console.error);