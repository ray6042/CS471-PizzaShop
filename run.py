# CS471 - Pizza Online Shop Project
# Authors: Andreas Lanni, Chris Meharg, Noah Ray, Matthew Tenniswood
# Date: 2024-09-03 (YYYY-MM-DD)
# Description: This file is the main entry point for the 
# PizzaShopBackEnd project, connection to the database and running the Flask
# app for the web application.
# To Run (With proper python, local mongod installation)
#   open a cmd prompt, type mongod to launch the local mongoDB server
#   activate myenv\Scripts\Activate in a terminal
#   python run.py
#   navigate website through given IP http://127.0.0.1.5000

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask import Flask, render_template, request, jsonify
import subprocess

app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route("/")
def index():
    return render_template("LoginPage.html")
# Create a new client and connect to the server
#client = MongoClient('mongodb://localhost:27017/') 
#db = client['demo']
#collection = db['data']

@app.route("/home/", methods=["POST"])
def home():
    login_data = {}
    login_data['username'] = request.form.get("username")
    login_data['password'] = request.form.get("password")
    
    #json_data = json.dumps(login_data)

    #collection.insert_one(login_data)
    
    return render_template("StoreFront.html")
@app.route("/builder/")
def builder():
    return render_template("PizzaBuilder.html")

if __name__ == "__main__":
    app.run()