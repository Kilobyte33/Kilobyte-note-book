from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import models
from django.db.models import Sum
from main.models import Note, Folder, UserSettings
from .forms import NoteForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect
import json
import zipfile
import io
import re
import os
from django.http import HttpResponse, JsonResponse
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

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
@login_required(login_url='/login/')
def folder_detail(request, folder_id):
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    notes = folder.notes.filter(is_trashed=False)

    return render(request, 'main/folder_detail.html', {
        'folder': folder,
        'notes': notes
    })


@login_required(login_url='/login/')
def create_note_in_folder(request, folder_id):
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip() or 'Untitled Note'
        note = Note.objects.create(
            title=title,
            content='',
            user=request.user,
            folder=folder,
        )
        return redirect('split_editor', id=note.id)
    # GET — just redirect back
    return redirect('folder_detail', folder_id=folder_id)


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
    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'appearance':
            user_settings.dark_mode = 'dark_mode' in request.POST
            user_settings.save()
            messages.success(request, 'Appearance saved.')

        elif action == 'editor':
            mode = request.POST.get('editor_mode', 'split')
            if mode in ('split', 'preview', 'edit'):
                user_settings.editor_mode = mode
                user_settings.save()
            messages.success(request, 'Editor preference saved.')

        elif action == 'password':
            current = request.POST.get('current_password', '')
            new_pw  = request.POST.get('new_password', '')
            confirm = request.POST.get('confirm_password', '')
            user = request.user
            if not user.check_password(current):
                messages.error(request, 'Current password is incorrect.')
            elif len(new_pw) < 6:
                messages.error(request, 'New password must be at least 6 characters.')
            elif new_pw != confirm:
                messages.error(request, 'Passwords do not match.')
            else:
                user.set_password(new_pw)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password updated successfully.')

        return redirect('settings')

    # Storage stats
    notes_count   = Note.objects.filter(user=request.user, is_trashed=False).count()
    folders_count = Folder.objects.filter(user=request.user).count()
    trashed_count = Note.objects.filter(user=request.user, is_trashed=True).count()
    all_content   = Note.objects.filter(user=request.user, is_trashed=False).values_list('content', flat=True)
    total_words   = sum(len(c.split()) for c in all_content)

    return render(request, 'main/settings.html', {
        'settings': user_settings,
        'notes_count': notes_count,
        'folders_count': folders_count,
        'trashed_count': trashed_count,
        'total_words': total_words,
    })


@login_required(login_url='/login/')
def export_notes(request):
    notes = Note.objects.filter(user=request.user, is_trashed=False)
    
    # Create an in-memory zip file
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Keep track of filenames to prevent duplicates in the zip
        used_filenames = set()
        
        for note in notes:
            # Create a safe filename from the note title
            safe_title = re.sub(r'[\\/*?:"<>|]', "", note.title)
            safe_title = safe_title.strip() or "Untitled_Note"
            
            # If the title already exists, append the note ID
            filename = f"{safe_title}.md"
            if filename in used_filenames:
                filename = f"{safe_title}_{note.id}.md"
            
            used_filenames.add(filename)
            
            # Content of the markdown file
            content = note.content or ""
            
            # Add file to zip
            zip_file.writestr(filename, content)
            
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="markdown_notes_backup.zip"'
    return response

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


