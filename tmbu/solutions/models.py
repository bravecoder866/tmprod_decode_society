"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



# Create your models here.
import os
import re
import logging
from django.db import models
from django.conf import settings  # For dynamic user model import
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, get_language
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import User
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError

def validate_word_count(value):
    lang = get_language()  # Get the current language from Django

    if lang == "zh-hans":  # Check if the active language is Simplified Chinese
        char_count = len(re.sub(r'\s+', '', value))  # Remove spaces & count characters
        min_chars = 50
        max_chars = 2500  # Set limits for Chinese

        if char_count < min_chars:
            raise ValidationError(
                _("您的输入必须至少包含 %(min_chars)s 个字符。目前，已输入 %(char_count)s 个字符。"),
                params={'min_chars': min_chars, 'char_count': char_count}  
            )
                   
        if char_count > max_chars:
            raise ValidationError(
                _("您的输入不得超过 %(max_chars)s 个字符。目前，已输入 %(char_count)s 个字符。"),
            params={'max_chars': max_chars, 'char_count': char_count}  
            )
            

    if lang == "en":

        words = value.split()
        word_count = len(words)
        min_words = 50  # Minimum number of words
        max_words = 2500  # Maximum number of words

        if word_count < min_words:
            raise ValidationError(
                _("Your input must contain at least {min_words} words. Currently, it has {word_count} words.").format(
                    min_words=min_words, word_count=word_count
                )
            )

        if word_count > max_words:
            raise ValidationError(
                _("Your input must contain no more than {max_words} words. Currently, it has {word_count} words.").format(
                    max_words=max_words, word_count=word_count
                )
            )



class ScenarioForMining(models.Model):
    scenario_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    scenario_input = models.TextField(validators=[validate_word_count])  
    scenario_input_time = models.DateTimeField(default=timezone.now)  
    scenario_form_submission_count = models.IntegerField(default=0)
    scenario_submitted = models.BooleanField(default=False) 

    def __str__(self):
        return f'Scenario {self.scenario_id} by {self.user.username}'


# class ScenarioLink(models.Model):
#     source = models.ForeignKey("ScenarioForMining", on_delete=models.CASCADE, related_name="outgoing_links")
#     target = models.ForeignKey("ScenarioForMining", on_delete=models.CASCADE, related_name="incoming_links")

#     relation_type = models.CharField(
#         max_length=50,
#         choices=[
#             ("same_event", "Same Event"),
#             ("continuation", "Continuation"),
#             ("consequence", "Consequence"),
#             ("related", "Related")
#         ],
#         default="related"
#     )
#     confidence = models.FloatField(default=0.0)
#     description = models.TextField(blank=True, null=True)



class Actors(models.Model):
    INDIVIDUAL = "individual"
    GROUP = "group"
    TYPE_CHOICES = [(INDIVIDUAL, "Individual"), (GROUP, "Group"),]
    actor_id = models.AutoField(primary_key=True) 
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(ScenarioForMining, on_delete=models.CASCADE, related_name="actors")
    name_or_alias = models.CharField(max_length=255)
    actor_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=INDIVIDUAL)
    

    def get_traits(self):
        """Return the correct traits object (IndividualTraits or GroupTraits)."""
        if self.actor_type == self.INDIVIDUAL:
            return getattr(self, "individual_traits", None)
        elif self.actor_type == self.GROUP:
            return getattr(self, "group_traits", None)
        return None

    def __str__(self):
        return f"{self.name_or_alias} ({self.actor_type})"


