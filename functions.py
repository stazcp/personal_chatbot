import json
import os

def create_assistant(client):
  assistant_file_path = 'assistant.json'

  if os.path.exists(assistant_file_path):
    with open(assistant_file_path, 'r') as file:
      assistant_data = json.load(file)
      assistant_id = assistant_data['assistant_id']
      print("Loaded existing assistant ID.")
  else:
    assistant_id = create_new_assistant(client)

  # Try to use the assistant ID
  try:
    client.beta.assistants.retrieve(assistant_id)
  except Exception:  # Replace with the specific exception if known
    print("Invalid assistant ID. Creating a new assistant.")
    assistant_id = create_new_assistant(client)

  return assistant_id

def create_new_assistant(client):
  file = client.files.create(file=open("knowledge.docx", "rb"),
                             purpose='assistants')

  assistant = client.beta.assistants.create(instructions="""
        Your job is to talk to potential recruiters or potential clients.
        Your instructions are to act like you are Staz (or his ai version), you will answer questions
        about him based on the provided docs.
        All your responses should be formatted into HTML.
        """,
                                            model="gpt-4-1106-preview",
                                            tools=[{
                                                "type": "retrieval"
                                            }],
                                            file_ids=[file.id])

  with open('assistant.json', 'w') as file:
    json.dump({'assistant_id': assistant.id}, file)
    print("Created a new assistant and saved the ID.")

  return assistant.id