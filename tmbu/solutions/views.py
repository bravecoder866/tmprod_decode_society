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
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt 
from django.conf import settings  
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.translation import gettext as _, get_language
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from .models import Scenario, ScenarioForMining, ScenarioActors, ScenarioDynamics, ScenarioNeeds, ScenarioSkillsResources, ScenarioAnalysisPrediction, ScenarioQuickSolution, Actors, IndividualTraits, GroupTraits, IndividualProfile, GroupProfile, Interactions, InteractionRelations, GlobalActorsProfiles, SocialNetworkGraphCache, GeneratedSimulation, LiveSimulation
from payments.models import UserSubscription
from accounts.models import UserFreeTrial, UserFreeTrialQuickSolution, UserFreeTrialScenarioMining
from .forms import ScenarioInputForm, SolutionInputForm, ExperienceForm, ScenarioInputQuickSolutionForm, ScenarioForMiningForm
from .milvus_connection_utils import ensure_connection
from .milvus_llm_utils import generate_element_advice, generate_factor_advice, generate_solution_advice, generate_quick_solution, extract_info_from_scenario, aggregate_individual_traits, aggregate_group_traits, generate_scenario_actors, generate_scenario_dynamics, generate_scenario_needs, generate_scenario_skills_resources, generate_analysis_prediction, generate_global_actors_profiles, summarize_relationship_status, llm_generate_simulation, llm_generate_live_simulation
from pymilvus import MilvusClient
from .tasks import build_scenario_actors_task, build_scenario_dynamics_task, build_scenario_needs_task, build_scenario_skills_resources_task, build_scenario_analysis_prediction_task, update_individual_profile_task, update_group_profile_task, build_global_actors_profiles_task, build_social_network_graph_task
from celery.result import AsyncResult
from celery import chain, chord
from collections import defaultdict
from typing import Dict, List, Tuple
from .update_aggregate_utils import resolve_to_canonical

logger = logging.getLogger(__name__)


def solution_center_view(request):
    return render(request, "solutions/solution_center.html")

def my_solutions_view(request):
    return render(request, "solutions/my_solutions.html")