class IndividualTraits(models.Model):
    individual_traits_id = models.AutoField(primary_key=True) 
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(ScenarioForMining, on_delete=models.CASCADE, related_name="interactions_individual_traits")
    actor = models.ForeignKey(Actors, on_delete=models.CASCADE, related_name="individual_traits")
    cognitive_pattern = models.TextField(blank=True, null=True, default=None) #patterns and characteristics of perception, learning, thoughts, decision-making and bias
    affect_pattern = models.TextField(blank=True, null=True, default=None) #patterns and characteristics of feelings, mood, emotion
    action_pattern = models.TextField(blank=True, null=True, default=None) #patterns and characteristics of actions
    personality = models.TextField(blank=True, null=True, default=None) #also including personality disorder and psychological disorder
    beliefs_values = models.TextField(blank=True, null=True, default=None) #also including religious beliefs and integrity
    priorities = models.TextField(blank=True, null=True, default=None) # motivation, need, desire, goal, objective
    life_style = models.TextField(blank=True, null=True, default=None) # way of life, including habits, interests and hobbies
    identity = models.TextField(blank=True, null=True, default=None) # associated groups,  self-perceived and socially-perceived identity
    capabilities = models.TextField(blank=True, null=True, default=None) # analytical, creative, practical intelligence; emotional intelligence; social skills in communication, listening, leadership, change catalyst, conflict resolution, relationship building, collaboration and cooperation, team building, political skills etc.; merits, talents and expertises
    family = models.TextField(blank=True, null=True, default=None) # type, structure and characteristics
    marriage_intimate_relationship = models.TextField(blank=True, null=True, default=None) # type and characteristics
    education = models.TextField(blank=True, null=True, default=None) # including both formal and informal education experience and level
    occupation_job_industry = models.TextField(blank=True, null=True, default=None)
    social_economic_status = models.TextField(blank=True, null=True, default=None)
    social_network = models.TextField(blank=True, null=True, default=None) # including relationship status
    biological_characteristics = models.TextField(blank=True, null=True, default=None) # race and ethnic group, age, gender, health, facial and body features etc.

    def save(self, *args, **kwargs):
        if self.actor.actor_type != Actors.INDIVIDUAL:
            raise ValueError("Cannot assign Group actor to IndividualTraits")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Traits of {self.actor.name_or_alias} (Individual)"


class GroupTraits(models.Model):
    group_traits_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    scenario = models.ForeignKey(ScenarioForMining, on_delete=models.CASCADE, related_name="interactions_group_traits")
    actor = models.ForeignKey(Actors, on_delete=models.CASCADE, related_name="group_traits")
    group_type = models.TextField(blank=True, null=True, default=None) # type of an organization can be formal organization, community or groups of people, or business, government, non-profit.
    domain = models.TextField(blank=True, null=True, default=None) # domain can be any specific industry or field of work, such as biotech, software-as-a-service, manufacturing, education, charitable cause etc.
    size = models.TextField(blank=True, null=True, default=None) # number of staff, geographic coverage, or revenue and market value
    mission_vision_value = models.TextField(blank=True, null=True, default=None) # 
    goal_strategy = models.TextField(blank=True, null=True, default=None) # long-term and mide-termgoal and how to achieve it.
    objectives_plan = models.TextField(blank=True, null=True, default=None) # short-term objectives and how to achieve them.
    governance = models.TextField(blank=True, null=True, default=None) # structure, process and characteristics of governance
    organizational_structure = models.TextField(blank=True, null=True, default=None) # 
    operation_system = models.TextField(blank=True, null=True, default=None) # how an organization operates include its policies. Processes and practices
    organizational_politics = models.TextField(blank=True, null=True, default=None) # who has what authority and decision-making power, who are alliances or adversaries.
    influence = models.TextField(blank=True, null=True, default=None) # importance, power and influence of an organization
    leadership = models.TextField(blank=True, null=True, default=None) # leaders and managers’ working style, characteristics, capabilities etc.
    culture = models.TextField(blank=True, null=True, default=None) # shared behavior norms that define an organization's environment and guide how organization’s members work and interact with each other and the external world.
    performance = models.TextField(blank=True, null=True, default=None) # metrics to measure the success, for example, profitability and growth for business organization, economic growth and social prosperity for government organization, influence for a non-profit organization, members’ satisfaction for a group etc.
    challenge = models.TextField(blank=True, null=True, default=None) # obstacles or adverse force for an organization to succeed or achieve its goal
    funding_resources_budget = models.TextField(blank=True, null=True, default=None) # an organization’s funding and resources such as land, utility or labor force etc., and spending or investing money
 
    def save(self, *args, **kwargs):
        if self.actor.actor_type != Actors.GROUP:
            raise ValueError("Cannot assign Individual actor to GroupTraits")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Traits of {self.actor.name_or_alias} (Group)"


