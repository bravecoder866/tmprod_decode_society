# tasks.py
from celery import shared_task
from django.utils import timezone
from .models import ScenarioForMining, ScenarioActors, ScenarioDynamics, ScenarioNeeds, ScenarioSkillsResources, ScenarioAnalysisPrediction, IndividualTraits, GroupTraits, IndividualProfile, GroupProfile, GlobalActorsProfiles, Interactions, InteractionRelations, SocialNetworkGraphCache
from .milvus_llm_utils import generate_scenario_actors, generate_scenario_dynamics, generate_scenario_needs, generate_scenario_skills_resources, generate_analysis_prediction, generate_global_actors_profiles, summarize_relationship_status
from django.db import transaction
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from .update_aggregate_utils import update_individual_profile, update_group_profile, aggregate_actors_relationship_status
import json


@shared_task
def build_scenario_actors_task(scenario_id):
    scenario = ScenarioForMining.objects.get(scenario_id=scenario_id)

    individuals_data = []
    for t in IndividualTraits.objects.filter(scenario=scenario).select_related("actor"):
        data = model_to_dict(t)
        actor = t.actor
        data["individual_name_or_alias"] = actor.name_or_alias  # attach identifier
        individuals_data.append(data)

    groups_data = []
    for g in GroupTraits.objects.filter(scenario=scenario).select_related("actor"):
        data = model_to_dict(g)
        actor = g.actor
        data["group_name_or_alias"] = actor.name_or_alias  # attach identifier
        groups_data.append(data)

    #Get all fields from IndividualTraits & GroupTraits
    #individuals_data = [model_to_dict(t) for t in IndividualTraits.objects.filter(scenario=scenario)]
    #groups_data = [model_to_dict(g) for g in GroupTraits.objects.filter(scenario=scenario)]

    # Combine for LLM
    combined_data = {"individual_traits": individuals_data, "group_traits": groups_data,}
    
    # LLM call
    llm_output = generate_scenario_actors(combined_data)

    # Save result
    ScenarioActors.objects.update_or_create(
        scenario=scenario,
        user=scenario.user,
        defaults={"scenario_actors_traits": llm_output}
    )

    print(f"Scenario Actors Traits built for scenario {scenario.scenario_id}")
    
    return f"Scenario Actor Traits built for scenario {scenario.scenario_id}"



@shared_task
def build_scenario_dynamics_task(scenario_id):

    scenario = ScenarioForMining.objects.get(scenario_id=scenario_id)

    interaction_data = []
    for t in Interactions.objects.filter(scenario=scenario).select_related("actor"):
        data = model_to_dict(t)
        actor = t.actor
        data["name_or_alias"] = actor.name_or_alias  # attach identifier
        interaction_data.append(data)

    # interaction_data = [model_to_dict(i) for i in Interactions.objects.filter(scenario=scenario)]
    
    relation_data = [model_to_dict(r) for r in InteractionRelations.objects.filter(scenario=scenario)]
   
    # Combine for LLM
    combined_data = {"interactions": interaction_data, "interaction_relations": relation_data,}


    # LLM call
    llm_output = generate_scenario_dynamics(combined_data)
    
    # Save result
    ScenarioDynamics.objects.update_or_create(
        scenario=scenario,
        user=scenario.user,
        defaults={"scenario_dynamics": llm_output}
    )

    print(f"Social Dynamics built for scenario {scenario.scenario_id}")

    return f"Social Dynamics built for scenario {scenario.scenario_id}"

    

