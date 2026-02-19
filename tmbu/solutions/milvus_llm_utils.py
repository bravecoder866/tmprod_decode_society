"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying,    distribution,    or modification of this software is strictly prohibited.
"""

import os
import re
import json
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from pymilvus import MilvusClient
from pymilvus import connections, db, Collection, CollectionSchema, FieldSchema, DataType
from .milvus_connection_utils import ensure_milvus_connection, ensure_connection
from django.conf import settings
from dotenv import load_dotenv
from openai import OpenAI
from openai import OpenAIError
from django.utils.translation import get_language

 


# Load environment variables from .env file
load_dotenv()


# Initialize the SentenceTransformer model (for embeddings) and Hugging Face Transformers model (for summarization, comparing and advising)
# embedding_model =  SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

embedding_model =  SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")


# Generate embeddings from any texts using SentenceTransformer
def generate_embeddings(text):
    
    # Single or batch input
    
    if isinstance(text, str):
        text = [text]
    elif not isinstance(text, list):
        raise ValueError("Input must be a string or a list of strings.")

    embeddings = embedding_model.encode(text).tolist()  # Generate embeddings from texts
    
    # Validate embedding dimension
    for i, embedding in enumerate(embeddings):
        if not isinstance(embedding, list):
            raise ValueError(f"Embedding {i} is not a list")
        if len(embedding) != 384:
            raise ValueError(f"Embedding dimension mismatch: expected 384, got {len(embeddings)}")
        if not all(isinstance(x, float) for x in embedding):
            raise ValueError(f"Embedding {i} contains non-float elements")

    return embeddings



# Open-source LLMs
#elements_model = pipeline("text-generation", model="EleutherAI/gpt-neo-2.7B")
#summarization_model = pipeline("summarization", model="facebook/bart-large-cnn")
#factors_model = pipeline("text-generation", model="EleutherAI/gpt-neo-2.7B")
#solution_model = pipeline("text-generation", model="EleutherAI/gpt-neo-2.7B")


# Clean the formats of LLM output
def clean_llm_output(output):
    # Remove Markdown headings (e.g., ###)
    output = re.sub(r"^###\s*", "", output, flags=re.MULTILINE)
    # Remove bold formatting (e.g., **text**)
    output = re.sub(r"\*\*(.*?)\*\*", r"\1", output)
    # Remove list markers (e.g., "- ")
    output = re.sub(r"^- ", "", output, flags=re.MULTILINE)
    return output.strip()


# Set the OpenAI API and key globally
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


# OpenAI Model
def call_openai(messages, model="gpt-4o-mini-2024-07-18", temperature=0.1, max_tokens=600, output_language=None):
    try:
        # Get user's preferred language from Django settings
        detected_language = output_language or get_language() or "en"  # Default to English if not set

        # More precise system instruction
        system_instruction = f"Please respond in {detected_language}."

        # Append system message to enforce response language
        messages.insert(0, {
            "role": "system",
            "content": [{"type": "text", "text": system_instruction}]
        })

    
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,  # Controls randomness in responses
            max_tokens=max_tokens,  # Limits response length
        )

        # Get the raw content from the OpenAI API response
        raw_output = response.choices[0].message.content
        
        # Clean the output before returning
        cleaned_output = clean_llm_output(raw_output)
        return cleaned_output
    
    except OpenAIError as e:
        print(f"OpenAI API error: {e}")
        return None


def call_openai_output_json_string(messages, model="gpt-4o-mini-2024-07-18", temperature=0.1, max_tokens=3000, output_language=None):
    try:
        # Get user's preferred language from Django settings
        detected_language = output_language or get_language() or "en"  # Default to English if not set

        # More precise system instruction
        system_instruction = f"Please respond in {detected_language}."

        # Append system message to enforce response language
        messages.insert(0, {
            "role": "system",   
            "content": [{"type": "text", "text": system_instruction}]
        })

    
        response = openai_client.chat.completions.create(
            model=model,   
            messages=messages,   
            temperature=temperature, # Controls randomness in responses
            response_format={"type": "json_object"},   
            max_tokens=max_tokens, # Limits response length
        )

        # Get the raw content from the OpenAI API response
        output_json_string = response.choices[0].message.content
        
        # --- Parse into dict ---
        parsed_output = json.loads(output_json_string)
        
        return parsed_output

    except OpenAIError as e:
        print(f"OpenAI API error {e}")
        return None

    except json.JSONDecodeError as e:
        print(f"JSON parsing error {e}. Raw output {output_json_string}")
        return None


def generate_element_advice(scenario_input):
    
        messages=[
            
            {"role": "system", 
            
            "content": [
                {
                    "type": "text",
                    "text": (
                            f"""
                            You are a helpful assistant. Your tone is always sympathetic, friendly, neutral and professional. 
                            You will be given a scenario input that may describe a goal, a situation, or mixed.  A goal is something that the user wants to achieve, while a situation is a challenge that the user is facing. It may be a mix of both because sometimes a user wants to achieve certain goals while dealing with a challenge.
                            
                            Your task is to use the following predefined related scenario elements in advising what additional information the user should add in the user scenario input to make it reasonably accurate, detailed and comprehensive, if the user scenario input lacks any related scenario elements substantially. What are the related scenario elements depend on whether the user scenario input is only related to a goal or a situation, or a mix of both.
                            Do not include any of these predefined scenario elements verbatim in your advice to the user.
                            
                            Scenario Elements only related to a goal:
                            - Specific description of the goal
                            - Actions already taken by the user related to the goal

                            Scenario Elements only related to a situation:
                            - Specific description of the situation, including what happened, the nature and characteristics of the situation
                            - Responses and actions already taken by the user about the situation
                            - Expected result after resolving the situation
                            - Motivation to achieve the goal or resolve the situation

                            Scenario Elements related to either of a goal or situation
                            - People, organizations, families, communities or other entities, their characteristics, their feelings, thoughts, attitude and positions, who are involved in achieving the goal, or in the situation itself and resolving the situation.
                            - The user's thoughts and feelings about the goal, or the situation.
                            - Impact of achieving the goal or of resolving the situation on the user, the involved people, organizations, families, communities or other entities.
                            - Available conditions and resources for achieving the goal, or resolving the situation.
                            - Missing conditions and resources, and actions necessary to acquire them, for achieving the goal, or resolving the situation.
                            - Obstacles, and actions necessary to overcome them, in achieving the goal or resolving the situation.
                            - Degree of strength of the user's intention to take the actions to achieve the goal, or resolve the situation.
                            - Chance of success to achieve the goal, or to resolve the situation.
                            - Possible reactions of the involved people, organizations, families, communities or other entities upon the user's actions. 
                            - Responses of the user to the possible reactions of the involved people, organizations, families, communities or other entities.
                                
                            Write your advice in this format: start by praising user's effort and briefly summarizing the user input in one sentence. Then provide detailed advice in bullet points, each in a separate paragraph. Leave one line space between paragraphs. Here is an example:
                            1. [Point description]
                            2. [Point description]
                            3. [Point description]
                            Do not use Markdown-style formatting. Do not use bold, italics, or any special formatting characters like `**`, `*`, `#`, `-`, or `_`.
                            """    
                    )
                }
              ]
            },

            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"This is the scenario input: '{scenario_input}'."
                    }
                ]
            }
        ]

        scenario_element_advice = call_openai(messages)
        return scenario_element_advice


# Convert Python Dict to Python List (keep both keys and values) of Strings for embedding and vector search
def flatten_dicts_to_strings(data: list[dict]) -> list[str]:
    
    bullet_points = []

    for item in data:
        # Create a list of "key: value" strings for the current dictionary
        item_parts = []
        for key, value in item.items():
            if value is None:
                continue  # skip empty fields

            # Convert non-string values to strings
            value_str = str(value).strip()

            # Skip empty strings
            if not value_str:
                continue

            # Format as a key-value pair
            item_parts.append(f"{key}: {value_str}")

        # Join all parts of the current dictionary into a single string
        if item_parts:
            # Using a space, newline, or a specific separator (e.g., "; ") works well for embeddings
            combined_string = "; ".join(item_parts) 

            bullet_points.append(combined_string)

    return bullet_points




# For OpenAI model
def generate_summary_bullet_points(scenario_input):
     
        messages=[
            {
                "role": "system", 
            
                "content": [
                    {
                        "type": "text",
                        "text":(
                                "You are a helpful assistant.\n\n" # for English-only embedding model, add this: Please always respond in English.
                                "You will be given a scenario input. Your task is to summarize the scenario input in a list of bullet points, with each point separated clearly by a line break."
                        )
                    }
                ] 
            },

            {
                "role": "user",
                "content":[
                    {
                        "type": "text",
                        "text": f"This is the scenario input: '{scenario_input}'."
                    }
                ]
            }        
        ]
        
        try:
            summary = call_openai(messages) # For English-only embedding model, add this as input: output_language="en"
            if not summary:
                raise ValueError("OpenAI returned an empty summary.")
        except Exception as e:
            raise RuntimeError(f"Failed to call OpenAI: {e}")
    
        # split the summary into bullet points by splitting on line breaks or custom markers
        bullet_points = summary.split("\n")  # Split by line breaks to create a list
    
        # Remove empty strings in case there are extra line breaks
        bullet_points = [point.strip() for point in bullet_points if point.strip()]
    
        return bullet_points  # Return a list of bullet points


# Perform a search on Milvus based on an embedding (e.g., for a user_input_query)
@ensure_connection
def search_relevant_factors_in_milvus(bullet_points, milvus_client=None):
    if milvus_client is None:
        raise ConnectionError("Milvus client not provided by decorator.") # Should not happen if decorator works 

    #milvus_client = ensure_milvus_connection()

    # Prepare the formatted output
    relevant_factors = []

    # Load Milvus collection and set search parameters
    # milvus_client.load_collection("kb_embeddings_collection") #for both development and production
    
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    
    for index, bullet_point in enumerate(bullet_points, start=1):
        # Add the bullet point to the formatted output
        relevant_factors.append(f"{index}. {bullet_point}")

        if bullet_point.strip().lower().startswith("me:") and bullet_point.strip()[3:].strip() == "":
            # (The [3:] skips "Me:" and checks if anything is left)
            relevant_factors.append("  No relevant factors found.")
            continue
        elif bullet_point.strip().startswith("我:") and bullet_point.strip[2:].strip() == "":
            relevant_factors.append("  No relevant factors found.")
            continue

        
        # Generate embedding for the bullet point (query)
        bullet_point_embeddings = generate_embeddings([bullet_point])  # Single query embedding
    
        results = milvus_client.search(
            collection_name="kb_embeddings_collection",
            data=bullet_point_embeddings,
            anns_field="factor_vector",
            search_params=search_params,
            limit=1,  # Return top 3 similar vectors
            output_fields=["factor_text"]
        )
    
        # Extract the top-k "factor_text" results
        if results and results[0]:
            relevant_factors.append("  Relevant Factors:")
            for factor_index, result in enumerate(results[0], start=1):
                factor_text = result.get("factor_text")
                if factor_text:
                    relevant_factors.append(f"     {factor_index}. {factor_text}")
        else:
            relevant_factors.append("  No relevant factors found.")
            
        # Join the formatted data into a single string
    return "\n".join(relevant_factors)



# For OpenAI model
def generate_factor_advice(scenario_input):

        
        bullet_points = generate_summary_bullet_points(scenario_input)
        if not bullet_points:
            raise ValueError("Failed to generate summary bullet points for the scenario input.")
        
        relevant_factors = search_relevant_factors_in_milvus(bullet_points)
    
        messages=[
            
            {
                "role": "system", 
                "content":[ 
                    {
                        "type": "text",
                        "text": (
                                "You are a helpful advisor. Your tone is always sympathetic, friendly, neutral and professional.\n\n"
                                "You will be given a scenario input and the relevant factors. Use the scenario input and the relevant factors as your **primary source of information**.\n\n"
                                "Your task is to use the relevant factors to find out the most important factors that must be considered in an effective solution for dealing with the situation or achieving the goal described in the scenario input.\n\n"
                                
                                "Do not copy the relevant factors verbatim. Paraphrase and synthesize the ideas naturally.\n\n"
                                "Do not include any previously generated summary bullet points.\n\n"
                                "Only use your own general knowledge when it is necessary.\n\n"

                                "Write your output in this format: start by praising user's effort and briefly summarizing the user input in one sentence. Then provide detailed advice in bullet points, each in a separate paragraph. Leave one line space between paragraphs. Here is an example:\n\n"
                                "1. [Point description]\n\n"
                                "2. [Point description]\n\n"
                                "3. [Point description]\n\n"
                                "Do not use Markdown-style formatting. Do not use bold, italics, or any special formatting characters like `**`, `*`, `#`, `-`, or `_`.\n\n"
                        )
                    }
                ]
            },
            
            {
                "role": "user", 
                "content":[
                    {
                        "type": "text",
                        "text": (
                                f"This is scenario input: '{scenario_input}'.\n\n"
                                f"These are the relevant factors: '{relevant_factors}'"
                        )                                
                    }
                ]
            }
        ]

        scenario_factor_advice = call_openai(messages)
        return scenario_factor_advice


# for OpenAI model
def generate_solution_advice (scenario_solution_input):
    

        messages=[
            {
                "role": "system", 
                "content": [
                    {
                        "type": "text",
                        "text": (
                                "You are a helpful advisor. Your tone is sympathetic, friendly, neutral and professional.\n\n"
                                "You will be given a proposed solution. Please advise what are the most effective strategies and tactics for executing the solution successfully.\n\n"  

                                "Do not include the previously generated summary bullet points and the searched relevant factors verbatim in your advice to the user.\n\n"
                                "Write your advice in this format: start by praising user's effort and briefly summarizing the user input in one sentence. Then provide detailed advice in bullet points, each in a separate paragraph. Leave one line space between paragraphs. Here is an example:\n\n"
                                "1. [Point description]\n\n"
                                "2. [Point description]\n\n"
                                "3. [Point description]\n\n"
                                "Do not use Markdown-style formatting. Do not use bold, italics, or any special formatting characters like `**`, `*`, `#`, `-`, or `_`.\n"
                        )                    
                    }
                ]
            },
                
            {
                "role": "user",
                "content":[
                    {
                        "type": "text",
                        "text": f"This is the proposed solution: '{scenario_solution_input}'."  
                    }           
                ]
            }
        ]

        scenario_solution_advice=call_openai(messages)
        return scenario_solution_advice


def generate_quick_solution(scenario_input):

        
        bullet_points = generate_summary_bullet_points(scenario_input)
        if not bullet_points:
            raise ValueError("Failed to generate summary bullet points for the scenario input.")
        
        relevant_factors = search_relevant_factors_in_milvus(bullet_points)
    
        messages=[
            
            {
                "role": "system", 
                "content":[ 
                    {
                        "type": "text",
                        "text": (
                                f"""
                                You are a helpful assistant who can provide quick and practical solutions to deal with a situation or achieving a goal. 
                                
                                Your tone is always sympathetic, friendly, neutral and professional.
                                You will be given the relevant factors and the scenario input. Use this as your **primary source of information**.
                                Your task is to use the relevant factors to provide short and practical solutions related to the situation or goal described in the scenario input.
                                If there are more than one solution, please compare the pros and cons of all the solutions briefly and suggest the best solution.
                                                              
                                Do not copy the relevant factors verbatim. Paraphrase and synthesize the ideas naturally.
                                Do not include any previously generated summary bullet points.
                                Only use your own general knowledge if the relevant factors do not address a point clearly.

                                Write your output in this format: start by briefly summarizing the scenario input in one sentence. Then provide the solutions, each in a separate paragraph. Each paragraph may have a few bullet points. Leave one line space between paragraphs.
                                Do not use Markdown-style formatting. Do not use bold, italics, or any special formatting characters like `**`, `*`, `#`, `-`, or `_`.
                                """
                        )
                    }                    
                ]
            },
            
            {
                "role": "user", 
                "content":[
                    {
                        "type": "text",
                        "text": (
                                f"These are the relevant factors: '{relevant_factors}'.\n\n"
                                f"This is the scenario input: '{scenario_input}'.\n\n"                               
                        )
                    }
                ]
            }
        ]

        scenario_quick_solution = call_openai(messages)
        return scenario_quick_solution



# For OpenAI model
def extract_info_from_scenario(scenario_input):
     
        messages=[
            {
                "role": "system",    
            
                "content": [
                    {
                        "type": "text",   
                        "text":(
                              f"""
                              You are a helpful assistant.
                              You are given a scenario input.
                              Your task is to extract structured information from the given scenario input and return **strict JSON only** (no explanations, no text outside JSON).
                              
                              Use the scenario input as your **only source of information**.
                             
                              Use consistent names for actors across all sections.

                              1. actors
                       
                                Rules:
                                - Extract all distinctive actors who are individual actors or group actors. Do not extract any entity which is not an individual actor or group actor. An individual actor is an individual person. A group actor is an organization or a community of people.
                                - If the same actor appears multiple times, include them only once.
                                - The name of any actor must be their formal, official or legal name. The alias of any actor must be their alternative names (for example: “Bob” is an alias for “Robert.”; “Johnny” is an alias for “John.”; “CIA” is an alias for “Central Intelligence Agency.”). Alias must not be any indivdiual actor's job title, profession, feature or social role etc. or any group actor's type, industry, feature or reputation etc.
                                - If any actor has only one name or alias, Set each actor's "name_or_alias" to their name or alias. 
                                - If any actor has both a name and an alias or multiple names and aliases, combine them into a single string as their "name_or_alias" in this format: "Formal Name (Alias1, Alias2, ...)". 
                                - Do not extract any person who has no name or alias and is only referred to by pronouns such as "we", "us", "she", "her", "he", "him", "they", "them" or "it" etc..                                                   
                                - Do not extract any person, people, group or groups who have no name or alias and are only referred to by general or vague references such as a category or feature description(for example: "employee", "employees", "management", "customers", "software engineer", "accountants", "automakers", "electronics industry", "friends", "neighbors", "passionate technologist" etc.).
                                - Do not invent any name or alias.
                                - Exception: if the scenario input clearly mentions the person who is submitting it by their name, alias, pronouns or other references, extract the person as an individiual actor and always set this individual actor's "name_or_alias" exclusively to "Me". Do not keep any of this individual actor's names, aliases or other references. There is only one such individual actor across all scenario inputs. 

                                Fields:        
                                - actor_ref_id: add one unique identifier for each actor. Form it as A1, A2, … .Use this exact ID in "individual_traits", "group_traits", "interactions" and "interaction_relations" to refer back to this section. 
                                - name_or_alias: the name of each actor. 
                                - actor_type: either "individual" or "group". "individual" if it is a individual actor, "group" if it is a group actor.
                                                                                              

                              2. individual_traits
                                    
                                Rules:
                                - Extract traits of each individual actor.
                                - Only for individual actors.
                                                         
                                Fields:
                                - actor: the actor_ref_id (e.g. A1, A2, …) of the individual actor who have these traits.
                                - cognitive_pattern: patterns and characteristics of perception, learning, thoughts, decision-making and bias.
                                - affect_pattern: patterns and characteristics of feelings, mood, emotion.
                                - action_pattern: patterns and characteristics of actions.
                                - personality: characteristics and relatively stable pattern of thoughts, feelings, and behaviors that make a person unique. It encompasses how an individual perceives the world, adapts to their environment, and interacts with others. Include personality disorder and psychological disorder, if there is any.
                                - beliefs_values: things or ideas accepted to be true or real including religious beliefs; things or ideas considered to be important such as hard-working, caring, successs or integrity etc.
                                - priorities: motivation, need, desire, goal, objective.
                                - life_style: way of life, including habits, interests and hobbies.
                                - identity: associated groups, self-perceived and socially-perceived identity.
                                - capabilities:  analytical, creative, practical intelligence; emotional intelligence; social skills in communication, listening, leadership, change catalyst, conflict resolution, relationship building, collaboration and cooperation, team building, political skills etc.; merits, talents and expertises
                                - family: family type, structure and characteristics.
                                - marriage_intimate_relationship: marriage or intimate partner relationship type and characteristics.
                                - education: both formal and informal education experience and level.
                                - occupation_job_industry: occupation, job title, job responsibility, related line of work or industry.
                                - social_economic_status: social and economic hirachical level in their society.
                                - social_network: personal connections with other people or groups that can be leveraged and used as social resources, including relationship status with other connnected people and groups.
                                - biological_characteristics: race, ethnicity, age, sex, gender, health, facial and body features etc.
                                
                              
                              3. group_traits
                                
                                Rules:
                                - Extract traits of each group actor.
                                - Only for group actors.
                                
                                Fields:
                                - actor: the actor_ref_id (e.g., A1, A2, …) of the group actor who have these traits.
                                - group_type: the category of a group based on various criteria such as its activities, legal entity registration, nature, function etc. 
                                - size: the number of staff, geographic coverage, revenue, market value or other metrics corresponding to the type of a group.
                                - mission_vision_value: what a group does, what a group wants to become and the guiding principles for the group's beahvior and culture.
                                - goal_strategy: the long-term and mide-term goals of a group and how the group plans to achieve them.
                                - objectives_plan: short-term objectives of a group and how the group plans to achieve them.
                                - governance:  how a group is governed, including governance structure, process and characteristics.
                                - organizational_structure: how a group is organized.  
                                - operation_system: how an group operates, including its policies, processes and practices.
                                - organizational_politics: who has what authority and decision-making power; who are alliances or adversaries.
                                - influence: the importance, power and influence of a group in its field or industry, and beyond.
                                - leadership: the working style, characteristics, capabilities of the leaders and managers of a group.
                                - culture: the shared behavior norms that define a group's environment and guide how group members work and interact with each other and the external world.
                                - performance: the metrics to measure the success of a group, for example, profitability and growth for business organizations, economy growth and social prosperity for government agencies, influence for a non-profit organization, members satisfaction for any group etc.
                                - challenge: the obstacles or adverse force for a group to succeed or achieve its goal.
                                - funding_resources_budget: how a group gets its funding and resources, and sets budget; how a group allocates its funding and resources.
                                
                            
                              4. interactions   
                              
                                Rules:
                                - Extract all distinct behaviors that each actor performs in the scenario input.                          
                                - A distinct behavior is a meaningful unit of thought, feeling, mood, emotion, speech, expression or other actions that can stand alone. 
                                - Assign a unique sequential behavior_id ("B1", "B2", ...) to each distinct behavior in order of appearance. Use this ID in "interaction_relations" to refer back to this section. 
                                
                                Fields:
                                - behavior_id: sequential unique identifier ("B1", "B2", …). 
                                - actor: the actor_ref_id (e.g. A1, A2, …) of the actor who performs this behavior.
                                - behavior_description: a short but precise description of an actor's distinctive behavior.
                                - env: environments surrounding the behavior, includimg time, location, social, economic, political conditions etc.
                                                 

                             5. interaction_relations

                                Rules:
                                - Among all extracted behaviors, if one behavior responds or references to another behavior, these two behaviors are related. The behavior that resonds or references is the source behavior. The behavior that is responded or referenced to is the target behavior.
                                - Find all pairs of the source behavior and target behavior.
                                - Provide a relation description with key details and meaningful insights about the characteristics, patterns and key details of how the source behaivor and the target behavior relates to each other.
                                - Based on the relation description, provide a related actors relationship status description with key details and meaningful insights about the characteristis, patterns and key details of the relationship between the actors who perform the source behavior and target behavior, focusing on the social relationship and the personal relationship between the actors. Social relationship is the relationship in their social roles at work, family and community. Personal relationship is the relationship in their capacity as private persons. Social relationship and personal relationship are often intertwined.
                             
                               
                               Fields:                                
                                - source: the behavior_id of the behavior that responds or references. This is source behavior.
                                - target: the behavior_id of the behavior being responded to or referenced to. This is target behavior.
                                - relation_description: the characteristics, patterns and key details of how the source behaivor and the target behavior relate to each other.
                                - related_actors: list of actor_ref_id values (A1, A2, …) of actors who perform the target behavior and the source behavior.
                                - related_actors_relationship_status: characteristics, patterns and key details of the relationship between all related actors.
                                                                                                                       
                            Return JSON in this format

                            {{
                            "actors": [...],   
                            "individual_traits": [...],   
                            "group_traits": [...],   
                            "interactions": [...],   
                            "interaction_relations": [...]   
                            }}
                            """                           
                        )
                    }
                ]
            },   
            
            {
                "role": "user",    
                "content":[
                    {
                        "type": "text",   
                        "text": (
                                f"This is scenario input '{scenario_input}'.\n\n"
                        )                                
                    }
                ]
            }
        ]
        
        try:
            extracted_info = call_openai_output_json_string(messages) #raw output string. Need to parse for saving in certain model fields

            if not extracted_info:
                 raise ValueError("OpenAI returned an empty response.")

            return extracted_info

        except Exception as e:
             raise RuntimeError(f"Failed to extract info {e}")


        
def aggregate_individual_traits(existing_profiles, new_traits):
    
    existing_profiles_str = (
        json.dumps(existing_profiles, indent=2) if existing_profiles else "None"
    )

    new_traits_str = json.dumps(new_traits, indent=2)

    messages=[
            {
                "role": "system",    
                "content":[ 
                    {
                        "type": "text",   
                        "text": (
                               f"""
                                You are given:
                                1. the existing profiles of individual actors. Each profile uniquely represents one individual actor.
                                2. the new traits of individual actors.
                                
                                Use them as your **only source of information**.
                                 
                                Your task is: 
                                1. First, identify if the new traits include any individual actor who is the same as any individual actor in the existing profiles or introduce any new individual actor.
                                2. Then, add any new information from the new traits to the existing profiles.

                                Rules: 
                                1. If the new traits include any individual actor who is the same as any individual actor in the existing profile, even if their names or aliases may be different:
                                    - Compare the new traits with this same individual actor's existing profile, then, add any new information from the new traits to the existing profile and resolve any conflicts, if there are any. If the new traits have no new information or are empty, do not make any change to the existing profile.
                                    - Copy the existing profile's "individual_profile_id" to the output "individual_profile_id" field. 
                                    - Copy the existing profile's "canonical_name" to the "old_canonical_name".
                                    - If the existing profile's "canonical_name" remains appropriate, copy it to the "new_canonical_name".
                                    - If a more formal single identifier is discovered from the "name_or_alias" in the new traits (e.g. "John" -> "John Smith"), set "new_canonical_name" to that identifier.  
                                    - Either "old_canonical_name" or "new_canonical_name" must be a single and clear identifier for the individual actor.  
                                    - Set "aliases" to include the new canonical name, the old canonical name (if different from the new canonical name) and all names or aliases from the existing profile's "aliases" and the new traits's "name_or_alias".
                                    - The "aliases" must always be a JSON array of strings. Each string must be a full name or alias such as ['John Smith', 'John', 'Mr. Smith']. Do not split any word into individual letters such as ["J","o","h","n"]. 
                                    - Exception Rule: if the individual actor's "name_or_alias" from the new traits is "Me", always set the "new_canonical_name" exclusively to "Me", always set the "old_canonical_name" exclusively to "Me", and always set "aliases" exclusively to "Me".                    

                                                                
                                2. If the new traits introduce a new individual actor who is not present in the existing profiles, even if the new individual actor shares the same name or alias with any individual actor in the existing profiles: 
                                    - Add all traits from the new traits for this new individual actor.                             
                                    - set "individual_profile_id" to null.
                                    - Select a new canonical name, using a formal name if possible, based on the "name_or_alias" in the new traits. Set "new_canonical_name" to this new canonical name.
                                    - The "new_canonical_name" must be a single and clear identifier for the new individual actor. 
                                    - If the selected "new_canonical_name" is identical to any existing canonical name for a different individual actor in the existing profiles, you must append a unique, descriptive qualifier in brackets to the "new_canonical_name" to distinguish them. This qualifier should be based on available context (e.g., profession, job title, social role, location or associated group etc.) 
                                    - Set "old_canonical_name" to null.
                                    - Set "aliases" to include the new canonical name and all other names or aliases from the new traits's "name_or_alias".
                                    - The "aliases" must always be a JSON array of strings. Each string must be a full name or alias such as ['John Smith', 'John', 'Mr. Smith']. Do not split any word into individual letters such as ["J","o","h","n"]. 
                                    - Exception Rule: if the new individual actor's "name_or_alias" from the new traits is "Me", always set the "new_canonical_name" exclusively to "Me", and always set "aliases" exclusively to "Me".                    
                                               

                                Output JSON as:
                                {{
                                "updates": [
                                    {{
                                    "individual_profile_id": "integer or null",
                                    "old_canonical_name": "string or null",
                                    "new_canonical_name": "string",
                                    "aliases": "JSON array of strings.",
                                    "cognitive_pattern": "string or null",
                                    "affect_pattern": "string or null",
                                    "action_pattern": "string or null",
                                    "personality": "string or null",
                                    "beliefs_values": "string or null",
                                    "priorities": "string or null",
                                    "life_style": "string or null",
                                    "identity": "string or null",
                                    "capabilities": "string or null",
                                    "family": "string or null",
                                    "marriage_intimate_relationship": "string or null",
                                    "education": "string or null",
                                    "occupation_job_industry": "string or null",
                                    "social_economic_status": "string or null",
                                    "social_network": "string or null",
                                    "biological_characteristics": "string or null"
                                    }}
                                ]
                                }}
                                """
                        )        
                    }                                        
                ]
            },   
            
            {
                "role": "user",    
                "content":[
                    {
                        "type": "text",   
                        "text": (
                                f"""
                                the existing profiles: {existing_profiles_str}                             
                                the new traits: {new_traits_str}                           
                                """
                        )                                                            
                    }
                ]
            }
        ]


   
    llm_output = call_openai_output_json_string(messages)
    return llm_output


def aggregate_group_traits(existing_profiles, new_traits):
    
    existing_profiles_str = (
        json.dumps(existing_profiles, indent=2) if existing_profiles else "None"
    )

    new_traits_str = json.dumps(new_traits, indent=2)

    messages=[
            {
                "role": "system",    
                "content":[ 
                    {
                        "type": "text",   
                        "text": (
                               f"""
                                You are given:
                                1. the existing profiles of group actors. Each profile uniquely represents one group actor.
                                2. the new traits of group actors.
                                
                                Use them as your **only source of information**.
                                 
                                Your task is:
                                1. First, identify if the new traits include any group actor who is the same as any group actor in the existing profiles or introduces any new group actor.
                                2. Then, add any new information from the new traits to the existing profiles.

                                Rules:
                                1. If the new traits include any group actor who is the same as any group actor in the existing profile, even if their names may be different:
                                    - Compare the new traits with this same group actor's existing profile, then, add any new information from the new traits to the existing profile and resolve any conflicts, if there are any. If the new traits have no new information or are empty, do not make any change to the existing profile.
                                    - Copy the existing profile's "group_profile_id" to the output "group_profile_id" field.
                                    - Copy the existing profile's "canonical_name" to the "old_canonical_name".
                                    - If the existing profile's "canonical_name" remains appropriate, copy it to "new_canonical_name".
                                    - If a more formal single identifier is discovered from the name_or_alias in the new traits, set "new_canonical_name" to that identifier.            
                                    - The "old_canonical_name" or "new_canonical_name" must be a single and clear identifier for the group actor.  
                                    - Set "aliases" to include the new canonical name, the old canonical name (if different from the new canonical name), all other names from the existing profile's aliases and the new traits's name_or_alias.
                                    - The "aliases" must always be a JSON array of strings. Each string must be a full name of the group actor. Do not split any word into individual letters.


                                2. If the new traits introduce a new group actor not present in the existing profiles, even if the new group actor shares the same name or alias with any group actor in the existing profiles: 
                                    - Add all traits from the new traits for that new group actor.
                                    - Set "group_profile_id" to null.                             
                                    - Select a new canonical name, using a formal name if possible, based on the "name_or_alias" in the new traits. Set "new_canonical_name" to this new canonical name.
                                    - The "new_canonical_name" must be a single and clear identifier for the new group actor. 
                                    - If the selected "new_canonical_name" is identical to any existing canonical name for a different group actor in the existing profiles, you must append a unique, descriptive qualifier in brackets to the "new_canonical_name" to distinguish them. This qualifier should be based on available context (e.g., industry, location or associated group etc.) 
                                       
                                    - Set "old_canonical_name" to null.                                  
                                    - Set "aliases" to include the new canonical name and all other names from the new traits's name_or_alias.
                                    - The "aliases" must always be a JSON array of strings. Each string must be a full name. Do not split any word into individual letters.
                                  
       
                                Output JSON as:
                                {{
                                "updates": [
                                    {{
                                    "group_profile_id": "integer or null",
                                    "old_canonical_name": "string or null",
                                    "new_canonical_name": "string",
                                    "aliases": "JSON array of strings.",
                                    "group_type": "string or null",    
                                    "domain": "string or null",  
                                    "size": "string or null",  
                                    "mission_vision_value": "string or null",   
                                    "goal_strategy": "string or null",    
                                    "objectives_plan": "string or null",     
                                    "governance": "string or null",   
                                    "organizational_structure": "string or null", 
                                    "operation_system": "string or null",
                                    "organizational_politics": "string or null",  
                                    "influence": "string or null",
                                    "leadership": "string or null",
                                    "culture": "string or null",  
                                    "performance": "string or null",
                                    "challenge": "string or null",   
                                    "funding_resources_budget": "string or null" 
                                    }}
                                ]
                                }}
                                """
                        )        
                    }                                        
                ]
            },   
            
            {
                "role": "user",    
                "content":[
                    {
                        "type": "text",   
                        "text": (
                                f"""
                                existing profiles: {existing_profiles_str}                             
                                new traits: {new_traits_str}                           
                                """
                        )                                                            
                    }
                ]
            }
        ]

  
    llm_output = call_openai_output_json_string(messages)
    return llm_output




def generate_scenario_actors(combined_data):

    bullet_points = (
            flatten_dicts_to_strings(combined_data["individual_traits"]) + 
            flatten_dicts_to_strings(combined_data["group_traits"])
    )
    
    if not bullet_points:
        return "No information available."
    
   
    relevant_factors = search_relevant_factors_in_milvus(bullet_points)
    
    messages=[
            {
                "role": "system", 
                "content":[ 
                    {
                        "type": "text",
                        "text": (
                                f"""
                                You are a helpful assistant. Your tone is always neutral and professional.
                                You will receive the relevant factors.
                                Use them as your **primary source of information**.
                                            
                                Your task is to generate free-text description of traits of:                            
                                - The individual actor whose "individual_name_or_alias" is "Me" in the relevant factors. Maximumly there is only one such individual actor. If no name "Me" exists, return "No information available".
                                - Any other individual actors by their name in "individual_name_or_alias" in the relevant factors.
                                - Any group actor by their name in "group_name_or_alias" in the relevant factors.

                                Rules:
                                - Summarize and describe each actor's traits clearly and concisely.
                                - Do not invent unsupported details.
                                - If information is missing, say "No information available.".
                                - Output must be free text only (no JSON, no Markdown, no bullet points).
                                - Do not copy sentences verbatim from the relevant factors.
                                - Do not use Markdown-style formatting. Do not use bold, italics, or any special formatting characters like `**`, `*`, `#`, `-`, or `_`.          
                             
                                Output must strictly follow this exact format:
                                
                                Me: [description of their traits]
                                
                                People
                                
                                [individual actor1]: [description of their traits]

                                [individual actor2]: [description of their traits]
                                
                                Group
                                
                                [group actor1]: [description of their traits]

                                [group actor2]: [description of their traits]
                                
                                This is an example:

                                Me: enters the story as an outsider from the Midwest who moves to New York to learn the bond business. Lives in West Egg near Gatsby and becomes a quiet observer of the wealthy elite, including Gatsby, Daisy, and Tom. Values honesty and modesty, and throughout the story, becomes disillusioned by the superficiality, carelessness, and moral decay of the wealthy.
                                
                                People
                                
                                Jay Gatsby: The mysterious and wealthy neighbor of Nick, known for his lavish parties and boundless optimism. He is driven by an idealistic dream to reunite with Daisy Buchanan, whom he once loved. Gatsby represents the romantic pursuit of the American Dream, but his idealism is revealed to be unrealistic and fragile.
                                
                                Daisy Buchanan: The former lover Gatsby, now married to Tom Buchanan. She lives a life of privilege and emotional passivity. Although Gatsby builds his dream around rekindling their love, Daisy ultimately chooses comfort and social status over passion. Her inability to act decisively and her complicity in the events leading to Gatsby’s downfall highlight her superficial and careless nature.
                                
                                Group

                                The Wealthy Elite East Coast Society: This unnamed social community includes characters like Daisy and Tom and represents the careless, privileged class of East Coast society. Obsessed with status and appearances, they exploit and discard people like Gatsby. Nick’s disgust with this group leads him to abandon the East and reject the hollow values they represent.                                                               
                                """
                       )        
                    }                                        
                ]
            },
            
            {
                "role": "user", 
                "content":[
                    {
                        "type": "text",
                        "text": (
                                f"These are the relevant factors: '{relevant_factors}'.\n\n"                                     
                        )                                                            
                    }
                ]
            }
        ]

    llm_output = call_openai(messages)
    return llm_output


def generate_scenario_dynamics(combined_data):
    
    bullet_points = (
            flatten_dicts_to_strings(combined_data["interactions"]) +
            flatten_dicts_to_strings(combined_data["interaction_relations"])       
    )

    if not bullet_points:
        return "No information available."
        # raise ValueError("Failed to generate summary bullet points.")
        
    relevant_factors = search_relevant_factors_in_milvus(bullet_points)
    

    messages=[
            {
                "role": "system", 
                "content":[ 
                    {
                        "type": "text",
                        "text": (
                                f"""
                                You are a helpful assistant. Your tone is always neutral and professional.
                                You will receive the relevant factors about interaction relations between actors from a scenario.
                                Use it as your **primary source of information**.

                                "Your task is:
                             
                                - summarize all of the interactions.
                                - compare the status of power between all actors in all interactions. 
                                - describe the change of power of each actor in all interactions.
                                - describe the strategy and tactics of each actor using in their interactions.

                                Rules:
                            
                                - Only use their name in "name_or_alias" in the relevant factors to refer to each actor. Do not use any other references, such as "(actor 16)" or "(actor 222)" etc..
                                - Do not invent unsupported details.
                                - If information is missing, say so.
                                - Output must be free text only, no JSON.
                                - Do not copy anything verbatim.
                                - Rely on the provided data.
                                - Do not use Markdown-style formatting. Do not use bold, italics, or any special formatting characters like `**`, `*`, `#`, `-`, or `_`.           
                                
                                Write your output in this format: in bullet points, each in a separate paragraph. Leave one line space between paragraphs. Here is an example:
                                 1. [Point description]
                                 2. [Point description]
                                 3. [Point description]
                                 """
                        )        
                    }                                        
                ]
            },
            
            {
                "role": "user", 
                "content":[
                    {
                        "type": "text",
                        "text": (
                                f"These are the relevant factors: '{relevant_factors}'"     
                        )                                                            
                    }
                ]
            }
        ]

    llm_output = call_openai(messages)
    return llm_output



def generate_scenario_needs(combined_data):

    bullet_points = (
            flatten_dicts_to_strings(combined_data["individual_traits"]) + 
            flatten_dicts_to_strings(combined_data["group_traits"]) +
            flatten_dicts_to_strings(combined_data["interaction_relations"])       
    )
    
    if not bullet_points:
        return "No information available."

    #if not bullet_points:
    #    raise ValueError("Failed to generate summary bullet points.")
        
    relevant_factors = search_relevant_factors_in_milvus(bullet_points)
    
    messages=[
            {
                "role": "system", 
                "content":[ 
                    {
                        "type": "text",
                        "text": (
                                f"""
                                You are a helpful assistant. Your tone is always neutral and professional.
                                You will receive relevant factors.
                                Use it as your **primary source of information**.

                                Your task is:
                             
                                - describe the specific, short-term needs, expectations and wants of each actor, including but not limited to psychological, physiological or emotional needs.
                                - describe the motivations of each actor. 
                                - analyze the long-term, deep-down needs of each actor, including but not limited to psychological, physiological or emotional needs.
                                - analyze what are the prioritized needs, expectation, wants or motivations for each actor, and any conflicts between those priorities if there is any.
                                - analyze the gap between current conditions and the required conditions neccessary for each actor to get their needs satisfied with.

                                Rules:                            
                                - Do not invent unsupported details.
                                - If information is missing, say so.
                                - Output must be free text only, no JSON.
                                - Do not copy anything verbatim.
                                - Rely on the provided data.
                                - Do not use Markdown-style formatting. Do not use bold, italics, or any special formatting characters like `**`, `*`, `#`, `-`, or `_`          
                                
                                Write your output in this format: in bullet points, each in a separate paragraph. Leave one line space between paragraphs. Here is an example:
                                 1. [Point description]
                                 2. [Point description]
                                 3. [Point description]
                                 """
                        )        
                    }                                        
                ]
            },
            
            {
                "role": "user", 
                "content":[
                    {
                        "type": "text",
                        "text": (
                                f"These are the relevant factors: '{relevant_factors}'"         
                        )                                                            
                    }
                ]
            }
        ]

    llm_output = call_openai(messages)
    return llm_output


def generate_scenario_skills_resources(combined_data):

    bullet_points = (
            flatten_dicts_to_strings(combined_data["individual_traits"]) + 
            flatten_dicts_to_strings(combined_data["group_traits"]) +
            flatten_dicts_to_strings(combined_data["interaction_relations"])       
    )

    if not bullet_points:
        return "No information available."

    #if not bullet_points:
    #    raise ValueError("Failed to generate summary bullet points.")
        
    relevant_factors = search_relevant_factors_in_milvus(bullet_points)
    

    messages=[
            {
                "role": "system", 
                "content":[ 
                    {
                        "type": "text",
                        "text": (
                            f"""
                                You are a helpful assistant. Your tone is always neutral and professional.
                                You will receive the relevant factors.
                                Use it as your **primary source of information**.
                                

                                Your task is:
                             
                                - describe the skills of each actor, including their knowledge, expertise, intelligence, capabilities, talents etc..
                                - describe the resources of each actor, including their social status, economic status, social network etc. 
                                - compare the skills and resources of all actors.
                                - analyze the gap between their current skills/resources and the required skills/resources neccessary for each actor to get their needs satisfied with.

                                Rules:
                                - Do not invent unsupported details.
                                - If information is missing, say so.
                                - Output must be free text only, no JSON.
                                - Do not copy anything verbatim.
                                - Rely on the provided data.
                                - Do not use Markdown-style formatting. Do not use bold, italics, or any special formatting characters like `**`, `*`, `#`, `-`, or `_`.          
                                
                                Write your output in this format: in bullet points, each in a separate paragraph. Leave one line space between paragraphs. Here is an example:
                                 1. [Point description]
                                 2. [Point description]
                                 3. [Point description]
                                 """
                        )        
                    }                                        
                ]
            },
            
            {
                "role": "user", 
                "content":[
                    {
                        "type": "text",
                        "text": (
                                f"These are the relevant factors: '{relevant_factors}'"
                        )                                                            
                    }
                ]
            }
        ]


    llm_output = call_openai(messages)
    return llm_output


def generate_analysis_prediction(scenario_input):

    bullet_points = generate_summary_bullet_points(scenario_input)
    
    if not bullet_points:
        return "No information available."
    
    #if not bullet_points:
    #    raise ValueError("Failed to generate summary bullet points for the scenario input.")
    
    relevant_factors = search_relevant_factors_in_milvus(bullet_points)

    messages=[
        
        {
            "role": "system", 
            "content":[ 
                {
                    "type": "text",
                    "text": (
                            f"""
                            You are an analyst who can think deep and comprehensively. Your tone is always friendly, neutral, and professional.
                            You will be given the relevant factors and the scenario input. Use this as your **primary source of information**.
                                                    
                            Your task is to use the relevant factors to generate an analysis about the scenario input, and then predict how each actor will behave and how the scenario will develop in near and far future.

                            Do not copy the relevant factors verbatim. Paraphrase and synthesize the ideas naturally.
                            Do not include any previously generated summary bullet points.
                            Only use your own general knowledge when it is necessary.

                            Write your analysis in this format: start by briefly summarizing the user input in one sentence. Then provide detailed analysis in bullet points, each in a separate paragraph. Leave one line space between paragraphs. Here is an example:
                            1. [Point description]
                            2. [Point description]
                            3. [Point description]
                            Do not use Markdown-style formatting. Do not use bold, italics, or any special formatting characters like `**`, `*`, `#`, `-`, or `_`.
                            """
                    )
                },                    
            ]
        },
        
        {
            "role": "user", 
            "content":[
                {
                    "type": "text",
                    "text": (
                            f"These are the relevant factors: '{relevant_factors}'.\n\n"
                            f"This is the scenario_input: '{scenario_input}'.\n\n"
                    )
                }
            ]
        }
    ]

    llm_output = call_openai(messages)
    return llm_output


def generate_global_actors_profiles(combined_data):

        
        bullet_points = (
            flatten_dicts_to_strings(combined_data["individual_profiles"]) + 
            flatten_dicts_to_strings(combined_data["group_profiles"])                  
        )
        
        if not bullet_points:
            raise ValueError("Failed to get information from the combined data.")
        
        relevant_factors = search_relevant_factors_in_milvus(bullet_points)

        # Convert bullet_points list to a single string where each original bullet point is on a new line.
        # bullet_points_string = "\n".join(bullet_points)

        messages=[
            {
                "role": "system", 
                "content":[ 
                    {
                        "type": "text",
                        "text": (
                                f"""
                                You are a helpful assistant. Your tone is always neutral and professional.
                                You will be given the relevant factors. Use them as your **only source of information**.
                                
                                Your task is to extract the "canonical_name" and the "traits" of all actors. You must extract all actors and assign each actor to exactly one of three categories: "Self", "People", and "Group".  

                                 - If there is the individual actor whose "canonical_name" is "Me", place this individal actor in "Self". Maximumly there is only one such individual actor in "Self". If no such actor exists, "Self" must be an empty list: [].     
                                 - Place all individual actors in "People", excluding the individual actor identified in "Self". If there is no individual actor in "People", "People" must be an empty list: [].
                                 - Place all group actors in "Group". If there is no group actor, "Group" must be an empty list: [].

                                 
                                Rules:
                                 - The three categories are completely independent. The presence or absence of actors in "Self" does not affect whether actors appear in "People" or "Group", and vice versa.
                                 - If an actor's "traits" field is empty, use an empty string: "traits": "". 


                                Output JSON strictly in this format:

                                {{
                                "Self": [
                                    {{
                                    "canonical_name": "...",
                                    "traits": "..."
                                    }}
                                ], 
                                "People": [
                                    {{
                                    "canonical_name": "...",
                                    "traits": "..."
                                    }}
                                ],
                                "Group": [
                                    {{
                                    "canonical_name": "...",
                                    "traits": "..."
                                    }}
                                ]
                                }} 
                                """
                            )        
                        }                                        
                    ]
                },
                
                {
                    "role": "user", 
                    "content":[
                        {
                            "type": "text",
                            "text": (
                                    f"These are relevant factors:'{relevant_factors}'\n\n"                                   
                            )     
                        }
                    ]
                }
            ]

        llm_output = call_openai_output_json_string(messages)
        return llm_output
            


def summarize_relationship_status(filtered_map: dict) -> dict:
    
    if not filtered_map:
        return {}

    # Build input text for the LLM
    pairs_text = []
    for (actor1, actor2), status in filtered_map.items():
        actor1, actor2 = sorted([actor1, actor2])
        status_str = ", ".join(status) if status else "None"
        pairs_text.append(f"- {actor1} ↔ {actor2}: {status_str}")
    
    pairs_input = "\n".join(pairs_text)
      
    messages=[
            {
                "role": "system", 
                "content":[ 
                    {
                        "type": "text",
                        "text": (
                                f"""
                                You are given actor pairs and their relationship status.                                
                                Use it as your **only source of information**.

                                Task:
                                - Analyze and summarize the characteristics and patterns of the relationship between the actors. 
                                - Cover both social relationship and personal relationship between the actors. Social relationship is the relationship in their social roles at work, family and community. Personal relationship is the relationship in their capacity as private persons. Social relationship and personal relationship are often intertwined.
                                - The summary must include key details and meaningful insights.
                             
                                Return your output strictly as JSON with this format:
                                {{
                                  "(actor1, actor2)": "summary",
                                  "(actorX, actorY)": "summary"
                                }}
                                """                                
                            )        
                        }                                        
                    ]
                },
                
                {
                    "role": "user", 
                    "content":[
                        {
                            "type": "text",
                            "text": (
                                    f"Actor pairs and their relationship status: \n{pairs_input}"                                   
                            )                                      
                        }
                    ]
                }
            ]

    try:
        summaries = call_openai_output_json_string(messages)
        return summaries
    except Exception as e:
        print(f"LLM error while summarizing batch relations: {e}")
        return {}
    

def llm_generate_simulation(canonical_names, scenario, profiles, relations):
    """
    Generate a simulation between selected actors based on scenario, their traits, and relationships.
    Simulation may include speech, actions, thoughts, and emotions.
    """
    profiles_str = json.dumps(profiles, indent=2, ensure_ascii=False)
    relations_str = json.dumps(relations, indent=2, ensure_ascii=False)
    actor_list_str = ", ".join(canonical_names)

    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"""
                        You are a professional social interaction simulation engine.
                        You will be given:
                        1. A scenario.
                        2. Selected actors (individuals or groups).
                        3. Profiles of the selected actors.
                        4. Relationship status between the selected actors.

                        Your task: Generate a **realistic, multi-turn simulation** of how the selected actors interact in the scenario.                       
                        
                        The simulation can include:
                        - speech (dialogue)
                        - thought (internal monologue, reasoning)
                        - feeling (emotions, moods, senses)
                        - action (behaviors, expressions)

                        Use the profiles of the selected actors and relationship status of the selected actors to shape how they think, feel and act. Show nuance, tension, cooperation, or conflict.                        
                        
                        Each turn must be represented as a JSON object with the fields:
                        - actor: string (the actor's canonical name)
                        - type: one of ['speech','thought','feeling','action']
                        - content: string (the text of what they say, think, feel, or do)

                        Wrap all turns in a JSON object of the form:
                        {{ "simulation": [ {{actor, type, content}}, ... ] }}

                        Here is the required JSON format (example):
                        {{
                        "simulation": [
                            {{"actor": "Alice", "type": "speech", "content": "We must move forward."}},
                            {{"actor": "Bob", "type": "thought", "content": "She seems confident."}},
                            {{"actor": "Bob", "type": "feeling", "content": "nervous but determined"}},
                            {{"actor": "Alice", "type": "action", "content": "signs the document"}}
                        ]
                        }}
                         
                        Do not invent new actors; only use the ones provided.   
                        IMPORTANT: Limit the simulation to at most 50 turns total. 
                        A 'turn' is one contribution by any actor.
                        Stop when you reach 50 turns, even if the scenario feels unfinished.
                        """
                    )
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"""
                        Scenario:
                        {scenario}

                        Selected Actors: 
                        {actor_list_str}

                        Profiles of the selected actors:
                        {profiles_str}

                        Relationship status of the selected actors:
                        {relations_str}
                        """                        
                    )
                }
            ]
        }
    ]

    simulation = call_openai_output_json_string(messages)
    
    return simulation


def llm_generate_live_simulation(session, user_actor, user_message, history):
    """
    Call LLM to generate next responses for all non-user actors,
    given scenario, actor traits, relationships, and conversation history.
    """
     
    # --- prepare context ---
    actors = session.actors  # list of canonical names
    profiles = session.actors_profiles_snapshot
    relations = session.actors_relation_statuses_snapshot
    scenario = session.scenario

    context_block = {
        "scenario": scenario,
        "actors": actors,
        "profiles": profiles,
        "relations": relations,
        "history": history,
        "latest_user_turn": {"actor": user_actor, "message": user_message},
    }

    # --- build messages for the chat model ---
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text", 
                    "text": 
                    f"""
                    You are simulating a multi-actor scenario. 
                    The user plays one actor; you control the others. 
                    Actors have defined traits and relationships. 
                    Simulate realistic behaviors: speech, thought, feeling, or action. 

                    IMPORTANT:
                    - Always respond strictly in JSON.
                    - Do not include any explanations or commentary.
                    - Only generate turns for non-user actors (never overwrite the user’s input).
                    - The conversation must not exceed 100 total turns.
                    - If the history already approaches 100 turns, you must stop immediately.

                    Your output must follow this schema:

                    {{
                    "responses": [
                        {{
                        "actor": "ActorName",
                        "type": "speech | thought | feeling | action",
                        "content": "string"
                        }}
                    ]
                    }}
                    """                            
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text", 
                    "text": json.dumps(context_block, indent=2)
                }
            ]
        },
    ]

    
    llm_response = call_openai_output_json_string(messages)
    
    return llm_response


