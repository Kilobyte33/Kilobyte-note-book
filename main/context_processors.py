from main.models import Folder

def folders_processor(request):
    if request.user.is_authenticated:
        return {
            'user_folders': Folder.objects.filter(user=request.user)
        }
    return {'user_folders': []}
