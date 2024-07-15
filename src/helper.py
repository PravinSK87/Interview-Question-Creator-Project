#from langchain.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import TokenTextSplitter
from langchain.docstore.document import Document
#from langchain.chat_models import ChatOpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
#from langchain.embeddings.openai import OpenAIEmbeddings
#from langchain.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
import os
from dotenv import load_dotenv
##import local functions and variables
from src.prompt import *


##OpenAI Authentication

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

## Load Document
def file_processing(file_path):

    ##Load the document
    loader = PyPDFLoader(file_path)
    data = loader.load()
    
    question_gen = ""
    
    for page in data:
        question_gen += page.page_content

    
    splitter_ques_gen = TokenTextSplitter(
    model_name= "gpt-3.5-turbo",
    chunk_size=10000,
    chunk_overlap=200 )

    chunk_ques_gen = splitter_ques_gen.split_text(question_gen)
    
    document = [Document(page_content=t) for t in chunk_ques_gen]

    splitter_ans_gen = TokenTextSplitter(
    model_name= "gpt-3.5-turbo",
    chunk_size=1000,
    chunk_overlap=100 )

    document_answer_gen = splitter_ans_gen.split_documents( document )
    
    return document, document_answer_gen


def llm_pipeline(file_path):
    document, document_answer_gen = file_processing(file_path)

    llm_ques_gen_pipeline = ChatOpenAI(model = "gpt-3.5-turbo", temperature=0.3)

    PROMPT_QUESTIONS = PromptTemplate(template = prompt_template,input_variables=["text"])

    REFINE_PROMPT_QUESTIONS = PromptTemplate(template=refine_template,input_variables=["existing_answer","text"])

    ques_gen_chain = load_summarize_chain(llm=llm_ques_gen_pipeline,
                                      chain_type="refine",
                                      verbose=True,
                                      question_prompt = PROMPT_QUESTIONS,
                                      refine_prompt = REFINE_PROMPT_QUESTIONS
                                      )
    
    ques = ques_gen_chain.run(document_answer_gen)
    
    embeddings = OpenAIEmbeddings()

    vector_store = FAISS.from_documents(document_answer_gen,embeddings)

    llm_answer_gen = ChatOpenAI(temperature=0.1,model="gpt-3.5-turbo")

    ques_list = ques.split("\n")

    filtered_ques_list = [element for element in ques_list if element.endswith('?') or element.endswith('.')]

    answer_generaion_chain = RetrievalQA.from_chain_type(llm = llm_answer_gen, chain_type = "stuff", retriever = vector_store.as_retriever())

    return answer_generaion_chain, filtered_ques_list
                                      

    
    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.from_documents(embeddings, document)
    
    retriever = vector_store.as_retriever(
        search_kwargs={"k": 5},
        search_strategy="deep"
    )
    
    chain_qa = RetrievalQA.from_chain_type(
        chain_type=load_summarize_chain,
        retriever=retriever,
        chain_name="QuestionAnsweringChain",
        question_prefix=QUESTION_PREFIX,
        max_length=500
    )
    
    return chain_qa