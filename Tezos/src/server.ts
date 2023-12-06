
import express, { Request, Response } from 'express';
import bodyParser from 'body-parser';
import * as config from '../config.json';
import { retrieveOracleDataFromCoinbase } from './controllers';

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

    // const priceData = getPrice(tokenPair);
    res.json("100");
});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});
