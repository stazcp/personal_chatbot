import json
import os
import openai

def create_new_assistant(client):
  knowledge_file = client.files.create(file=open("knowledge.docx", "rb"),
                             purpose='assistants')

  with open('instructions.txt', 'r') as instructions_file:
    instructions = instructions_file.read()
  
  assistant = client.beta.assistants.create(instructions=instructions,
                                            model="gpt-4-turbo-preview",
                                            name=os.getenv('ASSISTANT_NAME'),
                                            tools=[
                                              {"type": "code_interpreter"},
                                              {"type": "retrieval"}
                                            ],
                                            file_ids=[knowledge_file.id])
  print(f"Assistant created with ID: {assistant.id}")  # Debugging line
  return assistant.id

def create_new_thread(client):
  thread = client.beta.threads.create()
  print(f"New thread created with ID: {thread.id}")  # Debugging line
  return thread

# Save assistant_id and thread_id to a file
def save_ids(assistant_id, thread_id):
    with open('ids.json', 'w') as f:
        json.dump({'assistant_id': assistant_id, 'thread_id': thread_id}, f)

def get_assistant_id(client, name):
    response = client.beta.assistants.list()
    assistants = response.data
    for assistant in assistants:
        if assistant.name == name:
            return assistant.id
    return None

def setup_assistant_and_thread(client):
  ASSISTANT_NAME = os.getenv('ASSISTANT_NAME')
  assistant_id = get_assistant_id(client, ASSISTANT_NAME)
  if assistant_id == None:
    assistant_id = create_new_assistant(client)
  thread = create_new_thread(client)
  thread_id = thread.id
  save_ids(assistant_id, thread_id)

  return assistant_id, thread_id


# Load assistant_id and thread_id from a file
def load_ids():
    if os.path.exists('ids.json'):
        with open('ids.json', 'r') as f:
            ids = json.load(f)
            return ids.get('assistant_id'), ids.get('thread_id')
    else:
        return None, None
        