@shared_task
def build_scenario_needs_task(scenario_id):
    scenario = ScenarioForMining.objects.get(scenario_id=scenario_id)
      
    individuals_data = []
    for t in IndividualTraits.objects.filter(scenario=scenario).select_related("actor"):
        data = model_to_dict(t)
        actor = t.actor
        data["individual_name_or_alias"] = actor.name_or_alias  # attach identifier
        individuals_data.append(data)

    groups_data = []
    for g in GroupTraits.objects.filter(scenario=scenario).select_related("actor"):
        data = model_to_dict(g)
        actor = g.actor
        data["group_name_or_alias"] = actor.name_or_alias  # attach identifier
        groups_data.append(data)
    
    #Get all fields from IndividualTraits & GroupTraits
    #individuals_data = [model_to_dict(t) for t in IndividualTraits.objects.filter(scenario=scenario)]
    #groups_data = [model_to_dict(g) for g in GroupTraits.objects.filter(scenario=scenario)]


    #Get all fields from InteractionRelations
    relation_data = [model_to_dict(r) for r in InteractionRelations.objects.filter(scenario=scenario)]
   

    # Combine for LLM
    combined_data = {"individual_traits": individuals_data, "group_traits": groups_data, "interaction_relations": relation_data,}
    
    
    # LLM call
    llm_output = generate_scenario_needs(combined_data)

   
    # Save result
    ScenarioNeeds.objects.update_or_create(
        scenario=scenario,
        user=scenario.user,
        defaults={"scenario_needs": llm_output}
    )

    print(f"Scenario needs built for scenario {scenario.scenario_id}")
    
    return f"Scenario needs built for scenario {scenario.scenario_id}"

    

@shared_task
def build_scenario_skills_resources_task(scenario_id):
    scenario = ScenarioForMining.objects.get(scenario_id=scenario_id)
    
    individuals_data = []
    for t in IndividualTraits.objects.filter(scenario=scenario).select_related("actor"):
        data = model_to_dict(t)
        actor = t.actor
        data["individual_name_or_alias"] = actor.name_or_alias  # attach identifier
        individuals_data.append(data)

    groups_data = []
    for g in GroupTraits.objects.filter(scenario=scenario).select_related("actor"):
        data = model_to_dict(g)
        actor = g.actor
        data["group_name_or_alias"] = actor.name_or_alias  # attach identifier
        groups_data.append(data)


    #Get all fields from IndividualTraits & GroupTraits
    #individuals_data = [model_to_dict(t) for t in IndividualTraits.objects.filter(scenario=scenario)]
    #groups_data = [model_to_dict(g) for g in GroupTraits.objects.filter(scenario=scenario)]


    #Get all fields from InteractionRelations
    relation_data = [model_to_dict(r) for r in InteractionRelations.objects.filter(scenario=scenario)]
   

    # Combine for LLM
    combined_data = {"individual_traits": individuals_data, "group_traits": groups_data, "interaction_relations": relation_data,}
    
    # LLM call
    llm_output = generate_scenario_skills_resources(combined_data)

   
    # Save result
    ScenarioSkillsResources.objects.update_or_create(
        scenario=scenario,
        user=scenario.user,
        defaults={"scenario_skills_resources": llm_output}
    )


    print(f"Social Skills Resources built for scenario {scenario.scenario_id}")

    return f"Social Skills Resources built for scenario {scenario.scenario_id}"

    

@shared_task
def build_scenario_analysis_prediction_task(scenario_id):
    scenario = ScenarioForMining.objects.get(scenario_id=scenario_id)
    
     # LLM call
    llm_output = generate_analysis_prediction(scenario.scenario_input)

   
    # Save result
    ScenarioAnalysisPrediction.objects.update_or_create(
        scenario=scenario,
        user=scenario.user,
        defaults={"scenario_analysis_prediction": llm_output}
    )

    print(f"Analysis and Prediction built for scenario {scenario.scenario_id}")
    
    return f"Social Analysis and Prediction  built for scenario {scenario.scenario_id}"

    


@shared_task
def update_individual_profile_task(user_id):
    user = User.objects.get(id=user_id)
    try:
        update_individual_profile(user)
        return "Individual profiles updated"
    except Exception as e:
        import traceback
        print(f"update_individual_profile_task failed for user {user_id}: {e}")
        traceback.print_exc()
        # still return True so chord doesn’t break
        return "update_individual_profile_task failed but continued"

