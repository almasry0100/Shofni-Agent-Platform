04-provider-inventory


A6api Developer Docs

Connect to A6api model gateway in 30 seconds
Remember only one entry point: https://api.a6api.com . After creating the token, replace the baseURL and API Key of your existing SDK with A6api to access available models in the model marketplace.

Last updated: 2026-09-13
Compatible versions: A6api OpenAI / Claude / Gemini compatible gateway
Unified Entry Base URL
https://api.a6api.com
For the OpenAI SDK, simply enter this address; the old syntax https://api.a6api.com/v1 can still be used.

Copy Base URL

Create token

View the model market
01
Log in and create a token
Go to the token page in the console, create and copy an API Key in the form of sk-xxxxxxxxxxxxxxxxxxxxxxxx .

02
Select Model
Select models from the model marketplace by brand, price, and success rate, and fill in the displayed model name modelin the field.

03
Replace SDK configuration
Keep the original SDK calling method, only replace apiKeyand . baseURL

If it doesn't work, check these 5 steps first.
Is this the Base URL https://api.a6api.com? New projects only need to fill in the unified entry point; if the existing project is still using the old entry point , it can continue to be compatible. https://api.a6api.com/v1 https://a6api.com
Is the model name based on the current list in the model marketplace? The document gpt-5.4-mini only provides examples; if the call fails, please copy the currently available model name from the model marketplace .
Does the request header match the protocol? Use the OpenAI compatible protocol ; use the corresponding Claude/Gemini native protocol . Authorization: Bearer <api_key>x-api-key
Is your wallet balance or available amount sufficient? Insufficient balance will usually return a 402 error. Please check the availability of your wallet and tokens in the console first.
Did you receive the error message request_id? Please include it when contacting customer service or submitting a support ticket request_idso we can quickly locate the error in the usage log.
Quick Start
First, make the first request work.

Copy the current example
Node.js
Python
cURL
import OpenAI from "openai"; 

const client = new OpenAI({ 
  apiKey: process.env.A6API_KEY, // sk-xxxxxxxxxxxxxxxxxxxxxxxx 
  baseURL: "https://api.a6api.com" 
}); 

const result = await client.chat.completions.create({ 
  model: "gpt-5.4-mini", 
  messages: [ 
    { role: "system", content: "You are a concise and reliable assistant." }, 
    { role: "user", content: "Explain what an API gateway is in one sentence." } 
  ] 
}); 

console.log(result.choices[0].message.content);
Protocols
All three protocols share the same A6api token
recommend
OpenAI compatible
Most OpenAI SDKs only require changing the baseURL to A6api for a unified entry point. This is suitable for Chat, Responses, Images, and Embeddings.

Authorization: Bearer sk-xxxxxxxxxxxxxxxxxxxxxxxx
Anthropic
Claude Original
Use this when you need to preserve the body of Claude messages in the request. The path is /messages, with anthropic-version included.

x-api-key: sk-xxxxxxxxxxxxxxxxxxxxxxxx + anthropic-version
Google
Gemini native
Use this when you need direct compatibility with the Gemini SDK or the native contents format. The model name should be written in the URL path.

x-goog-api-key: sk-xxxxxxxxxxxxxxxxxxxxxxxx
Claude Original
Model names are subject to market availability.

copy
`curl https://api.a6api.com/messages 
  -H "Content-Type: application/json" 
  -H "x-api-key: sk-xxxxxxxxxxxxxxxxxxxxxxxx" 
  -H "anthropic-version: 2023-06-01" 
  -d '{ 
    "model": "claude-sonnet-4-5", 
    "max_tokens": 1024, 
    "messages": [ 
      {"role": "user", "content": "Please organize this requirement into 3 key points."} 
    ] 
  }'`
Gemini native
Model names are subject to market availability.

copy
curl "https://api.a6api.com/v1beta/models/gemini-2.5-pro:generateContent" \ 
  -H "Content-Type: application/json" \ 
  -H "x-goog-api-key: sk-xxxxxxxxxxxxxxxxxxxxxxxx" \ 
  -d '{ 
    "contents": [ 
      {"role": "user", "parts": [{"text": "Give me one practical API testing tip."}]} 
    ] 
  }'
