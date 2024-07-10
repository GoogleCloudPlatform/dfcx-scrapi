"""Sample Tool for Agent Builder."""
import logging
import requests
from google.auth import default as google_default_auth
from google.auth.transport.requests import Request as GoogleRequest
from flask import Flask, request
from firebase_admin import initialize_app
from firebase_functions import https_fn


initialize_app()
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Google Auth
creds, project = google_default_auth()
auth_req = GoogleRequest()

def get_request_params(param, default=None):
    request_json = request.get_json(silent=True)
    request_args = request.args

    return (request_json or {}).get(param, default) or request_args.get(
        param, default)

@app.route("/get_weather_grid", methods=["GET", "POST"])
def get_weather_grid():
    lat = get_request_params("latitude")
    long = get_request_params("longitude")

    url = f"https://api.weather.gov/points/{lat},{long}"
    response = requests.get(url)
    logging.info(f"FIRST RESPONSE: {response}")
    if response.status_code == 200:
        data = response.json()
        logging.info(f"FIRST RESPONSE DATA: {data}")

        response = requests.get(data["properties"]["forecast"])
        logging.info(f"SECOND RESPONSE: {response}")
        if response.status_code == 200:
            data = response.json()
            logging.info(f"SECOND RESPONSE DATA: {data}")

            # just take the weather from the current period
            period = data["properties"]["periods"][0]
            return {
                "temperature": period["temperature"],
                "temperatureUnit": period["temperatureUnit"]
                }

    return {}

@https_fn.on_request()
def main(req: https_fn.Request) -> https_fn.Response:
    creds.refresh(auth_req)
    with app.request_context(req.environ):
        return app.full_dispatch_request()
