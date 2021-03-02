import slack
import os
import requests
import re
import urllib.parse
import spacy
from pathlib import Path
from dotenv import load_dotenv
from slackeventsapi import SlackEventAdapter
from flask import Flask, request, Response
from textblob import TextBlob
from spellchecker import SpellChecker

# Load the Token from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
OWM_API = os.getenv('OWM_API')

# Configure your flask application
app = Flask(__name__)

# Using WebClient in slack, there are other clients built-in as well !!
client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

# Configure SlackEventAdapter to handle events
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

# Get Bot ID
BOT_ID = client.api_call("auth.test")['user_id']

OWM_API = os.getenv("OWM_API")
spell = SpellChecker()
nlp = spacy.load("en_core_web_sm")


def cityname(sentence):
    long = spell.split_words(sentence)
    count = 0
    city = []
    for word in long:
        can = spell.candidates(word)
        change = None
        # print(can)
        if len(can) > 1:
            for w in can:
                doc = nlp(w.title())
                for ent in doc.ents:
                    if ent.label_ == "GPE":
                        change = w.title()
                        city.append(change)
        doc = nlp(word.title())
        for ent in doc.ents:
            if ent.label_ == 'GPE':
                city.append(word.title())
        if change != None:
            long[count] = change
        count += 1

    long = [spell.correction(word) for word in long]
    return long, city

def setup():
    driver = webdriver.Chrome()
    driver.get("http://maps.google.com")
    return driver


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')

    value = cityname(text)
    city_list = []
    
    if len(value[1]) > 0:
        city_list.append(value[1][0])

    is_weather = 0

    if len(city_list) != 0:
        corrected_OWN_URL = f"https://api.openweathermap.org/data/2.5/weather?q={city_list[0]}&units=metric&appid={OWM_API}"
        corrected_response = requests.get(corrected_OWN_URL)
        if corrected_response.status_code == 200:
            is_weather = 1
            curr_weather = corrected_response.json()['weather']
            curr_temp = corrected_response.json()['main']
            weather_response = f"The current temperature in {city_list[0]} is {curr_temp['temp']} C, {curr_weather[0]['main']}, {curr_weather[0]['description']}."
            city_list = []

    if BOT_ID != user_id:
        if is_weather == 1:
            is_weather = 0
            client.chat_postMessage(channel=channel_id, text=weather_response)
        else:
            client.chat_postMessage(channel=channel_id, text=text)


if __name__ == "__main__":
    app.run(debug=True)
