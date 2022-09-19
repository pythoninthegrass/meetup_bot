const jwt = require('jsonwebtoken');
const fs = require('fs');
const privateKey = fs.readFileSync(`${__dirname}/../jwt_priv.pem`, 'utf8');

// source .env file one directory up
const env = require('dotenv').config({path: `${__dirname}/../.env`});
const SELF_ID = env.parsed.SELF_ID;
const CLIENT_SECRET = env.parsed.CLIENT_SECRET;
const SIGNING_KEY_ID = env.parsed.SIGNING_KEY_ID;

const token = jwt.sign(
  {},
  privateKey,
  {
    algorithm: 'RS256',
    issuer: CLIENT_SECRET,
    subject: SELF_ID,
    audience: 'api.meetup.com',
    keyid: SIGNING_KEY_ID,
    expiresIn: 120
  }
);

console.log(token);
