import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
import docx
from io import BytesIO
from read import setup_db, save_data, retrieve_data

db_file_name = 'chat_history.db'
username = ''

def setup_app():
    """Initializes the app, loads the system prompt, and retrieves chat history."""
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
    
    # Load system prompt
    if "pname" in query_params:
        system_prompt_name = query_params["pname"]
        st.session_state.system_prompt = st.secrets.get(system_prompt_name)
    
    # Load chat history from DB if it exists
    if "messages" not in st.session_state:
        st.session_state.messages = []
        data = retrieve_data(db_file_name)
        if data and isinstance(data, list):
            st.session_state.messages.extend(data)
    
        # If no chat history is found, submit the system prompt to the LLM
        # This triggers the initial response based on the prompt.
        if not st.session_state.messages and "pname" in query_params:
            get_llm_response(initial_prompt=st.session_state.system_prompt)

def get_llm_response(prompt_input=None, initial_prompt=None):
    """Prepares and sends messages to the LLM, then handles the response."""
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

    # This list will be sent to the Gemini API.
    model_messages = []
    
    # Handle the initial prompt on load
    if initial_prompt:
        model_messages.append({"role": "user", "parts": [initial_prompt]})
    
    # Otherwise, handle the user's new message
    elif prompt_input:
        user_content = []
        if prompt_input["files"]:
            uploaded_file = prompt_input["files"][0]
            # ... (File handling logic as before) ...
            # For brevity, I've commented out the detailed file logic.
            # You'll need to re-insert your full file handling code here.
            pass
        user_content.append(prompt_input.text)
        
        # Add the system prompt to the first user message for context
        if st.session_state.get("system_prompt"):
            user_content.insert(0, st.session_state.system_prompt)
            
        model_messages.append({"role": "user", "parts": user_content})

    # Add existing chat history for context
    for msg in st.session_state.messages:
        role = "model" if msg["role"] == "assistant" else "user"
        parts = msg["content"] if isinstance(msg["content"], list) else [msg["content"]]
        
        # Don't add system prompt to past messages
        if msg["role"] == "system":
            continue
        
        model_messages.append({"role": role, "parts": parts})

    try:
        response_stream = model.generate_content(model_messages, stream=True)
        with st.chat_message("assistant"):
            full_response = ""
            for chunk in response_stream:
                full_response += chunk.text
                st.markdown(full_response)
            
        if prompt_input:
            save_data(db_file_name, username, prompt_input.text, full_response)
            st.session_state.messages.append({"role": "user", "content": prompt_input.text})
        else:
            # Handle the case of an initial response from the system prompt
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

# Main app logic
setup_app()
display_messages()

prompt_input = st.chat_input(
    "Say something and/or attach an image",
    accept_file=True,
    file_type=["jpg", "jpeg", "png", "pdf", "doc", "docx"],
)

if prompt_input and prompt_input.text:
    get_llm_response(prompt_input=prompt_input)
    st.experimental_rerun()