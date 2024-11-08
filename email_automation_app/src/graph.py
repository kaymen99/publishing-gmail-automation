from langgraph.graph import END, StateGraph
from .state import GraphState
from .nodes import Nodes

class Workflow():
    def __init__(self):
        # initiate graph state & nodes
        workflow = StateGraph(GraphState)
        nodes = Nodes()
        
        # define all graph nodes
        workflow.add_node("process_email_inbox", nodes.process_email_inbox)
        workflow.add_node("load_new_emails", nodes.load_new_emails)
        workflow.add_node("is_email_inbox_empty", nodes.is_email_inbox_empty)
        workflow.add_node("categorize_email_intent", nodes.categorize_email_intent)
        workflow.add_node("extract_email_inquiries", nodes.extract_email_inquiries)
        workflow.add_node("retrieve_docs_from_rag", nodes.retrieve_docs_from_rag)
        workflow.add_node("generate_standard_draft_reply", nodes.generate_standard_draft_reply)
        workflow.add_node("generate_draft_reply", nodes.generate_draft_reply)
        workflow.add_node("create_draft_response", nodes.create_draft_response)
        workflow.add_node("skip_unrelated_email", nodes.skip_unrelated_email)
        
        # Set entry point
        workflow.set_entry_point("process_email_inbox")
        
        # Add edges for inbox processing
        workflow.add_conditional_edges(
            "process_email_inbox",
            nodes.process_email_inbox,
            {
                "continue": "load_new_emails",
                "complete": END
            }
        )
        
        # Add edges for email loading
        workflow.add_edge("load_new_emails", "is_email_inbox_empty")
        workflow.add_conditional_edges(
            "is_email_inbox_empty",
            nodes.check_new_emails,
            {
                "continue": "categorize_email_intent",
                "empty": "process_email_inbox"
            }
        )
        
        # Add edges for email categorization and routing
        workflow.add_conditional_edges(
            "categorize_email_intent",
            nodes.route_email_based_on_category,
            {
                "Write Directly": "generate_standard_draft_reply",
                "Need RAG": "extract_email_inquiries",
                "Unrelated": "skip_unrelated_email"
            }
        )
        
        # Add edges for RAG processing
        workflow.add_edge("extract_email_inquiries", "retrieve_docs_from_rag")
        workflow.add_edge("retrieve_docs_from_rag", "generate_draft_reply")
        
        # Add edges for email sending
        workflow.add_edge("generate_draft_reply", "create_draft_response")
        workflow.add_edge("generate_standard_draft_reply", "create_draft_response")
        
        # ////// Email editor Logic: Not implemented /////////
        # workflow.add_conditional_edges(
        #     "generate_draft_reply",
        #     nodes.need_to_review_email,
        #     {
        #         "review": "review_generated_draft",
        #         "send": "create_draft_response",
        #     }
        # )
        # workflow.add_conditional_edges(
        #     "review_generated_draft",
        #     nodes.must_rewrite,
        #     {
        #         "send": "create_draft_response",
        #         "rewrite": "rewrite_email_from_feedback"
        #     }
        # )
        # workflow.add_edge("rewrite_email_from_feedback", "review_generated_draft")
        # ///////////////////////////////////////////////////
        
        # Add edges for continuing to next email
        workflow.add_edge("create_draft_response", "is_email_inbox_empty")
        workflow.add_edge("skip_unrelated_email", "is_email_inbox_empty")
        
        # Compile
        self.app = workflow.compile()