@shared_task
def update_group_profile_task(user_id):
    user = User.objects.get(id=user_id)
    try:
      update_group_profile(user)
      return "Group profiles updated"
    except Exception as e:
        import traceback
        print(f"update_group_profile_task failed for user {user_id}: {e}")
        traceback.print_exc()
        # still return True so chord doesn’t break
        return "update_group_profile_task failed but continued"



@shared_task
def build_global_actors_profiles_task(_results, user_id):
    user = User.objects.get(id=user_id)

    individual_profiles = [model_to_dict(p) for p in IndividualProfile.objects.filter(user=user)]
    group_profiles = [model_to_dict(g) for g in GroupProfile.objects.filter(user=user)]

    combined_data = {
        "individual_profiles": individual_profiles,
        "group_profiles": group_profiles,
    }

    llm_output = generate_global_actors_profiles(combined_data)

    # Convert the Python dictionary back into a JSON string
    json_string_output = json.dumps(llm_output)

    GlobalActorsProfiles.objects.update_or_create(
        user=user,  # must pass a User instance
        defaults={"global_actors_profiles": json_string_output }
    )

    return user_id



@shared_task
def build_social_network_graph_task(user_id):
    user = User.objects.get(id=user_id)

    profile = GlobalActorsProfiles.objects.filter(user=user).order_by("-last_updated").first()
    if not profile or not profile.global_actors_profiles:
        # If no profile yet, skip building graph
        SocialNetworkGraphCache.objects.update_or_create(
            user=user, defaults={"graph_data": {"nodes": [], "edges": []}}
        )
        return {"nodes": [], "edges": []}

    try:
        categories = json.loads(profile.global_actors_profiles)
    except json.JSONDecodeError:
        print("JSON decode failed in GlobalActorsProfiles")
        SocialNetworkGraphCache.objects.update_or_create(
            user=user,
            defaults={"graph_data": {"nodes": [], "edges": []}}
        )
        return {"nodes": [], "edges": []}

    # Collect canonical names
    allowed_actors = set()

    # Self section
    for entry in categories.get("Self", []):
        name = entry.get("canonical_name")
        if name:
            allowed_actors.add(name)

    # People section
    for entry in categories.get("People", []):
        name = entry.get("canonical_name")
        if name:
            allowed_actors.add(name)

    # Group section
    for entry in categories.get("Group", []):
        name = entry.get("canonical_name")
        if name:
            allowed_actors.add(name)

    relation_map = aggregate_actors_relationship_status(user)
    
    if not relation_map:
        graph = {"nodes": [], "edges": []}
    else:
        filtered_map = {
            (actor1, actor2): status
            for (actor1, actor2), status in relation_map.items()
            if actor1 in allowed_actors and actor2 in allowed_actors
        }

        summaries = summarize_relationship_status(filtered_map)

        nodes = {}
        edges = []
        
        for (actor1, actor2), status in filtered_map.items():
            actor1, actor2 = sorted([actor1, actor2])
            # Add actors as nodes if not already there
            for actor in [actor1, actor2]:
                if actor not in nodes:
                    nodes[actor] = {
                        "id": actor,
                        "label": actor,
                    }

            # Add edge between actors with statuses + summary
            key = f"({actor1}, {actor2})"
            summary = summaries.get(key, f"Relationship between {actor1} and {actor2} not summarized.")
        
            edges.append({
                "source": actor1,
                "target": actor2,
                # "status": status,  # raw list of statuses from scenarios
                "summary": summary,    # optional LLM-generated description
            })

        graph = {"nodes": list(nodes.values()), "edges": edges}

    SocialNetworkGraphCache.objects.update_or_create(
            user=user,
            defaults={"graph_data": graph}
    )

    return graph