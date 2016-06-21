from django import forms


class DirectoryCreateForm(forms.Form):
    directory_name = forms.CharField()
