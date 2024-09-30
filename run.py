# CS471 - Pizza Online Shop Project
# Authors: Andreas Lanni, Chris Meharg, Noah Ray, Matthew Tenniswood
# Date: 2024-09-30 (YYYY-MM-DD)
# Description: This file is the main entry point for the 
# PizzaShop project, connection to the database and running the Flask
# app for the web application.
# To Run (With proper python, local mongod installation)
#   open a cmd prompt, type mongod to launch the local mongoDB server
#   activate myenv\Scripts\Activate in a terminal
#   python run.py
#   navigate website through given IP http://127.0.0.1.5000

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import json
import subprocess
import random
import math
from threading import Thread
import time

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
collectionMenu = db['menu']

# Set Default Site Location
@app.route("/")
def index():
    return render_template("LoginPage.html")

# Respond to login request
@app.route("/home/", methods=["POST"])
def home():
    global login_data
    login_data = {}
    login_data['username'] = request.form.get("username")
    login_data['password'] = request.form.get("password")

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

# Respond to sign-up request
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

# Transfer to speciality pizza page when speciality pizza selected
@app.route("/specialty/", methods=["POST"])
def specialty():
    #collect pizza name from form
    pizzaName = request.form.get("pizzaName")
    print(pizzaName)

    #collect pizza from menu database
    pizza = collectionMenu.find_one({"name": pizzaName})

    #get data from pizza object
    pizzaDesc = pizza['description']
    pizzaSauceCheese = pizza['saucecheese']
    pizzaToppings = pizza['toppings']
    pizzaMeats = pizza['meats']
    pizzaCost = pizza['smallCost']

    return render_template("SpecialtyPizza.html", pizzaName=pizzaName, pizzaDesc=pizzaDesc, pizzaSauceCheese=pizzaSauceCheese, pizzaToppings=pizzaToppings, pizzaMeats=pizzaMeats, pizzaCost=pizzaCost)

# Add a new speciality pizza to the menu via admin page
@app.route("/addSpecialityPizza/", methods=["POST"])
def addSpecialty():
    newPizza = request.get_json()
    # Add the new pizza to the menu
    collectionMenu.insert_one(newPizza)
    # Return to the admin page
    return render_template("PizzaAdmin.html")

# Pull menu data from database for storefront
@app.route("/menuItems/")
def menuItems():
    menu = list(collectionMenu.find({}, {'_id': 0}))
    print(menu)
    menuList = {}

    return jsonify(menu), 200 

# Reset home as storefront once login achieved
@app.route("/home/")
def menu():
    return render_template("StoreFront.html")

# Confirm order and transfer to tracking page after order is placed
@app.route("/confirmOrder/", methods=["POST"])
def confirmOrder():
    print("Order Placed")
    global order_data #access order data
    
    #collect user data from form to merge with order data
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

    #set the order status to Order Placed
    order_data['status'] = "Order Placed"

    #post the order data to database
    collectionOrders.insert_one(order_data)

    # Start the thread to update order status
    start_order_status_thread(order_data['orderID'])

    return redirect(url_for("tracking", order_id=order_id))

# Start a background thread to update order status
def start_order_status_thread(orderID):
    thread = Thread(target=update_order_status, args=(orderID,))
    thread.daemon = True
    thread.start()

# Show tracking page for order input
@app.route("/tracking/", methods=["POST", "GET"])
def tracking(order_id=None):

    # get order_id from url
    order_id = request.args.get("order_id")
    
    # If order_id not in url get from form
    if not order_id:
        order_id = request.form.get("trackingNumber")

    # Verify that the order ID exists in the database
    order = collectionOrders.find_one({"orderID": order_id})
    if not order:
        flash('Order ID does not exist! Please try again.', 'error')
        return render_template("LoginPage.html")
    else:
        # Update the global ID for the get function
        global currentOrderID
        currentOrderID = order_id
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
    return jsonify(order_data), 200 

@app.route('/getOrder/', methods=['GET'])
def getOrder():
    global currentOrderID

    # retrieve order data from database
    order_data = collectionOrders.find_one({"orderID": currentOrderID})
    
    #remove the generated _id from the database
    order_data.pop('_id')

    # Handle GET request to retrieve order
    return jsonify(order_data), 200 

# Set route for default admin overview page
@app.route('/admin/')
def admin():
    return render_template("PizzaAdmin.html")

# Set route for admin page to add a new pizza
@app.route('/admin-design')
def admin_design():
    return render_template("DesignPizza.html")

# Set route for admin page to remove a pizza from menu
@app.route('/admin-pizza-remover')
def admin_pizzaRemove():
    return render_template("RemovePizza.html")
    
# Handle pizza removal when selected in admin page
@app.route('/remove/', methods=['POST'])
def remove():
    #remove pizza from menu
    pizzaName = request.form.get("pizzaName")
    collectionMenu.delete_one({"name": pizzaName})
    return render_template("RemovePizza.html")

# Set route for admin page to view all orders and summary data
@app.route('/admin-orders')
def admin_orders():
    return render_template("AdminOrders.html")

# Retrieve all orders from the database
@app.route('/getAllOrders/', methods=['GET'])
def getAllOrders():
    #retrieve all orders from database
    orders = list(collectionOrders.find({}, {'_id': 0}))
    return jsonify(orders), 200

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

# Function for updating the order status
def update_order_status(orderID):
    # Define the order stages for pizza
    status_progression = ["Order Placed", "Preparing", "Baking", "Out for Delivery", "Completed"]

    # Loop indefinitely in background
    while True:
        # Fetch order if not yet completed
        order = collectionOrders.find_one({"orderID": orderID, "status": {"$ne": "Completed"}})

        # If the order is not complete, update status periodically
        if order:
            current_status = order.get("status", "Order Placed")
            try:
                next_status = status_progression[status_progression.index(current_status) + 1]
            except IndexError:
                next_status = "Completed"

            # Update the order status
            collectionOrders.update_one({"_id": order["_id"]}, {"$set": {"status": next_status}})
            print(f"Order {order['orderID']} status updated to {next_status}")

            # Sleep for a certain period before checking again
            time.sleep(10)  # Sleep for 10 seconds, to simulate order progression

# Run the app
if __name__ == "__main__":
    app.secret_key='test secret key'
    app.config['SESSION_TYPE'] = 'filesystem'

    app.run()