import smartpy as sp

Harbinger = sp.io.import_script_from_url("file:common.py")

#####################################################################
# An Oracle contract accepts signed updates for a list of assets.
#
# Oracles are configured with a list of assets whose updates they
# track and a public key which will verify signatures on the asset
# data.
#
# Anyone may update the Oracle with properly signed data. Signatures
# for the oracle are provided by signing the packed bytes of the
# following Michelson data:
# 'pair <asset code | string> (pair <start | timestamp> (pair <end | timestamp> (pair <nat | open> (pair <nat | high> (pair <nat low> (pair <close | nat> <volume | nat>))))))'
#
# Anyone can request the Oracle push its data to another contract. Pushed
# data should generally be pushed to a Normalizer contract rather than
# consumed directly.
#
# Oracles can be revoked by calling the revoke entry point with the
# signature for bytes representing an Option(Key) Michelson type with
# value none. After revocation, the Oracle will refuse to process
# further updates.
#
# Updates to the Oracle must be monotonically increasing in start time.
#
# Values in the Oracle are represented as a natural numbers with six
# digits of precision. For instance $123.45 USD would be represented
# as 123_450_000.
#####################################################################


class OracleContract(sp.Contract):
    # Initialze a new oracle.
    #
    # Parameters:
    # publicKey(sp.TKey): The public key used to verify Oracle updates.
    # initialData(sp.TBigMap(sp.TString, TezosOracle.OracleDataType)): A map of initial values for the Oracle.
    def __init__(
        self,
        publicKey=sp.some(
            sp.key("sppk7bkCcE4TZwnqqR7JAKJBybJ2XTCbKZu11ESTvvZQYtv3HGiiffN")),
        initialData=sp.big_map(
            l={
                "XTZ-USD": (sp.timestamp(0), (sp.timestamp(0), (0, (0, (0, (0, 0))))))
            },
            tkey=sp.TString,
            tvalue=Harbinger.OracleDataType
        )
    ):
        self.init(
            publicKey=publicKey,
            oracleData=initialData
        )


    # Push the assets
    @sp.entry_point
    def pushAsset(self, params):
        sp.verify(self.data.publicKey.is_some(), "revoked")
        sp.set_type(params, sp.TRecord(asset=sp.TString, urlType=sp.TString))
        assetCode = params.asset
        urltype = params.urlType
        # Check if the asset code is not in the oracle data
        # sp.verify(~ self.data.oracleData.contains(assetCode), "Asset already exists in oracle")
        # Initialize the initial data for the asset
        initialOracleData = (
            sp.timestamp(0),
            (
                sp.timestamp(0),
                (
                    0,
                    (
                        0,
                        (
                            0,
                            (
                                0,
                                0
                            )
                        )
                    )
                )
            )
        )
        self.data.oracleData[assetCode] = initialOracleData

        # Emit the event
        sp.emit(sp.record(event="REQUESTED_PUSHED",asset=assetCode, type=urltype),tag="REQUESTED_PUSHED")
  
    
    # Push the data for the Oracle to another contract.
    #
    # The parameter is a contract to push the data to.
    @sp.entry_point
    def push(self, contract):
        sp.transfer(self.data.oracleData, sp.mutez(0), contract)

    @sp.entry_point
    def update(self, params):
        # If there is no value for the public key, the oracle is revoked. Ignore updates.
        sp.verify(self.data.publicKey.is_some(), "revoked")

        # Iterate over assets in the input map.
        keyValueList = params.items()
        sp.for assetData in keyValueList:
            # Extract asset names, signatures, and the new data.
            assetName = assetData.key
            signature = sp.compute(sp.fst(assetData.value))
            newData = sp.compute(sp.snd(assetData.value))

            # Verify Oracle is tracking this asset.
            sp.if self.data.oracleData.contains(assetName):
                # Verify start timestamp is newer than the last update.
                oldData = sp.compute(self.data.oracleData[assetName])
                oldStartTime = sp.compute(sp.fst(oldData))
                newStartTime = sp.compute(sp.fst(newData))    
                sp.if newStartTime > oldStartTime:                
                    # Verify signature.
                    bytes = sp.pack((assetName, newData))
                    sp.verify(
                        sp.check_signature(
                            self.data.publicKey.open_some(), signature, bytes
                        ),
                        "bad sig"
                    )

                    # Replace the data.
                    self.data.oracleData[assetName] = newData

    # Returns the data in the Oracle for the given asset in an onchain view..
    #
    # The data returned is a price candle given in nested pairs with the following components:
    # - timestamp - candle start time
    # - timestamp - candle end time
    # - nat - open price
    # - nat - high price
    # - nat - low price
    # - nat - close price
    # - nat - volume
    #
    # Values represented as a natural number with six digits of precision. For instance $123.45 USD would be represented
    # as 123_450_000.
    #
    # Parameters: The of the asset code (ex. XTZ-USD)
    @sp.onchain_view()
    def pull(self, assetCode):
        sp.set_type(assetCode, sp.TString)

        # Verify this normalizer has data for the requested asset.
        sp.verify(
            self.data.oracleData.contains(assetCode),
            message="bad request"
        )

        # Callback with the requested data.
        sp.result(self.data.oracleData[assetCode])

# Only run tests if this file is main.
if __name__ == "__main__":
    
    #####################################################################
    # Test Helpers
    #####################################################################

    # Default Oracle Contract Keys
    testAccount = sp.test_account("Test1")
    testAccountPublicKey = sp.some(testAccount.public_key)
    
    # Initial data for the oracle
    initialOracleData = (
        sp.timestamp(0),
        (
            sp.timestamp(0),
            (
                0,
                (
                    0,
                    (
                        0,
                        (
                            0,
                            0
                        )
                    )
                )
            )
        )
    )
    
    @sp.add_test(name="Push Asset and Get")
    def test():
        scenario = sp.test_scenario()
        scenario.h1("Push Asset and Get")

        scenario.h2("GIVEN an Oracle contract")
        assetCode = "XTZ-USD"
        contract = OracleContract(
            publicKey=testAccountPublicKey,
            initialData=sp.big_map(
                l={
                    assetCode: initialOracleData
                },
                tkey=sp.TString,
                tvalue=Harbinger.OracleDataType
            )
        )
        scenario += contract

        scenario.h2("Push Asset")
        
        pushAssetCode = "BTC-USD"
        scenario += contract.pushAsset(
            sp.record(asset=pushAssetCode, urlType="1")
        )
        
        scenario.verify(contract.data.oracleData.contains(pushAssetCode))
    
    
    sp.add_compilation_target("oracle", OracleContract())