@login_required(login_url='/login/')
def chatbot(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
        except (json.JSONDecodeError, AttributeError):
            user_message = request.POST.get('message', '').strip()

        uploaded_file = request.FILES.get('file')

        if not user_message and not uploaded_file:
            return JsonResponse({'reply': "Please type a message or select a file first! 😊"})

        reply = get_bot_reply(request.user, user_message, uploaded_file)
        return JsonResponse({'reply': reply})

    return render(request, 'main/chatbot.html')


def get_bot_reply(user, message, uploaded_file=None):
    """Rule-based chatbot that replies based on keywords."""
    msg = message.lower().strip()
    username = user.username

    # ── Greetings ──────────────────────────────────────────────
    greetings = ['hello', 'hi', 'hey', 'howdy', 'sup', 'what\'s up', 'greetings', 'good morning', 'good afternoon', 'good evening']
    if any(g in msg for g in greetings):
        return f"Hey {username}! 👋 Great to see you. How can I help you today?"

    # ── How are you ────────────────────────────────────────────
    if any(p in msg for p in ['how are you', 'how do you do', 'how\'s it going', 'you okay', 'are you okay']):
        return "I'm doing great, thanks for asking! 😄 I'm here and ready to help you with anything."

    # ── Name ──────────────────────────────────────────────────
    if any(p in msg for p in ['your name', 'who are you', 'what are you']):
        return "I'm **Kibo** 🤖 — your personal assistant inside Kilobyte Note Book! Ask me anything."

    # ── Notes ─────────────────────────────────────────────────
    if any(p in msg for p in ['how many notes', 'note count', 'my notes']):
        from main.models import Note
        count = Note.objects.filter(user=user, is_trashed=False).count()
        return f"You currently have **{count} note{'s' if count != 1 else ''}** 📝. Want to create a new one?"

    if any(p in msg for p in ['create note', 'new note', 'add note', 'make note', 'write note']):
        return "To create a note, click **All Notes** in the sidebar, then scroll down to the 'Create New Note' form. ✏️ You can also add notes inside folders!"

    if any(p in msg for p in ['delete note', 'remove note', 'trash note']):
        return "To delete a note, open it and click the 🗑️ trash icon. Deleted notes go to **Trash** and can be restored anytime."

    if any(p in msg for p in ['favourite', 'favorite', 'starred']):
        return "You can mark any note as a favourite ⭐ by clicking the star icon when viewing a note."

    # ── Folders ───────────────────────────────────────────────
    if any(p in msg for p in ['how many folder', 'folder count', 'my folder']):
        from main.models import Folder
        count = Folder.objects.filter(user=user).count()
        return f"You have **{count} folder{'s' if count != 1 else ''}** 📁 set up."

    if any(p in msg for p in ['create folder', 'new folder', 'add folder', 'make folder']):
        return "Go to **Folders** in the sidebar and click **New Folder** to create one. You can then add notes directly inside it! 📁"

    # ── Markdown ───────────────────────────────────────────────
    if any(p in msg for p in ['markdown', 'formatting', 'bold', 'italic', 'syntax']):
        return ("Here's a quick Markdown cheatsheet 📋:\n"
                "- **Bold**: `**text**`\n"
                "- *Italic*: `*text*`\n"
                "- Heading: `# Heading`\n"
                "- List: `- item`\n"
                "- Code: `` `code` ``\n"
                "Check out **Markdown Help** in your settings for the full guide!")

    # ── Settings ──────────────────────────────────────────────
    if any(p in msg for p in ['dark mode', 'theme', 'appearance', 'dark theme', 'light mode']):
        return "You can toggle **Dark Mode** in ⚙️ Settings → Appearance. Your preference is saved automatically!"

    if any(p in msg for p in ['password', 'change password', 'update password', 'security']):
        return "You can change your password in ⚙️ **Settings → Security**. Make sure it's at least 6 characters long."

    if any(p in msg for p in ['export', 'backup', 'download notes']):
        return "You can export all your notes as a ZIP of `.md` files from ⚙️ **Settings → Backup & Data**. 💾"

    if any(p in msg for p in ['setting', 'preferences', 'configure']):
        return "Open ⚙️ **Settings** from the sidebar to control dark mode, editor layout, password, and backups."

    # ── Editor ────────────────────────────────────────────────
    if any(p in msg for p in ['editor', 'split view', 'preview', 'edit mode']):
        return "The editor has three modes: **Split** (write + preview side by side), **Edit only**, and **Preview only**. Change it in ⚙️ Settings → Editor."

    # ── Trash ─────────────────────────────────────────────────
    if any(p in msg for p in ['trash', 'deleted', 'restore', 'recycle']):
        return "Deleted notes live in the **Trash** 🗑️ (sidebar). You can restore or permanently delete them from there."

    # ── Recent ────────────────────────────────────────────────
    if any(p in msg for p in ['recent', 'last edited', 'latest note']):
        return "The **Recent** section (sidebar) shows notes updated in the last 7 days. Great for picking up where you left off! ⏱️"

    # ── Help ──────────────────────────────────────────────────
    if any(p in msg for p in ['help', 'what can you do', 'commands', 'guide']):
        return ("Here's what I can help you with 🤖:\n"
                "- 📝 Notes — creating, deleting, favouriting\n"
                "- 📁 Folders — creating and managing\n"
                "- ✏️ Markdown formatting tips\n"
                "- ⚙️ Settings — dark mode, editor, password, export\n"
                "- 🗑️ Trash & restore\n"
                "- ⏱️ Recent notes\n"
                "Just ask me anything!")

    # ── Thank you ─────────────────────────────────────────────
    if any(p in msg for p in ['thank', 'thanks', 'cheers', 'appreciate']):
        return f"You're very welcome, {username}! 😊 Let me know if there's anything else I can do for you."

    # ── Bye ───────────────────────────────────────────────────
    if any(p in msg for p in ['bye', 'goodbye', 'see you', 'cya', 'farewell']):
        return f"Goodbye, {username}! 👋 Come back anytime. Happy note-taking! 📝"

    # ── Time / date ───────────────────────────────────────────
    if any(p in msg for p in ['time', 'date', 'today', 'day']):
        from django.utils import timezone as tz
        now = tz.localtime(tz.now())
        return f"It's currently **{now.strftime('%A, %B %d, %Y')}** at **{now.strftime('%H:%M')}** 🕐"

    # ── Who made you ──────────────────────────────────────────
    if any(p in msg for p in ['who made you', 'who built you', 'who created you', 'developer', 'creator']):
        return f"I was built into **Kilobyte Note Book** to help users like you navigate and make the most of the app! 🚀"

    # ── Fallback ──────────────────────────────────────────────
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"You are Kibo, an educational tutor and assistant for Kilobyte Note Book. Answer the following question in a helpful and educational manner. Be concise but informative: {message}"
            
            contents = [prompt]
            if uploaded_file:
                if uploaded_file.content_type.startswith('image/'):
                    from PIL import Image
                    img = Image.open(uploaded_file)
                    contents.append(img)
                else:
                    file_text = uploaded_file.read().decode('utf-8', errors='ignore')
                    contents.append(f"\n\n[Attached File Content: {uploaded_file.name}]\n{file_text}")
            
            response = model.generate_content(contents)
            return response.text
        except Exception as e:
            return f"I tried to ask my AI brain, but I encountered an error: {str(e)}"

    if uploaded_file:
        return f"I received your file **{uploaded_file.name}**, but I need a Gemini API key configured in `.env` to analyze attachments! 😅"

    # Free fallback using Wikipedia
    try:
        import wikipedia
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning, module='wikipedia')
        
        search_results = wikipedia.search(message)
        if search_results:
            page_title = search_results[0]
            try:
                summary = wikipedia.summary(page_title, sentences=3, auto_suggest=False)
                return f"Here is what I found on Wikipedia for **{page_title}**:\n\n{summary}\n\n*(Tip: Add a Gemini API key to .env for smarter, conversational AI!)*"
            except wikipedia.exceptions.DisambiguationError as e:
                if e.options:
                    summary = wikipedia.summary(e.options[0], sentences=3, auto_suggest=False)
                    return f"Here is what I found on Wikipedia for **{e.options[0]}**:\n\n{summary}\n\n*(Tip: Add a Gemini API key to .env for smarter, conversational AI!)*"
    except Exception:
        pass

    return (f"Hmm, I'm not sure how to answer that 🤔. "
            f"You asked: *\"{message}\"*\n\n"
            f"Try asking me about notes, folders, markdown, settings, or type **help** to see what I can do! (Note: To enable general education questions, please configure a Gemini API Key in the .env file).")