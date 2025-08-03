import sqlite3
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.docstore.document import Document
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
import requests.exceptions


def load_documents_from_db(db_path="cheating_system.db"):
    """Loads cheating and absence data from SQLite and converts to LangChain Documents"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.name, s.academic_id, s.committee, ce.formatted_time, 
               ce.details, ce.confidence, ce.image_path, ce.datetime_recorded
        FROM cheating_events ce
        JOIN students s ON ce.academic_id = s.academic_id
        ORDER BY ce.timestamp
    ''')
    cheating_rows = cursor.fetchall()
    conn.close()

    documents = []
    for row in cheating_rows:
        content = (
            f"Cheating Incident:\n"
            f"Student Name: {row[0]}\n"
            f"Academic ID: {row[1]}\n"
            f"Committee: {row[2]}\n"
            f"Time: {row[3]}\n"
            f"Details: {row[4]}\n"
            f"Confidence: {row[5]:.2f}\n"
            f"Image Path: {row[6]}\n"
            f"Recorded At: {row[7]}"
        )
        documents.append(Document(
            page_content=content,
            metadata={
                "type": "cheating",
                "student_name": row[0],
                "confidence": row[5],
                "datetime": row[7]
            }
        ))

    return documents


def build_vectorstore(documents):
    """Create a FAISS vector store from documents"""
    if not documents:
        raise ValueError("No documents found in database. Please add data first.")
    
    embeddings = OllamaEmbeddings(model="all-minilm:33m")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("faiss_cheating_index")
    return vectorstore


def create_rag_chain(vectorstore):
    """Create RAG chain using FAISS retriever and LLM"""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    llm = OllamaLLM(model="llama3.2:3b")

    prompt_template = """
You are a smart assistant helping monitor exam committees for cheating and absences.

When answering questions:
1. Analyze the provided context carefully even if data seems limited.
2. For cheating questions:
   - Who's cheating most → name and incident count
   - When cheating happens most → time with most records
   - About specific student → summarize their incidents with confidence levels
3. For absence questions:
   - Who's absent most → name and absence count
   - Absence reasons → most common reasons
   - About specific student → summarize their absences
4. If exact info isn't available, provide reasonable insights from available data.
5. Be concise but natural in responses.

Context:
{context}

Question:
{question}

Answer:
"""
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

    return (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )


def save_rag_result(question, answer, db_path="cheating_system.db"):
    """Stores RAG input/output in the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rag_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO rag_results (question, answer, timestamp)
        VALUES (?, ?, ?)
    """, (question, answer, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def query_documents(rag_chain, question: str):
    try:
        answer = rag_chain.invoke(question)
        if "no relevant data" in answer.lower() or not answer.strip():
            fallback_llm = OllamaLLM(model="llama3.2:3b")
            answer = fallback_llm.invoke(question)
        return answer
    except requests.exceptions.ConnectionError:
        return "⚠️ تأكد إن خدمة Ollama شغالة."
    except ValueError as e:
        return f"⚠️ {str(e)}"
    except Exception as e:
        return f"🚫 حصل خطأ: {str(e)}"


if __name__ == "__main__":
    print("📊 Exam Monitoring RAG System Initialized ✅")

    try:
        all_docs = load_documents_from_db()
        vectorstore = build_vectorstore(all_docs)
        rag_chain = create_rag_chain(vectorstore)

        print("\n💡 Example questions:")
        print("- Who is cheating the most?")
        print("- What time has the most cheating incidents?")
        print("- Tell me about [student name]'s cheating incidents")
        print("- Who has the most absences?")
        print("- What are the common absence reasons?")
        print("- Tell me about [student name]'s absences")

        while True:
            question = input("\n📝 Your question: ")
            if question.lower() in ['quit', 'exit']:
                print("👋 Exiting the system.")
                break
            if not question.strip():
                continue

            print("🔍 Analyzing...")
            response = query_documents(rag_chain, question)
            print("\n🧠 Answer:", response)
            save_rag_result(question, response)

    except ValueError as e:
        print(f"⚠️ {str(e)}")
    except Exception as e:
        print(f"🚫 فشل تشغيل النظام: {str(e)}")
