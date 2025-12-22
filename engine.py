import os
import json
import logging
from typing import Dict
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from langchain_core.output_parsers import StrOutputParser

# Define Folders
load_dotenv()
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploaded_pdfs") # Documents Dir
PERSIST_DIR = os.getenv("PERSIST_DIR", "./chroma_store") # Vector Data Dir
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Embedding & LLM Models
embeddings = OllamaEmbeddings(model="mxbai-embed-large")
llm = OllamaLLM(model="qwen3-vl:235b-cloud", base_url="http://localhost:11434")

# Logger
def setup_logger(name="gaia"):

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] - %(message)s ")
    ch.setFormatter(formatter)

    # Duplicate Log Handler
    if not logger.hasHandlers():
        logger.addHandler(ch)

    return logger

logger = setup_logger()

# Load the vectors
def load_vectors():
    vectorstore = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings,
        collection_name="knowledge_base"
    )

    return vectorstore

# Retrieve the chunks
def get_retriever(vectorstore, k=3):
    return vectorstore.as_retriever(search_kwargs={"k": k})

DUMMY_DB = [
  {
    "role_name": "TELLER_CASH",
    "topic": "Prosedur Penanganan Uang Tunai & Deteksi Uang Palsu",
    "mentor_persona": "Anda adalah Senior Head Teller bernama 'Pak Teguh'. Karakter Anda sangat teliti, tegas terhadap kepatuhan (compliance), dan tidak mentolerir kesalahan sekecil apapun terkait keamanan uang. Nada bicara Anda formal, langsung pada inti, dan sering mengutip nomor regulasi bank.",
    "simulation_persona_text": "Anda sekarang adalah 'Bapak Hartono', seorang nasabah prioritas yang sedang terburu-buru. Anda berusia 50 tahunan, memakai jas rapi, tetapi terlihat sangat tidak sabar. Anda membawa uang tunai Rp 100 Juta untuk disetorkan. Emosi Anda saat ini: Tegang dan Mudah Tersinggung.",
    "scenario_details_text": "Nasabah (Bapak Hartono) ingin menyetor uang tunai Rp 100 Juta. Saat penghitungan di mesin, satu lembar uang pecahan Rp 100.000 terdeteksi palsu (rejected). Konflik utama: Nasabah tidak terima uangnya dibilang palsu dan menuduh mesin Anda yang rusak. Kendala Trainee: Trainee harus menahan uang palsu tersebut sesuai regulasi BI, tetapi tidak boleh menuduh nasabah sebagai kriminal di depan umum.",
    "success_criteria": [
      {
        "criteria": "Deteksi & Konfirmasi",
        "description": "Trainee harus memeriksa ulang uang tersebut secara manual (Dilihat, Diraba, Diterawang) di depan nasabah tanpa menyembunyikan tangan."
      },
      {
        "criteria": "Komunikasi Non-Verbal",
        "description": "Trainee tidak boleh berteriak 'Uang Palsu'. Trainee harus menggunakan istilah halus seperti 'Uang yang diragukan keasliannya'."
      },
      {
        "criteria": "Eskalasi Supervisor",
        "description": "Trainee harus memanggil Supervisor (Head Teller) untuk verifikasi ganda sebelum menahan uang tersebut."
      },
      {
        "criteria": "Penahanan Fisik",
        "description": "Trainee menjelaskan bahwa uang tidak bisa dikembalikan ke nasabah dan harus dibuatkan Berita Acara."
      }
    ]
  },
  {
    "role_name": "CS_COMPLAINT",
    "topic": "Handling Customer Complaints (Lost Card)",
    "mentor_persona": "Anda adalah Customer Service Manager bernama 'Ibu Sari'. Karakter Anda sangat keibuan, suportif, dan sangat menekankan pada Empati. Anda percaya bahwa teknis bisa diajarkan, tetapi senyum dan ketulusan adalah kunci. Nada bicara Anda lembut dan menenangkan.",
    "simulation_persona_text": "Anda sekarang adalah 'Ibu Lina', seorang ibu rumah tangga yang sedang panik dan menangis. Kartu ATM Anda tertelan mesin saat Anda mau mengambil uang untuk bayar uang sekolah anak. Anda merasa bank ini menyusahkan. Emosi Anda: Sedih, Panik, dan Merasa Menjadi Korban.",
    "scenario_details_text": "Kartu tertelan di mesin ATM on-site (di cabang). Nasabah meminta kartu dikembalikan 'sekarang juga' karena dia butuh uang tunai segera. Masalah Teknis: Kunci mesin ATM dipegang vendor, bukan cabang, jadi kartu tidak bisa diambil instan. Trainee harus menenangkan nasabah dan menawarkan solusi alternatif (tarik tunai tanpa kartu / buku tabungan).",
    "success_criteria": [
      {
        "criteria": "Empati Awal (3A)",
        "description": "Trainee harus memulai dengan meminta maaf dan menenangkan nasabah (misal: 'Saya mengerti kekhawatiran Ibu')."
      },
      {
        "criteria": "Verifikasi Data",
        "description": "Trainee harus memverifikasi KTP dan Buku Tabungan sebelum memblokir kartu lama."
      },
      {
        "criteria": "Penjelasan Solutif",
        "description": "Trainee tidak boleh hanya bilang 'Tidak Bisa'. Trainee harus menawarkan Tarik Tunai via Teller atau Mobile Banking sebagai solusi pengganti."
      },
      {
        "criteria": "Closing",
        "description": "Trainee menawarkan penggantian kartu instan (jika sistem memungkinkan) atau jadwal pengambilan kartu baru."
      }
    ]
  }
]

