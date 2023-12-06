import smartpy as sp

class EUC(sp.Contract):
    def __init__(self, creator, buyer, escrowToken, tokenPair, oracleContract, normalizerContract):
        self.init(
            creator=creator,
            buyer=buyer,
            escrowToken=escrowToken,
            escrowAmount=sp.nat(0),
            escrowTokenId=sp.nat(0),
            strikePrice=sp.nat(0),
            expireTime=sp.timestamp(0),
            fee=sp.nat(0),
            paused=False,
            oraclePrice = sp.nat(0),
            tokenPair = "XTZ-USD",
            oracle = oracleContract,
            normalizer = normalizerContract
        )
    
    @sp.entry_point
    def oracleCallback(self, newNatValue):
        self.data.oraclePrice = newNatValue

    @sp.entry_point
    def init_option(self, params):
        self.data.creator = params.creator
        self.data.escrowToken = params.escrowToken
        self.data.escrowAmount = params.escrowAmount
        self.data.escrowTokenId = params.escrowTokenId
        self.data.strikePrice = params.strikePrice
        self.data.expireTime = params.expireTime
        self.data.fee = params.fee

        sp.verify(~self.data.paused,
                  "Contract is not accepting New Option Orders")
        sp.if self.data.tokenPair == "XTZ-USD":
            sp.verify(sp.utils.nat_to_mutez(self.data.escrowAmount) == sp.amount, "Wrong amount")
            
        sp.if self.data.tokenPair != "XTZ-USD":
            sp.verify(sp.amount == sp.mutez(0), "Invalid Send")
            # deposit escrow token to the contract
            _params = [
                    sp.record(from_=sp.sender,
                                        txs=[
                                            sp.record(to_=sp.self_address,
                                                        amount=params.escrowAmount,
                                                        token_id=params.escrowTokenId)
                                        ])
                ]
            self.transfer_token(params.escrowToken, _params)
        # get price
        pushParams = sp.record(asset=self.data.tokenPair, urlType="coinbase")
        self.pushAsset(self.data.oracle, pushParams)
        sp.emit(sp.record(creator=params.creator), tag="INIT_OPTION")

    @sp.entry_point
    def buy_option(self):
        Amount = sp.local("Amount", self.data.strikePrice * self.data.escrowAmount)
        sp.if self.data.tokenPair != "XTZ-USD":
            # check deposit amount
            sp.verify(sp.utils.nat_to_mutez(Amount.value) == sp.amount, "Insufficient Amount")
        
            # send premieum to the creator
            _params = [
                    sp.record(from_=sp.self_address,
                                        txs=[
                                            sp.record(to_=self.data.creator,
                                                        amount=self.data.fee,
                                                        token_id=self.data.escrowTokenId)
                                        ])
                ]
            self.transfer_token(self.data.escrowToken, _params)
        sp.else:
            sp.verify(sp.amount == sp.utils.nat_to_mutez(self.data.fee), "Insufficient Premieum Amount")
            # send premiuem to the creator
            sp.send(self.data.creator, sp.utils.nat_to_mutez(self.data.fee))
            # send deposit to the option
            _params = [
                    sp.record(from_=sp.sender,
                                        txs=[
                                            sp.record(to_=sp.self_address,
                                                        amount=Amount.value,
                                                        token_id=self.data.escrowTokenId)
                                        ])
                ]
            self.transfer_token(self.data.escrowToken, _params)

        self.data.buyer = sp.sender
        self.data.paused = True
        sp.emit(sp.record(buyer=self.data.buyer), tag="BUY_OPTION")

    @sp.entry_point
    def execute_option(self):

        # check expire time
        sp.verify(sp.now >= self.data.expireTime, "NOT EXPIRED")
        sp.verify(self.data.paused, "Not Created")
        
        Amount = sp.local("Amount", self.data.strikePrice * self.data.escrowAmount)
        price = sp.view("getPrice", self.data.normalizer, self.data.tokenPair, t=sp.TRecord(time=sp.TTimestamp, price=sp.TNat)).open_some("Invalid view")
        self.data.oraclePrice = price.price
        
        sp.if self.data.tokenPair != "XTZ-USD":
            sp.if self.data.strikePrice > self.data.oraclePrice:
                # send strikePrice * escrowAmount to buyer
                sp.send(self.data.buyer, sp.utils.nat_to_mutez(Amount.value))

                # send escrow-token to seller
                _params = [
                    sp.record(from_=sp.self_address,
                                        txs=[
                                            sp.record(to_=self.data.creator,
                                                        amount=self.data.escrowAmount,
                                                        token_id=self.data.escrowTokenId)
                                        ])
                ]
                self.transfer_token(self.data.escrowToken, _params)
            sp.else:
                # send strikePrice * escrowAmount to seller
                sp.send(self.data.creator, sp.utils.nat_to_mutez(Amount.value))

                # send escrow-token to buyer
                _params = [
                    sp.record(from_=sp.self_address,
                                        txs=[
                                            sp.record(to_=self.data.buyer,
                                                        amount=self.data.escrowAmount,
                                                        token_id=self.data.escrowTokenId)
                                        ])
                ]
                self.transfer_token(self.data.escrowToken, _params)
        sp.else:
            sp.if self.data.strikePrice > self.data.oraclePrice:
                # send strikePrice * escrowAmount to buyer
                _params = [
                sp.record(from_=sp.self_address,
                                    txs=[
                                        sp.record(to_=self.data.buyer,
                                                    amount=Amount.value,
                                                    token_id=self.data.escrowTokenId)
                                    ])
                ]
                self.transfer_token(self.data.escrowToken, _params)
                
                # send escrow-token to seller
                sp.send(self.data.creator, sp.utils.nat_to_mutez(self.data.escrowAmount))
            sp.else:
                # send strikePrice * escrowAmount to seller
                _params = [
                    sp.record(from_=sp.self_address,
                                        txs=[
                                            sp.record(to_=self.data.creator,
                                                        amount=Amount.value,
                                                        token_id=self.data.escrowTokenId)
                                        ])
                ]
                self.transfer_token(self.data.escrowToken, _params)
                
                # send escrow-token to buyer
                sp.send(self.data.buyer, sp.utils.nat_to_mutez(self.data.escrowAmount))
        self.data.paused = False
    
    def pushAsset(self, contract, params_):
        sp.set_type(contract, sp.TAddress)
        sp.set_type(params_, sp.TRecord(asset=sp.TString, urlType=sp.TString))
        
        contractParams = sp.contract(sp.TRecord(asset=sp.TString, urlType=sp.TString), contract, entry_point="pushAsset").open_some()
        sp.transfer(params_, sp.mutez(0), contractParams)
        
    def transfer_token(self, contract, params_):
        sp.set_type(contract, sp.TAddress)
        sp.set_type(params_, sp.TList(
                sp.TRecord(
                    from_ = sp.TAddress, 
                    txs = sp.TList(
                        sp.TRecord(
                            amount = sp.TNat, 
                            to_ = sp.TAddress, 
                            token_id = sp.TNat
                        ).layout(("to_", ("token_id", "amount")))
                    )
                )
            .layout(("from_", "txs"))))
        contractParams = sp.contract(sp.TList(
                sp.TRecord(
                    from_ = sp.TAddress, 
                    txs = sp.TList(
                        sp.TRecord(
                            amount = sp.TNat, 
                            to_ = sp.TAddress, 
                            token_id = sp.TNat
                        ).layout(("to_", ("token_id", "amount")))
                    )
                )
            .layout(("from_", "txs"))), contract, entry_point="transfer").open_some()
        sp.transfer(params_, sp.mutez(0), contractParams)

