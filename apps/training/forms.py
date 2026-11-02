"""Guide and category forms for authorized documentation authors."""

from django import forms
from django.utils.text import slugify

from apps.inventory.models import Asset, Room
from .models import TrainingCategory, TrainingGuide


class TrainingGuideForm(forms.ModelForm):
    assets = forms.ModelMultipleChoiceField(queryset=Asset.objects.select_related('room').order_by('inventory_number'), required=False, widget=forms.SelectMultiple(attrs={'size': 7}))
    rooms = forms.ModelMultipleChoiceField(queryset=Room.objects.order_by('name'), required=False, widget=forms.SelectMultiple(attrs={'size': 6}))

    class Meta:
        model = TrainingGuide
        fields = ('title', 'slug', 'summary', 'category', 'tags', 'content_markdown', 'assets', 'rooms')
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 2}),
            'content_markdown': forms.Textarea(attrs={'rows': 24, 'spellcheck': 'true'}),
            'tags': forms.TextInput(attrs={'placeholder': 'zoom, audio, troubleshooting'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['category'].queryset = TrainingCategory.objects.filter(is_active=True).order_by('display_order', 'name')
        if self.instance.pk and self.instance.category_id:
            self.fields['category'].queryset = TrainingCategory.objects.filter(is_active=True) | TrainingCategory.objects.filter(pk=self.instance.category_id)

    def clean_slug(self):
        value = self.cleaned_data.get('slug') or slugify(self.cleaned_data.get('title', ''))
        if self.instance.pk and self.instance.published_revision_id and value != self.instance.slug:
            raise forms.ValidationError('A published guide URL is permanent so existing bookmarks keep working.')
        qs = TrainingGuide.objects.filter(slug=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A guide already uses this URL. Choose a different slug.')
        return value


class GuideReviewForm(forms.Form):
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 4}), label='Review notes')


class TrainingCategoryForm(forms.ModelForm):
    class Meta:
        model = TrainingCategory
        fields = ('name', 'slug', 'description', 'display_order', 'is_active')

    def clean_slug(self):
        value = self.cleaned_data['slug']
        if self.instance.pk and self.instance.slug != value and self.instance.guides.filter(revisions__isnull=False).exists():
            raise forms.ValidationError('This category URL is already recorded in published guide revisions and cannot be changed.')
        return value
