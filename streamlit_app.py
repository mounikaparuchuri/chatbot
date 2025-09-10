import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
import docx
from io import BytesIO
from read import setup_db, save_data, retrieve_data

db_file_name = 'chat_history.db'
username = ''

def initialize_app():
    """Initializes the app by checking for a username and setting up the DB."""
    global username, db_file_name
    query_params = st.query_params
    if "username" in query_params:
        username = query_params["username"]
        db_file_name = f"{username}_chat_history.db"
        setup_db(db_file_name)
        st.title("💬 Chatbot")
        st.write("Find My Chapter 3 chatbot.")
    else:
        st.title("💬 Chatbot")
        st.write("Error occurred: 'username' parameter is missing.")
        st.stop()  # Stop the app if username is not provided

def load_system_prompt():
    """Loads the system prompt from secrets and sets it in session state."""
    if "system_prompt_loaded" not in st.session_state:
        query_params = st.query_params
        if "pname" in query_params:
            system_prompt_name = query_params["pname"]
            st.session_state.system_prompt = st.secrets.get(system_prompt_name)
            st.session_state.system_prompt_loaded = True

def load_user_chat_history():
    """Loads user-specific chat history from the database on app load."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
        data = retrieve_data(db_file_name)
        if data and isinstance(data, list):
            st.session_state.messages.extend(data)

def display_messages():
    """Displays chat messages from session state, excluding the system prompt."""
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                content = message["content"]
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, str):
                            st.markdown(part)
                        elif isinstance(part, Image.Image):
                            st.image(part)
                else:
                    st.markdown(content)
        elif message["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(message["content"])

def handle_user_input(prompt_input):
    """Processes user's prompt and file uploads."""
    user_content = []
    
    # Handle files first
    if prompt_input["files"]:
        uploaded_file = prompt_input["files"][0]
        file_extension = uploaded_file.name.split(".")[-1].lower()

        if file_extension in ["jpg", "jpeg", "png"]:
            image = Image.open(uploaded_file)
            user_content.append(image)
        elif file_extension == "pdf":
            try:
                pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.getvalue()))
                pdf_text = "".join(page.extract_text() or "" for page in pdf_reader.pages)
                user_content.append(f"Content from PDF: {pdf_text}")
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
                user_content.append(f"Could not read PDF. Error: {e}")
        elif file_extension in ["doc", "docx"]:
            try:
                doc = docx.Document(uploaded_file)
                doc_text = " ".join(p.text for p in doc.paragraphs)
                user_content.append(f"Content from Word document: {doc_text}")
            except Exception as e:
                st.error(f"Error reading Word document: {e}")
                user_content.append(f"Could not read Word document. Error: {e}")
    
    user_content.append(prompt_input.text)
    
    st.session_state.messages.append({"role": "user", "content": user_content})

def get_llm_response():
    """Prepares and sends messages to the LLM, then handles the response."""
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Prepare messages for the Gemini API call
    model_messages = []
    
    # Prepend the system prompt to the first user message
    system_instruction = st.session_state.get("system_prompt", "")
    if system_instruction:
        first_user_message = next((msg for msg in st.session_state.messages if msg["role"] == "user"), None)
        if first_user_message:
            content_list = first_user_message["content"]
            if not isinstance(content_list, list):
                content_list = [content_list]
            content_list.insert(0, system_instruction)
    
    # Format all messages for the API call
    for msg in st.session_state.messages:
        role = "model" if msg["role"] == "assistant" else "user"
        
        parts = []
        content = msg["content"]
        if isinstance(content, list):
            parts.extend(content)
        else:
            parts.append(content)
        
        model_messages.append({"role": role, "parts": parts})
    
    try:
        response_stream = model.generate_content(model_messages, stream=True)
        with st.chat_message("assistant"):
            full_response = ""
            for chunk in response_stream:
                full_response += chunk.text
            st.markdown(full_response)
            save_data(db_file_name, username, st.session_state.messages[-1]["content"][-1], full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Main app logic
initialize_app()
load_system_prompt()
load_user_chat_history()
display_messages()

prompt_input = st.chat_input(
    "Say something and/or attach an image",
    accept_file=True,
    file_type=["jpg", "jpeg", "png", "pdf", "doc", "docx"],
)

if prompt_input and prompt_input.text:
    handle_user_input(prompt_input)
    display_messages()  # Display the user's message
    get_llm_response()