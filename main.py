import os
import streamlit as st
from dotenv import load_dotenv
from engine import query_chain, load_vectors, get_retriever
from langchain_ollama.llms import OllamaLLM
from langchain_google_genai import ChatGoogleGenerativeAI

st.set_page_config(page_title="GAIA", layout="wide")

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def render_advisor_grid(data):
    num_cols = 3
    num_cards = len(data["Title"])

    for start in range(0, num_cards, num_cols):
        row = st.columns(num_cols)
        for idx, col in enumerate(row):
            card_idx = start + idx
            if card_idx < num_cards:
                with col:
                    with st.container(border=True, height="stretch"):
                        left, right = st.columns(2)
                        with left:
                            st.image(image=data["Image Path"][card_idx])
                        with right:
                            st.markdown(f"### {data['Title'][card_idx]}") 
                            st.caption(data['Description'][card_idx])
                            
                            # Use a unique key based on title or ID to avoid conflicts
                            unique_key = f"btn_{data['Title'][card_idx].replace(' ', '_')}_{card_idx}"
                            
                            if st.button(label=":speech_balloon: Chat", key=unique_key, use_container_width=True, type="primary"):
                                # Navigate to the specific page defined in the data
                                st.switch_page(data["Destination"][card_idx])

def mainpage():
    st.title("Main Page")

def mb_page():
    st.title("Explore all the Trusted Advisory")
    st.markdown("Practice real-world scenario through immersive roleplays or personalized tutoring.")
    # NOTE: Implement a functional search bar here.
    st.text_input(label = "Search for tutors", label_visibility = "collapsed", width = 600, icon = ":material/search:", placeholder = "Search for tutors")
    st.divider()
    st.subheader("Trusted Advisory")

    dummy_advisor = {
        "Title": [
            "Product Knowledge",
            "Business Relationship",
            "Management",
            "Risk Assessment",
            "Compliance Training",
            "Customer Service"
        ],
        "Description": [
            "Master key banking products and services through interactive real-world scenarios.",
            "Develop essential skills to build trust, communicate effectively, and grow client relationships.",
            "Enhance leadership and decision-making abilities for team management and strategic planning for agile growth.",
            "Identify, evaluate, and mitigate financial risks proactively and continuously using industry best practices.",
            "Stay updated on regulatory requirements and compliance standards through engaging.",
            "Deliver exceptional customer experiences by learning effective communication."
        ],
        "Image Path": [
            "https://placehold.co/500x500",
            "https://placehold.co/500x500",
            "https://placehold.co/500x500",
            "https://placehold.co/500x500",
            "https://placehold.co/500x500",
            "https://placehold.co/500x500",
        ],
        "Destination": [
            st.Page(cxo_page),
            st.Page(cxo_page),
            st.Page(cxo_page),
            st.Page(cxo_page),
            st.Page(cxo_page),
            st.Page(cxo_page),
        ]
    }
    
    # 3. Call the reusable function
    render_advisor_grid(dummy_advisor)

    st.sidebar.title("Welcome, User")
    with st.sidebar:
        if st.button(
            label = "Logout",
            type = "primary"
        ):
            st.text("Logout")

def cxo_page():
    st.markdown("""
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 60px;
        ">
            <div style="
                overflow: hidden;
                background-color: rgba(0, 0, 0, 0);
                border: 0px solid black;
                box-sizing: border-box;
                width: 150px;
                height: 150px;
                border-radius: 100%;
                position: relative;
                display: flex;
                flex-direction: column;
            ">
                <div style="width: 150px; height: 150px; position: relative;">
                    <img 
                        src="https://placehold.co/500x500"
                        alt=""
                        loading="lazy"
                        decoding="async"
                        style="
                            object-position: left 50% top 50%;
                            width: 100%;
                            height: 100%;
                            position: absolute;
                            top: 0px;
                            left: 0px;
                            object-fit: cover;
                            border-radius: 100%;
                        "
                    >
                </div>
            </div>
            <div>
                <h1>Product Knowledge</h1>
            </div>
            <div style="margin-bottom: 32px; color: #aaa; font-size: 15px; text-align: center; max-width: 320px;">
                Master key banking products and services through interactive real-world scenarios.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # 1. INITIALIZE SESSION STATE
    # ==========================================
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Initialize the Phase if it doesn't exist
    if "phase" not in st.session_state:
        st.session_state.phase = "GREETING"
        st.session_state.trigger_ai_greeting = True # Set the AI to speak first on page load

    # Cache AI Variables
    if "retriever" not in st.session_state:
        with st.spinner("Initializing AI..."):
            vs = load_vectors()
            st.session_state.retriever = get_retriever(vs)
            st.session_state.llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")
            # st.session_state.llm = OllamaLLM(model="qwen3-vl:235b-cloud", base_url="http://localhost:11434")

    # ==========================================
    # 2. RENDER HISTORY
    # ==========================================
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"])

    # ==========================================
    # 3. AUTO-TRIGGER (AI Speaks First)
    # ==========================================

    # Sidebar
    with st.sidebar:
        st.title("Welcome, User")
        st.caption(f"Mode: {st.session_state.phase}")
        if st.button(
            label = "Logout",
            type = "primary"
        ):
            st.text("Logout")

    role_id = "CS_COMPLAINT" # Change the variable into the respective role
    if st.session_state.get("trigger_ai_greeting"):
        with st.chat_message("assistant"):
            with st.spinner("AI is preparing..."):
                response_text = query_chain(
                    retriever=st.session_state.retriever,
                    llm=st.session_state.llm,
                    user_input="[SYSTEM_TRIGGER_START]",
                    role_id=role_id, 
                    current_phase=st.session_state.phase,
                    chat_history=st.session_state.messages
                )
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.session_state.trigger_ai_greeting = False
    
    # ==========================================
    # 4. MAIN CHAT INTERFACE
    # ==========================================

    # Chatbot Input
    user_input = st.chat_input("Hi! Ask me anything...")

    if user_input:
        # Show user input
        st.chat_message("user").markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Generate API Response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response_text = query_chain(
                    retriever=st.session_state.retriever,
                    llm=st.session_state.llm,
                    user_input=user_input,
                    role_id=role_id,
                    current_phase=st.session_state.phase,
                    chat_history=st.session_state.messages
                )

                # response = response_text.json()
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

    # ==========================================
    # 5. BUTTON CONTROLS
    # ==========================================
    with st.container(horizontal_alignment="center"):
        if st.session_state.phase == "GREETING":
            if st.button("🎓 Start Tutoring", key="start_tutoring"):
                st.session_state.phase = "TUTORING"
                st.session_state.trigger_ai_greeting = True
                st.rerun()
        elif st.session_state.phase == "TUTORING":
            if st.button("🚀 Start Roleplay", key="start_roleplay"):
                st.session_state.phase = "ROLEPLAY"
                st.session_state.messages = []
                st.session_state.trigger_ai_greeting = True
                st.rerun()
            # st.info("Ask questions to deepen understanding")
        elif st.session_state.phase == "ROLEPLAY":
            if st.button("🏁 Finish & Grade", key="finish_grade"):
                st.session_state.phase = "GRADING"
                st.session_state.trigger_ai_greeting = True
                st.rerun()
            # st.error("Simulation in progress")

pages = {
    "": [
        st.Page(mainpage, title="👤 Roleplay & Tutor"),
        st.Page(mb_page, title="Magang Bakti"),
        st.Page(cxo_page, title="CXO Chatbot")
    ]
}
pg = st.navigation(pages)
pg.run()