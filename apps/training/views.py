"""Public published guides and permission-checked authoring workflows."""

from difflib import unified_diff

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import GuideReviewForm, TrainingCategoryForm, TrainingGuideForm
from .models import TrainingCategory, TrainingGuide, TrainingGuideRevision
from .services import public_queryset, publish_guide, render_markdown, restore_working_copy


STARTER_TEMPLATES = {
    'operating': ('Equipment Operating Procedure', '''# Purpose\n\nWhat this equipment is for.\n\n# Before you begin\n\n- Confirm you are authorized to operate the equipment.\n- Identify any required equipment or supplies.\n\n# Steps\n\n1. \n2. \n3. \n\n# Expected result\n\n# When to ask for help\n\n# Related equipment and guides\n'''),
    'troubleshooting': ('Troubleshooting Guide', '''# Purpose\n\n# Symptoms\n\n# Before you begin\n\n- Check that you are authorized to perform these steps.\n- Do not change network or managed equipment settings without approval.\n\n# Troubleshooting steps\n\n1. Observe and record the symptom.\n2. Check the approved user-facing controls and connections.\n3. Stop if the issue requires an unauthorized configuration change.\n\n# Expected results\n\n# When to escalate\n\n# Related equipment and guides\n'''),
    'maintenance': ('Maintenance Procedure', '''# Purpose\n\n# Scope and authorization\n\nIdentify who may perform this work and any FMG approval required.\n\n# Before you begin\n\n# Procedure\n\n1. \n2. \n3. \n\n# Completion checks\n\n# Record keeping\n\n# Escalation\n'''),
    'setup': ('Installation or Setup Procedure', '''# Purpose\n\n# Scope and authorization\n\n# Required equipment\n\n# Before you begin\n\n# Setup steps\n\n1. \n2. \n3. \n\n# Verification\n\n# Rollback or escalation\n'''),
    'quick-reference': ('Quick Reference Guide', '''# Purpose\n\n# Quick steps\n\n1. \n2. \n3. \n\n# If something goes wrong\n\n# Need help?\n'''),
}


def index(request):
    """Published training landing page with safe search and category counts."""
    search = request.GET.get('q', '').strip()[:100]
    guides = public_queryset()
    if search:
        guides = guides.filter(
            Q(published_revision__title__icontains=search)
            | Q(published_revision__summary__icontains=search)
            | Q(published_revision__content_markdown__icontains=search)
            | Q(published_revision__tags__icontains=search)
            | Q(published_revision__category_name__icontains=search)
        ).distinct()
    categories = TrainingCategory.objects.filter(is_active=True).annotate(
        public_guide_count=Count('guides', filter=Q(guides__published_revision__isnull=False) & ~Q(guides__status='archived'), distinct=True),
    )
    recently_updated = public_queryset().order_by('-published_revision__published_at')[:6]
    results = Paginator(guides.order_by('published_revision__title'), 20).get_page(request.GET.get('page')) if search else None
    return render(request, 'training/index.html', {
        'categories': categories, 'recently_updated': recently_updated,
        'search': search, 'results': results,
    })


def category_detail(request, slug):
    category = get_object_or_404(TrainingCategory, slug=slug, is_active=True)
    guides = public_queryset().filter(published_revision__category_slug=category.slug).order_by('published_revision__title')
    page = Paginator(guides, 24).get_page(request.GET.get('page'))
    return render(request, 'training/category_detail.html', {'category': category, 'page': page})