class IndividualProfile(models.Model):
    individual_profile_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    canonical_name = models.CharField(max_length=255)
    aliases = models.JSONField(default=list, blank=True)  # store list of aliases
    cognitive_pattern = models.TextField(blank=True, null=True, default=None) #patterns and characteristics of perception, learning, thoughts, decision-making and bias
    affect_pattern = models.TextField(blank=True, null=True, default=None) #patterns and characteristics of feelings, mood, emotion
    action_pattern = models.TextField(blank=True, null=True, default=None) #patterns and characteristics of actions
    personality = models.TextField(blank=True, null=True, default=None) #also including personality disorder and psychological disorder
    beliefs_values = models.TextField(blank=True, null=True, default=None) #also including religious beliefs and integrity
    priorities = models.TextField(blank=True, null=True, default=None) # motivation, need, desire, goal, objective
    life_style = models.TextField(blank=True, null=True, default=None) # way of life, including habits, interests and hobbies
    identity = models.TextField(blank=True, null=True, default=None) # associated groups,  self-perceived and socially-perceived identity
    capabilities = models.TextField(blank=True, null=True, default=None) # analytical, creative, practical intelligence; emotional intelligence; social skills in communication, listening, leadership, change catalyst, conflict resolution, relationship building, collaboration and cooperation, team building, political skills etc.; merits, talents and expertises
    family = models.TextField(blank=True, null=True, default=None) # type, structure and characteristics
    marriage_intimate_relationship = models.TextField(blank=True, null=True, default=None) # type and characteristics
    education = models.TextField(blank=True, null=True, default=None) # including both formal and informal education experience and level
    occupation_job_industry = models.TextField(blank=True, null=True, default=None)
    social_economic_status = models.TextField(blank=True, null=True, default=None)
    social_network = models.TextField(blank=True, null=True, default=None) # including relationship status
    biological_characteristics = models.TextField(blank=True, null=True, default=None) # race and ethnic group, age, gender, health, facial and body features etc.
    last_updated = models.DateTimeField(auto_now=True)


class GroupProfile(models.Model):
    group_profile_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    canonical_name = models.CharField(max_length=255)
    aliases = models.JSONField(default=list, blank=True)  # store list of aliases
    group_type = models.TextField(blank=True, null=True, default=None) # type of an organization can be formal organization, community or groups of people, or business, government, non-profit.
    domain = models.TextField(blank=True, null=True, default=None) # domain can be any specific industry or field of work, such as biotech, software-as-a-service, manufacturing, education, charitable cause etc.
    size = models.TextField(blank=True, null=True, default=None) # number of staff, geographic coverage, or revenue and market value
    mission_vision_value = models.TextField(blank=True, null=True, default=None) # 
    goal_strategy = models.TextField(blank=True, null=True, default=None) # long-term and mide-termgoal and how to achieve it.
    objectives_plan = models.TextField(blank=True, null=True, default=None) # short-term objectives and how to achieve them.
    governance = models.TextField(blank=True, null=True, default=None) # structure, process and characteristics of governance
    organizational_structure = models.TextField(blank=True, null=True, default=None) # 
    operation_system = models.TextField(blank=True, null=True, default=None) # how an organization operates include its policies. Processes and practices
    organizational_politics = models.TextField(blank=True, null=True, default=None) # who has what authority and decision-making power, who are alliances or adversaries.
    influence = models.TextField(blank=True, null=True, default=None) # importance, power and influence of an organization
    leadership = models.TextField(blank=True, null=True, default=None) # leaders and managers’ working style, characteristics, capabilities etc.
    culture = models.TextField(blank=True, null=True, default=None) # shared behavior norms that define an organization's environment and guide how organization’s members work and interact with each other and the external world.
    performance = models.TextField(blank=True, null=True, default=None) # metrics to measure the success, for example, profitability and growth for business organization, economic growth and social prosperity for government organization, influence for a non-profit organization, members’ satisfaction for a group etc.
    challenge = models.TextField(blank=True, null=True, default=None) # obstacles or adverse force for an organization to succeed or achieve its goal
    funding_resources_budget = models.TextField(blank=True, null=True, default=None) # an organization’s funding and resources such as land, utility or labor force etc., and spending or investing money
    last_updated = models.DateTimeField(auto_now=True)



