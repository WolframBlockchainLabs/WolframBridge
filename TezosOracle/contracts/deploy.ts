// main.ts
import fs = require('fs')
import { TezosToolkit, OriginationOperation } from '@taquito/taquito';
import { InMemorySigner } from '@taquito/signer';
import * as config from '../config.json';
import { LogLevel } from '../src/controllers/common';
import Utils from '../src/controllers/utils'

function pad(number: any) {
  return number.toString().padStart(2, '0');
}

function elementsStringFromAssetName(assetNames: Array<string>): string {

  const timestamp = Date.now(); // Get the current timestamp in milliseconds
  const date = new Date(timestamp); // Create a Date object from the timestamp
  const formattedDate = `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}Z`;

  const elements = assetNames.map((assetName) => {
    return `Elt "${assetName}" (Pair "${formattedDate}" (Pair "${formattedDate}" (Pair 0 (Pair 0 (Pair 0 (Pair 0 0))))))`
  })

  // Reduce to a single string.
  const elementsString = elements.reduce(
    (previousValue: string, currentValue: string) => {
      return previousValue + '\n' + currentValue
    },
    '',
  )

  return elementsString.trim()
}

/**
 * Make a storage parameter for an oracle.
 *
 * @param logLevel The level at which to log output.
 * @param assetNames An array of asset names to include in the oracle. The asset names must be in alphabetical order.
 * @param signerPublicKey The public key of the entity which will sign data for the oracle.
 * @returns The storage for a new oracle as a string.
 */
function makeOracleStorage(
  logLevel: LogLevel,
  assetNames: Array<string>,
  signerPublicKey: string,
): string {
  if (logLevel == LogLevel.Debug) {
    Utils.print(
      'Using assets: ' +
      assetNames.reduce((previousValue, assetName) => {
        return previousValue + assetName + ', '
      }, ''),
    )
  }
  Utils.print('')

  const elementsString = elementsStringFromAssetName(assetNames)
  const storage = `
    (Pair {${elementsString}} (Some "sppk7bkCcE4TZwnqqR7JAKJBybJ2XTCbKZu11ESTvvZQYtv3HGiiffN"))
    `
  return storage
}

/**
 * Make a storage parameter for a Normalizer contract.
 *
 * @param assetNames An array of asset names to include in the oracle. The asset names must be in alphabetical order.
 * @param numDataPoints The number of data points to normalize over.
 * @param oracleContractAddress The KT1 address of the Oracle contract.
 */
function makeNormalizerStorage(
  assetNames: Array<string>,
  numDataPoints: number,
  oracleContractAddress: string,
) {
  const assetNameParam = assetNames.reduce((previous, current) => {
    return previous + `"${current}"; `
  }, '')

  const timestamp = Date.now(); // Get the current timestamp in milliseconds
  const date = new Date(timestamp); // Create a Date object from the timestamp
  const formattedDate = `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}Z`;


  const assetValuesParam = assetNames.reduce((previous, current) => {
    return (
      previous +
      `Elt "${current}"(Pair(Pair 0 "${formattedDate}")(Pair (Pair (Pair 0 -1) (Pair { Elt 0 0 } 0))(Pair (Pair 0 -1) (Pair { Elt 0 0 } 0))));`
    )
  }, '')

  return `(Pair (Pair { ${assetNameParam}} {${assetValuesParam} }) (Pair ${numDataPoints} "${oracleContractAddress}"))`
}


function readContract(filename: string) {
  const contractFile = filename
  const contract = fs.readFileSync(contractFile).toString('latin1')
  return contract
}

const ORACLE_CONTRACT_FILE = __dirname + '/oracle.tz'
const ORACLE_STORAGE_FILE = __dirname + '/oracle_storage.tz'

const NORMALIZER_CONTRACT_FILE = __dirname + '/normalizer.tz'
const NORMALIZER_STORAGE_FILE = __dirname + '/normalizer_storage.tz'

const deploy = async () => {
  try {
    const tezos = new TezosToolkit(config.tezosConfig.nodeAddress);
    tezos.setSignerProvider(new InMemorySigner(config.tezosConfig.privateKey));

    const oracle_contract = readContract(ORACLE_CONTRACT_FILE);
    const oracle_storage = makeOracleStorage(LogLevel.Debug, ["XTZ-USD"], config.tezosConfig.publicKey);

    const deployResult: OriginationOperation = await tezos.contract.originate({
      code: oracle_contract,
      init: oracle_storage,
    })
    console.log(`New Oracle Contract Address: ${deployResult.contractAddress!} \n\n`)
    
    await Utils.sleep(10);
    const normalizer_contract = readContract(NORMALIZER_CONTRACT_FILE);
    const normalizer_storage = makeNormalizerStorage(
      ["XTZ-USD"],
      3,
      deployResult.contractAddress!,
    )
    const normalizer_deployResult: OriginationOperation = await tezos.contract.originate({
      code: normalizer_contract,
      init: normalizer_storage,
    })
    console.log(`New Normalizer Contract Address: ${ normalizer_deployResult.contractAddress! } `)

  } catch (err) {
    console.log(err);
  }
}

deploy();