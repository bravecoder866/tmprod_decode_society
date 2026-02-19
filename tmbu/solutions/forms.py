"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



from django import forms
from .models import Scenario, ScenarioQuickSolution, ScenarioForMining 
from django.utils.translation import gettext_lazy as _



class ScenarioInputForm(forms.ModelForm):
    class Meta:
        model = Scenario
        fields = ['scenario_input']
        labels = {
            'scenario_input': _("Describe a goal or situation:"),  # Mark label for translation
        }

    def __init__(self, *args, **kwargs):
        scenario = kwargs.pop('scenario', None)
        super().__init__(*args, **kwargs)

        scenario_id = scenario.scenario_id if scenario and scenario.pk else 'new'  # Ensure new forms get 'new'
            
        self.fields['scenario_input'].widget = forms.Textarea(attrs={
            'class': 'input-underline',
            'rows': 3,
            # 'placeholder': _('Describe your scenario here...'),
            'id': f'scenario_input_{scenario_id}',  # Unique ID
            'name': f'scenario_input_{scenario_id}',  # Unique Name
        })
    
    def clean_scenario_input(self):
        scenario_input = self.cleaned_data.get('scenario_input')
        # The validator will automatically run and raise ValidationError if needed
        return scenario_input


class SolutionInputForm(forms.ModelForm):
    class Meta:
        model = Scenario
        fields = ['scenario_solution_input']
        labels = {
            'scenario_solution_input': _("Draft a solution:"), 
        }

    def __init__(self, *args, **kwargs):
        scenario = kwargs.pop('scenario', None)  # Extract extra argument
        super().__init__(*args, **kwargs)

        scenario_id = scenario.scenario_id if scenario and scenario.pk else 'new'
        
        self.fields['scenario_solution_input'].widget = forms.Textarea(attrs={
            'class': 'input-underline',
            'rows': 3,
            # 'placeholder': _('Input your solution here...'),
            'id': f'solution_input_{scenario_id}',
            'name': f'solution_input_{scenario_id}',
        })    

    def clean_scenario_solution_input(self):
        scenario_solution_input = self.cleaned_data.get('scenario_solution_input')
        # The validator will automatically run and raise ValidationError if needed
        return scenario_solution_input


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Scenario
        fields = ['user_experience']
        labels = {
            'user_experience': _("Your experience with the solution:"),  # Mark label for translation
        }

    def __init__(self, *args, **kwargs):
        scenario = kwargs.pop('scenario', None)  # Extract extra argument
        super().__init__(*args, **kwargs)

        scenario_id = scenario.scenario_id if scenario and scenario.pk else 'new'
        
        self.fields['user_experience'].widget = forms.Textarea(attrs={
            'class': 'input-underline',
            'rows': 3,
            # 'placeholder': _('Describe your experience here...'),
            'id': f'user_experience_{scenario_id}',
            'name': f'user_experience_{scenario_id}',
        })

    def clean_user_feedback(self):
        user_experience = self.cleaned_data.get('user_experience')
        # The validator will automatically run and raise ValidationError if needed
        return user_experience


class ScenarioInputQuickSolutionForm(forms.ModelForm):
    class Meta:
        model = ScenarioQuickSolution
        fields = ['scenario_input']
        labels = {
            'scenario_input': _("Describe a goal or situation:"),  # Mark label for translation
        }

    def __init__(self, *args, **kwargs):
        scenario = kwargs.pop('scenario', None)
        super().__init__(*args, **kwargs)

        scenario_id = scenario.scenario_id if scenario and scenario.pk else 'new'  # Ensure new forms get 'new'
                
        self.fields['scenario_input'].widget = forms.Textarea(attrs={
            'class': 'input-underline',
            'rows': 3,
            # 'placeholder': _('Describe your scenario here...'),
            'id': f'scenario_input_{scenario_id}',  # Unique ID
            'name': f'scenario_input_{scenario_id}',  # Unique Name
        })
        
    def clean_scenario_input(self):
        scenario_input = self.cleaned_data.get('scenario_input')
        #The validator will automatically run and raise ValidationError if needed
        return scenario_input


class ScenarioForMiningForm(forms.ModelForm):
    class Meta:
        model = ScenarioForMining
        fields = ['scenario_input']
        labels = {
        'scenario_input': _("Input Experience or Observation:"),  # Mark label for translation
        }

    def __init__(self, *args, **kwargs):
        scenario = kwargs.pop('scenario', None)
        super().__init__(*args, **kwargs)

        scenario_id = scenario.scenario_id if scenario and scenario.pk else 'new'  # Ensure new forms get 'new'
            
        self.fields['scenario_input'].widget = forms.Textarea(attrs={
            'class': 'input-underline',
            'rows': 3,
             # 'placeholder': _('Describe your experience here...'),
            'id': f'scenario_input_{scenario_id}',  # Unique ID
            'name': f'scenario_input_{scenario_id}',  # Unique Name
        })
    
    def clean_scenario_input(self):
        scenario_input = self.cleaned_data.get('scenario_input')
        # The validator will automatically run and raise ValidationError if needed
        return scenario_input


