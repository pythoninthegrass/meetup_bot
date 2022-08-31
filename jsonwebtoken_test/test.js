const jwt = require('jsonwebtoken');
const fs = require('fs');
const privateKey = fs.readFileSync('../jwt_priv.pem');

// source .env file one directory up
const envFile = require('dotenv').config({path: '../.env'});

const SELF_ID = process.env.SELF_ID;
const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const SIGNING_KEY_ID = process.env.SIGNING_KEY_ID;

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
