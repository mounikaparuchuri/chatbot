# prompts_utility.py
import streamlit as st

def get_prompt(prompt_name):
    """
    Retrieves a system prompt by name.
    
    Args:
        prompt_name (str): The name of the prompt to retrieve.
        
    Returns:
        str: The corresponding system prompt string, or a default message if not found.
    """
    prompts = st.secrets["prompts"]
    return prompts.get(prompt_name, "You are a helpful assistant.")