def scenario_process_view(request, scenario_id=None):

    MAX_FREE_USES = 20
 
    is_new_scenario = request.GET.get('new', 'false').lower() == 'true' or scenario_id is None
    scenario = None 

    # --- Refill form data after login ---
    prefill_data = request.session.pop('pending_scenario_data', None)


    # Check if starting a new scenario
    if is_new_scenario:
        scenario = Scenario()
        if prefill_data:
            scenario_form = ScenarioInputForm(initial=prefill_data, instance=scenario)
            solution_form = None  # No solution form initially
            experience_form = None  # No experience form initially
        else:
            scenario_form = ScenarioInputForm(request.POST.copy() if request.method == 'POST' else None, instance=scenario)
            solution_form = None  # No solution form initially
            experience_form = None  # No experience form initially

    elif scenario_id:
        # Fetch the specific scenario
        scenario = get_object_or_404(Scenario, scenario_id=scenario_id, user=request.user)
    
        scenario_form = ScenarioInputForm(request.POST.copy() if request.method == 'POST' else None, instance=scenario)
        solution_form = SolutionInputForm(request.POST.copy() if request.method == 'POST' else None, instance=scenario) if scenario and scenario.scenario_factor_advice else None
        experience_form = ExperienceForm(request.POST.copy() if request.method == 'POST' else None, instance=scenario) if scenario and scenario.scenario_solution_advice and scenario.solution_form_submission_count >= 2 else None
    else:
        # Default behavior: redirect to My Scenarios
        return redirect('my_scenarios')


    free_trial = None
    subscription = None
    if request.user.is_authenticated:
        # Fetch free trial and subscription details
        free_trial = UserFreeTrial.objects.filter(user=request.user).first()
        subscription = UserSubscription.objects.filter(user=request.user, subscription_status='active').first()


    if request.method == 'POST':
    
        if 'submit_scenario' in request.POST:
            if not request.user.is_authenticated:
                data = request.POST.dict()
                data.pop('csrfmiddlewaretoken', None)
                request.session['pending_scenario_data'] = data
                # messages.error(request, _("Please log in."))
                return redirect(f"{reverse('login')}?next={request.path}")
      
            if scenario_form.is_valid():
                with transaction.atomic():
                    
                    # Check if the user can submit a scenario
                    if not (free_trial and not free_trial.has_used_free_trial) and not subscription:   
                        # No free trial left and no subscription
                        # messages.error(request, _("You must have an active subscription to submit a scenario."))
                        return redirect('subscription_plan')
            
                    # First submission or update scenario_input
                    if is_new_scenario:

                        ## Check for exceeding scenario creation attempts
                        #if free_trial.scenario_creation_attempts > 0 and not subscription:
                        #    # messages.error(request, _("You have exceeded the free trial limit for scenario creation."))
                        #    return redirect('subscription_plan')

                        scenario = scenario_form.save(commit=False)
                        scenario.user = request.user
                        scenario.scenario_input_time = timezone.now()
                        scenario.save()
                        # messages.success(request, _("New goal/situation created successfully."))
                        
                        scenario.scenario_form_submission_count += 1  # Increment counter for first submission
                        scenario.save()

                        #if not free_trial.has_used_free_trial:
                        #    free_trial.scenario_creation_attempts += 1
                        #    free_trial.save()

                        

                    else:  # Second submission: update the scenario input
                        if scenario.scenario_form_submission_count >= 2:
                            # messages.error(request, _("You have already submitted your goal/situation twice. Further updates are not allowed."))  
                            return redirect('existing_scenario', scenario_id=scenario.scenario_id) # Silent block
                        
                        scenario.scenario_input = scenario_form.cleaned_data['scenario_input']
                        scenario.save()
                        # messages.info(request, _("Goal/situation updated successfully."))
                                
                        scenario.scenario_form_submission_count += 1 # Increment counter for all submissions
                        scenario.save()


                    if not scenario.scenario_element_advice:
                        # First submission: generate element advice
                        scenario.scenario_element_advice = generate_element_advice(scenario.scenario_input)
                        scenario.save()
                        # messages.info(request, _("Goal/situation review generated."))


                        # Count this as a free use (new or update submission)
                        if free_trial and not free_trial.has_used_free_trial and not subscription:
                            free_trial.scenario_creation_attempts += 1
                            if free_trial.scenario_creation_attempts >= MAX_FREE_USES:
                                free_trial.has_used_free_trial = True
                            free_trial.save()


                        return redirect('existing_scenario', scenario_id=scenario.scenario_id)  # add this

                    else:
                        # Second submission: generate factors advice
                        scenario.scenario_factor_advice = generate_factor_advice(scenario.scenario_input)
                        scenario.save()
                        # messages.info(request, _("Solution ideas generated."))


                        # Count this as a free use (second submission)
                        if free_trial and not free_trial.has_used_free_trial and not subscription:
                            free_trial.scenario_creation_attempts += 1
                            if free_trial.scenario_creation_attempts >= MAX_FREE_USES:
                                free_trial.has_used_free_trial = True
                            free_trial.save()
                        

                        return redirect('existing_scenario', scenario_id=scenario.scenario_id)  # Redirect to refresh the page with the updated advice

                              
        # Handle solution form submission
        elif 'submit_solution' in request.POST and solution_form:
            
            if solution_form.is_valid():
                with transaction.atomic():

                # Check if this is the first submission
                    if not scenario.scenario_solution_input:
                        # First submission: Save the input and generate advice
                        solution_form.save()
                        # messages.success(request, _("Solution draft created successfully."))

                        scenario.solution_form_submission_count += 1
                        scenario.save()

                    else:
                        # Second submission: update the solution input 
                        if scenario.solution_form_submission_count >= 2: 
                            # messages.error(request, _("You have already submitted your solution twice. Further updates are not allowed.")) 
                            return redirect('existing_scenario', scenario_id=scenario.scenario_id) # Silent block

                        updated_solution_input = solution_form.cleaned_data['scenario_solution_input']
                        if scenario.scenario_solution_input != updated_solution_input:
                            scenario.scenario_solution_input = updated_solution_input
                            solution_form.save()  # Save the updated solution input
                            # messages.success(request, _("You've got a solution! Please share your experience after you try it. "))
                        # else:
                        #    messages.info(request, _("You've got a solution! Please share your experience after you try it."))    
                            
                        scenario.solution_form_submission_count += 1
                        scenario.save()  

                    if not scenario.scenario_solution_advice:
                        scenario.scenario_solution_advice = generate_solution_advice(scenario.scenario_solution_input)
                        # messages.info(request, _("Strategic considerations generated."))
                        scenario.save()

                    return redirect('existing_scenario', scenario_id=scenario.scenario_id)  # Redirect to refresh the page

                
        # Handle experience form submission
        elif 'submit_experience' in request.POST and experience_form:
            
            if experience_form.is_valid():
                with transaction.atomic():  # Important for data consistency
                    if scenario.experience_submitted:
                        # messages.error(request, _("You have already submitted your experience. Further updates are not allowed."))  
                        return redirect('existing_scenario', scenario_id=scenario.scenario_id)  

                    experience_form.save()                
                    scenario.experience_submitted = True
                    scenario.save()

                    ## Mark the free trial as used
                    #if free_trial and not free_trial.has_used_free_trial:
                    #    free_trial.has_used_free_trial = True
                    #    free_trial.save()
                    #    # messages.success(request, _("You have completed the free trial."))

                    return redirect('existing_scenario', scenario_id=scenario.scenario_id)  # Redirect to refresh the page


    # Context for template rendering
    context = {
        'free_trial': free_trial,
        'subscription': subscription,
        "is_new_scenario": is_new_scenario,
        'scenario': scenario,
        'scenario_form': scenario_form if not scenario or scenario.scenario_form_submission_count < 2 else None,
        'solution_form': solution_form if scenario and scenario.solution_form_submission_count < 2 else None,
        'experience_form': experience_form if scenario and not scenario.experience_submitted else None,
        'last_scenario_input': scenario.scenario_input if scenario else "",
        'last_solution_input': scenario.scenario_solution_input if scenario else "",
        'last_experience_input': scenario.user_experience if scenario and scenario.experience_submitted else "",  
    }

    return render(request, 'solutions/scenario_process.html', context)