Model Market
Copy real, usable model names from the model market.

Open up the model market
Brand and Model
The model market organizes available models by brand and model; clicking on a brand allows you to quickly view popular models under that brand.

Price and success rate
The list displays the input price, output price, real-time success rate, latency, and most recent success time, making it easy to compare different vendors.

Fixed Merchants / Smart Selection
If you need to specify a supplier, you can fix the vendor; if you want more stable availability, it is recommended to let the intelligent selection automatically bypass abnormal channels.

How should I fill in the model name?
When making a formal call, fill in the field with the model string displayed in the model marketplace as is . To query the currently available models using the API, you can call: model

List available models
/models

copy
curl https://api.a6api.com/models \ 
  -H "Authorization: Bearer sk-xxxxxxxxxxxxxxxxxxxxxxxx"
Endpoints
List of commonly used endpoints
The following paths https://api.a6api.comare prefixed with "Unified Entry Point"; older /v1prefixes are still compatible. Accessing the website via a browser will open the model marketplace; API clients that request with a token will receive a list of models. /models

Text, Dialogue, and Agent
POST
/chat/completions
OpenAI-compatible dialogue, chat, streaming, and tool calls should prioritize using this method.
POST
/responses
Responses API is suitable for Agent, multi-step output, and tool calls.
POST
/messages
The Claude native protocol requires an x-api-key and anthropic-version.
POST
/v1beta/models/{model}:generateContent
Gemini native protocol, preserving Google Contents format.
POST
/completions
The old version of Completes only required a small number of models.
Multimodal and Retrieval
POST
/images/generations
Image generation
POST
/images/edits
Image editing / Local redraw
POST
/embeddings
Text vector
POST
/rerank
Reordering
POST
/audio/transcriptions
Speech-to-text
POST
/audio/speech
Text to speech
Model and Real-time
GET
/models
The API request lists the models currently available for the token; opening it in a browser will take you to the model marketplace.
GET
/models/{model}
Query details of a single model
WS
/realtime
Realtime WebSocket
POST
/mj/submit/imagine
Midjourney Imagine Task
GET
/mj/task/{id}/fetch
Midjourney Mission Search
POST
/suno/submit/{action}
Suno Music Task Submission
Responses
Agent/Tool Invocation

copy
`curl https://api.a6api.com/responses 
  -H "Content-Type: application/json" 
  -H "Authorization: Bearer sk-xxxxxxxxxxxxxxxxxxxxxxxx" 
  -d '{ 
    "model": "gpt-5.4-mini", 
    "input": "Write an internal communication email about the SaaS pricing redesign." 
  }'`
Embeddings
Text vector

copy
`curl https://api.a6api.com/embeddings 
  -H "Content-Type: application/json" 
  -H "Authorization: Bearer sk-xxxxxxxxxxxxxxxxxxxxxxxx" 
  -d '{ 
    "model": "text-embedding-3-large", 
    "input": "A6api is a unified large model API gateway." 
  }'`
Images
Image generation

copy
`curl https://api.a6api.com/images/generations 
  -H "Content-Type: application/json" 
  -H "Authorization: Bearer sk-xxxxxxxxxxxxxxxxxxxxxxxx" 
  -d '{ 
    "model": "gpt-image-1", 
    "prompt": "Minimalist tech-style SaaS backend dashboard rendering", 
    "size": "1024x1024" 
  }'`
Troubleshooting
User and Merchant Error Code Inquiry
This page only lists user issues and merchant issues. The purpose of troubleshooting is to error.code pinpoint the specific cause. "User issues" indicate that adjustments to requests or account settings are needed, while "merchant issues" indicate anomalies with the model provider or channel. Internal platform issues are not displayed in this list. Please provide this information when contacting support . request_id

Unified error body
Including request_id

copy
{ 
  "error": { 
    "message": "model not found or not available for this token", 
    "type": "invalid_request_error", 
    "param": "model", 
    "code": "model_not_found" 
  }, 
  "request_id": "req_xxxxxxxxxxxx" 
}
Enter the error code, problem type, or fault location.
HTTP Status

all
Problem Type

all
Subsystem

all
Retry strategy

all

