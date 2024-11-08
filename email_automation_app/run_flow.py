from src.graph import Workflow
from dotenv import load_dotenv
from langchain_core.runnables.graph import MermaidDrawMethod


# Load all env variables
load_dotenv()

workflow = Workflow()
automation = workflow.app

# config 
config = {'recursion_limit': 1000}

initial_state = {
    "emails": [],
    "current_email": {
      "id": "",
      "threadId": "",
      "sender": "",
      "sender_email": "",
      "subject": "",
      "body": ""
    },
    "email_category": "",
    "email_inquiries": [],
    "retrieved_context": "",
    "generated_email": "",
    "editor_feedback": "",
    "trials": 0
}

# Run the agent
print("Starting workflow...")
output = automation.invoke(initial_state, config)
print(output)
# for output in automation.stream(initial_state, config):
#     for key, value in output.items():
#         print(f"Finished running: **{key}**")


