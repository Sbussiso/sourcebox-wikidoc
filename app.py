from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from dotenv import load_dotenv
import requests
import os
import logging

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTH_API_URL = os.getenv('AUTH_API_URL')  # Auth API
RAG_API_URL = os.getenv('RAG_API_URL')  # LLM API

def check_authentication():
    access_token = session.get('access_token')
    if access_token:
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{AUTH_API_URL}/user_history", headers=headers)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Authentication check failed: {response.text}")
                session.pop('access_token', None)
                flash('Session expired, please login again', 'danger')
                return False
        except requests.RequestException as e:
            logger.error(f"Error during authentication check: {e}")
            flash('Error during authentication check. Please login again.', 'danger')
            session.pop('access_token', None)
            return False
    else:
        flash('You need to login first', 'danger')
        return False

@app.before_request
def before_request():
    if request.endpoint not in ('login', 'register', 'static'):
        if not check_authentication():
            return redirect(url_for('login'))

@app.route('/')
def index():
    packs = []
    if 'access_token' in session:
        token = session.get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        try:
            response = requests.get(f"{AUTH_API_URL}/packman/list_packs", headers=headers)
            if response.status_code == 200:
                packs = response.json()
            else:
                logger.error(f"Failed to fetch packs: {response.text}")
                flash('Failed to fetch packs', 'danger')
        except requests.RequestException as e:
            logger.error(f"Error fetching packs: {e}")
            flash('Error fetching packs', 'danger')
    return render_template('index.html', packs=packs)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get("message", "").lower()
        selected_pack = request.json.get("pack_id", None)  # Default to None if not provided
        conversation_history = request.json.get("history", [])
        
        # Define the payload with the required parameters
        payload = {
            "user_message": user_message,
            "history": conversation_history
        }

        if selected_pack:  # Include pack_id only if it is provided
            payload["pack_id"] = selected_pack

        logger.info(f"Sending payload to LLM API: {payload}")

        # Fetch the access token from session
        token = session.get('access_token')
        headers = {'Authorization': f'Bearer {token}'}

        # Send the user message to the LLM API with the token in headers
        response = requests.post(f"{RAG_API_URL}/gpt-pack-response", json=payload, headers=headers)
        
        logger.info(f"Received response from LLM API: {response.status_code} {response.text}")

        if response.status_code == 200:
            response_data = response.json()
            response_message = response_data.get("message", "Sorry, I don't understand that.")
        else:
            response_message = "Error communicating with the LLM API."
            logger.error(f"Error response from LLM API: {response.status_code} {response.text}")

        return jsonify({"response": response_message})

    except Exception as e:
        logger.exception("Error in chat route")
        return jsonify({"response": "An error occurred while processing your request."}), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            payload = {
                'email': email,
                'password': password
            }
            logger.info(f"Sending login payload: {payload}")

            response = requests.post(f"{AUTH_API_URL}/login", json=payload)

            logger.info(f"Received response from AUTH API: {response.status_code} {response.text}")

            if response.status_code == 200:
                access_token = response.json().get('access_token')
                session['access_token'] = access_token
                flash('Logged in successfully!', 'success')
                return redirect(url_for('index'))
            else:
                message = response.json().get('message', 'Login failed')
                logger.error(f"Login failed: {message}")
                flash(message, 'danger')
        except requests.RequestException as e:
            logger.error(f"Error during login: {e}")
            flash('Error during login', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    return redirect("https://sourcebox-official-website-9f3f8ae82f0b.herokuapp.com/sign_up")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port) #was port 80