def scenario_quick_solution_view(request, scenario_id=None):

    MAX_FREE_USES = 20
    
    is_new_scenario = request.GET.get('new', 'false').lower() == 'true' or scenario_id is None
    scenario = None 

    # --- Refill form data after login ---
    prefill_data = request.session.pop('pending_scenario_data', None)

    # Check if it is a new scenario or existing scenario
    if is_new_scenario:
        scenario = ScenarioQuickSolution()
        if prefill_data:
            scenario_form = ScenarioInputQuickSolutionForm(initial=prefill_data, instance=scenario)
        else:
            scenario_form = ScenarioInputQuickSolutionForm(request.POST.copy() if request.method == 'POST' else None, instance=scenario)
        
    elif scenario_id:
        # Fetch the specific scenario
        scenario = get_object_or_404(ScenarioQuickSolution, scenario_id=scenario_id, user=request.user)
        scenario_form = ScenarioInputQuickSolutionForm(request.POST.copy() if request.method == 'POST' else None, instance=scenario)
        
    else:
        # Default behavior: redirect to My Resources
        return redirect('my_scenarios_quick_solution')


    free_trial = None
    subscription = None        
    if request.user.is_authenticated:
        # Fetch free trial and subscription status
        free_trial = UserFreeTrialQuickSolution.objects.filter(user=request.user).first()
        subscription = UserSubscription.objects.filter(user=request.user, subscription_status='active').first()


    if request.method == 'POST':
    
        if 'submit_scenario' in request.POST:
            if not request.user.is_authenticated:
                # Save data for after login
                data = request.POST.dict()
                data.pop('csrfmiddlewaretoken', None)
                request.session['pending_scenario_data'] = data
                # messages.error(request, _("Please log in."))
                return redirect(f"{reverse('login')}?next={request.path}")
      
            if scenario_form.is_valid():
                with transaction.atomic():
                    
                    # Check if the user can submit a scenario
                    if not (free_trial and not free_trial.has_used_free_trial) and not subscription:   
                        # No free trial left and no subscription
                        # messages.error(request, _("You must have an active subscription to submit a scenario."))
                        return redirect('subscription_plan')
            
                    ## New scenario submission
                    #if is_new_scenario:

                    #    # Check for exceeding scenario creation attempts
                    #    if free_trial and free_trial.scenario_creation_attempts > 0 and not subscription:
                    #        # messages.error(request, _("You have exceeded the free trial limit for scenario creation."))
                    #        return redirect('subscription_plan')
                        
                    # Scenario submission
                    scenario = scenario_form.save(commit=False)
                    scenario.user = request.user
                    scenario.scenario_input_time = timezone.now()
                    scenario.save()
                        
                    # Generate quick solution
                    try:
                        scenario.scenario_quick_solution = generate_quick_solution(scenario.scenario_input)
                        scenario.scenario_form_submission_count += 1  # Increment counter for each submission
                        scenario.scenario_submitted = True
                                    
                        #if scenario.scenario_form_submission_count == 1:
                            #messages.success(request, _("Scenario submitted and quick solution generated!"))
                        # else:
                            #messages.success(request, _("Scenario and quick solution updated!"))
                    
                        scenario.save(update_fields=["scenario_quick_solution", "scenario_form_submission_count", "scenario_submitted"])

                    except Exception as e:
                        # messages.error(request, _("Something went wrong while generating quick solution. Please try again."))
                        
                        return redirect('existing_scenario_quick_solution', scenario_id=scenario.scenario_id)  
   

                    # Mark the free trial as used
                    
                    if free_trial and not free_trial.has_used_free_trial and not subscription:
                        free_trial.scenario_creation_attempts += 1

                        if free_trial.scenario_creation_attempts >= MAX_FREE_USES:
                            free_trial.has_used_free_trial = True

                        free_trial.save()
                        # messages.success(request, _("You have completed the free trial."))

                    return redirect('existing_scenario_quick_solution', scenario_id=scenario.scenario_id)  # Redirect to refresh the page


    # Context for template rendering
    context = {
        'free_trial': free_trial,
        'subscription': subscription,
        "is_new_scenario": is_new_scenario,
        'scenario': scenario,
        'scenario_form': scenario_form,
        #'last_scenario_input': scenario.scenario_input if scenario else "",
    }

    return render(request, 'solutions/scenario_quick_solution.html', context)



@login_required
def my_scenarios_view(request):
    scenarios = Scenario.objects.filter(user=request.user).order_by('-scenario_input_time')
    paginator = Paginator(scenarios, 10)  # Show 10 scenarios per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    

    # Debugging outputs
    print(f"Total scenarios for user {request.user.id}: {scenarios.count()}")
    print(f"Page number requested: {page_number}")
    print(f"Scenarios on this page: {[scenario.scenario_id for scenario in page_obj]}")


    return render(request, 'solutions/my_scenarios.html', {
        'page_obj': page_obj,
        'total_scenarios': scenarios.count(),  # Total number of scenarios
    })


@login_required
def delete_selected_comprehensive_solutions(request):
    """Delete selected comprehensive solution scenarios."""
    if request.method == "POST":
        selected_ids = request.POST.getlist("selected_comprehensive_solutions")
        if selected_ids:
            Scenario.objects.filter(
                scenario_id__in=selected_ids,
                user=request.user
            ).delete()
            messages.success(request, f"Deleted {len(selected_ids)} comprehensive solution(s).")
        else:
            messages.warning(request, "No comprehensive solutions selected.")
    return redirect("my_scenarios")


@login_required
def my_scenarios_quick_solution_view(request):
    scenarios = ScenarioQuickSolution.objects.filter(user=request.user).order_by('-scenario_input_time')
    paginator = Paginator(scenarios, 10)  # Show 10 scenarios per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    

    # Debugging outputs
    print(f"Total scenarios for user {request.user.id}: {scenarios.count()}")
    print(f"Page number requested: {page_number}")
    print(f"Scenarios on this page: {[scenario.scenario_id for scenario in page_obj]}")


    return render(request, 'solutions/my_scenarios_quick_solutions.html', {
        'page_obj': page_obj,
        'total_scenarios': scenarios.count(),  # Total number of scenarios
    })


@login_required
def delete_selected_quick_solutions(request):
    """Deletes selected quick solution scenarios."""
    if request.method == "POST":
        selected_ids = request.POST.getlist("selected_quick_solutions")
        if selected_ids:
            ScenarioQuickSolution.objects.filter(
                scenario_id__in=selected_ids,
                user=request.user
            ).delete()
            messages.success(request, f"Deleted {len(selected_ids)} quick solution(s).")
        else:
            messages.warning(request, "No quick solutions selected.")
    return redirect("my_scenarios_quick_solution")