class Interactions(models.Model):
    interaction_id = models.AutoField(primary_key=True) 
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(ScenarioForMining, on_delete=models.CASCADE, related_name="interactions")
    actor = models.ForeignKey(Actors, on_delete=models.CASCADE, related_name="actions")
    behavior_description = models.TextField(blank=True, null=True, default=None)
    env = models.TextField(blank=True, null=True, help_text="Relevant social, political, economic, cultural conditions")


    def __str__(self):
        return f"{self.actor.name_or_alias}: {self.behavior_description[:50] if self.behavior_description else ''}"



class InteractionRelations(models.Model):
    interaction_relation_id = models.AutoField(primary_key=True) 
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(ScenarioForMining, on_delete=models.CASCADE, related_name="interaction_relations")
    source = models.ForeignKey("Interactions", on_delete=models.CASCADE, related_name="outgoing_relations")
    target = models.ForeignKey("Interactions", on_delete=models.CASCADE, related_name="incoming_relations") # For each interaction:
    relation_description = models.TextField(blank=True, null=True) 
    related_actors = models.ManyToManyField("Actors", blank=True, related_name="related_interaction_actors", help_text="Actors explicitly involved in this relation")
    related_actors_relationship_status = models.TextField(blank=True, null=True)
    

    def __str__(self):
        return f"{self.source.id} -> {self.target.id} ({self.relation_description or 'No description'})"
 

class ScenarioActors(models.Model):
    scenario_actors_id = models.AutoField(primary_key=True) 
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.OneToOneField(ScenarioForMining, on_delete=models.CASCADE, related_name="scenario_actors")
    scenario_actors_traits = models.TextField(blank=True, null=True, default=None)
        
    def __str__(self):
        return f'Scenario {self.scenario_id} by {self.user.username}'


class ScenarioDynamics(models.Model):
    scenario_dynamics_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    scenario = models.OneToOneField(ScenarioForMining, on_delete=models.CASCADE, related_name="scenario_dynamics")
    scenario_dynamics = models.TextField(blank=True, null=True, default=None)
        
    def __str__(self):
        return f'Scenario {self.scenario_id} by {self.user.username}'


class ScenarioNeeds(models.Model):
    scenario_needs_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    scenario = models.OneToOneField(ScenarioForMining, on_delete=models.CASCADE, related_name="scenario_needs")
    scenario_needs = models.TextField(blank=True, null=True, default=None)
        
    def __str__(self):
        return f'Scenario {self.scenario_id} by {self.user.username}'


class ScenarioSkillsResources(models.Model):
    scenario_skills_resources_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    scenario = models.OneToOneField(ScenarioForMining, on_delete=models.CASCADE, related_name="scenario_skills_resources")
    scenario_skills_resources = models.TextField(blank=True, null=True, default=None)
        
    def __str__(self):
        return f'Scenario {self.scenario_id} by {self.user.username}'


class ScenarioAnalysisPrediction(models.Model):
    scenario_analysis_prediction_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    scenario = models.OneToOneField(ScenarioForMining, on_delete=models.CASCADE, related_name="scenario_analyze_predict")
    scenario_analysis_prediction = models.TextField(blank=True, null=True, default=None)
        
    def __str__(self):
        return f'Scenario {self.scenario_id} by {self.user.username}'



