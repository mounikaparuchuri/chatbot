import streamlit as st
#from openai import OpenAI
import google.generativeai as genai
from prompts_utility import get_prompt

# Show title and description.
st.title("💬 Chatbot")
st.write(
    "Find My Chapter 3 chatbot."
)

# Create an OpenAI client.
# This client is created once at the start of the app's life.
#client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# Create a session state variable to store the chat messages.
# This ensures that the messages persist across reruns.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Retrieve the query parameters from the URL.
query_params = st.query_params
if "pname" in query_params:
    systempromptname = query_params["pname"]
    system_prompt = get_prompt(systempromptname)
    st.session_state.messages = [
        {"role": "system", "content": system_prompt}
    ]

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

    # # Generate a response using the OpenAI API.
    # stream = client.chat.completions.create(
    #     model="gpt-3.5-turbo",
    #     messages=[
    #         {"role": m["role"], "content": m["content"]}
    #         for m in st.session_state.messages
    #     ],
    #     stream=True,
    # )

    # # Stream the response to the chat using `st.write_stream`, then store it in
    # # session state.
    # with st.chat_message("assistant"):
    #     response = st.write_stream(stream)
    # st.session_state.messages.append({"role": "assistant", "content": response})

    # Convert Streamlit's message format to Google's format
    # The system message is handled implicitly by adding it to the history
    model_messages = []
    for message in st.session_state.messages:
        if message["role"] == "system":
            # The system prompt is an initial instruction, not part of the conversation turn.
            # You handle this by adding the instruction to the first user message.
            # However, for a chat model, the best practice is to include it as a context setting
            # in the prompt itself, as the Gemini API doesn't have a dedicated "system" role.
            continue
        # The API requires "model" and "user" roles.
        # The assistant role from st.session_state becomes "model" for the API.
        role = "model" if message["role"] == "assistant" else "user"
        model_messages.append({"role": role, "parts": [message["content"]]})

    # The first message from the user should include the system prompt for context
    if model_messages:
        model_messages[0]["parts"] = [st.session_state.messages[0]["content"]] + model_messages[0]["parts"]

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # The Gemini API uses `generate_content` for streaming
        response_stream = model.generate_content(
            model_messages,
            stream=True
        )

        with st.chat_message("assistant"):
            full_response = ""
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    st.write(chunk.text, end="")
            st.markdown(full_response)
        
        # Add the assistant's response to the chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

    except Exception as e:
        st.error(f"An error occurred: {e}")