def save_extracted_info(user, scenario, extracted_info):

    # --- 1. Save Actors ---
    actor_map = {}
    for actor_data in extracted_info.get("actors", []):
        actor_obj = Actors.objects.create(
            user=user,
            scenario=scenario,
            name_or_alias=actor_data["name_or_alias"],
            actor_type=actor_data["actor_type"]
        )
        actor_map[actor_data["actor_ref_id"]] = actor_obj



    # --- 2. Individual Traits ---
    for ind in extracted_info.get("individual_traits", []):
        actor = actor_map.get(ind.get("actor"))
        if actor and actor.actor_type == Actors.INDIVIDUAL:
            IndividualTraits.objects.create(
                user=user,
                scenario=scenario,
                actor=actor,                
                cognitive_pattern=ind.get("cognitive_pattern"),
                affect_pattern=ind.get("affect_pattern"),
                action_pattern=ind.get("action_pattern"),
                personality=ind.get("personality"),                    
                beliefs_values=ind.get("beliefs_values"),
                priorities=ind.get("priorities"),
                life_style=ind.get("life_style"),
                identity=ind.get("identity"),
                capabilities=ind.get("capabilities"),
                family=ind.get("family"),
                marriage_intimate_relationship=ind.get("marriage_intimate_relationship"),
                education=ind.get("education"),
                occupation_job_industry=ind.get("occupation_job_industry"),
                social_economic_status=ind.get("social_economic_status"),
                social_network=ind.get("social_network"),
                biological_characteristics=ind.get("biological_characteristics"),              
            )

    # --- 3. Group Traits ---
    for grp in extracted_info.get("group_traits", []):
        actor = actor_map.get(grp.get("actor"))
        if actor and actor.actor_type == Actors.GROUP:
            GroupTraits.objects.create(
                user=user,
                scenario=scenario,
                actor=actor,               
                group_type=grp.get("group_type"),
                domain=grp.get("domain"),
                size=grp.get("size"),
                mission_vision_value=grp.get("mission_vision_value"),
                goal_strategy=grp.get("goal_strategy"),
                objectives_plan=grp.get("objectives_plan"),
                governance=grp.get("governance"),
                organizational_structure=grp.get("organizational_structure"),
                operation_system=grp.get("operation_system"),
                organizational_politics=grp.get("organizaional_politics"),
                influence=grp.get("influence"),
                leadership=grp.get("leadership"),
                culture=grp.get("culture"),
                performance=grp.get("performance"),
                challenge=grp.get("challenge"),
                funding_resources_budget=grp.get("funding_resources_budget"),
            )


    # --- 4. Save Interactions ---
    interaction_map = {}
    for inter in extracted_info.get("interactions", []):
        actor = actor_map.get(inter["actor"])
        interaction = Interactions.objects.create(
            user=user,
            scenario=scenario,
            actor=actor,
            behavior_description=inter.get("behavior_description"),
            env=inter.get("env"),
        )
        interaction_map[inter["behavior_id"]] = interaction

    # --- 5. Save InteractionRelations ---
    for rel in extracted_info.get("interaction_relations", []):
        relation = InteractionRelations.objects.create(
            user=user,
            scenario=scenario,
            source=interaction_map.get(rel["source"]),
            target=interaction_map.get(rel["target"]),
            relation_description=rel.get("relation_description"),
            related_actors_relationship_status=rel.get("related_actors_relationship_status"),
        )
        # add related actors (many-to-many)
        for actor_ref_id in rel.get("related_actors", []):
            if actor_ref_id in actor_map:
                relation.related_actors.add(actor_map[actor_ref_id])



