
from django.core.paginator import Paginator
def paginate_queryset(queryset, request, start_from_last=False):
    page_size = request.query_params.get("page_size", 10)
    try:
        page_size = int(page_size)
    except (ValueError, TypeError):
        page_size = 10  # fallback to default if not a valid integer

    paginator = Paginator(queryset, page_size)
    page_number = request.query_params.get("page")
    if not page_number:
        page_number = paginator.num_pages if start_from_last else 1
    else:
        try:
            page_number = int(page_number)
        except (ValueError, TypeError):
            page_number = 1  # fallback to page 1 if invalid input

    page_obj = paginator.get_page(page_number)
    return page_obj, paginator