class Scenario(models.Model):    
    scenario_id = models.AutoField(primary_key=True) 
    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    scenario_input = models.TextField(validators=[validate_word_count])  
    scenario_input_time = models.DateTimeField(default=timezone.now)  
    scenario_element_advice = models.TextField(blank=True, null=True, default=None)
    scenario_factor_advice = models.TextField(blank=True, null=True, default=None)  
    scenario_solution_input = models.TextField(blank=True, null=True, validators=[validate_word_count])
    scenario_solution_advice = models.TextField(blank=True, null=True, default=None)
    user_experience = models.TextField(blank=True, null=True, validators=[validate_word_count]) 
    scenario_form_submission_count = models.IntegerField(default=0)
    solution_form_submission_count = models.IntegerField(default=0)
    experience_submitted = models.BooleanField(default=False) 
       
    def __str__(self):
        return f'Scenario {self.scenario_id} by {self.user.username}'


class ScenarioQuickSolution(models.Model):  
   scenario_id = models.AutoField(primary_key=True)  
   user = models.ForeignKey(User, on_delete=models.CASCADE) 
   scenario_input = models.TextField(validators=[validate_word_count])  
   scenario_input_time = models.DateTimeField(default=timezone.now)  
   scenario_quick_solution = models.TextField(blank=True, null=True, default=None)
   scenario_form_submission_count = models.IntegerField(default=0)
   scenario_submitted = models.BooleanField(default=False) 
   
   def __str__(self):
       return f'Scenario {self.scenario_id} by {self.user.username}'


class GlobalActorsProfiles(models.Model):
    global_actors_profiles_id = models.AutoField(primary_key=True) 
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    global_actors_profiles = models.TextField(blank=True, null=True, default=None)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Social Map {self.global_actors_profiles_id} by {self.user.username}'


class SocialNetworkGraphCache(models.Model):
    social_network_graph_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    graph_data = models.JSONField(default=dict)
    last_built = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"GraphCache for {self.user.username} at {self.last_built}"


class GeneratedSimulation(models.Model):
    generated_simulation_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    actors = models.JSONField()  # list of canonical names
    scenario = models.TextField()
    result = models.JSONField()  # structured JSON simulation
    actors_traits_snapshot = models.JSONField()
    actors_relations_snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Generated Simulation {self.generated_simulation_id} on '{self.scenario}'"


class LiveSimulation(models.Model):
    live_simulation_id = models.AutoField(primary_key=True) 
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    actors = models.JSONField(default=list)
    scenario = models.TextField()
    interactions = models.JSONField(default=list)  # grows turn by turn
    actors_profiles_snapshot = models.JSONField(default=dict, blank=True)
    actors_relation_statuses_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Live Simulation {self.live_simulation_id} on '{self.scenario}'"

   
class CorekbDocumentStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None):
        location = location or os.path.join(os.path.dirname(__file__), 'corekb')
        super().__init__(location, base_url)

corekb_document_storage = CorekbDocumentStorage()

def corekb_document_path(instance, filename):
    # Sanitize the file name
    sanitized_filename = filename.strip().replace(' ', '_')
    return sanitized_filename

class CorekbUpload(models.Model):
    name = models.CharField(max_length=100, default="Manual Corekb Upload")
    file = models.FileField(upload_to=corekb_document_path, storage=corekb_document_storage)
    upload_date = models.DateTimeField(auto_now_add=True)
    is_inserted = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        # Debugging logs
        logging.info(f"Deleting file for instance: {self.name}")
        logging.info(f"File path: {self.file.path}")

        # Delete the file from the filesystem
        if self.file:
            logging.info("File exists. Deleting now.")
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
            else:
                logging.warning("File does not exist.")

        # Call the parent class delete method to delete the instance
        super().delete(*args, **kwargs)

@receiver(post_delete, sender=CorekbUpload)
def delete_file_on_model_delete(sender, instance, **kwargs):
    # Ensure the file is deleted when the model is deleted
    if instance.file and os.path.isfile(instance.file.path):
        logging.info(f"Post-delete signal: Deleting file at {instance.file.path}")
        os.remove(instance.file.path)  