from django.urls import path
from .views.instruction_files import InstructionFilePublicListView, InstructionFilePublicDetailView

urlpatterns = [
    # Public Instruction Files (No auth required)
    path('instruction-files/', InstructionFilePublicListView.as_view(), name='public_instruction_files_list'),
    path('instruction-files/<str:file_type>/', InstructionFilePublicDetailView.as_view(), name='public_instruction_file_detail'),
]
