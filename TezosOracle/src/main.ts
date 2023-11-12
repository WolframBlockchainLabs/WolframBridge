import { TezosToolkit, PollingSubscribeProvider } from '@taquito/taquito';
import { InMemorySigner } from '@taquito/signer';
import { Schema } from '@taquito/michelson-encoder'
import * as config from '../config.json';
import { retrieveOracleDataFromCoinbase, updateOracleFromCoinbaseOnce, updateOracleFromFeedOnce } from './controllers/update';
import { LogLevel } from './controllers/common';
import express, { Request, Response } from 'express';
import bodyParser from 'body-parser';

const app = express();
const port = 3000;
const apiKey = config.API_KEY;

interface PriceData {
  price: number;
  time: number;
}

// Simulated data, replace with your actual logic to get the price
async function getPrice(tokenPair: string): Promise<PriceData> {
  const oracleData = await retrieveOracleDataFromCoinbase(
    config.apiKeyID,
    config.apiSecret,
    config.apiPassphrase,
  )
  return oracleData;
}

app.use(bodyParser.json());

app.get('/getPrice', (req: Request, res: Response) => {
  const tokenPair = req.query.tokenPair as string;
  const providedApiKey = req.query.apiKey as string;

  if (!tokenPair || !providedApiKey || providedApiKey !== apiKey) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const priceData = getPrice(tokenPair);
  res.json(priceData);
});

app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});

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