def guide_detail(request, slug):
    guide = get_object_or_404(public_queryset(), slug=slug)
    revision = guide.published_revision
    related = public_queryset().filter(published_revision__category_slug=revision.category_slug).exclude(pk=guide.pk).order_by('published_revision__title')[:5]
    word_count = len(revision.content_markdown.split())
    reading_minutes = max(1, (word_count + 199) // 200)
    return render(request, 'training/guide_detail.html', {
        'guide': guide, 'revision': revision, 'content_html': render_markdown(revision.content_markdown),
        'related_guides': related, 'reading_minutes': reading_minutes,
        'related_references': revision.related_references,
    })


@login_required
@permission_required('training.view_trainingguide', raise_exception=True)
def guide_list(request):
    status = request.GET.get('status', '')
    valid_statuses = dict(TrainingGuide.PublicationStatus.choices)
    if status and status not in valid_statuses:
        status = ''
    search = request.GET.get('q', '').strip()[:100]
    guides = TrainingGuide.objects.select_related('category', 'last_editor', 'published_revision').all()
    if status:
        guides = guides.filter(status=status)
    if search:
        guides = guides.filter(Q(title__icontains=search) | Q(summary__icontains=search) | Q(tags__icontains=search) | Q(slug__icontains=search))
    page = Paginator(guides.order_by('-updated_at'), 25).get_page(request.GET.get('page'))
    return render(request, 'training/manage/guide_list.html', {
        'page': page, 'status': status, 'status_choices': TrainingGuide.PublicationStatus.choices,
        'search': search,
    })


@login_required
@permission_required('training.add_trainingguide', raise_exception=True)
def guide_create(request):
    starter = request.GET.get('template', '')
    initial = {}
    if starter in STARTER_TEMPLATES:
        initial['title'], initial['content_markdown'] = STARTER_TEMPLATES[starter]
    form = TrainingGuideForm(request.POST or None, initial=initial)
    preview_html = None
    if request.method == 'POST' and request.POST.get('action') == 'preview':
        preview_html = render_markdown(request.POST.get('content_markdown', ''))
    elif request.method == 'POST' and form.is_valid():
        guide = form.save(commit=False)
        guide.author = request.user
        guide.last_editor = request.user
        guide.status = TrainingGuide.PublicationStatus.DRAFT
        guide.save()
        form.save_m2m()
        messages.success(request, 'Draft guide saved. It is not public until reviewed and published.')
        return redirect('training:manage_guide_edit', pk=guide.pk)
    return render(request, 'training/manage/guide_form.html', {
        'form': form, 'guide': None, 'preview_html': preview_html,
        'starter_templates': STARTER_TEMPLATES,
        'policy_reminder': True,
    })


@login_required
@permission_required('training.change_trainingguide', raise_exception=True)
def guide_edit(request, pk):
    guide = get_object_or_404(TrainingGuide.objects.select_related('published_revision'), pk=pk)
    if guide.status == TrainingGuide.PublicationStatus.ARCHIVED:
        raise PermissionDenied('Restore an archived guide revision before editing it.')
    form = TrainingGuideForm(request.POST or None, instance=guide)
    preview_html = None
    if request.method == 'POST' and request.POST.get('action') == 'preview':
        preview_html = render_markdown(request.POST.get('content_markdown', ''))
    elif request.method == 'POST' and form.is_valid():
        guide = form.save(commit=False)
        if guide.status == TrainingGuide.PublicationStatus.IN_REVIEW:
            guide.status = TrainingGuide.PublicationStatus.DRAFT
            guide.review_date = None
            guide.reviewer = None
        guide.last_editor = request.user
        guide.save()
        form.save_m2m()
        messages.success(request, 'Working guide saved. Public readers continue to see the last published revision until you publish a new one.')
        return redirect('training:manage_guide_edit', pk=guide.pk)
    return render(request, 'training/manage/guide_form.html', {
        'form': form, 'guide': guide, 'preview_html': preview_html,
        'starter_templates': STARTER_TEMPLATES, 'policy_reminder': True,
    })


@login_required
@permission_required('training.change_trainingguide', raise_exception=True)
@require_POST
def guide_submit_review(request, pk):
    guide = get_object_or_404(TrainingGuide, pk=pk)
    if guide.status == TrainingGuide.PublicationStatus.ARCHIVED:
        raise PermissionDenied('Archived guides must be restored before review.')
    guide.status = TrainingGuide.PublicationStatus.IN_REVIEW
    guide.last_editor = request.user
    guide.save(update_fields=('status', 'last_editor', 'updated_at'))
    messages.success(request, 'Guide submitted for review. Its current published revision remains public until archived or replaced.')
    return redirect('training:manage_guide_edit', pk=guide.pk)


@login_required
@permission_required('training.review_trainingguide', raise_exception=True)
def guide_review(request, pk):
    guide = get_object_or_404(TrainingGuide, pk=pk)
    if guide.status != TrainingGuide.PublicationStatus.IN_REVIEW:
        raise PermissionDenied('Only guides in review can be reviewed.')
    form = GuideReviewForm(request.POST or None, initial={'notes': guide.review_notes})
    if request.method == 'POST' and form.is_valid():
        guide.review_notes = form.cleaned_data['notes']
        if request.POST.get('action') == 'return':
            guide.status = TrainingGuide.PublicationStatus.DRAFT
            guide.review_date = None
            guide.reviewer = None
            messages.info(request, 'Guide returned to Draft with review notes.')
        elif request.POST.get('action') == 'approve':
            guide.review_date = timezone.localdate()
            guide.reviewer = request.user
            messages.success(request, 'Review recorded. Publishing remains a separate explicit action.')
        guide.last_editor = request.user
        guide.save()
        return redirect('training:manage_guide_edit', pk=guide.pk)
    return render(request, 'training/manage/review.html', {
        'guide': guide, 'form': form,
        'preview_html': render_markdown(guide.content_markdown),
    })


@login_required
@permission_required('training.publish_trainingguide', raise_exception=True)
def guide_publish(request, pk):
    guide = get_object_or_404(TrainingGuide.objects.select_related('category'), pk=pk)
    if request.method == 'POST':
        if request.POST.get('confirm_publish') != 'yes':
            messages.error(request, 'Confirm publication before publishing this guide.')
        else:
            if guide.status == TrainingGuide.PublicationStatus.IN_REVIEW and not guide.review_date:
                guide.review_date = timezone.localdate()
                guide.reviewer = request.user
                guide.save(update_fields=('review_date', 'reviewer', 'updated_at'))
            try:
                publish_guide(guide, editor=request.user)
            except ValidationError as error:
                messages.error(request, error.messages[0])
            else:
                messages.success(request, f'Published revision {guide.published_revision.revision_number}.')
                return redirect('training:manage_guide_revisions', pk=guide.pk)
    return render(request, 'training/manage/publish_confirm.html', {'guide': guide})


@login_required
@permission_required('training.archive_trainingguide', raise_exception=True)
def guide_archive(request, pk):
    guide = get_object_or_404(TrainingGuide, pk=pk)
    if request.method == 'POST' and request.POST.get('confirm_archive') == 'yes':
        guide.status = TrainingGuide.PublicationStatus.ARCHIVED
        guide.last_editor = request.user
        guide.save(update_fields=('status', 'last_editor', 'updated_at'))
        messages.success(request, 'Guide archived. Its revisions remain in history.')
        return redirect('training:manage_guides')
    return render(request, 'training/manage/archive_confirm.html', {'guide': guide})


@login_required
@permission_required('training.view_trainingguiderevision', raise_exception=True)
def guide_revisions(request, pk):
    guide = get_object_or_404(TrainingGuide, pk=pk)
    revisions = Paginator(guide.revisions.select_related('editor', 'author').all(), 25).get_page(request.GET.get('page'))
    revision_id = request.GET.get('compare', '')
    selected = guide.revisions.filter(pk=revision_id).first() if revision_id.isdigit() else None
    current = guide.published_revision
    diff_lines = None
    if selected and current and selected.pk != current.pk:
        diff_lines = list(unified_diff(
            selected.content_markdown.splitlines(), current.content_markdown.splitlines(),
            fromfile=f'Revision {selected.revision_number}', tofile=f'Revision {current.revision_number}', lineterm='',
        ))
    return render(request, 'training/manage/revisions.html', {
        'guide': guide, 'page': revisions, 'selected_revision': selected,
        'current_revision': current, 'diff_lines': diff_lines,
    })


@login_required
@permission_required('training.restore_trainingguide', raise_exception=True)
@require_POST
def guide_restore(request, pk, revision_pk):
    guide = get_object_or_404(TrainingGuide, pk=pk)
    revision = get_object_or_404(TrainingGuideRevision, pk=revision_pk)
    try:
        restore_working_copy(guide, revision, editor=request.user)
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect('training:manage_guide_revisions', pk=guide.pk)
    messages.success(request, f'Revision {revision.revision_number} copied into a new working version. Revision history was preserved.')
    return redirect('training:manage_guide_edit', pk=guide.pk)


@login_required
@permission_required('training.view_trainingcategory', raise_exception=True)
def category_list(request):
    categories = TrainingCategory.objects.annotate(guide_count=Count('guides')).all()
    active = request.GET.get('active')
    if active == '1': categories = categories.filter(is_active=True)
    elif active == '0': categories = categories.filter(is_active=False)
    return render(request, 'training/manage/category_list.html', {'categories': categories})


@login_required
@permission_required('training.add_trainingcategory', raise_exception=True)
def category_create(request):
    form = TrainingCategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Training category created.')
        return redirect('training:manage_categories')
    return render(request, 'training/manage/category_form.html', {'form': form, 'is_edit': False})


@login_required
@permission_required('training.change_trainingcategory', raise_exception=True)
def category_edit(request, pk):
    category = get_object_or_404(TrainingCategory, pk=pk)
    form = TrainingCategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Training category updated.')
        return redirect('training:manage_categories')
    return render(request, 'training/manage/category_form.html', {'form': form, 'category': category, 'is_edit': True})
