#Marlowe

This section contains examples of Marlowe smart contracts that leverage the bridge real-world data as input for desentralized applications. This bridge plays a crucial role in bringing external data onto the blockchain, enabling applications to interact with off-chain information.

## Table of Contents

- [Introduction](#introduction)
- [Examples](#examples)
- [Getting Started](#getting-started)

## Introduction

Marlowe comprises a suite of tools and languages designed to facilitate the creation of financial and transactional smart contracts that ensure safety and reliability.
Our mission is to advance the science of blockchains, one of our approaches is to make real world data accessible on-chain.  

## Examples

### 1. Simple Bet
We have developed a prototype smart contract that allocates the gathered funds to specific wallets based on choices made by a designated Bridge address. The guide in Jupyter Notebook, available here, walks through the deployment and execution steps for the entire smart contract workflow.

Our prototype directly inputs values into the smart contract by the Bridge address. The primary objective of this proposal is to advance this prototype by integrating our Wolfram Price Feed Infrastructure into the smart contract. This enhancement aims to automate the data input process, demonstrating the utility of our service within the Cardano community.

## Getting Started
Here are the steps to run our prototypes:
# 1. To make sure we are always up to date with the Marlowe versions clone [Marlowe Starter Kit](https://github.com/input-output-hk/marlowe-starter-kit).
# 2. In an other folder copy the contents of the Marlowe directory
```
git clone --depth 1 --no-checkout https://github.com/WolframBlockchainLabs/WolframBridge
cd WolframBridge
git sparse-checkout set Marlowe
git checkout
```
# 3. Copy the contents of the lessons folder and copy it on the starter-kit lessons folder

