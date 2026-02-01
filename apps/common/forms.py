# apps/common/forms.py など（新規）
from django import forms

class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True
