"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""

import os
import re
import logging
import requests
import json
from django.db import transaction
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from .milvus_llm_utils import aggregate_individual_traits, aggregate_group_traits
from .models import ScenarioForMining, Actors, IndividualTraits, IndividualProfile, GroupTraits, GroupProfile, InteractionRelations
from collections import defaultdict
from typing import Dict, List, Tuple



def update_individual_profile(user):

    latest_scenario = ScenarioForMining.objects.filter(user=user).latest("scenario_input_time")
    new_scenario_traits = IndividualTraits.objects.filter(user=user, scenario=latest_scenario)
    
    new_traits = []
    for t in new_scenario_traits:
        new_traits.append({
            "name_or_alias": t.actor.name_or_alias,
            "cognitive_pattern": t.cognitive_pattern,
            "affect_pattern": t.affect_pattern,
            "action_pattern": t.action_pattern,
            "personality": t.personality,
            "beliefs_values": t.beliefs_values,
            "priorities": t.priorities,
            "life_style": t.life_style,
            "identity": t.identity,
            "capabilities": t.capabilities,
            "family": t.family,
            "marriage_intimate_relationship": t.marriage_intimate_relationship,
            "education": t.education,
            "occupation_job_industry": t.occupation_job_industry,
            "social_economic_status": t.social_economic_status,
            "social_network": t.social_network,
            "biological_characteristics": t.biological_characteristics,
        })

    existing_individual_profiles = IndividualProfile.objects.filter(user=user)
    
    existing_profiles = []
    
    for p in existing_individual_profiles:
        existing_profiles.append({
            "individual_profile_id": p.pk,
            "canonical_name": p.canonical_name,
            "aliases": getattr(p, "aliases", []),
            "cognitive_pattern": p.cognitive_pattern,
            "affect_pattern": p.affect_pattern,
            "action_pattern": p.action_pattern,
            "personality": p.personality,
            "beliefs_values": p.beliefs_values,
            "priorities": p.priorities,
            "life_style": p.life_style,
            "identity": p.identity,
            "capabilities": p.capabilities,
            "family": p.family,
            "marriage_intimate_relationship": p.marriage_intimate_relationship,
            "education": p.education,
            "occupation_job_industry": p.occupation_job_industry,
            "social_economic_status": p.social_economic_status,
            "social_network": p.social_network,
            "biological_characteristics": p.biological_characteristics,
        })
    
    llm_output = aggregate_individual_traits(existing_profiles, new_traits)
    updates = llm_output.get("updates", []) if isinstance(llm_output, dict) else []


    # ---- Main update loop ----
    with transaction.atomic():
        for update in updates:
            individual_profile_id = update.get("individual_profile_id")
            old_name = update.get("old_canonical_name")
            new_name = update.get("new_canonical_name") or old_name 
    
            # Skip incomplete entries
            if not new_name:
                continue

            profile = None

            # --- LOOKUP BY ID ---
            if individual_profile_id is not None:
                try:
                    profile = IndividualProfile.objects.get(pk=individual_profile_id, user=user)
                except IndividualProfile.DoesNotExist:
                    individual_profile_id = None


            #if old_name:
            #    profile = (
            #        IndividualProfile.objects.filter(user=user, canonical_name=old_name).first() or
            #        IndividualProfile.objects.filter(user=user, aliases__contains=[old_name]).first()
            #    )

            # Create new if none found
            if profile is None:            
                profile = IndividualProfile.objects.create(
                    user=user,
                    canonical_name=new_name,
                )

            else:

                # If refined canonical name, update it
                if profile.canonical_name != new_name:
                   profile.canonical_name = new_name


            # --- Update aliases safely ---
            aliases = set(profile.aliases or [])
        

            # Add identity names
            if old_name:
                aliases.add(old_name)
            if new_name:
                aliases.add(new_name)


            # Add aliases from LLM output
            incoming_aliases = update.get("aliases", [])
            aliases.update(a.strip() for a in incoming_aliases if a and a.strip())

            # Always include canonical name in aliases
            aliases.add(profile.canonical_name)
       

            # Clean & store sorted
            profile.aliases = sorted(aliases)
            
   
            cognitive_pattern = update.get("cognitive_pattern")
            affect_pattern = update.get("affect_pattern")
            action_pattern = update.get("action_pattern")  
            personality = update.get("personality")
            beliefs_values = update.get("beliefs_values")
            priorities = update.get("priorities")
            life_style = update.get("life_style")
            identity = update.get("identity")
            capabilities = update.get("capabilities")
            family = update.get("family")
            marriage_intimate_relationship = update.get("marriage_intimate_relationship")
            education = update.get("education")
            occupation_job_industry = update.get("occupation_job_industry")
            social_economic_status = update.get("social_economic_status")
            social_network = update.get("social_network")
            biological_characteristics = update.get("biological_characteristics")


            if cognitive_pattern is not None:
                profile.cognitive_pattern = cognitive_pattern

            if affect_pattern is not None:
                profile.affect_pattern = affect_pattern

            if action_pattern is not None:
                profile.action_pattern = action_pattern 

            if personality is not None:
                profile.personality = personality

            if beliefs_values is not None:
                profile.beliefs_values = beliefs_values

            if priorities is not None:
                profile.priorities = priorities

            if life_style is not None:
                profile.life_style = life_style

            if identity is not None:
                profile.identity = identity

            if capabilities is not None:
                profile.capabilities = capabilities

            if family is not None:
                profile.family = family

            if marriage_intimate_relationship is not None:
                profile.marriage_intimate_relationship = marriage_intimate_relationship

            if education is not None:
                profile.education = education

            if occupation_job_industry is not None:
                profile.occupation_job_industry = occupation_job_industry

            if social_economic_status is not None:
                profile.social_economic_status = social_economic_status

            if social_network is not None:
                profile.social_network = social_network

            if biological_characteristics is not None:
                profile.biological_characteristics = biological_characteristics

            profile.save()

    print(f"Individual profile update complete.")


