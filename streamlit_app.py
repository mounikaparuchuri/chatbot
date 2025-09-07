import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
import docx
from io import BytesIO
from read import setup_db, save_data, retrieve_data

# Show title and description.
st.title("💬 Chatbot")
st.write(
    "Find My Chapter 3 chatbot."
)
db_file_name = 'chat_history.db'
username = ''
# Retrieve the query parameters from the URL.
query_params = st.query_params
if "pname" in query_params:
    systempromptname = query_params["pname"]
    system_prompt = st.secrets[systempromptname]
    # st.session_state.messages = [
    #     {"role": "system", "content": system_prompt}
    # ]
    if not st.session_state.messages or st.session_state.messages[0]["role"] != "system":
        st.session_state.messages.insert(0, {"role": "system", "content": system_prompt})

# Retrieve the query parameters from the URL.
query_params = st.query_params
if "username" in query_params:
    username = query_params["username"]
    db_file_name = username + db_file_name
setup_db(db_file_name)

# Configure the Google Generative AI client with your API key
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# Create a session state variable to store the chat messages.
if "messages" not in st.session_state:
    data = retrieve_data(db_file_name)
    st.session_state.messages = []
    st.session_state.messages.insert(1, {"role": "user", "content": data})




# Display the existing chat messages.
for message in st.session_state.messages:
    # Google's Gemini API has a specific structure for chat history
    # We need to filter out the system message for display purposes
    if message["role"] == "user":
        with st.chat_message("user"):
            if isinstance(message["content"], list):
                # Handle multimodal content
                for part in message["content"]:
                    if isinstance(part, str):
                        st.markdown(part)
                    elif isinstance(part, Image.Image):
                        st.image(part)
            else:
                st.markdown(message["content"])
    elif message["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(message["content"])


# Create a chat input field to allow the user to enter a message.
prompt_input = st.chat_input(
    "Say something and/or attach an image",
    accept_file=True,
    file_type=["jpg", "jpeg", "png", "pdf", "doc", "docx"],
)

if prompt_input and prompt_input.text:
    # Create the user message content.
    user_content = []

    # Check for uploaded files
    if prompt_input["files"]:
        uploaded_file = prompt_input["files"][0]
        file_extension = uploaded_file.name.split(".")[-1].lower()

        # Handle images
        if file_extension in ["jpg", "jpeg", "png"]:
            image = Image.open(uploaded_file)
            user_content.append(image)
            with st.chat_message("user"):
                st.image(image)

        # Handle PDFs
        elif file_extension == "pdf":
            pdf_text = ""
            try:
                # We need to use BytesIO to read the file in-memory
                pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.getvalue()))
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text() or ""
                user_content.append(f"Content from PDF: {pdf_text}")
                with st.chat_message("user"):
                    st.success("PDF processed successfully.")
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
                user_content.append(f"Could not read PDF. Error: {e}")
                
        # Handle Word documents
        elif file_extension in ["doc", "docx"]:
            doc_text = ""
            try:
                # Streamlit's UploadedFile object is file-like.
                # docx library can read from it directly.
                doc = docx.Document(uploaded_file)
                for paragraph in doc.paragraphs:
                    doc_text += paragraph.text + " "
                user_content.append(f"Content from Word document: {doc_text}")
                with st.chat_message("user"):
                    st.success("Word document processed successfully.")
            except Exception as e:
                st.error(f"Error reading Word document: {e}")
                user_content.append(f"Could not read Word document. Error: {e}")
    
    # Add the text from the prompt.
    user_content.append(prompt_input.text)
    
    # Store and display the user message in session state.
    st.session_state.messages.append({"role": "user", "content": user_content})
    with st.chat_message("user"):
        st.markdown(prompt_input.text)
    # --- Prepare Messages for Gemini API ---
    model_messages = []
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            # The Gemini API doesn't have a "system" role, so we prepend
            # the system instruction to the first user message.
            continue

        role = "model" if msg["role"] == "assistant" else "user"
        parts = []

        if isinstance(msg["content"], list):
            for part in msg["content"]:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, Image.Image):
                    parts.append(part)
        else:
            parts.append(msg["content"])
        
        model_messages.append({"role": role, "parts": parts})
    
    # Add the system prompt to the first user message parts.
    if st.session_state.messages and st.session_state.messages[0]["role"] == "system":
        system_instruction = st.session_state.messages[0]["content"]
        if model_messages:
            model_messages[0]["parts"].insert(0, system_instruction)

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Prepare the messages for the Gemini API call.
        # This part requires careful formatting for multimodal input.
        model_messages = []
        for msg in st.session_state.messages:
            role = "model" if msg["role"] == "assistant" else "user"
            
            # The API's 'parts' list can contain both text and images.
            parts = []
            if isinstance(msg["content"], list):
                for part in msg["content"]:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, Image.Image):
                        parts.append(part)
            else:
                # Handle simple text messages.
                parts.append(msg["content"])
            
            model_messages.append({"role": role, "parts": parts})
        for msgStr in model_messages:    
            print("model_messages " + {msgStr}) 
        # # The system prompt is an initial instruction and not part of the conversation turn.
        # # You handle this by adding the instruction to the first user message.
        # if model_messages and st.session_state.messages[0]["role"] == "system":
        #     system_instruction = st.session_state.messages[0]["content"]
        #     model_messages[0]["parts"] = [system_instruction] + model_messages[0]["parts"]
            
        # The Gemini API uses `generate_content` for streaming.
        response_stream = model.generate_content(
            model_messages,
            stream=True
        )

        with st.chat_message("assistant"):
            full_response = ""
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    # st.write(chunk.text, end="")
            st.markdown(full_response)
            save_data(db_file_name, username, prompt_input.text, full_response)
        
        # Add the assistant's response to the chat history.
        st.session_state.messages.append({"role": "assistant", "content": full_response})

    except Exception as e:
        st.error(f"An error occurred: {e}")