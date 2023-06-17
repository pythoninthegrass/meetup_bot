// Postman Pre-Request Script

// source .env file one directory up
const env = require('dotenv').config({path: `${__dirname}/../.env`});

// read env file
const URL = env.parsed.URL;
const DB_USER = env.parsed.DB_USER;
const DB_PASS = env.parsed.DB_PASS;

// set the environment variables (postman)
// const URL = pm.environment.get("URL");
// const DB_USER = pm.environment.get("DB_USER");
// const DB_PASS = pm.environment.get("DB_PASS");

// TODO: replace `request` with `pm` for postman
// post to token endpoint with basic auth to get token
var request = require('request');
var options = {
  'method': 'POST',
  'url': URL + '/' + 'token',
  'headers': {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json"
  },
  form: {
    'grant_type': 'password',
    'username': DB_USER,
    'password': DB_PASS
  }
};

request(options, function (error, response) {
  if (error) throw new Error(error);
  console.log(response.body);
  var json = JSON.parse(response.body);
  var access_token = json.access_token;
  console.log(access_token);
  // pm.environment.set("accessToken", json.access_token);
});
