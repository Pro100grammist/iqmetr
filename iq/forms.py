from django import forms


class StartForm(forms.Form):
    name = forms.CharField(label="Ваше ім’я", max_length=120)
    age = forms.IntegerField(label="Вік", min_value=5, max_value=120)
