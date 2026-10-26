import 'server-only';
import {MongoClient} from 'mongodb';
const globalMongo=globalThis as unknown as {hazardMongo?:Promise<MongoClient>};
export const mongoUri=()=>process.env.MONGODB_URI || process.env.MONGODB_URL;
export async function mongoDatabase(){
  const uri=mongoUri();
  if(!uri)throw new Error('MongoDB is not configured');
  const connection=globalMongo.hazardMongo ??= new MongoClient(uri,{
    maxPoolSize:5,serverSelectionTimeoutMS:5000,connectTimeoutMS:5000,socketTimeoutMS:10000
  }).connect().catch(error=>{globalMongo.hazardMongo=undefined;throw error;});
  return (await connection).db(process.env.MONGODB_DB_NAME || 'weather_db');
}
