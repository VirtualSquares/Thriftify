from flask import Flask, render_template, request, redirect, session, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from icrawler.builtin import GoogleImageCrawler
import base64
import os
from dotenv import load_dotenv
import google.generativeai as genai
from bson import json_util, ObjectId
from datetime import datetime, timedelta

app = Flask(__name__)

appPath = os.path.join(os.path.dirname(__file__), ".")
dotenvpath = os.path.join(appPath, ".env")
load_dotenv(dotenvpath)

app.secret_key = os.environ.get("APPSECRETKEY")
client = MongoClient(os.environ.get("DBKEY"))
db = client.Thriftify

genai.configure(api_key = os.environ.get("APIKEY"))

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 8192,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
]

model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

convo = model.start_chat(history=[])

def add_spaces(model_name):
    words = []
    current_word = ""
    for char in model_name:
        if char.isupper() and current_word:
            words.append(current_word)
            current_word = char
        else:
            current_word += char
    words.append(current_word)
    return " ".join(words)

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/forms", methods=["GET", "POST"])
def forms():
    if request.method == "GET":
        return render_template("forms.html")
    if request.method == "POST":
        topic = request.form["topic"]
        budget = request.form["budget"]

        # Request product names and descriptions
        convo.send_message(
            "Find 6 different models of " + topic + " in the range of " + budget +
            ". Don't give me personalized information or ask for more context, I want ONLY 6 precise model names that I can search up, and NOTHING else in the response. Include short descriptions for each product. Format it as follows: " +
            "Model1: Description1; Model2: Description2; Model3: Description3; Model4: Description4; Model5: Description5; Model6: Description6. (But don't make the actual model names model1, model2, etc, make it the actual model)"
        )

        response = convo.last.text.split("; ")

        products = []
        for item in response:
            parts = item.split(": ", 1)
            if len(parts) == 2:
                model_name, description = parts
                products.append({
                    "name": add_spaces(model_name.strip()),
                    "description": description.strip()
                })
            else:
                print(f"Unexpected response format: {item}")
                continue

        # Download images for each product
        for product in products:
            model_name = product["name"].replace(' ', '')
            google_crawler = GoogleImageCrawler(storage={'root_dir': 'static/crawl_images/' + model_name})
            google_crawler.crawl(keyword=model_name, max_num=1)


        print(products)

        return render_template("products.html", products=products)



@app.route("/products", methods=["GET", "POST"])
def products():
    return render_template("products.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)
        db.credentials.insert_one({"Username": username, "Password": hashed_password})
        return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = db.credentials.find_one({"Username": username})
        if user:
            hashed_password = user["Password"]
            if check_password_hash(hashed_password, password):
                session["username"] = username
                return redirect("/dashboard")
            else:
                return redirect("/login")

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if request.method == "GET":
        budget_data = db.budget.find({"username": session["username"]}).sort("start_date", -1).limit(1)

        budgetValues = list(budget_data)
        print(budgetValues)
        if len(budgetValues) > 0:
            start_date = budgetValues[0]["start_date"]
            duration = budgetValues[0]["duration"]

            end_date = start_date + timedelta(days = int(duration))
            log_data = db.log.find({"username": session["username"], "date": {"$gte": start_date, "$lte": end_date}}).sort("date", 1)
            print(list(log_data))
            logs = list(map(data_to_json, log_data))
            print("HI")
        print("hi")
        print(budgetValues)
        budgets = list(map(data_to_json, (budgetValues)))
        print(budgets)

        return render_template("dashboard.html", budgets=budgets)

@app.route("/dashboardData")
def dashboardData():
    budget_id = request.args.get("budget_id")
    print(budget_id)
    if budget_id:
        data = db.budget.find_one({"_id": ObjectId(budget_id)})

    else:
        data = list(db.budget.find({"username": session["username"]}).sort("start_date", -1).limit(1))[0]

    start_date = data["start_date"]
    duration = data["duration"]

    end_date = start_date + timedelta(days = int(duration))
    log_data = db.log.find({"username": session["username"], "date": {"$gte": start_date, "$lte": end_date}}).sort("date", 1)

    spending_logs = []

    for n in log_data:
        each_spent = {}
        day = (n["date"] -  start_date).days
        amount = n["spent"]
        purpose = n["purpose"]

        each_spent["day"] = day
        each_spent["amount"] = amount
        each_spent["purpose"] = purpose

        spending_logs.append(each_spent)

    budgets = list(map(data_to_json, list(db.budget.find({"username": session["username"]}))))
    values = {"budget": {"duration": data["duration"], "budget": data["budget"]}, "spending": spending_logs, "allBudgets": budgets}

    return jsonify(values)

def data_to_json(document):
    data = document
    print(1, 2, 3)
    print(data)
    if "_id" in data:
        data["_id"] = str(data["_id"])

    print("hello")
    json_data = json_util.loads(json_util.dumps(data))
    print(json_data)
    print(data)
    return json_data

@app.route("/createBudget", methods = ["POST"])
def createBudget():

    data = request.get_json()
    duration = data.get("duration")
    budget = data.get("budget")
    startDate = data.get("startDate")

    if duration is not None and budget is not None:
        startDate = datetime.strptime(startDate, "%Y-%m-%d")
        db.budget.insert_one({"start_date": startDate, "duration": duration, "budget": budget, "username": session["username"]})
        return jsonify({"message": "Budget Created Succesfully!"}), 200
    else:
        return jsonify({"error": "Invalid Data."}), 400

@app.route("/spendingBudget", methods = ["POST"])
def spendingLog():

    data = request.get_json()
    date = data.get("date")
    spent = data.get("spent")
    purpose = data.get("purpose")

    user = db.credentials.find_one({"Username": session["username"]})

    if user:
        if date is not None and spent is not None and purpose is not None:
            date = datetime.strptime(date, "%Y-%m-%d")
            print(date)
            db.log.insert_one({"date": date, "spent": spent, "purpose": purpose, "username": session["username"]})
            return jsonify({"message": "Spending information inputted succesfully!"}), 200
        else:
            return jsonify({"error": "Invalid Data."}), 400
    else:
        return jsonify({"error": "User Not Logged In."}), 400

@app.route("/stats")
def stats():
    budget_data = list(db.budget.find({"username": session["username"]}).sort("start_date", -1).limit(1))
    if not budget_data:
        return render_template("stats.html", summary="No budget data available.", spending_data=[])

    start_date = budget_data[0]["start_date"]
    duration = budget_data[0]["duration"]
    end_date = start_date + timedelta(days=int(duration))

    log_data = list(db.log.find({"username": session["username"], "date": {"$gte": start_date, "$lte": end_date}}))

    spending_summary = {}
    spending_details = []
    for entry in log_data:
        purpose = entry["purpose"]
        spent = entry["spent"]

        spent = int(spent) if isinstance(spent, (int, float, str)) and str(spent).isdigit() else 0

        spending_summary[purpose] = spending_summary.get(purpose, 0) + spent

    spending_details = [{"purpose": purpose, "spent": amount} for purpose, amount in spending_summary.items()]

    spending_summary_text = " ".join([f"{purpose}: {amount}" for purpose, amount in spending_summary.items()])

    convo.send_message(f"Given the following spending details: {spending_summary_text}, what should I cut spending on? I don't want a personalized response saying it's based on my priorities. I simply want a straight answer on if I wanted to save money, ideally what could I cut on?")

    response = convo.last.text.strip()

    return render_template("stats.html", summary=response, spending_data=spending_details)






if __name__ == '__main__':
    app.run(debug=True)



