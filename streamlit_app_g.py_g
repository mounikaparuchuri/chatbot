# app.py

import streamlit as st
import google.generativeai as genai

# --- Streamlit Application ---

st.title("Gemini Conversational Chatbot")
st.caption("A simple chatbot built with Streamlit and Google Gemini.")

# --- Google Gemini API Setup ---
# Use Streamlit's built-in secrets management to retrieve the API key.
# You must set this in your Streamlit Cloud app's secrets.
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# Initialize the generative model with a chat session for conversational memory.
model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')

# st.session_state is used to store and persist data across app reruns.
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Customization for Squarespace Integration ---
# Retrieve the query parameters from the URL.
query_params = st.query_params

# Check if the 'user' parameter exists in the URL.
if "user" in query_params:
    username = query_params["user"]
    st.write(f"Hello, {username}! This chatbot is now embedded in your Squarespace member site.")
else:
    st.write("Hello, guest! Please log in to your Squarespace member site to see your personalized content.")

st.write("---")

# Display chat messages from history on app rerun.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input.
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history.
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container.
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container.
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Prepare the history for the API call, converting the 'assistant' role to 'model'.
            history = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in st.session_state.messages]
            # Call the Gemini API with the full conversation history.
            response = model.generate_content(history)
            st.markdown(response.text)
    # Add assistant response to chat history.
    st.session_state.messages.append({"role": "assistant", "content": response.text})
