import json
import os
import requests
from datetime import datetime
from threading import Event
from dotenv import load_dotenv

from slack_sdk.web import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.socket_mode.request import SocketModeRequest

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

client = SocketModeClient(
    app_token=SLACK_APP_TOKEN, web_client=WebClient(token=SLACK_BOT_TOKEN)
)


def on_message(client, channel, message):
    if not message["event"]["text"].startswith("coinone"):
        return

    input_message = message["event"]["text"].split()
    if len(input_message) < 2:
        response_text = "'coinone <코인이름>'의 형태로 코인을 입력해주세요"
        client.web_client.chat_postMessage(channel=channel, text=response_text)

    currency = input_message[1]

    coin_url = "https://api.coinone.co.kr/public/v2/ticker_new/KRW/{0}".format(currency)
    headers = {"accept": "application/json"}
    coin_response = requests.get(coin_url, headers=headers)
    if coin_response.status_code != 200:
        response_text = "API와의 통신이 원활하지 않습니다. https://coinone.co.kr/"
        client.web_client.chat_postMessage(channel=channel, text=response_text)
    else:
        text = coin_response.text
        response_json = json.loads(text)
        ticker_info = response_json["tickers"][0]
        last = ticker_info["last"]
        first = ticker_info["first"]
        high = ticker_info["high"]
        low = ticker_info["low"]
        best_asks = ticker_info["best_asks"][0]
        best_bids = ticker_info["best_bids"][0]
        quote_volume = ticker_info["quote_volume"]
        target_volume = ticker_info["target_volume"]

        timestamp = response_json["tickers"][0]["timestamp"] / 1000.0
        timestamp = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")
        response_text = "{0} 기준 {1}\n고가: {2}\n저가: {3}\n시가: {4}\n종가: {5}\n매도 최저가 오더북: 매도 가격: {6}, 매도 수량: {7}\n매수 최고가 오더북: 매수 가격: {8}, 매수 수량: {9}\n24시간 기준 종목 체결 금액 (원화): {10}\n24시간 기준 종목 체결량 (종목): {11} {12}".format(
            timestamp,
            currency,
            high,
            low,
            first,
            last,
            best_asks["price"],
            best_asks["qty"],
            best_bids["price"],
            best_bids["qty"],
            quote_volume,
            target_volume,
            currency,
        )
        client.web_client.chat_postMessage(channel=channel, text=response_text)


def process(client: SocketModeClient, req: SocketModeRequest):
    if req.type == "events_api":
        response = SocketModeResponse(envelope_id=req.envelope_id)
        client.send_socket_mode_response(response)
        if (
            req.payload["event"]["type"] == "message"
            and req.payload["event"].get("subtype") is None
        ):
            channel = req.payload["event"]["channel"]
            on_message(client, channel, req.payload)


client.socket_mode_request_listeners.append(process)
client.connect()

Event().wait()
