import os, re
from .agents import Agents
from .tools.GoogleAPITools import GmailToolsClass, GoogleSheetsToolsClass
from .state import Email
from .utils import (
    STANDARD_REPLIES_TEMPLATES,
    extract_response,
    compose_update_information
)

EMAIL_INBOXES = ["editorials@nabpress.com", "journals@nabpress.com"]

class Nodes:
    def __init__(self):
        self.agents = Agents()
        
        # Initialize Gmail tools for each inbox
        self.gmail_tools = {
            inbox: GmailToolsClass(inbox)
            for inbox in EMAIL_INBOXES
        }
        self.current_inbox_index = 0
        
        self.sheet_tools = GoogleSheetsToolsClass(
            sheet_id='1G05gQG02uiOUPT1cGx3X5QCdnzkfrEKY8Ziu49zRZSw', 
            range_name='Sheet1!A2:B11'
        )
        self.journal_prices = self.sheet_tools.fetch_sheet_data()

    def process_email_inbox(self, state):
        if self.current_inbox_index >= len(EMAIL_INBOXES):
            print("All inboxes processed")
            return "complete"
        
        current_inbox = EMAIL_INBOXES[self.current_inbox_index]
        print(f"\nProcessing inbox: {current_inbox}\n")
        return "continue"
        
    def load_new_emails(self, state):
        print("Loading new emails...\n")
        current_inbox = EMAIL_INBOXES[self.current_inbox_index]
        recent_emails = self.gmail_tools[current_inbox].fetch_unreplied_threads()
        # Only keep received emails
        emails = [Email(**email) for email in recent_emails if (current_inbox not in email['sender_email'])]
        return {"emails": emails}
    
    def check_new_emails(self, state):
        number_emails = len(state['emails'])
        if number_emails == 0:
            print("No new emails in current inbox")
            self.current_inbox_index += 1
            return "empty"
        else:
            print(f"{number_emails} new emails to process")
            return "continue"
        
    def is_email_inbox_empty(self, state):
        return state

    def categorize_email_intent(self, state):
        print("Checking email category...\n")
        current_email = state["emails"][-1]
        if_submission_msg = bool(re.search(r'This is a new submission for', current_email.body))
        email_intent = ""
        if if_submission_msg:
            email_intent = "After submission"
        else:
            email_body = self.parse_email_content(current_email.body)
            current_email.body = email_body
            category_result = self.agents.intent_detection_chain.invoke({"email_content": email_body})
            email_intent = category_result["intent"]
        print("Email category:", email_intent)
        return { 
            "email_category": email_intent,
            "current_email": current_email
        }
        
    def parse_email_content(self, email_body):
        if len(email_body) > 1000:
            email_body = self.agents.email_parse_chain.invoke({"email_content": email_body})
        elif len(email_body) <= 30:
            email_body = f"Note this a response to our outreach email mentioning our interest in publishing a paper.\n\n{email_body}"
        return email_body
        
    def route_email_based_on_category(self, state):
        print("Routing email based on category...\n")
        category = state["email_category"]
        if (
            category == "Paper Already Published" or 
            category == "After submission" or 
            category == "Not Interested"
        ):
            return "Write Directly"
        elif (category == "Want to Publish" or category == "Share Another Paper"):
            return "Need RAG"
        elif category == "Unrelated":
            return "Unrelated"

    def extract_email_inquiries(self, state):
        print("Extracting inquiries from emails...\n")
        email_content = state["current_email"].body
        inquiries = self.agents.inquiry_extraction_chain.invoke({"email_content": email_content})
        if state["email_category"] == "Want to Publish":
            if 'Submission Process and Procedure' not in inquiries['inquiries']:
                inquiries['inquiries'].extend(['Submission Process and Procedure'])
        elif state["email_category"] == "Share Another Paper":
            inquiries['inquiries'].extend(['Want to share a draft'])
            if 'Submission Process and Procedure' in inquiries['inquiries']:
                inquiries['inquiries'].remove('Submission Process and Procedure')
            
        return {"email_inquiries": inquiries["inquiries"]}

    def retrieve_docs_from_rag(self, state):
        print("Retrieve docs from vector DB...\n")
        retriever = self.agents.vectorstore.as_retriever(search_kwargs={"k": 2})
        
        docs = []
        for q in state['email_inquiries']:
            docs += [extract_response(doc.page_content) for doc in retriever.invoke(q)]
        documents = "\n\n////////////\n\n".join(docs)
        
        context = self.agents.docs_writer_chain.invoke({
            "inquiries": state['email_inquiries'],
            "documents": documents
        })
        return {"retrieved_context": context}
    
    def generate_standard_draft_reply(self, state):
        print("Writing draft email...\n")
        email_category = state["email_category"]
        generated_email = self.agents.write_standard_email_chain.invoke({
            "email_template": STANDARD_REPLIES_TEMPLATES[email_category],
            "recipient_info": state["current_email"].sender
        })
        return {"generated_email": generated_email}

    def generate_draft_reply(self, state):
        print("Writing draft email...\n")
        email_content = state["current_email"].body
        email_category = state["email_category"]
        generated_email = ""
        if (
            email_category == "Paper Already Published" or 
            email_category == "After submission" or 
            email_category == "Not Interested"
            ):
            generated_email = self.agents.write_standard_email_chain.invoke({
                "email_template": STANDARD_REPLIES_TEMPLATES[email_category],
                "recipient_info": state["current_email"].sender
            })
        else:
            generated_email = self.agents.write_email_chain.invoke({
                "email_content": email_content,
                "context": state["retrieved_context"]
            })
            
            # Add latest information to email
            update_information = compose_update_information(state, self.journal_prices)
            generated_email = self.agents.update_email_info_chain.invoke({
                "email_content": generated_email,
                "recipient": state["current_email"].sender,
                "information": update_information
            })
        return {"generated_email": generated_email}
    
    # def need_to_review_email(self, state):
    #     category = state["email_category"]
    #     if (category == "Paper Already Published" or category == "After submission"):
    #         return "send"
    #     elif (category == "Want to Publish" or category == "Share Another Paper"):
    #         return "review"

    # def review_generated_draft(self, state):
    #     print("Verifying generated email...\n")
    #     feedback = self.agents.email_editor_chain.invoke({
    #         "generated_email": state["generated_email"],
    #         "initial_email": state["current_email"].body
    #     })
    #     return {"editor_feedback": feedback["feedback"]}
    
    # def must_rewrite(self, state):
    #     review = "feedback["feedback"]"
    #     if (review == "ready" or state["trials"] > 2):
    #         print("Email is good, create draft...")
    #         return "send"
    #     else:
    #         print("Email is not good, must rewrite it...")
    #         return "rewrite"
        
    # def rewrite_email_from_feedback(self, state):
    #     print("Rewriting email...\n")
    #     new_email = self.agents.email_rewriter_chain.invoke({
    #         "initial_email": state["current_email"].body,
    #         "generated_email": state["generated_email"],
    #         "feedback": state["editor_feedback"]
    #     })
    #     trials = state.get('trials', 0) + 1
    #     return {"generated_email": new_email, "trials": trials}

    def create_draft_response(self, state):
        print("Creating draft response...\n")
        current_inbox = EMAIL_INBOXES[self.current_inbox_index]
        state["emails"].pop()
        self.gmail_tools[current_inbox].create_draft_reply(
            state["current_email"].id,
            state["current_email"].threadId,
            state["current_email"].sender_email,
            state["current_email"].subject,
            state["generated_email"]
        )
        return {"retrieved_context": "", "email_inquiries": [], "feedback": "", "trials": 0}
    
    def send_email_response(self, state):
        print("Sending email...\n")
        current_inbox = EMAIL_INBOXES[self.current_inbox_index]
        state["emails"].pop()
        self.gmail_tools[current_inbox].send_reply(
            state["current_email"].id,
            state["current_email"].threadId,
            state["current_email"].sender_email,
            state["current_email"].subject,
            state["generated_email"]
        )
        return {"retrieved_context": "", "email_inquiries": [], "feedback": "", "trials": 0}
    
    def skip_unrelated_email(self, state):
        print("Skipping unrelated email...\n")
        state["emails"].pop()
        return {"retrieved_context": "", "email_inquiries": [], "feedback": "", "trials": 0}