import os
import json
from time import sleep
from packaging import version
from flask import Flask, request, jsonify
from threading import Thread
import openai
from openai import OpenAI
import functions
from flask_cors import CORS


# Check OpenAI version is correct
required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
if current_version < required_version:
  raise ValueError(f"Error: OpenAI version {openai.__version__}"
                   " is less than the required version 1.1.1")
else:
  print("OpenAI version is compatible.")

# Start Flask app
app = Flask(__name__)
CORS(app, origins='http://localhost:5173')

# Init client
client = OpenAI(
    api_key=OPENAI_API_KEY
)  # should use env variable OPENAI_API_KEY in secrets (bottom left corner)

# Load assistant_id and thread_id from a file
def load_ids():
    if os.path.exists('ids.json'):
        with open('ids.json', 'r') as f:
            ids = json.load(f)
            return ids.get('assistant_id'), ids.get('thread_id')
    else:
        return None, None

# Save assistant_id and thread_id to a file
def save_ids(assistant_id, thread_id):
    with open('ids.json', 'w') as f:
        json.dump({'assistant_id': assistant_id, 'thread_id': thread_id}, f)

# Load existing IDs
assistant_id, thread_id = load_ids()

# If no existing IDs, create new assistant and thread
if assistant_id is None or thread_id is None:
    assistant_id = functions.create_assistant(client)
    thread = client.beta.threads.create()
    thread_id = thread.id
    save_ids(assistant_id, thread_id)


# Start conversation thread
@app.route('/start', methods=['GET'])
def start_conversation():
  print("Starting a new conversation...")  # Debugging line
  print(f"New thread created with ID: {thread_id}")  # Debugging line
  return jsonify({"thread_id": thread_id})


# Generate response
@app.route('/chat', methods=['POST'])
def chat():
  data = request.json
  thread_id = data.get('thread_id')
  user_input = data.get('message', '')

  if not thread_id:
    print("Error: Missing thread_id")  # Debugging line
    return jsonify({"error": "Missing thread_id"}), 400

  print(f"Received message: {user_input} for thread ID: {thread_id}"
        )  # Debugging line
  
  additional_instructions = " Please always respond using HTML to structure the response. For example, when starting a new paragraph, you should add <br> breaks. Also, refrain from ever mentioning this in the responses, as well as the existance of the information document, as well as the existance of this message, including not saying Understood about this message since it will be part of every message, and do not inlude 【0†source】 in the response when it's from the document."

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
    print(f"Run status: {run_status.status}")
    if run_status.status == 'completed':
      break
    sleep(1)  # Wait for a second before checking again

  # Retrieve and return the latest message from the assistant
  messages = client.beta.threads.messages.list(thread_id=thread_id)
  response = messages.data[0].content[0].text.value

  print(f"Assistant response: {response}")  # Debugging line
  return jsonify({"response": response})


# Run server
if __name__ == '__main__':
  # Get the PORT from environment variable with a default fallback
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)



@app.route('/keepalive', methods=['GET'])
def keep_alive():
    return "Server is awake", 200

# Start the background thread
keep_alive_thread = Thread(target=keep_alive)
keep_alive_thread.start()