def update_group_profile(user):

    latest_scenario = ScenarioForMining.objects.filter(user=user).latest("scenario_input_time")
    new_scenario_traits = GroupTraits.objects.filter(user=user, scenario=latest_scenario)

    new_traits = []
    for t in new_scenario_traits:
        new_traits.append({
            "name_or_alias": t.actor.name_or_alias,
            "group_type": t.group_type,    
            "domain": t.domain,  
            "size": t.size,  
            "mission_vision_value": t.mission_vision_value,   
            "goal_strategy": t.goal_strategy,    
            "objectives_plan": t.objectives_plan,    
            "governance": t.governance,   
            "organizational_structure": t.organizational_structure,   
            "operation_system": t.operation_system, 
            "organizational_politics": t.organizational_politics,  
            "influence": t.influence, 
            "leadership": t.leadership,
            "culture": t.culture,    
            "performance": t.performance,  
            "challenge": t.challenge,   
            "funding_resources_budget": t.funding_resources_budget,  
        })    


    existing_group_profiles = GroupProfile.objects.filter(user=user)
    
    existing_profiles = []
    
    for p in existing_group_profiles:
        existing_profiles.append({
            "group_profile_id": p.pk,
            "canonical_name": p.canonical_name,
            "aliases": getattr(p, "aliases", []),
            "group_type": p.group_type,    
            "domain": p.domain,  
            "size": p.size,  
            "mission_vision_value": p.mission_vision_value,   
            "goal_strategy": p.goal_strategy,    
            "objectives_plan": p.objectives_plan,    
            "governance": p.governance,   
            "organizational_structure": p.organizational_structure,   
            "operation_system": p.operation_system, 
            "organizational_politics": p.organizational_politics,  
            "influence": p.influence, 
            "leadership": p.leadership,
            "culture": p.culture,    
            "performance": p.performance,  
            "challenge": p.challenge,   
            "funding_resources_budget": p.funding_resources_budget,  
        })


    llm_output = aggregate_group_traits(existing_profiles, new_traits)
    updates = llm_output.get("updates", []) if isinstance(llm_output, dict) else []

    with transaction.atomic():
        for update in updates:
            group_profile_id = update.get("group_profile_id")
            old_name = update.get("old_canonical_name")
            new_name = update.get("new_canonical_name") or old_name
        

            # Skip incomplete entries
            if not new_name:
                continue

            profile = None

            # --- LOOKUP BY ID ---
            if group_profile_id is not None:
                try:
                    profile = IndividualProfile.objects.get(pk=group_profile_id, user=user)
                except IndividualProfile.DoesNotExist:
                    group_profile_id = None

            #if old_name:
            #    profile = (
            #        GroupProfile.objects.filter(user=user, canonical_name=old_name).first() or
            #        GroupProfile.objects.filter(user=user, aliases__contains=[old_name]).first()
            #    )

        
            # Create new if none found
            if profile is None:            
                profile = GroupProfile.objects.create(
                    user=user,
                    canonical_name=new_name,
                )

            else:
                # If refined canonical name, update it
                if profile.canonical_name != new_name:
                   profile.canonical_name = new_name

        
            # --- Update aliases safely ---
            aliases = set(profile.aliases or [])
        

            # Add identity names
            if old_name:
                aliases.add(old_name)
            if new_name:
                aliases.add(new_name)

            # Add aliases from LLM output
            incoming_aliases = update.get("aliases", [])
            aliases.update(a.strip() for a in incoming_aliases if a and a.strip())

            # Always include canonical name in aliases
            aliases.add(profile.canonical_name)
        
            # Clean & store sorted
            profile.aliases = sorted(aliases)
            

            group_type = update.get("group_type")
            domain = update.get("domain")
            size = update.get("size")  
            mission_vision_value = update.get("mission_vision_value")
            goal_strategy = update.get("goal_strategy")
            objectives_plan = update.get("objectives_plan")
            governance = update.get("governance")
            organizational_structure = update.get("organizational_structure")
            operation_system = update.get("operation_system")
            organizational_politics = update.get("organizational_politics")
            influence = update.get("influence")
            leadership = update.get("leadership")
            culture = update.get("culture")
            performance = update.get("performance")
            challenge = update.get("challenge")
            funding_resources_budget = update.get("funding_resources_budget")

            if group_type is not None:
                profile.group_type = group_type

            if domain is not None:
                profile.domain = domain

            if size is not None:
                profile.size = size 

            if mission_vision_value is not None:
                profile.mission_vision_value = mission_vision_value

            if goal_strategy is not None:
                profile.goal_strategy = goal_strategy

            if objectives_plan is not None:
                profile.objectives_plan = objectives_plan

            if governance is not None:
                profile.governance = governance

            if organizational_structure is not None:
                profile.organizational_structure = organizational_structure

            if operation_system is not None:
                profile.operation_system = operation_system

            if organizational_politics is not None:
                profile.organizational_politics = organizational_politics

            if influence is not None:
                profile.influence = influence

            if leadership is not None:
                profile.leadership = leadership

            if culture is not None:
                profile.culture = culture

            if performance is not None:
                profile.performance = performance

            if challenge is not None:
                profile.challenge = challenge

            if funding_resources_budget is not None:
                profile.funding_resources_budget = funding_resources_budget


            profile.save()

    print(f"Group profile updates complete.")



