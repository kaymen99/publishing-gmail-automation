from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from .utils import RAG_DATABASE_DIR
from .prompts import *

class Agents():
    def __init__(self):
        flash = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1)
        gemini = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.1)

        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        self.vectorstore = Chroma(persist_directory=RAG_DATABASE_DIR, embedding_function=embeddings)
        
        parser_prompt = ChatPromptTemplate.from_template(EMAIL_PARSER_PROMPT)
        self.email_parse_chain = parser_prompt | flash | StrOutputParser()
        
        intent_prompt = ChatPromptTemplate.from_template(INTENT_DETECTION_PROMPT)
        self.intent_detection_chain = intent_prompt | flash | JsonOutputParser()

        inquiry_prompt = ChatPromptTemplate.from_template(INQUIRY_EXTRACTION_PROMPT)
        self.inquiry_extraction_chain = inquiry_prompt | flash | JsonOutputParser()
        
        docs_writer_prompt = ChatPromptTemplate.from_template(DOCS_WRITER_PROMPT)
        self.docs_writer_chain = docs_writer_prompt | flash | StrOutputParser()
        
        standard_email_writer_prompt = ChatPromptTemplate.from_template(STANDARD_EMAIL_RESPONSE_PROMPT)
        self.write_standard_email_chain = standard_email_writer_prompt | flash | StrOutputParser()
        
        email_writer_prompt = ChatPromptTemplate.from_template(RAG_EMAIL_RESPONSE_PROMPT_TEMPLATE)
        self.write_email_chain = email_writer_prompt | gemini | StrOutputParser()
        
        update_info_prompt = ChatPromptTemplate.from_template(INFORMATION_UPDATER_PROMPT)
        self.update_email_info_chain = update_info_prompt | flash | StrOutputParser()
        
        email_editor_prompt = ChatPromptTemplate.from_template(EDITOR_EMAIL_ANALYSIS_PROMPT_TEMPLATE)
        self.email_editor_chain = email_editor_prompt | flash | JsonOutputParser()
        
        email_rewriter_prompt = ChatPromptTemplate.from_template(EMAIL_REWRITER_PROMPT_TEMPLATE)
        self.email_rewriter_chain = email_rewriter_prompt | gemini | StrOutputParser()