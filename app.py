import requests

from flask import Flask, render_template, request, url_for, redirect, session, jsonify
import pymongo
from flask_cors import CORS
import bcrypt
import json
import torch
from transformers import AutoTokenizer, AutoModel
tokenizer = AutoTokenizer.from_pretrained("law-ai/InLegalBERT")
model = AutoModel.from_pretrained("law-ai/InLegalBERT")

torch.save(model, "./model.pt")

app = Flask(__name__)
app.secret_key = "testing"

CORS(app)

allowed_ips = ['192.168.0.1', '10.0.0.2', '10.172.53.47', '10.172.54.37']


@app.before_request
def restrict_ip():
    client_ip = request.remote_addr
    if client_ip not in allowed_ips:
        return "Unauthorized", 401  # Return unauthorized status code for denied requests

# Your API route handler


@app.route('/api/myendpoint', methods=['GET'])
def my_endpoint():
    return "Hello, API request accepted!"


uri = "mongodb+srv://shravan:ravilata@cluster0.yyer7.mongodb.net/Hackathon?retryWrites=true&w=majority"

client = pymongo.MongoClient(uri)

db = client["MumbaiHacks"]

users = db["Users"]

# lawyers = db["Lawyers"]
encodings = None
sections = None

with open('Law_encoding2.json', 'r') as file:
    encodings = json.load(file)['Encodings']

encodings = torch.tensor(encodings).squeeze(1)

with open('Sections_3.json', 'r') as file:
    sections = json.load(file)

with open('Acts_3.json', 'r') as file:
    acts = json.load(file)


@app.route("/")
def hello():
    return "Hello, world!"


@app.route("/prompt", methods=["POST"])
def getResponseForPrompt():
    # Query the data here
    responseFromModel = "Getting the data.."
    response = jsonify(responseFromModel)
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response


@app.route("/register", methods=["POST"])
def registerUser():
    message = ''
    if "email" in session:
        message = 'Already Logged-In'
        return message
    if request.method == "POST":
        # check the form details
        user = request.form.get("fullname")
        email = request.form.get("email")

        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        user_found = users.find_one({"name": user})
        email_found = users.find_one({"email": email})
        if user_found:
            message = 'There already is a user by that name'
            return message
        if email_found:
            message = 'This email already exists in database'
            return message
        if password1 != password2:
            message = 'Passwords should match!'
            return message
        else:
            hashed = bcrypt.hashpw(password2.encode('utf-8'), bcrypt.gensalt())
            user_input = {'name': user, 'email': email, 'password': hashed}
            users.insert_one(user_input)

            user_data = users.find_one({"email": email})
            new_email = user_data['email']
            message = "New User Created"
            return message


@app.route('/logged_in', methods=["GET"])
def logged_in():
    if "email" in session:
        email = session["email"]
        return email
    else:
        return None


@app.route("/login", methods=["POST", "GET"])
def login():
    message = 'not logged in'
    if "email" in session:
        message = 'logged in'
        return message

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        email_found = users.find_one({"email": email})
        if email_found:
            email_val = email_found['email']
            passwordcheck = email_found['password']

            if bcrypt.checkpw(password.encode('utf-8'), passwordcheck):
                session["email"] = email_val
                # Add other details for premium users

                message = 'logged in'
                return message
            else:
                if "email" in session:
                    message = 'logged in'
                    return message
                message = 'wrong password'
                return message
        else:
            message = 'email not found'
            return message
    return message


@app.route("/logout", methods=["POST", "GET"])
def logout():
    if "email" in session:
        session.pop("email", None)
        return True
    else:
        return False


@app.route("/lawyers", methods=['GET'])
def getLawyers():
    lawyers = []
    if "email" in session:
        user = users.find_one({"email": session["email"]})
        if user != None and user.premium:
            lawyers = db["Lawyers"]
            return lawyers

    return []

# @app.route("/chat")


@app.route("/model", methods=['POST'])
def api():
    text = request.json['text']
    print(text)
    encoded_input = tokenizer(
        text, truncation=True, padding=True, max_length=512, return_tensors="pt")
    output = model(**encoded_input)
    last_hidden_state = output.last_hidden_state
    output, _ = torch.max(last_hidden_state, dim=1)
    output = output.squeeze(1)
    # print(output.shape)
    cos_sim = torch.nn.CosineSimilarity(dim=1, eps=1e-6)
    sim = cos_sim(encodings, output)
    best_recommend = torch.argmax(sim)
    sec_info = sections[best_recommend]
    act_id = sec_info['Act ID']
    act_info = acts[act_id]
    return [act_info, sections[best_recommend]]

@app.route("/chatgpt", methods=['POST'])
def chatgpt():
    print(request.json)
    text = request.json['text']
    text_out = text['Description'][0][:100]
    print(text_out)
    data = {'prompt': text_out}
    r = requests.post(
        'http://962d-104-196-119-85.ngrok-free.app/api/endpoint', json=data)
    print(r.json())
    return r.json()

if __name__ == '__main__':
    app.run()