65 results found
65 user and merchant error codes have been registered.
HTTP
429
model_request_rate_limit
You can try again
User Issues

Fault location
admission/ model_success_rate_limit/limit_reached
Problem Description
The model has reached its current limit on the frequency of successful requests.
Solution
Reduce request frequency and back off retries exponentially; adjust the model's successful request limit when a higher limit is needed.
HTTP
429
model_total_request_rate_limit
You can try again
User Issues

Fault location
admission/ model_total_rate_limit/limit_reached
Problem Description
The model's total request frequency has reached the current limit.
Solution
Reduce the overall request frequency, including failed requests, retry by Retry-After, and check for retry storms on the client side.
HTTP
429
payment_rate_limited
You can try again
User Issues

Fault location
admission/ payment_rate_limit/limit_reached
Problem Description
The frequency of creating payment orders has reached the current limit.
Solution
Please place your order again after the specified time indicated on the page, or after the specified time. If you have already placed an order, please check your recharge history to avoid placing a duplicate order.
HTTP
403
insufficient_privilege
Don't retry directly.
User Issues

Fault location
auth/ role_authorization/insufficient_privilege
Problem Description
The current account/role does not have permission to perform this operation.
Solution
Please use an account with the appropriate permissions, or contact the account administrator to grant the required permissions.
HTTP
401
invalid_api_key
Don't retry directly.
User Issues

Fault location
auth/ api_key_validation/invalid_key
Problem Description
API Key is missing, incorrectly formatted, revoked, or unavailable.
Solution
Copy the valid token from the console to confirm that the authentication header and protocol match and that the token has not been disabled or deleted.
HTTP
401
token_expired
Don't retry directly.
User Issues

Fault location
auth/ token_validation/expired
Problem Description
The login token or access token has expired.
Solution
Log in again or refresh the token before making the request; the server-side call should be replaced with an unexpired API Key.
HTTP
400
oauth_state_invalid
Don't retry directly.
User Issues

Fault location
oauth/ callback_state/invalid
Problem Description
The state in the OAuth callback is invalid, missing, or does not match the current session.
Solution
Re-initiate OAuth authorization from the login page to avoid reusing the old callback URL; at the same time, confirm that the cookie is not blocked by the browser.
HTTP
403
csrf_origin_missing
Don't retry directly.
User Issues

Fault location
security/ csrf_origin/missing
Problem Description
Requests requiring CSRF verification do not have an Origin or Referer.
Solution
Initiate the request from a normal web page session and retain the browser's Origin/Referer headers; do not directly replay write requests that lack source headers.
HTTP
403
csrf_origin_invalid
Don't retry directly.
User Issues

Fault location
security/ csrf_origin/invalid
Problem Description
The request originates from sites outside the allowed range.
Solution
Confirm that the request originates from the current site domain and uses the correct protocol; the reverse proxy must correctly transmit Host, Origin, and HTTPS information.
HTTP
403
not_a_supplier
Don't retry directly.
User Issues

Fault location
supplier/ authorization/role_missing
Problem Description
The current account is not a supplier and cannot access supplier functions.
Solution
Please use an account that has already completed the merchant onboarding review, or submit a merchant application first.
HTTP
422
channel_not_marketplace
Don't retry directly.
User Issues

Fault location
marketplace/ channel_validation/not_marketplace
Problem Description
The designated channel is not a model market channel and cannot perform this market operation.
Solution
Choose a new channel that is already listed on the model marketplace, or complete the channel listing configuration first and then submit.
HTTP
403
request_blocked
Don't retry directly.
User Issues

Fault location
security/ request_policy/blocked
Problem Description
The request was blocked by the platform's security policy.
Solution
Check if the request content, source, and usage comply with the rules; contact support with the request_id and avoid frequent retrying.

Show all
65
entries
Billing
Prices depend on the market, charges are based on logs.
Log recording
Each request records the input token, output token, cache read/write, model multiplier, group multiplier, and actual charge.

Market price
The model market displays publicly available prices, making it easy to compare vendors; the final charge will be calculated based on multipliers, per-use prices, or tiered pricing.

Flow cytometry usage
Streaming responses will return as much usage information as possible to help the client verify the actual cost of the call.

Flow response
Python SDK

copy
from openai import OpenAI 