def scenario_mining_view(request, scenario_id=None):

    MAX_FREE_USES = 20

    is_new_scenario = request.GET.get('new', 'false').lower() == 'true' or scenario_id is None
    scenario = None 

    # --- Refill form data after login ---
    prefill_data = request.session.pop('pending_scenario_data', None)

    # Check if it is a new scenario or existing scenario
    if is_new_scenario:
        scenario = ScenarioForMining()
        if prefill_data:
            scenario_form = ScenarioForMiningForm(initial=prefill_data, instance=scenario)
        else:
            scenario_form = ScenarioForMiningForm(request.POST.copy() if request.method == 'POST' else None, instance=scenario)
        
    elif scenario_id:
        # Fetch the specific scenario
        scenario = get_object_or_404(ScenarioForMining, scenario_id=scenario_id, user=request.user)
        scenario_form = ScenarioForMiningForm(request.POST.copy() if request.method == 'POST' else None, instance=scenario)
        
    else:
        # Default behavior: redirect to My Resources
        return redirect('my_scenarios_mining')


    free_trial = None
    subscription = None
    if request.user.is_authenticated:      
        # Fetch subscription status and free trial status       
        free_trial = UserFreeTrialScenarioMining.objects.filter(user=request.user).first()
        subscription = UserSubscription.objects.filter(user=request.user, subscription_status='active').first()

    task_ids = {}

    if request.method == 'POST':
    
        if 'submit_scenario' in request.POST:
            if not request.user.is_authenticated:
                # --- Save data for after login ---
                data = request.POST.dict()
                data.pop('csrfmiddlewaretoken', None)
                request.session['pending_scenario_data'] = data
                # messages.error(request, _("Please log in."))
                return redirect(f"{reverse('login')}?next={request.path}")
                  
            if scenario_form.is_valid():
                with transaction.atomic():
                                          
                    # Check if the user can submit a scenario
                    if not (free_trial and not free_trial.has_used_free_trial) and not subscription:   
                    # No free trial left and no subscription
                        # messages.error(request, _("You must have an active subscription to submit a scenario."))
                        return redirect('subscription_plan')
        
                    ## New scenario submission
                    #if is_new_scenario:

                    #    # Check for exceeding scenario creation attempts
                    #    if free_trial and free_trial.scenario_creation_attempts > 0 and not subscription:
                    #        # messages.error(request, _("You have exceeded the free trial limit for scenario creation."))
                    #        return redirect('subscription_plan')
                     
                       
                    # Scenario submission
                    scenario = scenario_form.save(commit=False)
                    scenario.user = request.user
                    scenario.scenario_input_time = timezone.now()
                    scenario.save()
                                          
                    try:
                        # Call LLM
                        extracted_info = extract_info_from_scenario(scenario.scenario_input)

                        # Save extracted info
                        save_extracted_info(scenario.user, scenario, extracted_info)

                        scenario.scenario_form_submission_count += 1  # Increment counter for each submission
                        scenario.scenario_submitted = True
                                    
                        # if scenario.scenario_form_submission_count == 1:
                            # messages.success(request, _("experience mining is done !"))
                        # else:
                            # messages.success(request, _("Submit new experience!"))
                    
                        scenario.save(update_fields=["scenario_form_submission_count", "scenario_submitted"])


                    except Exception as e:
                        logger.exception("Error in extracting info")
                        # messages.error(request, _("Something went wrong while extracting info."))
                        return redirect('existing_scenario_mining', scenario_id=scenario.scenario_id)  
                                        
                    
                    # Trigger independent async tasks

                    actors_task = build_scenario_actors_task.delay(scenario.scenario_id)
                    dynamics_task = build_scenario_dynamics_task.delay(scenario.scenario_id)
                    needs_task = build_scenario_needs_task.delay(scenario.scenario_id)
                    skills_resources_task = build_scenario_skills_resources_task.delay(scenario.scenario_id)
                    analysis_prediction_task = build_scenario_analysis_prediction_task.delay(scenario.scenario_id)
                    
                    # Launch chord: run two updates in parallel, then build global
                    workflow = chord(
                        [update_individual_profile_task.s(scenario.user_id),
                        update_group_profile_task.s(scenario.user_id)
                        ]
                    )(
                        build_global_actors_profiles_task.s(user_id=scenario.user_id)
                        | build_social_network_graph_task.s()
                    )


                    # Build social network graph (user-specific)
                    # graph_task = build_social_network_graph_task.delay(scenario.user_id)
                    
                    task_ids = {
                        "Actor": actors_task.id,
                        "Dynamics": dynamics_task.id,
                        "Needs": needs_task.id,
                        "Skills_Resources": skills_resources_task.id,
                        "Analysis_Prediction": analysis_prediction_task.id,
                        #"Graph": graph_task.id,
                        "Profile+Graph": workflow.id,
                    }
                                    
                    # Mark the free trial as used
                    
                    if free_trial and not free_trial.has_used_free_trial and not subscription:
                        free_trial.scenario_creation_attempts += 1

                        if free_trial.scenario_creation_attempts >= MAX_FREE_USES:
                            free_trial.has_used_free_trial = True

                        free_trial.save()
                        # messages.success(request, _("You have completed the free trial."))

                    return redirect('existing_scenario_mining', scenario_id=scenario.scenario_id)  # Redirect to refresh the page


    # Context for template rendering
    context = {
        'free_trial': free_trial,
        'subscription': subscription,
        "is_new_scenario": is_new_scenario,
        'scenario': scenario,
        'scenario_form': scenario_form,
        "task_ids": task_ids,
    }

    return render(request, 'solutions/scenario_mining.html', context)


@login_required
def get_scenario_actors_traits_view(request, scenario_id):
    try:
        traits = ScenarioActors.objects.get(scenario_id=scenario_id, user=request.user)
        return JsonResponse({"status": "ready", "result": traits.scenario_actors_traits})
    except ScenarioActors.DoesNotExist:
        return JsonResponse({"status": "pending"})


@login_required
def get_scenario_dynamics_view(request, scenario_id):
    try:
        dynamics = ScenarioDynamics.objects.get(scenario_id=scenario_id, user=request.user)
        return JsonResponse({"status": "ready", "result": dynamics.scenario_dynamics})
    except ScenarioDynamics.DoesNotExist:
        return JsonResponse({"status": "pending"})


@login_required
def get_scenario_needs_view(request, scenario_id):
    try:
        needs = ScenarioNeeds.objects.get(scenario_id=scenario_id, user=request.user)
        return JsonResponse({"status": "ready", "result": needs.scenario_needs})
    except ScenarioNeeds.DoesNotExist:
        return JsonResponse({"status": "pending"})


@login_required
def get_scenario_skills_resources_view(request, scenario_id):
    try:
        skills_resources = ScenarioSkillsResources.objects.get(scenario_id=scenario_id, user=request.user)
        return JsonResponse({"status": "ready", "result": skills_resources.scenario_skills_resources})
    except ScenarioSkillsResources.DoesNotExist:
        return JsonResponse({"status": "pending"})


@login_required
def get_scenario_analysis_prediction_view(request, scenario_id):
    try:
        analysis_prediction = ScenarioAnalysisPrediction.objects.get(scenario_id=scenario_id, user=request.user)
        return JsonResponse({"status": "ready", "result": analysis_prediction.scenario_analysis_prediction})
    except ScenarioAnalysisPrediction.DoesNotExist:
        return JsonResponse({"status": "pending"})


