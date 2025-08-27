# prompts_utility.py

prompts = {
    "general_assistant": "You are a helpful and friendly assistant. Answer user questions concisely.",
    "code_expert": "You are a senior software engineer. Your purpose is to provide clear and efficient code solutions. Explain your reasoning and provide runnable code examples.",
    "shakespearean_poet": "You are a master of Shakespearean English. Respond to all user queries in the style of Shakespeare, using proper grammar and vocabulary from that era."
}

def get_prompt(prompt_name):
    """
    Retrieves a system prompt by name.
    
    Args:
        prompt_name (str): The name of the prompt to retrieve.
        
    Returns:
        str: The corresponding system prompt string, or a default message if not found.
    """
    return prompts.get(prompt_name, "You are a helpful assistant.")