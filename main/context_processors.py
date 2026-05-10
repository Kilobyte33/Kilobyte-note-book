from main.models import Folder, UserSettings

def folders_processor(request):
    if request.user.is_authenticated:
        user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
        return {
            'user_folders': Folder.objects.filter(user=request.user),
            'user_settings': user_settings
        }
    return {'user_folders': []}
