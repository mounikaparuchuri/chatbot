import streamlit as st
from openai import OpenAI

# Show title and description.
st.title("💬 Chatbot")
st.write(
    "This is a simple chatbot that uses OpenAI's GPT-3.5 model to generate responses. "
)

# Create an OpenAI client.
# This client is created once at the start of the app's life.
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Retrieve the query parameters from the URL.
query_params = st.query_params
if "pname" in query_params:
    promptname = query_params["pname"]

# Create a session state variable to store the chat messages.
# This ensures that the messages persist across reruns.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the existing chat messages.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a chat input field to allow the user to enter a message.
# This will display automatically at the bottom of the page.

prompt = st.chat_input(
    "Say something and/or attach an image",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if prompt and prompt.text:
    # Store and display the current prompt as a user message.
    if prompt and prompt["files"]:
        st.image(prompt["files"][0])
        print("received file")
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt.text)
        # st.markdown(prompt.text)

    # Generate a response using the OpenAI API.
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ],
        stream=True,
    )

    # Stream the response to the chat using `st.write_stream`, then store it in
    # session state.
    with st.chat_message("assistant"):
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})


