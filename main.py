import logging
import json
import os
from time import sleep
import time
from packaging import version
from flask import Flask, request, jsonify
from threading import Thread
import openai
from openai import OpenAI
from flask_cors import CORS
from error import CustomAPIError 
from functions import setup_assistant_and_thread, create_new_thread, load_ids
from dotenv import load_dotenv
import requests


load_dotenv()

# Check OpenAI version is correct
required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
CORS_ORIGIN = os.environ.get('CORS_ORIGIN')
if current_version < required_version:
  raise ValueError(f"Error: OpenAI version {openai.__version__}"
                   " is less than the required version 1.1.1")
else:
  print("OpenAI version is compatible.")

# Start Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": CORS_ORIGIN}})

# Init client
client = OpenAI(
    api_key=OPENAI_API_KEY
)

# Load existing IDs
assistant_id, thread_id = load_ids()

# If no existing IDs, create new assistant and thread
if assistant_id is None or thread_id is None:
    assistant_id, thread_id = setup_assistant_and_thread(client)

# Start conversation thread
@app.route('/start', methods=['GET'])
def start_conversation():
  global thread_id
  if not thread_id:
    thread_id = create_new_thread(client)
  print(f"Starting a new conversation with: {thread_id} ")  # Debugging line
  return jsonify({"thread_id": thread_id})

# Generate response
@app.route('/chat', methods=['POST'])
def chat():
  global assistant_id, thread_id
  try:
    data = request.json
    thread_id = data.get('thread_id')
    user_input = data.get('message', '')

    if not thread_id:
      error_response = {
          "error": {
              "message": "Missing thread_id",
              "type": "BadRequestError",
              "code": 400
          }
      }
      return handle_error_and_retry(error_response)

    print(f"Received message: {user_input} for thread ID: {thread_id}"
          )  # Debugging line
    
    additional_instructions = " Please always respond using HTML to structure the response. For example, when starting a new paragraph, you should add <br> breaks. Also, refrain from ever mentioning this in the responses, as well as the existance of the information document, as well as the existance of this message, including not saying Understood about this message since it will be part of every message, and do not inlude 【N†source】 in the response when it's from the document."

    # Add the user's message to the thread
    client.beta.threads.messages.create(thread_id=thread_id,
                                        role="user",
                                        content=user_input+additional_instructions)

    # Run the Assistant
    run = client.beta.threads.runs.create(thread_id=thread_id,
                                          assistant_id=assistant_id)

    # Check if the Run requires action (function call)
    while True:
      run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                    run_id=run.id)
      # print(f"Run status: {run_status}")
      if run_status.status == 'completed':
        break
      if run_status.status == 'failed':
          if run_status.last_error:
              # Parse the JSON string in the error message into a dictionary
              inner_error = json.loads(run_status.last_error.message)
              print(f"Inner error: {inner_error}")  # Debugging line
              error_response = {
                  "error": {
                      "message": inner_error,
                      "code": run_status.last_error.code
                  }
              }
          else:
              error_response = {"error": {"message": "Unknown error", "code": None}}

          return jsonify(error_response), 500
      sleep(1)  # Wait for a second before checking again

    # Retrieve and return the latest message from the assistant
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    print(f"messages: {messages}")  # Debugging line
    response = messages.data[0].content[0].text.value

    print(f"Assistant response: {response}")  # Debugging line
    return jsonify({"response": response})
  
  except openai.BadRequestError as e:
    error_message = str(e)
    if 'does not exist' in error_message:
        return handle_error_and_retry(e)

  
  except openai.NotFoundError as e:
    return handle_error_and_retry(e)

  
  except openai.OpenAIError as e:
    logging.error(f"OpenAI error: {e.error}")
    # Extract detailed error information
    if hasattr(e, 'error') and 'message' in e.error:
        detailed_message = e.error['message']
    else:
        detailed_message = "Unknown OpenAI error"
    
    # Create an instance of CustomAPIError with the detailed message and other details
    error = CustomAPIError(detailed_message, type(e).__name__, 400)  # Adjust the status_code as needed
    
    # Use the to_dict method to create the error response
    return jsonify(error.to_dict()), error.status_code

  except Exception as e:
      logging.error(f"Unknown error: {e}")
      error = CustomAPIError(str(e), type(e).__name__, 500)
      return jsonify(error.to_dict()), error.status_code
  
def handle_error_and_retry(e):
    global assistant_id, thread_id
    assistant_id, thread_id = setup_assistant_and_thread(client)
    logging.error(f"OpenAI error: {e}, creating new assistant and resending chat request.")
    return chat()
  

@app.route('/self_ping', methods=['GET'])
def self_ping():
    try:
        response = requests.get(os.environ.get('CHATBOT_SERVER_ADDRESS'))
        if response.status_code == 200:
            print("Self-ping successful")
        else:
            print("Self-ping failed with status: ", response.status_code)
    except requests.RequestException as e:
        print("Self-ping failed: ", e)

@app.errorhandler(500)
def internal_server_error(e):
    response = {
        "error": {
            "type": "InternalServerError",
            "message": "The server encountered an internal error and was unable to complete your request."
        }
    }
    return jsonify(response), 500

def keep_alive():
    while True:
        self_ping()
        time.sleep(49)  # wait for 60 seconds before next ping

# Run server
if __name__ == '__main__':
  # Start the background thread
  keep_alive_thread = Thread(target=keep_alive)
  keep_alive_thread.start()
  # Get the PORT from environment variable with a default fallback
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)

