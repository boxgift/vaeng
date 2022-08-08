from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from app.models import PageReview, Tag, Blog, BlogReview, Page, Category


class PageReviewForm(forms.ModelForm):
    class Meta:
        model = PageReview
        fields = ['text', ]


class BlogReviewForm(forms.ModelForm):
    class Meta:
        model = BlogReview
        fields = ['text']


class UserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1']


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name']


class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['name', 'content', 'meta', 'title']


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'title', 'slug']


class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = ['name', 'content', 'category', 'meta', 'title']


class PageEditForm(PageForm):
    class Meta:
        model = Page
        fields = ['name', 'content', 'category', 'meta', 'title', 'url']

    def save(self, commit=True):
        form = super(PageEditForm, self).save(commit=False)
        url = self.cleaned_data['url']
        if commit:
            form.url = url[:-1] if url[-1] == '/' else url
            form.save()
        return form
