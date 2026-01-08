import os
import re
import uuid
import json
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime
from dotenv import load_dotenv
from engine import query_chain, load_vectors, get_retriever, create_executive_summary, create_individual_report, fetch_all_sessions, init_db, save_full_session
from langchain_ollama.llms import OllamaLLM
from langchain_google_genai import ChatGoogleGenerativeAI

st.set_page_config(page_title="GAIA", layout="wide")

load_dotenv()
init_db()
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
    st.title("Explore all Magang Bakti Roleplay")
    st.markdown("Practice real-world scenario through immersive roleplays or personalized tutoring.")
    # TODO: Implement a functional search bar here.
    st.text_input(label = "Search for tutors", label_visibility = "collapsed", width = 600, icon = ":material/search:", placeholder = "Search for tutors")
    st.divider()
    st.subheader("Trusted Advisory")

    # NOTE: Change this with real data
    dummy_advisor = {
        "Title": [
            "Customer Service",
            "Business Relationship",
            "Management",
            "Risk Assessment",
            "Compliance Training",
            "Product Knowledge"
        ],
        "Description": [
            "Deliver exceptional customer experiences by learning effective communication.",
            "Develop essential skills to build trust, communicate effectively, and grow client relationships.",
            "Enhance leadership and decision-making abilities for team management and strategic planning for agile growth.",
            "Identify, evaluate, and mitigate financial risks proactively and continuously using industry best practices.",
            "Stay updated on regulatory requirements and compliance standards through engaging.",
            "Master key banking products and services through interactive real-world scenarios."
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

    # 
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
                <h1>Customer Service</h1>
            </div>
            <div style="margin-bottom: 32px; color: #aaa; font-size: 15px; text-align: center; max-width: 320px;">
                Deliver exceptional customer experiences by learning effective communication.
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

def new_cxo_page():
    # ==========================================
    # 1. INITIALIZE SESSION STATE
    # ==========================================
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Initialize the Phase if it doesn't exist
    if "phase" not in st.session_state:
        st.session_state.phase = "START"
        st.session_state.trigger_ai_greeting = False # Set the AI to speak first on page load

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

    # Sidebar
    with st.sidebar:
        st.title("Welcome, User")
        # st.caption(f"Mode: {st.session_state.phase}")
        if st.button(
            label = "Logout",
            type = "primary"
        ):
            st.text("Logout")

    # ==========================================
    # 3. AUTO-TRIGGER (AI Speaks First)
    # ==========================================

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
        if st.session_state.phase == "START":
            # Content Information
            st.header("Virtual Advisory & Roleplay Simulator")
            
            st.markdown("""
            Welcome to your personal **AI Training Ground**. 
            This simulator is designed to help you master Banking Standard Operating Procedures (SOPs) through a structured, interactive learning journey.

            ### 🗺️ How This Session Works
            Unlike a standard chat, this session follows a strict **3-Phase Learning Path**:

            1.  **🎓 Tutoring Phase:** Start here to validate your knowledge. The AI Mentor will quiz you on the SOPs. *Use this time to ask questions!*
            2.  **🚀 Roleplay Phase:** Once you are ready, you will enter the simulation. 
                * **⚠️ Warning:** The AI will switch personas (e.g., to an Angry Customer) and will **STOP** helping you. 
                * You must handle the situation based on regulations without assistance.
            3.  **🏁 Grading Phase:** The session concludes with a detailed audit. You will receive a score and specific feedback based on the rubric.

            ---
            
            ### 💡 Guidelines for Success
            * **Follow the UI Buttons:** To move between phases, you **must click the buttons** located below the chat. The AI will tell you when to click them.
            * **Be Specific:** During the Roleplay, general answers like *"I will handle it"* won't work. You must speak exactly as you would to a real customer (e.g., *"Mohon maaf Bapak, boleh saya pinjam KTP-nya?"*).
            * **Check the Knowledge Base:** During Tutoring, the AI answers based on the official PDF manuals. Trust the data provided.
            
            **Ready to begin?** Click the "📖 Start Session" button to initialize the session!
            """)
            st.divider()
            if st.button("📖 Start Session", key="start_session"):
                st.session_state.phase = "GREETING"
                st.session_state.trigger_ai_greeting = True
                st.rerun()  
        elif st.session_state.phase == "GREETING":
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
            if st.button("💯 Finish & Grade", key="finish_grade"):
                st.session_state.phase = "GRADING"
                st.session_state.trigger_ai_greeting = True
                st.rerun()
            # st.error("Simulation in progress")
        elif st.session_state.phase == "GRADING":
            if st.button("🏁 Finish the Session", key="finish_session"):
                # Logic to create a record and report
                with st.spinner("Analyzing performance and saving the session"):
                    
                    # 1. Extract JSON from AI (Parsing the grading output)
                    last_msg = st.session_state[-1]["content"]
                    try:
                        # Find JSON content between braces
                        json_matches = re.search(r'\{.*\}', last_msg, re.DOTALL)
                        if json_matches:
                            metrics = json.loads(json_matches.group())
                        else:
                            metrics = {}
                    except Exception as e:
                        st.error(f"Error parsing AI grades: {e}")

                    # 2. Prepare Data Objects
                    # Header Data
                    session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"
                    session_data = {
                        "session_id": session_id,
                        "trainee_name": "Filbert Sembiring M.",
                        "scenario_id": role_id,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "total_score": metrics.get("total_score", 0),
                        "readiness": metrics.get("readiness", "Undetected"),
                        "chat_log": json.dumps(st.session_state.messages)
                    }

                    # Detailed Grades List
                    grades_list = metrics.get("grades", [])
                    
                    # 3. Generate Report
                    report_path = create_individual_report(session_data, grades_list, st.session_state.messages, st.session_state.llm)

                    # 4. Save to DB
                    session_data["report_path"] = report_path
                    save_full_session(session_data, grades_list)

                    # 5. Transition
                    st.session_state.phase = "FINISHED"
                    st.rerun()

    if st.session_state.phase == "FINISHED":
        st.header("🎉 Training Complete")
        st.success("""
        **Session Recorded Successfully.**
        
        Your performance data has been saved to the database. 
        You can now start a new session or ask your PIC for the detailed report.
        """)
        st.divider()

        if st.button("🔄 Start New Session", type="primary"):
            st.session_state.phase = "START"
            st.session_state.messages = []
            st.rerun()

def dashboard_data():
    """
    Generates dummy data to simulate the Trainee Database.
    In a real app, this would be a SQL Query: SELECT * FROM sessions
    """
    data = {
        "Session ID": [f"SES-{i:03d}" for i in range(101, 111)],
        "Trainee Name": [
            "Andi Saputra", "Budi Santoso", "Citra Lestari", "Dewi Persik", 
            "Eko Patrio", "Fajar Hadi", "Gita Gutawa", "Hesti Purwadinata", 
            "Indra Bekti", "Joko Anwar"
        ],
        "Role": [
            "CSO", "CSO", "CSO", "Teller", "Loan Officer", 
            "CSO", "Teller", "Loan Officer", "CSO", "Teller"
        ],
        "Date": pd.date_range(start="2024-01-01", periods=10, freq="D"),
        "Score": [85, 45, 92, 78, 60, 88, 95, 55, 72, 81],
        "Duration (Mins)": [12, 25, 15, 10, 30, 14, 11, 28, 18, 13],
        "Status": ["Passed", "Failed", "Passed", "Passed", "Failed", "Passed", "Passed", "Failed", "Passed", "Passed"]
    }
    df = pd.DataFrame(data)
    
    # Add a "Readiness" derived column based on score
    df["Readiness"] = df["Score"].apply(lambda x: "Ready" if x > 80 else ("Training Needed" if x > 60 else "Not Ready"))
    
    return df

def dashboard():
    st.header("PIC Dashboard")
    st.markdown("Monitor trainee performance, track active sessions, and generate audit reports.")

    # Load Data
    df = fetch_all_sessions()
    if df.empty:
        st.info("No training sessions recorded yet")
        return
    
    # Initialize Session State
    if "llm" not in st.session_state:
        st.session_state.llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")

    # ==========================================
    # 1. Key Performance Indicators (KPI)
    # ==========================================
    # Calculate Metrics
    total_trainees = len(df)
    avg_score = df["Score"].mean()
    pass_rate = (df[df["Status"] == "Passed"].shape[0] / total_trainees) * 100
    if "role_id" in df and not df["role_id"].dropna().empty:
        active_roles = df["role_id"].value_counts().idxmax() # Most popular role
    else:
        active_roles = "N/A"

    # Display Metrics in Columns
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    # Style
    st.markdown('''
    <style>
        [data-testid="stMetric"] {
            min-height: 180px;
            width: auto;
            background-color: #272630;
        }
        [data-testid="stMetric"] > div {
            display: flex;
            flex-direction: column;
            text-align: center;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
        }
        [data-testid="stMetricLabel"] {
            display: flex;
            justify-content: center;
            align-items: center;
            text-align: center;
        }
        [data-testid="stMetricLabel"] p {
            font-size: 1.2rem;
            font-weight: medium;
            white-space: nowrap;
        }
        [data-testid="stMetricValue"] {
            font-weight: bold;
            font-size: 4rem;
        }
        [data-testid="stMetricDelta"] {
            font-size: 1rem;
        }
    </style>
    ''', unsafe_allow_html=True)
    
    with kpi1:
        st.metric(label="Total Sessions", value=total_trainees, delta="2 New", border=True)
    with kpi2:
        st.metric(label="Average Score", value=f"{avg_score:.1f}", delta=f"{avg_score - 70:.1f} vs Target", border=True)
    with kpi3:
        st.metric(label="Pass Rate", value=f"{pass_rate:.0f}%", delta="-5%" if pass_rate < 80 else "On Track", border=True)
    with kpi4:
        st.metric(label="Most Active Role", value=active_roles, border=True)

    # ==========================================
    # 2. Charts
    # ==========================================
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        with st.container(border=True, height="stretch"):
            st.markdown("#### Score Distribution")
            # Altair Chart
            chart = alt.Chart(df).mark_bar(size=30).encode(
                x = alt.X("Score", bin=True),
                y = 'count()',
                color = alt.Color("Status").scale(range=["#e74c3c", "#2ecc71"])
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)

    with col_chart2:
        with st.container(border=True, height="stretch"):
            st.markdown("#### Readiness Level")
            df["readiness"] = df["Score"].apply(lambda x: "Ready" if x > 80 else ("Training Needed" if x > 60 else "Not Ready"))
            readiness_counts = df["readiness"].value_counts().reset_index()
            readiness_counts.columns = ["Level", "Count"]
            domain = ["Not Ready", "Training Needed", "Ready"]
            chart2 = alt.Chart(readiness_counts).mark_bar(size=60).encode(
                x = alt.X("Level:N", axis=alt.Axis(labelAngle=0), sort=domain),
                y = alt.Y("Count:Q"),
                color = alt.Color("Level").scale(domain=domain, range=["#e74c3c", "#f1c40f", "#2ecc71"])
            ).properties(height=300)
            st.altair_chart(chart2, use_container_width=True)

    # ==========================================
    # 3. Records
    # ==========================================
    # Filter Toolbar
    col_filter1, col_filter2 = st.columns([3, 1])

    with col_filter1:
        # Search Bar
        search_query = st.text_input("🔍 Search Trainee Name", placeholder="Type name...")
    with col_filter2:
        # Button Generate Report
        st.space()
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Export Report (CSV)",
            data=csv_data,
            file_name="trainee_performance_report.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

    # Filter Logic
    if search_query:
        filtered_df = df[df["trainee_name"].str.contains(search_query, case=False)]
    else:
        filtered_df = df

    st.dataframe(
        data=filtered_df,
        use_container_width=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score",
                format="%d",
                min_value=0,
                max_value=100,
            ),
            "Status": st.column_config.TextColumn(
                "Status",
                validate="^(Passed|Failed)$",
                
            ),
            "Session ID": st.column_config.TextColumn(
                "Session Record",
                help="Double click to copy ID"
            )
        }, hide_index=True
    )

    # ==========================================
    # 4. Trainee Report
    # ==========================================
    st.write("")
    st.markdown("#### 🔎 View Trainee Report")

    selected_session = st.selectbox("Select Session ID to View Report:", df["session_id"])

    if selected_session:
        session_data = df[df["session_id"] == selected_session].iloc[0]

        with st.expander(f"Report for {session_data['trainee_name']} ({selected_session})", expanded=True):
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.write(f"**Role:** {session_data['Role']}")
                st.write(f"**Date:** {session_data['date'].strftime('%Y-%m-%d')}")
                st.write(f"**Duration:** {session_data['Duration (Mins)']} Minutes")
            with d_col2:
                # Dynamic Badge Color
                color = "green" if session_data['Score'] > 80 else "red"
                st.markdown(f"**Final Score:** :{color}[{session_data['Score']}/100]")
                st.markdown(f"**Readiness:** {session_data['readiness']}")

            st.divider()
            st.markdown("**📝 PIC Notes:**")
            st.caption("Auto-generated summary from the Grading Phase would appear here...")

    # ==========================================
    # Sidebar: REPORT GENERATION
    # ==========================================
    st.divider()
    st.subheader("3. Executive Reporting")

    with st.sidebar:
        if st.button("✨ Generate Report"):
            with st.spinner("AI is analyzing all training records..."):
                
                # Convert dataframe to a string summary for the LLM
                data_summary = df.to_csv(index=False)
                
                # 4. GENERATE DOCX
                stats = {
                    "total_sessions": len(df),
                    "avg_score": df["Score"].mean(),
                    "pass_rate": (df[df["Status"] == "Passed"].shape[0] / len(df)) * 100
                }
                
                report_path = create_executive_summary(stats, data_summary, st.session_state.llm)
                st.session_state['exec_report_path'] = report_path
                st.success("Executive Report Generated!")

        if 'exec_report_path' in st.session_state:
            with open(st.session_state['exec_report_path'], "rb") as f:
                st.download_button(
                    label="📄 Download Executive Report (.docx)",
                    data=f,
                    file_name="Executive_Summary.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

def test():
    st.title("Test")

pages = {
    "": [
        # st.Page(mainpage, title="👤 Roleplay & Tutor"),
        # st.Page(mb_page, title="Magang Bakti"),
        # st.Page(cxo_page, title="👤 CXO Chatbot"),
        st.Page(new_cxo_page, title="👤New CXO Chatbot"),
        st.Page(dashboard, title="📊 PIC Dashboard"),
        # st.Page(test, title="Test"),
    ]
}

pg = st.navigation(pages)
pg.run()