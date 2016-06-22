from django import forms


class DirectoryCreateForm(forms.Form):
    directory_name = forms.CharField( widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '1'}))
