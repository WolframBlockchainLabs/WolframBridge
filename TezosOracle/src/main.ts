import { TezosToolkit, PollingSubscribeProvider } from '@taquito/taquito';
import { InMemorySigner } from '@taquito/signer';
import { Schema } from '@taquito/michelson-encoder'
import * as config from '../config.json';
import { updateOracleFromCoinbaseOnce, updateOracleFromFeedOnce } from './controllers/update';
import { LogLevel } from './controllers/common';


async function main() {

  const signer = config.tezosConfig.publicKey;
  const nodeURL = config.tezosConfig.nodeAddress;
  const pk = config.tezosConfig.privateKey;
  // Define the event name you want to listen for
  const eventName = config.eventName;

  // Address of your smart contract
  const contractAddress = 'KT1P1rYngNnYx8EWmLu8pybZKroVYYFvi7Qv';
  const normalizerContractAddress = 'KT1RnKD434UguQbKERPQ3N9gDGZ6W8BscFDg';

  // Initialize the Tezos toolkit
  const tezos = new TezosToolkit(nodeURL);
  tezos.setSignerProvider(new InMemorySigner(pk));

  tezos.setStreamProvider(
    tezos.getFactory(PollingSubscribeProvider)({
      shouldObservableSubscriptionRetry: true,
      pollingIntervalMilliseconds: 1500
    })
  );

  try {
    const sub = tezos.stream.subscribeEvent({
      tag: eventName,
      address: contractAddress,
      excludeFailedOperations: true
    });

    const storageType = {
      prim: 'pair',
      args: [
        { prim: 'string', annots: ['%assetCode'] },
        {
          prim: 'pair',
          args: [
            { prim: 'string', annots: ['%urltype'] },
            { prim: 'string', annots: ['%urltype'] }
          ]
        },
      ]
    };
    const storageSchema = new Schema(storageType);

    sub.on('data', async eventData => {
      const encodedPayload = eventData.payload;
      const data = storageSchema.Execute(encodedPayload)
      const assetName = data.assetCode;
      const urltype = data.urltype;
      let hash = "";
      if (urltype.includes('coinbase.com')) {
        hash = await updateOracleFromCoinbaseOnce(
          LogLevel.Debug,
          tezos,
          config.apiKeyID,
          config.apiSecret,
          config.apiPassphrase,
          contractAddress,
          [assetName],
          undefined,
        )
      } else {
        hash = await updateOracleFromFeedOnce(
          LogLevel.Debug,
          tezos,
          urltype,
          contractAddress,
          [assetName],
          undefined,
        )
      }
      console.log(data)
    });


  } catch (e) {
    console.log(e);
  }
}

main();