@login_required
def my_scenarios_mining_view(request):
    scenarios = ScenarioForMining.objects.filter(user=request.user).order_by('-scenario_input_time')
    paginator = Paginator(scenarios, 10)  # Show 10 scenarios per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    

    # Debugging outputs
    print(f"Total scenarios for user {request.user.id}: {scenarios.count()}")
    print(f"Page number requested: {page_number}")
    print(f"Scenarios on this page: {[scenario.scenario_id for scenario in page_obj]}")

    return render(request, 'solutions/my_scenarios_mining.html', {
        'page_obj': page_obj,
        'total_scenarios': scenarios.count(),  # Total number of scenarios
    })


@login_required
def delete_selected_experiences(request):
    """Deletes selected experience records."""
    if request.method == "POST":
        selected_ids = request.POST.getlist("selected_experiences")
        if selected_ids:
            ScenarioForMining.objects.filter(
                scenario_id__in=selected_ids,
                user=request.user
            ).delete()
            messages.success(request, f"Deleted {len(selected_ids)} experience(s).")
        else:
            messages.warning(request, "No experiences selected.")
    return redirect("my_scenarios_mining")


def interaction_space_view(request):
    """
    Overall view: renders the page.
    Data for each section is fetched via AJAX from supporting views.
    """
    return render(request, "solutions/interaction_space.html")



def global_actors_profiles(user):
    latest_global_actors_profiles = GlobalActorsProfiles.objects.filter(user=user).order_by('-last_updated').first()

    categories = {"Self": [], "People": [], "Group": []}
    if latest_global_actors_profiles and latest_global_actors_profiles.global_actors_profiles:
        try:
            data = json.loads(latest_global_actors_profiles.global_actors_profiles)

            # Ensure required sections exist
            categories["Self"] = data.get("Self", [])
            categories["People"] = data.get("People", [])
            categories["Group"] = data.get("Group", [])

        except json.JSONDecodeError:
            print("Error decoding global actors JSON. Returning fallback empty categories.")
    
    return categories


@login_required
def get_global_actors_profiles_view(request):
    categories = global_actors_profiles(request.user)
    return JsonResponse(categories, safe=False)


