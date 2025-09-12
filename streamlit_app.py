import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
import docx
from io import BytesIO
from read import setup_db, save_data, retrieve_data

db_file_name = 'chat_history.db'
username = ''

# Retrieve the query parameters from the URL.
query_params = st.query_params
if "username" in query_params:
    username = query_params["username"]
    db_file_name = username + db_file_name
    setup_db(db_file_name)
    # Show title and description.
    st.title("💬 Chatbot")
    st.write(
        "Find My Chapter 3 chatbot."
    )
else:
    st.title("💬 Chatbot")
    st.write(
        "error occured"
    )
    st.stop

# Configure the Google Generative AI client with your API key
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# Get the system prompt from secrets.
system_prompt = ""
if "pname" in query_params:
    system_prompt_name = query_params["pname"]
    system_prompt = st.secrets[system_prompt_name]
else:
    #raise ValueError("System prompt name not provided in URL.")
    st.title("💬 Chatbot")
    st.write(
        "error occured. missing name"
    )
    st.stop

# Initialize the chat session with a system prompt when the app loads.
# This ensures a continuous chat history with the system instruction.
if "chat" not in st.session_state:
    #model = genai.GenerativeModel("gemini-1.5-pro-001")
    model = genai.GenerativeModel(model="gemini-1.5-pro-001",
    system_instructions = {
        "role": "system",
        "content": system_prompt
    })

    # Start a chat session with system instructions
    # chat_session = Chat.start_chat(messages=[system_instructions])

# # User sends a message
# user_message = {"role": "user", "content": "Can you explain what Vertex AI is?"}
# response = chat_session.send_message(user_message)

# # Print the assistant's response
# print("Assistant:", response["content"])

# # Continue the conversation
# follow_up_message = {"role": "user", "content": "How can I use it for machine learning?"}
# response = chat_session.send_message(follow_up_message)

# # Print the follow-up response
# print("Assistant:", response["content"])

    st.session_state.chat = model.start_chat(
        history=[]
    )
    # The history will be populated by retrieve_data
    db_data = retrieve_data(db_file_name)
    if db_data and isinstance(db_data, list):
        # We need to correctly load the history into the chat object.
        # The history in `start_chat` is a list of dicts with 'role' and 'parts'.
        # We assume `retrieve_data` returns data in a compatible format.
        # We need to map our saved data format to Gemini's expected format.
        # The `start_chat` method can be initialized with history.
        # So we create a new chat object with the retrieved history.
        # This is a bit of a workaround since you can't append to a live session's history.
        history_for_new_chat = []
        for msg in db_data:
            role = "model" if msg["role"] == "assistant" else "user"
            history_for_new_chat.append({"role": role, "parts": [msg["content"]]})
        
        # Re-initialize the chat session with the loaded history.
        st.session_state.chat = model.start_chat(
            history=history_for_new_chat
        )

# Create a session state variable to store the chat messages for display.
if "messages" not in st.session_state:
    st.session_state.messages = []
    # If the chat object was loaded with history from the DB, populate the display messages.
    if st.session_state.chat.history:
        for msg in st.session_state.chat.history:
            role = "assistant" if msg.role == "model" else "user"
            st.session_state.messages.append({"role": role, "content": msg.parts[0].text})
            

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

    # Use the `send_message` method on the chat object.
    # This automatically handles the history for you.
    try:
        response_stream = st.session_state.chat.send_message(
            user_content,
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