def fetch_roleplay_data(role_id: str) -> Dict:
    # Fetching the data
    role_data = next((item for item in DUMMY_DB if item["role_name"] == role_id), None)
    if not role_data:
        raise ValueError(f"Role ID {role_id} not found.")
    return role_data

def build_system_prompt(phase: str, data: dict) -> str:
    """
    Constructs the System Prompt dynamically based on the current Phase 
    and the Topic Configuration (data) retrieved from the Database.
    """

    # Variables
    mentor_persona = data.get("mentor_persona")

    if phase == "GREETING": # Inject Greeting Prompt
        return "Session Initiated. No specific knowledge base needed yet."
    elif phase == "TUTORING": # Inject Tutoring Prompt
        return f"""
        ROLE: {mentor_persona}
        TASK: Conduct a Q&A session about {data['topic']}.
        CONSTRAINT: Use the retrieved Knowledge Base to answer.
        """
    elif phase == "ROLEPLAY": # Inject Roleplay Prompt
        return f"""
        ROLE: {data['simulation_persona']}
        SCENARIO: {data['scenario_details']}
        CONSTRAINT: Do NOT act as a mentor. React realistically to the trainee.
        """
    elif phase == "GRADING": # Inject Grading Prompt
        rubric = json.dumps(data.get("success_criteria"), indent=2)
        return f"""
        ROLE: Lead Auditor.
        TASK: Grade the previous conversation based on this rubric:
        {rubric}
        OUTPUT: Markdown table.
        """

    return mentor_persona

# Chain Query
def query_chain(retriever, llm, user_input: str, role_id: str, current_phase: str):
    """
    Orchestrates the entire flow: Data -> Prompt -> RAG -> LLM
    """

    try:
        logger.info(f"--- Starting Chain: {role_id} | Phase: {current_phase} ---")

        # Fetch Data from DB
        role_data = fetch_roleplay_data(role_id)

        # Build Dynamic System Prompt
        system_instructions = build_system_prompt(current_phase, role_data)

        # Optimization: Only retrieve docs in 'TUTORING'. In 'ROLEPLAY', context is the scenario.
        if current_phase == "TUTORING":
            knowledge_base_content = retriever.invoke(user_input)
        elif current_phase == "GREETING":
            knowledge_base_content = "Session Initiated."
        else:
            knowledge_base_content = "Refer to Scenario Details in System Prompt."

        # Prompt Template
        template = """
        {role_instruction}

        [CONTEXT/KNOWLEDGE BASE]: {knowledgeBase}

        [USER INPUT]: {question}
        """

        # Build the Chain
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm | StrOutputParser()

        # Invoke
        result = chain.invoke({"role_instruction": system_instructions, "knowledgeBase": knowledge_base_content, "question": user_input})
        return result
    except Exception as e:
        logger.exception("Error querying the chain")
        raise