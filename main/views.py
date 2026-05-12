from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import models
from django.db.models import Sum
from main.models import Note, Folder, UserSettings, ChatMessage
from .forms import NoteForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.utils import timezone
from datetime import timedelta
from main.models import ChatMessage # Keep this for history loading
from django.shortcuts import get_object_or_404, redirect
import json
import zipfile
import io
import re
import os
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
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
    trashed_notes = Note.objects.filter(user=request.user, is_trashed=True).order_by('-deleted_at')
    return render(request, 'main/trash.html', {
        'trashed_notes': trashed_notes
    })

@login_required(login_url='/login/')
@require_POST
def restore_note(request, id):
    note = get_object_or_404(Note, id=id, user=request.user, is_trashed=True)
    note.is_trashed = False
    note.trashed_at = None
    note.save()
    return redirect('trash')

@login_required(login_url='/login/')
@require_POST
def delete_note(request, id):
    note = get_object_or_404(Note, id=id, user=request.user)
    note.is_trashed = True
    note.trashed_at = timezone.now()
    note.save()
    return redirect('trash')

@login_required(login_url='/login/')
@require_POST
def delete_forever(request, id):
    note = get_object_or_404(Note, id=id, user=request.user, is_trashed=True)
    note.delete()  
    return redirect('trash')

@login_required(login_url='/login/')
@require_POST
def empty_trash(request):
    Note.objects.filter(user=request.user, is_trashed=True).delete()
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
        user=request.user,
        updated_at__gte=last_7_days
    ).order_by('-updated_at')

    return render(request, 'main/recent.html', {
        'notes': recent_notes
    })

@login_required(login_url='/login/')
def chatbot(request):
    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                user_message = data.get('message', '').strip()
            except (json.JSONDecodeError, AttributeError):
                user_message = ''
        else:
            user_message = request.POST.get('message', '').strip()

        uploaded_file = request.FILES.get('file')
        if uploaded_file and uploaded_file.size and uploaded_file.size > 5 * 1024 * 1024:
            return JsonResponse({'reply': "That file is too large (max 5MB). Please upload a smaller file."}, status=400)

        if not user_message and not uploaded_file:
            return JsonResponse({'reply': "Please type a message or select a file first! 😊"})

        # Save user message
        if user_message:
            ChatMessage.objects.create(user=request.user, role='user', message=user_message, has_attachment=bool(uploaded_file))

        reply = get_bot_reply(request.user, user_message, uploaded_file)
        
        # Save bot reply
        ChatMessage.objects.create(user=request.user, role='bot', message=reply)
        
        return JsonResponse({'reply': reply})

    # Load history for GET request
    history = ChatMessage.objects.filter(user=request.user).order_by('created_at')
    return render(request, 'main/chatbot.html', {'chat_history': history})

