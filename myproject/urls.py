"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main.views import home
from main import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.redirect_root, name='root'),
    path('register/', views.register_user, name='register'),
    path('home/', views.home, name='home'),
    path('edit/<int:id>/', views.edit_note, name='edit_note'),
    path('delete_note/<int:id>/', views.delete_note1, name='delete_note'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('folders/', views.folders, name='folders'),
    path('folders/new/', views.new_folder, name='new_folder'),
    path('folder/<int:folder_id>/', views.folder_detail, name='folder_detail'),
    path('folder/<int:folder_id>/new-note/', views.create_note_in_folder, name='create_note_in_folder'),
    path('settings/', views.settings, name='settings'),
    path('settings/export/', views.export_notes, name='export_notes'),
    path('trash/', views.trash, name='trash'),
    path('note/delete/<int:id>/', views.delete_note, name='delete_note'),
    path('note/restore/<int:id>/', views.restore_note, name='restore_note'),
    path('note/delete-forever/<int:id>/', views.delete_forever, name='delete_forever'),
    path('markdown-help/', views.markdown_help, name='markdown_help'),
    path('note/<int:id>/', views.note_view, name='note_view'),
    path('split-editor/<int:id>/', views.split_editor, name='split_editor'),
    path('recent/', views.recent_notes, name='recent_notes'),
    path('trash/empty/', views.empty_trash, name='empty_trash'),
    path('chatbot/', views.chatbot, name='chatbot'),
]