@sp.add_test(name="EuropeanCallOption")
def test():
    sc = sp.test_scenario()
    sc.h1("EuropeanCallOption")
    seller = sp.test_account("Administrator")
    buyer = sp.test_account("Alice")
    escrowToken = sp.address("KT1AFA2mwNUMNd4SsujE1YYp29vd8BZejyKW")
    oracleContract = sp.address('KT1QLPABNCD4z1cSYVv3ntYDYgtWTed7LkYr')
    normalizerContract = sp.address('KT1RnKD434UguQbKERPQ3N9gDGZ6W8BscFDg')
    sc.h1("Full test")
    eu_contract = EUC(seller.address, buyer.address, escrowToken, "XYZ-USD", oracleContract, normalizerContract)
    sc += eu_contract
    
    sc.h2("Init Option")
    sc += eu_contract.init_option(sp.record(
        creator=seller.address,
        buyer=buyer.address,
        escrowToken=escrowToken,
        escrowAmount=sp.nat(10),
        escrowTokenId=sp.nat(0),
        strikePrice=sp.nat(100),
        expireTime = sp.timestamp(10),
        fee=sp.nat(10),
        faTwoToken=False,
    )).run(sender=seller.address, amount=sp.mutez(10))
    
    sc.h2("Buy Option")
    sc += eu_contract.buy_option().run(sender=buyer.address, amount=sp.mutez(10))
    
    sc.h2("Execute Option")
    sc += eu_contract.execute_option().run(now=sp.timestamp(20), valid=False)
    
    
    
    