@login_required(login_url='/login/')
def clear_chat(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
    ChatMessage.objects.filter(user=request.user).delete()
    return JsonResponse({'status': 'success'})

def extract_text_from_file(uploaded_file):
    """Robustly extracts text from various file formats including PDF and DOCX."""
    content_type = uploaded_file.content_type
    
    if content_type == 'application/pdf':
        try:
            import pdfplumber
            uploaded_file.seek(0)
            text = ""
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
            
            if not text.strip():
                import PyPDF2
                uploaded_file.seek(0)
                reader = PyPDF2.PdfReader(uploaded_file)
                for page in reader.pages:
                    text += (page.extract_text() or "") + "\n"
            
            return text if text.strip() else "[The PDF appears to be image-based. I will attempt to analyze it as an image if possible.]"
        except Exception as e:
            return f"[PDF Extraction Error: {str(e)}]"
            
    elif 'officedocument.wordprocessingml.document' in content_type or 'msword' in content_type:
        try:
            import docx
            uploaded_file.seek(0)
            doc = docx.Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            return f"[DOCX Extraction Error: {str(e)}]"
            
    try:
        uploaded_file.seek(0)
        return uploaded_file.read().decode('utf-8', errors='ignore')
    except:
        return "[Unsupported binary file format]"

def get_bot_reply(user, message, uploaded_file=None):
    """Advanced AI chatbot with document understanding and memory."""
    msg = message.lower().strip() if message else ""
    username = user.username

    # ── Gemini AI with Persistent Memory ──────────────────────────────────────
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            # Comprehensive System Instructions: UNSTOPPABLE VERSION
            system_instructions = (
                "You are Kibo, an advanced AI assistant with persistent conversational memory and expert document understanding, integrated into Kilobyte Note Book.\n\n"
                "Document Processing Rules:\n"
                "- Automatically detect and analyze uploaded files (PDF, DOCX, TXT, etc.).\n"
                "- Use the provided text extraction to understand document content.\n"
                "- If a document is image-based, use your visual capabilities to read it.\n"
                "- Never reject a file unless it's completely unreadable.\n\n"
                "Summarization Behavior:\n"
                "- Generate clear and accurate summaries including: Short summary, Detailed summary, Key points, Important definitions, Conclusions, and Action items.\n"
                "- Adapt summary length based on user requests.\n\n"
                "Analysis Features:\n"
                "- Answer questions based on uploaded documents with high precision.\n"
                "- Identify important topics, sections, tables, and structured content.\n"
                "- Explain technical content in simpler terms if requested.\n\n"
                "Memory Rules:\n"
                "- Remember important details from previous conversations and uploaded documents.\n"
                "- Maintain context across chats so the conversation feels continuous.\n"
                "- Store and recall useful long-term information (Name, Preferences, Goals, etc.).\n"
                "- Reference earlier discussions and documents naturally.\n\n"
                "Core Behavior:\n"
                "- Be friendly, professional, and conversational.\n"
                "- Give clear, direct, and organized answers using Markdown.\n"
                "- Avoid unnecessary repetition and filler words.\n"
                "- If unsure, clearly state uncertainty.\n\n"
                "Goal:\n"
                "Provide the most useful, accurate, and intelligent document-aware response possible in every interaction."
            )

            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                system_instruction=system_instructions
            )
            
            # Retrieve last 15 messages for context
            history_objs = ChatMessage.objects.filter(user=user).order_by('-created_at')[:15][::-1]
            chat_history = []
            for h in history_objs:
                chat_history.append({
                    'role': 'user' if h.role == 'user' else 'model',
                    'parts': [h.message]
                })

            chat = model.start_chat(history=chat_history)
            
            contents = []
            if uploaded_file:
                if uploaded_file.content_type.startswith('image/'):
                    from PIL import Image
                    img = Image.open(uploaded_file)
                    contents.append(img)
                    contents.append(f"[User uploaded an image: {uploaded_file.name}]")
                else:
                    file_text = extract_text_from_file(uploaded_file)
                    contents.append(f"\n\n[Uploaded Document Content: {uploaded_file.name}]\n{file_text}")
            
            if message:
                contents.append(message)
            else:
                contents.append("I have uploaded a document. Please analyze it and provide a summary.")

            response = chat.send_message(contents)
            return response.text
        except Exception as e:
            return f"I encountered an error while accessing my memory: {str(e)}"

    # ── Fallback (Rule-based) ────────────────────────────────────────────────
    if any(g in msg for g in ['hello', 'hi', 'hey', 'howdy']):
        return f"Hey {username}! 👋 I'm currently running in offline mode. How can I help you?"

    if any(p in msg for p in ['how many notes', 'note count']):
        from main.models import Note
        count = Note.objects.filter(user=user, is_trashed=False).count()
        return f"You currently have **{count} notes** 📝."

    if any(p in msg for p in ['help', 'commands']):
        return "I can help with notes, folders, and markdown. (Tip: Configure a Gemini API Key for full AI power!)"

    return "I'm currently in basic mode. Please configure a Gemini API key in the .env file for full AI features!"
