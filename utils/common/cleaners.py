from django.core.files.uploadedfile import UploadedFile

def remove_empty_values(input_dict):
    # Create a new dictionary to store cleaned data
    cleaned_dict = {}
    for key, value in input_dict.items():
        if isinstance(value, dict):
            nested_cleaned = remove_empty_values(value)
            if nested_cleaned:  
                cleaned_dict[key] = nested_cleaned
        elif value:  
            cleaned_dict[key] = value  
    
    return cleaned_dict  



# def remove_empty_values(d):
#     if not isinstance(d, dict):
#         return d

#     cleaned = {}
#     for key, value in d.items():
#         if isinstance(value, dict):
#             nested = remove_empty_values(value)
#             if nested:
#                 cleaned[key] = nested
#         elif isinstance(value, UploadedFile):  # keep file
#             cleaned[key] = value
#         elif value not in [None, '', [], ()]:
#             cleaned[key] = value
#     return cleaned



def extract_clean_data_from_request(request):
    """
    Extracts non-empty form fields and file uploads from a multipart/form-data request.
    Returns a unified flat dictionary that combines cleaned text fields and files.
    """
    #Copy the text fields as a dict (safe)
    text_data = request.data.dict()
    cleaned_text_data = remove_empty_values(text_data)
    #Extracting files only
    file_data = {key: file for key, file in request.FILES.items()}
    
    return {**cleaned_text_data, **file_data}




def get_base_url(request):
    scheme = request.scheme  # 'http' or 'https'
    host = request.get_host()  # e.g., 'example.com' or 'example.com:8000'
    return f"{scheme}://{host}"


