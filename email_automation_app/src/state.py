from pydantic import BaseModel, Field
from typing import List
from typing_extensions import TypedDict

class Email(BaseModel):
    id: str = Field(..., description="Unique identifier of the email")
    threadId: str = Field(..., description="Thread identifier of the email")
    sender: str = Field(..., description="Information of the email sender")
    sender_email: str = Field(..., description="Email address of the sender")
    subject: str = Field(..., description="Subject line of the email")
    body: str = Field(..., description="Body content of the email")

class GraphState(TypedDict):
    emails: List[Email]
    current_email: Email
    email_category: str
    email_inquiries: List[str]
    retrieved_context: str
    generated_email: str
    editor_feedback: str
    trials: int