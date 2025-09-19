from google import genai
from google.genai import types
from google.genai.types import (
    CreateBatchJobConfig,
    CreateCachedContentConfig,
    EmbedContentConfig,
    FunctionDeclaration,
    GenerateContentConfig,
    HarmBlockThreshold,
    HarmCategory,
    Part,
    SafetySetting,
    Tool,
)
import streamlit as st
import base64
import os

def generate(prompt):
  
  print(prompt)
  client = genai.Client(
      api_key=st.secrets["GEMINI_API_KEY"],
  )


  model = "gemini-2.0-flash-lite-001"
  contents = [
    types.Content(
      role="user",
      parts=[{"text": "write me a hello world python function"}]
    )
  ]

  system_instruction = """
        You are an expert software developer and a helpful coding assistant.
        You are able to generate high-quality code in any programming language.
        """

  generate_content_config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 8192,
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
  )

#   for chunk in client.models.generate_content_stream(
#     model = model,
#     contents = contents,
#     config = generate_content_config,
#     ):
#     print(chunk.text, end="")
  chat = client.chats.create(model = model, config = generate_content_config,)
#   prompt = st.chat_input("Enter your question here")
  st.session_state.message = []
  if prompt:
    with st.chat_message("user"):
        st.write(prompt)

    st.session_state.message += prompt
    with st.chat_message(
        "model", avatar="🧞‍♀️",
    ):
        response = chat.send_message(st.session_state.message)
        st.markdown(response.text) 
        st.sidebar.markdown(response.usage_metadata)
    st.session_state.message += response.text

generate("write me a hello world python function")