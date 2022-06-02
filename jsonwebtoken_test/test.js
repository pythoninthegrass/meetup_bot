const jwt = require('jsonwebtoken');
const fs = require('fs');
const privateKey = fs.readFileSync('../jwt_priv.pem');

// source .env file one directory up
const envFile = require('dotenv').config({path: '../.env'});

CLIENT_ID = process.env.CLIENT_ID;
CLIENT_SECRET = process.env.CLIENT_SECRET;
SIGNING_KEY_ID = process.env.SIGNING_KEY_ID;

//   {
//     algorithm: 'RS256',
//     issuer: '{YOUR_CONSUMER_KEY}',
//     subject: '{AUTHORIZED_MEMBER_ID}',
//     audience: 'api.meetup.com',
//     keyid: '{SIGNING_KEY_ID}',
//     expiresIn: 120
//   }

jwt.sign(
  {},
  privateKey,
  {
    algorithm: 'RS256',
    issuer: CLIENT_SECRET,
    subject: CLIENT_ID,
    audience: 'api.meetup.com',
    keyid: SIGNING_KEY_ID,
    expiresIn: 120
  }
);