@login_required
def delete_global_actor_profiles(request):
    """Delete one social node (actor or group) and update both profile + graph caches."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("canonical_name")
            if not name:
                return JsonResponse({"error": "No actor name provided"}, status=400)

            # --- Load latest actor profile ---
            profile = GlobalActorsProfiles.objects.filter(user=request.user).order_by('-last_updated').first()
            if not profile or not profile.global_actors_profiles:
                return JsonResponse({"error": "No profiles found"}, status=404)

            # ✅ Always treat as JSON string
            try:
                categories = json.loads(profile.global_actors_profiles)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Corrupted profile JSON"}, status=500)

            found = False
            for cat, entities in categories.items():
                updated = [e for e in entities if e.get("canonical_name", "").strip().lower() != name.strip().lower()]
                if len(updated) != len(entities):
                    categories[cat] = updated
                    found = True
                  
            if found:
                profile.global_actors_profiles = json.dumps(categories, ensure_ascii=False)
                profile.save(update_fields=["global_actors_profiles"])

                # Also remove from IndividualProfile & GroupProfile
                IndividualProfile.objects.filter(user=request.user, canonical_name__iexact=name).delete()                
                GroupProfile.objects.filter(user=request.user, canonical_name__iexact=name).delete()
            
            else:
                return JsonResponse({"error": "Node not found"}, status=404)

            # ---- Remove from SocialNetworkGraphCache ----
            graph_cache = SocialNetworkGraphCache.objects.filter(user=request.user).first()
            if graph_cache and isinstance(graph_cache.graph_data, dict):
                graph_data = graph_cache.graph_data

                # Remove node and its connected edges
                nodes = [
                    n for n in graph_data.get("nodes", []) 
                    if n.get("label", "").strip().lower() != name.strip().lower()
                ]
                edges = [
                    e for e in graph_data.get("edges", [])
                    if e.get("source", "").strip().lower() != name.strip().lower()
                    and e.get("target", "").strip().lower() != name.strip().lower()
                ]
                graph_data["nodes"] = nodes
                graph_data["edges"] = edges
                graph_cache.graph_data = graph_data
                graph_cache.save(update_fields=["graph_data"])

            # --- Rebuild graph for full consistency ---
            build_social_network_graph_task.delay(request.user.id)

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    # Non-POST requests just return a safe response
    return JsonResponse({"error": "Invalid request method"}, status=405)



@login_required
def get_social_network_graph_view(request):
    graph_cache = SocialNetworkGraphCache.objects.filter(user=request.user).first()
    if graph_cache:
        return JsonResponse(graph_cache.graph_data, safe=False)
    return JsonResponse({"status": "pending"}, status=202)



#For simulations
def selected_actors_profiles(user, canonical_names):
    profiles = []
    for name in canonical_names:
        individual = IndividualProfile.objects.filter(user=user, canonical_name=name).first()
        if individual:
            profiles.append({
                "canonical_name": name,
                "traits": {
                    "cognitive_pattern": individual.cognitive_pattern,
                    "affect_pattern": individual.affect_pattern,
                    "action_pattern": individual.action_pattern,
                    "personality": individual.personality,
                    "beliefs_values": individual.beliefs_values,
                    "priorities": individual.priorities,
                    "life_style": individual.life_style,
                    "identity": individual.identity,
                    "capabilities": individual.capabilities,
                    "family": individual.family,
                    "marriage_intimate_relationship": individual.marriage_intimate_relationship,
                    "education": individual.education,
                    "occupation_job_industry": individual.occupation_job_industry,
                    "social_economic_status": individual.social_economic_status,
                    "social_network": individual.social_network,
                    "biological_characteristics": individual.biological_characteristics,
                }
            })
        else:
            group = GroupProfile.objects.filter(user=user, canonical_name=name).first()
            if group:
                profiles.append({
                    "canonical_name": name,
                    "traits": {
                        "group_type": group.group_type,
                        "domain": group.domain,
                        "size": group.size,
                        "mission_vision_value": group.mission_vision_value,   
                        "goal_strategy": group.goal_strategy,    
                        "objectives_plan": group.objectives_plan,    
                        "governance": group.governance,   
                        "organizational_structure": group.organizational_structure,   
                        "operation_system": group.operation_system, 
                        "organizational_politics": group.organizational_politics,  
                        "influence": group.influence, 
                        "leadership": group.leading,
                        "culture": group.culture,    
                        "performance": group.performance,  
                        "challenge": group.challenge,   
                        "funding_resources_budget": group.funding_resources_budget,  
                    }
                })
    return profiles


def selected_actors_relationship_statuses(user, canonical_names):
    """
    Given selected canonical names, find all relationships that link only those actors.
    """
    relations = []

    # Prefetch to avoid N+1 queries
    qs = InteractionRelations.objects.filter(user=user).prefetch_related("related_actors")

    for rel in qs:
        # Map all related actors to their canonical names
        related_canonicals = [resolve_to_canonical(actor.name_or_alias, user) for actor in rel.related_actors.all()]

        # Keep relation only if all involved actors are inside the selection
        if set(related_canonicals).issubset(set(canonical_names)) and rel.related_actors_relationship_status:
            relations.append({
                "actors": related_canonicals,
                "status": rel.related_actors_relationship_status,
            })

    return relations


@csrf_exempt
def generate_simulation_view(request):
    """
    Generate full simulation among selected actors for a given topic.
    """
    if request.method == "POST":
        data = json.loads(request.body)
        canonical_names = data.get("actors", [])
        scenario = data.get("scenario", "").strip()

        # 1. Validate actors
        if not canonical_names or len(canonical_names) < 2:
            return JsonResponse(
                {"error": "At least 2 actors must be selected."},
                status=400
            )

        # 2. Validate scenario length
        if len(scenario) < 50 or len(scenario) > 2500:
            return JsonResponse(
                {"error": "Scenario must be between 50 and 2500 characters."},
                status=400
            )

        # Check login
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required.", "redirect": reverse("login")}, status=401)

        user = request.user
       
        # Check subscription
        subscription = UserSubscription.objects.filter(
            user=user, subscription_status="active"
        ).first()
        if not subscription:
            return JsonResponse(
                {"error": "Subscription required.", "redirect": reverse("subscription_plan")},
                status=402  # Payment Required
            )

        # Get traits + relationships
        profiles = selected_actors_profiles(request.user, canonical_names)
        relations = selected_actors_relationship_statuses(request.user, canonical_names)

       
        simulation = llm_generate_simulation(
            canonical_names=canonical_names,
            scenario=scenario,
            profiles=profiles,
            relations=relations,
        )

        # ✅ enforce 50-turn limit
        if isinstance(simulation, dict) and "simulation" in simulation:
            simulation["simulation"] = simulation["simulation"][:50]   # keep max 50
            
        
        session = GeneratedSimulation.objects.create(
            user=user,
            actors=canonical_names,
            scenario=scenario,
            result=simulation,
            actors_traits_snapshot=profiles,
            actors_relations_snapshot=relations,
        )

        
        return JsonResponse({
            "generated_simulation_id": session.generated_simulation_id,
            "simulation": simulation.get("simulation", [])
        })

    return JsonResponse({"error": "Invalid request"}, status=400)



@csrf_exempt
def live_simulation_view(request):
    """
    Live simulation: user plays one actor ("Me" or any other actor),
    LLM controls the others. Supports continuous turns.
    """
    if request.method == "POST":
        data = json.loads(request.body)

        canonical_names = data.get("actors", [])
        scenario = data.get("scenario", "").strip()
        user_actor = data.get("user_actor")  # "Me" or one of canonical_names
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id")

        # --- validation (before login required) ---
        if not canonical_names or len(canonical_names) < 2:
            return JsonResponse({"error": "At least 2 actors must be selected. If you want to simulate in your own role, please select Me."}, status=400)
        if not scenario or len(scenario) < 50 or len(scenario) > 2500:
            return JsonResponse({"error": "Scenario must be between 50 and 2500 characters."}, status=400)
        if not user_actor or user_actor not in (["Me"] + canonical_names):
            return JsonResponse({"error": "User actor must be 'Me' or one of the selected actors."}, status=400)
        if not user_message:
            return JsonResponse({"error": "Message cannot be empty."}, status=400)

        # Check login
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required.", "redirect": reverse("login")}, status=401)

        user = request.user

        # Check subscription
        subscription = UserSubscription.objects.filter(
            user=user, subscription_status="active"
        ).first()
        if not subscription:
            return JsonResponse(
                {"error": "Subscription required.", "redirect": reverse("subscription_plan")},
                status=402  # Payment Required
            )

        # --- start new session or continue existing ---
        if session_id:
            try:
                session = LiveSimulation.objects.get(live_simulation_id=session_id, user=user)
            except LiveSimulation.DoesNotExist:
                return JsonResponse({"error": "Invalid session ID."}, status=404)
        else:
            profiles = selected_actors_profiles(request.user, canonical_names)
            relations = selected_actors_relationship_statuses(request.user, canonical_names)

            session = LiveSimulation.objects.create(
                user=user,
                actors=canonical_names,
                scenario=scenario,
                interactions=[],
                actors_profiles_snapshot=profiles,
                actors_relation_statuses_snapshot=relations
            )

        # ✅ Add backend safeguard here
        if len(session.interactions) >= 100:
            return JsonResponse({"error": "Chat ended: maximum 100 turns reached."}, status=400)

        # --- build conversation history ---
        history = session.interactions.copy()
        history.append({"actor": user_actor, "type": "speech", "content": user_message})

        # --- call LLM ---
        llm_response = llm_generate_live_simulation(
            session=session,
            user_actor=user_actor,
            user_message=user_message,
            history=history
        )

        # --- update session ---
        session.interactions.append({"actor": user_actor, "type": "speech", "content": user_message})
        if isinstance(llm_response, dict) and "responses" in llm_response:
            responses = llm_response["responses"][:100 - len(session.interactions)]
            session.interactions.extend(responses)
        else:
            session.interactions.append({"actor": "Systems", "type": "error", "content": str(llm_response)})

        session.save(update_fields=["interactions", "updated_at"])

        return JsonResponse({
            "session_id": session.live_simulation_id,
            "llm_response": llm_response.get("responses", []) if isinstance(llm_response, dict) else [],
            "history": session.interactions
        })

    return JsonResponse({"error": "Invalid request"}, status=400)



@login_required
def my_simulations_view(request):
    generated = GeneratedSimulation.objects.filter(user=request.user).values(
        "generated_simulation_id", "created_at", "scenario"
    )
    for g in generated:
        g["id"] = g.pop("generated_simulation_id")
        g["preview"] = g["scenario"]
        g["type"] = "Generated"

    live = LiveSimulation.objects.filter(user=request.user).values(
        "live_simulation_id", "created_at", "scenario"
    )
    for l in live:
        l["id"] = l.pop("live_simulation_id")
        l["preview"] = l["scenario"]
        l["type"] = "Live"

    combined = sorted(list(generated) + list(live), key=lambda x: x["created_at"], reverse=True)

    paginator = Paginator(combined, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "solutions/my_simulations.html", {
        "page_obj": page_obj,
        "total_simulations": len(combined)
    })

def generated_simulation_detail(request, pk):
    sim = get_object_or_404(GeneratedSimulation, pk=pk, user=request.user)
    context = {
        "simulation": sim,
        "type": "Generated",
    }
    return render(request, "solutions/my_simulation_detail.html", context)


def live_simulation_detail(request, pk):
    sim = get_object_or_404(LiveSimulation, pk=pk, user=request.user)
    context = {
        "simulation": sim,
        "type": "Live",
    }
    return render(request, "solutions/my_simulation_detail.html", context)


@login_required
def delete_selected_simulations(request):
    if request.method == "POST":
        selected_data = request.POST.get("selected_data", "")
        if not selected_data:
            messages.warning(request, "No simulations selected.")
            return redirect("my_simulations")

        # Example format: "Generated:12,Live:8,Generated:5"
        items = selected_data.split(",")
        gen_ids = []
        live_ids = []
        for item in items:
            try:
                sim_type, sim_id = item.split(":")
                if sim_type == "Generated":
                    gen_ids.append(sim_id)
                elif sim_type == "Live":
                    live_ids.append(sim_id)
            except ValueError:
                continue

        deleted_count = 0
        if gen_ids:
            deleted_count += GeneratedSimulation.objects.filter(
                user=request.user, generated_simulation_id__in=gen_ids
            ).delete()[0]
        if live_ids:
            deleted_count += LiveSimulation.objects.filter(
                user=request.user, live_simulation_id__in=live_ids
            ).delete()[0]

        messages.success(request, f"Deleted {deleted_count} simulations successfully.")
        return redirect("my_simulations")

    return redirect("my_simulations")



def transcribe_audio_view(request):
    if request.method == 'POST':
        audio_file = request.FILES.get('audio')
        if not audio_file:
            logger.warning("Transcription request received with no audio file provided.")
            return JsonResponse({'error': 'No audio file provided'}, status=400)

        if audio_file.content_type.startswith('video/'):
            audio_file.content_type = 'audio/mp4'
            logger.info(f"Received video MIME {audio_file.content_type}, forcing audio/mp4.")
        
        try:
            headers = {
                'Authorization': f'Token {settings.DEEPGRAM_API_KEY}',
                'Content-Type': audio_file.content_type,
            }

            audio_file.seek(0) # Ensure the file pointer is at the beginning for streaming

            response = requests.post(
                'https://api.deepgram.com/v1/listen?punctuate=true&detect_language=true',
                headers=headers,
                data=audio_file,
                #files={'audio': (audio_file.name, audio_file, audio_file.content_type)}
            )

            if not response.ok:

                try:
                    error_data = response.json()
                    deepgram_error_message = error_data.get('err_msg') or \
                                            error_data.get('error') or \
                                            error_data.get('message', f'Unknown Deepgram error for status {response.status_code}')
                    logger.error(f"Deepgram API returned an error ({response.status_code}): {deepgram_error_message}")
                    return JsonResponse({'error': f'Transcription failed: {deepgram_error_message}'}, status=response.status_code)
                except requests.exceptions.JSONDecodeError:
                    logger.error(f"Deepgram API returned a non-JSON error ({response.status_code}): {response.text}")
                    return JsonResponse({'error': f'Transcription failed: Deepgram API error (Status: {response.status_code})'}, status=response.status_code)

            result = response.json()
            transcript = result.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0].get('transcript', '')

            logger.info(f"Successfully transcribed audio. Transcript length: {len(transcript)} characters.")
            return JsonResponse({'transcript': transcript})
        
        except requests.exceptions.RequestException as req_e:
            logger.exception("Network error communicating with Deepgram API:")
            return JsonResponse({'error': 'Network error during transcription. Please try again.'}, status=500)
        except Exception as e:
            logger.exception("An unexpected internal error occurred during audio transcription.")
            return JsonResponse({'error': 'An internal server error occurred. Please contact support if the issue persists.'}, status=500)
