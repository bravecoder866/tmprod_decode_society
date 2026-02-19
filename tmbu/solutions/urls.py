"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""

from django.urls import path
from . import views

urlpatterns = [
    path("solution-center/", views.solution_center_view, name="solution_center"),
    path("my-solutions/", views.my_solutions_view, name="my_solutions"),
    path('scenario-process/', views.scenario_process_view, name='new_scenario'),  
    path('scenario-process/<int:scenario_id>/', views.scenario_process_view, name='existing_scenario'),  
    path('my-scenarios/', views.my_scenarios_view, name='my_scenarios'), 
    path("delete-selected-comprehensive-solutions/", views.delete_selected_comprehensive_solutions, name="delete_selected_comprehensive_solutions"),
    path('scenario-quick-solution/', views.scenario_quick_solution_view, name='new_scenario_quick_solution'),  
    path('scenario-quick-solution/<int:scenario_id>/', views.scenario_quick_solution_view, name='existing_scenario_quick_solution'),  
    path('my-scenarios-quick-solution/', views.my_scenarios_quick_solution_view, name='my_scenarios_quick_solution'),   
    path("delete-selected-quick-solutions/", views.delete_selected_quick_solutions, name="delete_selected_quick_solutions"),
    path('scenario-mining/', views.scenario_mining_view, name='new_scenario_mining'),  
    path('scenario-mining/<int:scenario_id>/', views.scenario_mining_view, name='existing_scenario_mining'),  
    path('my-scenarios-mining/', views.my_scenarios_mining_view, name='my_scenarios_mining'),  
    path("delete-selected-experiences/", views.delete_selected_experiences, name="delete_selected_experiences"),
    path("get-scenario-actors-traits/<int:scenario_id>/", views.get_scenario_actors_traits_view, name="get_scenario_actors_traits"),
    path("get-scenario-dynamics/<int:scenario_id>/", views.get_scenario_dynamics_view, name="get_scenario_dynamics"),
    path("get-scenario-needs/<int:scenario_id>/", views.get_scenario_needs_view, name="get_scenario_needs"),
    path("get-scenario-skills-resources/<int:scenario_id>/", views.get_scenario_skills_resources_view, name="get_scenario_skills_resources"),
    path("get-scenario-analysis-prediction/<int:scenario_id>/", views.get_scenario_analysis_prediction_view, name="get_scenario_analysis_prediction"),    
    path("interaction-space/", views.interaction_space_view, name="interaction_space"),
    path("interaction-space/profiles/", views.get_global_actors_profiles_view, name="get_global_actors_profiles"),
    path("interaction-space/delete-global-actor-profiles/", views.delete_global_actor_profiles, name="delete_global_actor_profiles"),
    path("interaction-space/graph/", views.get_social_network_graph_view, name="get_social_network_graph"), 
    path("interaction-space/generate-simulation/", views.generate_simulation_view, name="generate_simulation"),   
    path("interaction-space/live-simulation/", views.live_simulation_view, name="live_simulation"),
    path("my_simulations/", views.my_simulations_view, name="my_simulations"),
    path("delete-selected-simulations/", views.delete_selected_simulations, name="delete_selected_simulations"),   
    path("simulation/generated/<int:pk>/", views.generated_simulation_detail, name="generated_simulation_detail"),
    path("simulation/live/<int:pk>/", views.live_simulation_detail, name="live_simulation_detail"),
    ]