def resolve_to_canonical(name_or_alias: str, user) -> str:
    """
    Given a name_or_alias from scenario Actor, 
    resolve to canonical_name from IndividualProfile or GroupProfile.
    Returns name_or_alias itself if no match is found.
    """

    # Split into individual names
    names = [n.strip() for n in name_or_alias.split(",") if n.strip()]
    
    # Check individuals first
    individual = IndividualProfile.objects.filter(user=user, aliases__contains=names).first()
    if individual:
        return individual.canonical_name

    # Check groups
    group = GroupProfile.objects.filter(user=user, aliases__contains=names).first()
    if group:
        return group.canonical_name

    # Fallback: alias itself (new actor, not merged yet)
    return names[0] if names else name_or_alias



def aggregate_actors_relationship_status(user) -> Dict[Tuple[str, str], List[str]]:
    """
    Collect all relationship statuses across all scenarios.
    Returns dict keyed by (actor1, actor2) -> list of statuses.
    """
    relation_map = defaultdict(list)

    relations = InteractionRelations.objects.filter(user=user).prefetch_related("related_actors")

    for rel in relations:
        actors = list(rel.related_actors.all())
        if len(actors) >= 2 and rel.related_actors_relationship_status:
            for i in range(len(actors)):
                for j in range(i + 1, len(actors)):
                    # Resolve both names to canonical identities
                    actor1 = resolve_to_canonical(actors[i].name_or_alias, user)
                    actor2 = resolve_to_canonical(actors[j].name_or_alias, user)

                    key = tuple(sorted([actor1, actor2]))
                    relation_map[key].append(rel.related_actors_relationship_status)

    return dict(relation_map)