client = OpenAI(api_key="sk-xxxxxxxxxxxxxxxxxxxxxxxx", base_url="https://api.a6api.com") 

stream = client.chat.completions.create( 
    model="gpt-5.4-mini", 
    messages=[{"role": "user", "content": "Tell a short joke of 50 words."}], 
    stream=True, 
) 

for chunk in stream: 
    delta = chunk.choices[0].delta.content or "" 
    print(delta, end="", flush=True)


    ------------ ------------------------------------------------------------------------------------

relayrouter
Developer guide

API documentation
Everything you need to send your first request and ship with RelayRouter.

Manage API keys
On this page
Quickstart
Authentication
Request format
JavaScript SDK
Agent harnesses
Streaming
Limits
Errors
Getting started

Your first request
RelayRouter exposes an OpenAI-compatible Chat Completions API. Create a key, set the base URL, and send a message using any model in the fleet — the same request shape works for all twenty.

Base URL
Copy
https://api.relayrouter.org/v1
cURL
Copy
curl https://api.relayrouter.org/v1/chat/completions \
  -H "Authorization: Bearer $RELAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.6-terra","messages":[{"role":"user","content":"Hello"}]}'
Authentication
Send your RelayRouter API key in the Authorization header on every request. Keys are shown once when created; use a separate key for each environment and never expose one in browser code.

HTTP header
Copy
Authorization: Bearer $RELAY_API_KEY
Request format
Requests use JSON. model and messages are required; generation controls are optional.

model
string · required
An enabled model ID from the catalog.

messages
array · required
Conversation messages with a role and content.

temperature
number · optional
Sampling temperature from 0 to 2.

max_tokens
integer · optional
Maximum tokens to generate.

stream
boolean · optional
Return server-sent events when true.

JavaScript SDK
RelayRouter is compatible with the OpenAI SDK. Point the client at the RelayRouter base URL and keep the API key on the server.

Node.js
Copy
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.RELAY_API_KEY,
  baseURL: "https://api.relayrouter.org/v1",
});

const response = await client.chat.completions.create({
  model: "gpt-5.6-terra",
  messages: [{ role: "user", content: "Hello" }],
});

console.log(response.choices[0].message.content);
Agent harnesses
Use RelayRouter directly from coding agents. The gateway translates Anthropic Messages requests — including streaming, images, function calls, and tool results — onto the same routed fleet, against the same balance.

OpenAI-compatible agent
Copy
export OPENAI_BASE_URL="https://api.relayrouter.org/v1"
export OPENAI_API_KEY="$RELAY_API_KEY"
# Point any OpenAI-compatible agent at RelayRouter, e.g. model "gpt-5.6-terra".
Replace the example model with an exact ID from the Models catalog. Anthropic-style clients use /v1/messages; OpenAI-style clients use /v1/chat/completions.

Streaming responses
Set stream to true to receive server-sent events. Read each data: frame in order and stop when the stream emits [DONE]. The final usage frame records input and output tokens — that is what your balance is settled against.

Streaming request
Copy
curl -N https://api.relayrouter.org/v1/chat/completions \
  -H "Authorization: Bearer $RELAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.6-terra","messages":[{"role":"user","content":"Hello"}],"stream":true}'
Limits and billing
Two billing modes, one key. On a flat plan, requests draw from your plan's 6-hour and daily token windows at your plan's requests-per-minute — nothing metered per token; an exhausted window is a 429 with code plan_window_exhausted and a retry-after pointing at the reset. Without a plan, requests bill your prepaid credit at the provider's token price plus a fixed margin, and an empty balance is a 402 insufficient_credit. Either way, back off with jitter on any 429 and read retry-after.

429
Window or rate limit reached
402
Insufficient credit (no plan)
600/min
Per-key ceiling
24 MiB
Max request body
Errors
Errors come back in the dialect you called with — an OpenAI-format request gets {"error": {"message", "type", "code"}}, so existing SDK error handling works unchanged. Every response carries an x-request-id header; quote it in any support conversation. Codes prefixed upstream_ mean the provider rejected the request and the message is passed through verbatim.

400
Request rejected
401
Authentication rejected
402
Insufficient credit
5xx
Gateway request failed