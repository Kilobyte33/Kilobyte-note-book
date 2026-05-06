from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import models
from django.db.models import Sum
from main.models import Note, Folder, UserSettings
from .forms import NoteForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect

@login_required(login_url='/login/')
def dashboard(request):
    notes_count = Note.objects.filter(user=request.user, is_trashed=False).count()
    folders_count = Folder.objects.filter(user=request.user).count()
    favorites_count = Note.objects.filter(user=request.user, is_favorite=True, is_trashed=False).count()

    ['total'] or 0
    recent_notes = Note.objects.filter(user=request.user, is_trashed=False).order_by('-updated_at')[:5]
    favorite_notes = Note.objects.filter(user=request.user, is_favorite=True, is_trashed=False)[:5]
    return render(request, 'main/dashboard.html', {
        'notes_count': notes_count,
        'folders_count': folders_count,
        'favorites_count': favorites_count,
    
        'recent_notes': recent_notes,
        'favorite_notes': favorite_notes,
    })

# Folders view
@login_required(login_url='/login/')
def folders(request):
    folders_list = Folder.objects.filter(user=request.user)
    return render(request, 'main/folders.html', {'folders': folders_list})

# New folder view
@login_required(login_url='/login/')
def new_folder(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Folder.objects.create(name=name, user=request.user)
            return redirect('folders')
    return render(request, 'main/folders.html', {'folders': Folder.objects.filter(user=request.user), 'error': 'Folder name required'})
def folder_detail(request, folder_id):
    folder = get_object_or_404(Folder, id=folder_id)
    notes = folder.notes.all()  

    return render(request, 'main/folder_detail.html', {
        'folder': folder,
        'notes': notes
    })


@login_required(login_url='/login/')
def home(request):
    notes = Note.objects.filter(user=request.user)
    form = NoteForm(request.POST or None)

    if form.is_valid():
        note = form.save(commit=False)
        note.user = request.user 
        note.save()
        messages.success(request, 'Note added successfully!')
        return redirect('home')

    context = {
        'notes': notes,
        'form': form
    }
    return render(request, 'main/home.html', context)

@login_required(login_url='/login/')
def edit_note(request, id):
    note = Note.objects.get(id=id, user=request.user)
    form = NoteForm(request.POST or None, instance=note)

    if form.is_valid():
        form.save()
        return redirect('home')

    return render(request, 'main/edit.html', {'form': form})

@login_required(login_url='/login/')
def delete_note1(request, id):
    note = Note.objects.get(id=id, user=request.user)
    if request.method == 'POST':
        note.delete()
        return redirect('home')
    return render(request, 'main/delete_note.html', {'note': note})

def register_user(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            return render(request, 'main/register.html', {
                'error': 'Username already exists'
            })

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        
        login(request, user)
        messages.success(request, f'Welcome, {username}! Your account has been created.')
        return redirect('dashboard')

    return render(request, 'main/register.html')

def login_user(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'main/login.html')

def redirect_root(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

def logout_user(request):
    logout(request)
    return redirect('/login/')

@login_required(login_url='/login/')
def settings(request):
    settings, _ = UserSettings.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        dark_mode = bool(request.POST.get('dark_mode'))
        settings.dark_mode = dark_mode
        settings.save()
    return render(request, 'main/settings.html', {'settings': settings})

@login_required(login_url='/login/')
def trash(request):
    trashed_notes = Note.objects.filter(is_trashed=True).order_by('-deleted_at')
    return render(request, 'main/trash.html', {
        'trashed_notes': trashed_notes
    })

@login_required(login_url='/login/')
def restore_note(request, id):
    note = get_object_or_404(Note, id=id, is_trashed=True)
    note.is_trashed = False
    note.trashed_at = None
    note.save()
    return redirect('trash')

@login_required(login_url='/login/')

def delete_note(request, id):
    note = get_object_or_404(Note, id=id)
    note.is_trashed = True
    note.trashed_at = timezone.now()
    note.save()
    return redirect('trash')

def delete_forever(request, id):
    note = get_object_or_404(Note, id=id, is_trashed =True)
    note.delete()  
    return redirect('trash')

def empty_trash(request):
    Note.objects.filter(is_trashed =True).delete()
    return redirect('trash')

@login_required(login_url='/login/')
def markdown_help(request):
    return render(request, 'main/markdown_help.html')

@login_required(login_url='/login/')
def note_view(request, id):
    note = Note.objects.get(id=id, user=request.user)
    return render(request, 'main/note_view.html', {'note': note})

@login_required(login_url='/login/')
def split_editor(request, id):
    note = Note.objects.get(id=id, user=request.user)
    preview_html = note.content 
    if request.method == 'POST':
        note.title = request.POST.get('title')
        note.content = request.POST.get('content')
        note.save()
        return redirect('note_view', id=note.id)
    return render(request, 'main/split_editor.html', {'form': note, 'preview_html': preview_html})


@login_required(login_url='/login/')

def recent_notes(request):
    last_7_days = timezone.now() - timedelta(days=7)
    recent_notes = Note.objects.filter(
        updated_at__gte=last_7_days
    ).order_by('-updated_at')

    return render(request, 'main/recent.html', {
        'notes': recent_notes
    })