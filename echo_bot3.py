import slack
import os
import requests
import re
import urllib.parse
import spacy
from pathlib import Path
from dotenv import load_dotenv
from slackeventsapi import SlackEventAdapter
from flask import Flask,request,Response
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
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'],'/slack/events',app)

# Get Bot ID
BOT_ID = client.api_call("auth.test")['user_id']

OWM_API = os.getenv("OWM_API")
spell = SpellChecker()
nlp = spacy.load("en_core_web_sm")


def cityname(sentence):
    long = spell.split_words(sentence)
    count = 0
    for word in long:
        can = spell.candidates(word)
        change = None
        # print(can)
        if len(can) > 1:
            for w in can:
                doc = nlp(w.title())
                for ent in doc.ents:
                    print(ent.text, ent.label_)
                    if ent.label_ == "GPE":
                        change = w.title()
        if change != None:
            long[count] = change
        count += 1
    print(long)
    long = [spell.correction(word) for word in long]
    print(long)
    return long

def setup():
    driver = webdriver.Chrome()
    driver.get("http://maps.google.com")
    return driver

@slack_event_adapter.on('message')
def message(payload):
    
    event = payload.get('event',{})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    
    str=re.findall("[a-zA-Z,.]+",text)
    updated_text=(" ".join(str))
    misspelled = spell.unknown(str)
    city_list = []

    is_weather = 0

    if len(misspelled) > 0:
        new_doc = TextBlob(updated_text)
        tb = new_doc.correct()
        s = ''
        result = (s.join(tb))
        print(result)
        doc = nlp(result)
        result_dict = {}
        for ent in doc.ents:
            result_dict[ent.text] = ent.label_
        city_list = [k for k,v in result_dict.items() if v == 'GPE']
        print('result ', result, 'city list', city_list)
    
    if len(city_list) != 0:
        corrected_OWN_URL = f"https://api.openweathermap.org/data/2.5/weather?q={city_list[0]}&units=metric&appid={OWM_API}"
        corrected_response = requests.get(corrected_OWN_URL)
        if corrected_response.status_code == 200:
            is_weather = 1
            curr_weather = corrected_response.json()['weather']
            curr_temp = corrected_response.json()['main']
            weather_response = f"The current temperature in {city_list[0]} is {curr_temp['temp']} C, {curr_weather[0]['main']}, {curr_weather[0]['description']}."
            result=""
            result_dict.clear()
            city_list = []
    else:
        OWN_URL = f"https://api.openweathermap.org/data/2.5/weather?q={text}&units=metric&appid={OWM_API}"
        normal_response = requests.get(OWN_URL)
        if normal_response.status_code == 200:
            is_weather = 1
            curr_weather = normal_response.json()['weather']
            curr_temp = normal_response.json()['main']
            weather_response = f"The current temperature in {text} is {curr_temp['temp']} C, {curr_weather[0]['main']}, {curr_weather[0]['description']}."
    
    if BOT_ID != user_id:
        if is_weather == 1:
            is_weather = 0
            client.chat_postMessage(channel=channel_id, text=weather_response)
            return 0
            
        else:
            client.chat_postMessage(channel=channel_id, text=text)
            return 0

if __name__ == "__main__":
    app.run(debug=True)
