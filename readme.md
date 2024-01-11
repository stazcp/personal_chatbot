# Staz AI

Staz AI is a conversational AI designed to answer questions about Staz based on provided documents. It acts as an AI version of Staz, interacting with potential recruiters or clients.

## Setup

1. Clone the repository: `git clone <repository-url>`
2. Navigate to the project directory: `cd <project-directory>`
3. Install the required dependencies: `pip install -r requirements.txt`
4. Run the application: `python app.py`

## Usage

To interact with Staz AI, send a POST request to the `/ask` endpoint with a JSON body containing your question. For example:

```json
{
  "question": "What is Staz's favorite programming language?"
}
```
