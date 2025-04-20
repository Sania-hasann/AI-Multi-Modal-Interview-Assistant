import os
import configparser

# Load configuration files
subdomain_config = configparser.ConfigParser()
subdomain_config.read('subdomain_config.ini')

hallucination_config = configparser.ConfigParser()
hallucination_config.read('hallucination_handling_config.ini')

# Function to load subdomain configuration
def load_domain_config(subdomain_file):
    config = configparser.ConfigParser()
    config.read(os.path.join("domains", subdomain_file))

    if "Details" not in config or "Prompt" not in config:
        raise KeyError(f"Missing 'Details' or 'Prompt' section in {subdomain_file}")

    domain_details = {
        "difficulty_level": config["Details"].get("difficulty_level", ""),
        "question_types": config["Details"].get("question_types", "general"),
        "hallucination_handling": config["Details"].get("hallucination_handling", ""),
        "llm_guidance": config["Details"].get("llm_guidance", ""),
    }
    
    # Load question distribution percentages
    question_distribution = {}
    if "QuestionDistribution" in config:
        for key in config["QuestionDistribution"]:
            question_distribution[key] = int(config["QuestionDistribution"][key])

    intro_prompt = config["Prompt"].get("intro_prompt", "")
    #first_question = config["Prompt"].get("first_question", "")
    
    # Load topics for each question type
    topics = {}
    if "Topics" in config:
        for key in config["Topics"]:
            topics[key] = config["Topics"][key]

    return domain_details, intro_prompt, question_distribution, topics

# Get subdomains
def get_subdomains():
    return subdomain_config['Subdomains']['subdomains'].split(', ')

# Function to get hallucination handling text
def get_hallucination_handling():
    return hallucination_config['HallucinationHandling']['hallucination_handling']