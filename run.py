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
from flask import Flask, render_template, request, jsonify, flash
import json
import subprocess
import random
import math

app = Flask(__name__, template_folder='templates', static_folder='static')

#initialize global variables
login_data = {}
order_data = {}
orderItemCount = 0
currentOrderID= ""

# Create a new client and connect to the server
client = MongoClient('mongodb://localhost:27017/') 
db = client['pizzaShop']
collectionLogin = db['loginData']
collectionOrders = db['currentOrder']

# Set Default Site Location
@app.route("/")
def index():
    return render_template("LoginPage.html")

# Respond to POST request to login
@app.route("/home/", methods=["POST"])
def home():
    global login_data
    login_data = {}
    login_data['username'] = request.form.get("username")
    login_data['password'] = request.form.get("password")

    print("test")

    # Check if username and password match
    user = collectionLogin.find_one(login_data)
    if user:
        # if login successful, check access level
        access = user['access']

        if access == 'admin':
            return render_template("PizzaAdmin.html")
        else:
            return render_template("StoreFront.html")
    else:
        if collectionLogin.find_one({"username": login_data['username']}):
            flash('Incorrect password! Please try again.', 'error')
        else:
            flash('Username does not exist! Please try again.', 'error')
        return render_template("LoginPage.html")

# Respond to POST request to sign up   
@app.route("/signUp/", methods=["POST"])
def signUp():
    sign_up_data = {}
    sign_up_data['username'] = request.form.get("newUsername")
    sign_up_data['password'] = request.form.get("newPassword")
    sign_up_data['access'] = 'user' #default access level, admin must be manually set
    confirmPassword = request.form.get("confirmPassword")

    # Check if passwords match
    if sign_up_data['password'] != confirmPassword:
        flash('Passwords do not match! Please try again.', 'error')
    else:
        #check is username already exists, and show error if so
        if collectionLogin.find_one({"username": sign_up_data['username']}):
            flash('Username already exists! Please try again.', 'error')
        else:
            #add sign-up if no errors
            flash('Passwords match! You are now signed up.', 'success')
            collectionLogin.insert_one(sign_up_data)
    
    # Return to login page after account creation        
    return render_template("LoginPage.html")

# Transfer to builder page when selected
@app.route("/builder/")
def builder():
    return render_template("PizzaBuilder.html")

# Reset home as storefront once login achieved
@app.route("/home/")
def menu():
    return render_template("StoreFront.html")

# Transfer to tracking page after order is placed
@app.route("/tracking/", methods=["POST"])
def tracking():
    print("Order Placed")
    global order_data #access order data to merge
    user_data = {}
    user_data['first-name'] = request.form.get("first-name")
    user_data['last-name'] = request.form.get("last-name")
    user_data['email'] = request.form.get("email")
    user_data['mobile-phone'] = request.form.get("mobile-phone")
    user_data['address'] = request.form.get("address")
    user_data['card-number'] = request.form.get("card-number")
    user_data['name-on-card'] = request.form.get("name-on-card")
    user_data['expiration-date'] = request.form.get("expiration-date")
    user_data['cvv'] = request.form.get("cvv")

    #extract order ID for tracking page
    order_id = order_data['orderID']
    print(user_data)
    #combine user data with order data
    order_data = {**order_data, **user_data}
    print(order_data)

    collectionOrders.insert_one(order_data)

    return render_template("Tracking.html", order_id=order_id)

# Transfer to checkout page
@app.route("/checkout/", methods=["GET", "POST"])
def checkout():
    #post the order data to database when order confirmed
    global order_data
    
    #pull order ID for tracking page
    orderID = order_data['orderID']

    return render_template("Checkout.html", orderID=orderID)

# Pass data about the order to the backend or retrieve it
@app.route('/updateOrder/', methods=['GET','POST'])
def updateOrder():
    if request.method == 'POST':
        # Handle POST request to update order
        order = request.get_json()
        global order_data
        global orderItemCount
        orderItemCount += 1
        keyString = "Pizza " + str(orderItemCount)
        #store order_data locally and update the page, append if already has order
        if bool(order_data):
            order_data['order'][keyString]= order
            order_data['items'] = orderItemCount
            order_data['totalCost'] = order_data['totalCost'] + order['cost']
        else:
            #create an order number for this order
            orderID = 'ORD-' + str(math.floor(random.random() * 1000000))
            #set currentOrderID to this orderID
            global currentOrderID
            currentOrderID = orderID
            order_data = {"order": {keyString: order}, "username": login_data['username'], "items": orderItemCount, "orderID": orderID, "totalCost": order['cost']}
        print(order_data)
    return jsonify(order_data), 200 # This ensures Content-Type is application/json

@app.route('/getOrder/', methods=['GET'])
def getOrder():
    global currentOrderID

    # retrieve order data from database
    order_data = collectionOrders.find_one({"orderID": currentOrderID})
    
    #remove the generated _id from the database
    order_data.pop('_id')

    # Handle GET request to retrieve order
    return jsonify(order_data), 200 # This ensures Content-Type is application/json

@app.route('/admin/')
def admin():
    return render_template("PizzaAdmin.html")
@app.route('/admin-design')
def admin_design():
    return render_template("DesignPizza.html")
@app.route('/admin-add-remove')
def admin_pizzaDesign():
    return render_template("AddandRemove.html")
@app.route('/admin-pizza-remover')
def admin_pizzaRemove():
    return render_template("RemovePizza.html")

# Handle logout
@app.route('/logout/')
def logout():
    #clear login data and order data to reset app
    global login_data
    global order_data
    global orderItemCount
    global currentOrderID
    login_data = {}
    order_data = {}
    orderItemCount = 0
    currentOrderID = ""
    return render_template("LoginPage.html")

# Run the app
if __name__ == "__main__":
    app.secret_key='test secret key'
    app.config['SESSION_TYPE'] = 'filesystem'

    app.run()