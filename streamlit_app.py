import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
import docx
import pprint
from io import BytesIO
from read import setup_db, save_data, retrieve_data

# Global variables
db_file_name = 'chat_history.db'
username = ''

def setup_app():
    """Initializes the app by checking for a username, setting up the DB, and loading chat history."""
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
        st.stop()
    
    # Load system prompt from secrets
    if "pname" in query_params:
        system_prompt_name = query_params["pname"]
        st.session_state.system_prompt = st.secrets.get(system_prompt_name)

    # Initialize messages and load history if it's the first run
    if "messages" not in st.session_state:
        st.session_state.messages = retrieve_data(db_file_name) or []
        
    # If there's no chat history and a system prompt exists, send a hidden initial message
    if not st.session_state.messages and "system_prompt" in st.session_state:
        get_llm_response(initial_prompt=st.session_state.system_prompt)

def get_llm_response(user_input_content=None, initial_prompt=None):
    """Prepares and sends messages to the LLM, then handles the response."""
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    # This list will be sent to the Gemini API
    model_messages = []
    
    # Add the system prompt to the very first message for context.
    # For subsequent user messages
    user_parts = user_input_content if isinstance(user_input_content, list) else [user_input_content]
    # The Gemini API doesn't have a dedicated system role, so we prepend it to the user's message.
    if initial_prompt:
        user_parts.insert(0, [initial_prompt])


    # Add the system prompt to the current message if it exists
    model_messages.append({"role": "user", "parts": user_parts})

    # Add previous chat history for continuity
    for msg in st.session_state.messages:
        role = "model" if msg["role"] == "assistant" else "user"
        parts = msg["content"] if isinstance(msg["content"], list) else [msg["content"]]
        
        # Exclude the system prompt from the history
        if msg["role"] != "system":
            model_messages.append({"role": role, "parts": parts})
    
    try:
        response_stream = model().generate_content(model_messages, stream=True)
        
        with st.chat_message("assistant"):
            full_response = ""
            for chunk in response_stream:
                full_response += chunk.text
                st.markdown(full_response)
        
        # Save the new user message and the assistant's response
        if user_input_content:
            save_data(db_file_name, username, user_input_content, full_response)
            st.session_state.messages.append({"role": "user", "content": user_input_content})
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        else: # This branch handles the initial response from the system prompt
            st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    except Exception as e:
        st.error(f"An error occurred: {e}")

def display_messages():
    """Displays chat messages from session state, excluding the system prompt."""
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                content = message["content"]
                if isinstance(content, list):
                    text_content = next((part for part in content if isinstance(part, str)), None)
                    if text_content:
                        st.markdown(text_content)
                else:
                    st.markdown(content)
        elif message["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(message["content"])

def handle_file_uploads(uploaded_files):
    """Processes uploaded files and returns a list of content parts."""
    user_content = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_extension = uploaded_file.name.split(".")[-1].lower()
            
            if file_extension in ["jpg", "jpeg", "png"]:
                image = Image.open(uploaded_file)
                user_content.append(image)
            elif file_extension == "pdf":
                try:
                    pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.getvalue()))
                    pdf_text = "".join(p.extract_text() or "" for p in pdf_reader.pages)
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
    return user_content

# Main app logic
setup_app()
display_messages()

prompt_input = st.chat_input(
    "Say something and/or attach an image",
    accept_file=True,
    file_type=["jpg", "jpeg", "png", "pdf", "doc", "docx"],
)

if prompt_input:
    # Get user text and file content
    user_content_list = []
    if prompt_input.text:
        user_content_list.append(prompt_input.text)
    
    file_content = handle_file_uploads(prompt_input.get("files", []))
    if file_content:
        user_content_list.extend(file_content)

    # Display the user's message
    with st.chat_message("user"):
        st.markdown(prompt_input.text)
    
    # Get LLM response
    get_llm_response(user_input_content=user_content_list)
    st.rerun()