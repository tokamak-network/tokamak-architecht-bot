import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

load_dotenv()

DB_DIR = "./chroma_db"

class TokamakArchitect:
    def __init__(self):
        embeddings = OpenAIEmbeddings()
        
        if not os.path.exists(DB_DIR):
            print("⚠️ Warning: Vector DB not found. Please run 'python ingest.py' first.")
            self.rag_chain = None
            return

        self.vectorstore = Chroma(
            persist_directory=DB_DIR, 
            embedding_function=embeddings
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # 1. Contextualize Question Prompt
        contextualize_q_system_prompt = """Given a chat history and the latest user question 
        which might reference context in the chat history, formulate a standalone question 
        which can be understood without the chat history. Do NOT answer the question, 
        just reformulate it if needed and otherwise return it as is."""
        
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        
        history_aware_retriever = create_history_aware_retriever(
            self.llm, self.retriever, contextualize_q_prompt
        )

        # 2. Answer Question Prompt
        qa_system_prompt = """You are 'Tokamak Architect', an expert DevOps consultant for the Tokamak Network.
        Your goal is to help users deploy L2 Rollups using the TRH Platform.
        
        Use the following pieces of retrieved context to answer the question.
        If you don't know the answer, say that you don't know. DO NOT hallucinate features.
        
        Guidelines:
        - Be concise and actionable.
        - If a user asks about configurations (e.g., Block Time), explain the trade-offs (Speed vs Cost).
        - NEVER ask for private keys or seed phrases.
        - If the user asks for "Testnet", assume Sepolia.
        
        Context: {context}"""
        
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        
        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        
        self.rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    def ask(self, query: str, chat_history: list = []):
        if not self.rag_chain:
            return "System Error: Knowledge base not initialized. Please run ingestion script."
            
        response = self.rag_chain.invoke({"input": query, "chat_history": chat_history})
        return response["answer"]
