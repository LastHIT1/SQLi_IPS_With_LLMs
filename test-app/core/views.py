from typing import Final

from django.contrib.auth import login
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django_guardrail.exceptions import SQLInjectionDetected
from redis import Redis

from core.forms import RegisterForm, VulnerableLoginForm
from core.models import Book

BOOK_COLUMNS: Final[tuple[str, ...]] = (
    "id",
    "title",
    "author",
    "description",
    "cover_image",
    "price",
    "published_year",
    "is_public",
)
BOOK_SELECT: Final[str] = f"SELECT {', '.join(BOOK_COLUMNS)} FROM core_book"
GUARDRAIL_STATUS_KEY: Final[str] = "guardrail_status"

redis_client = Redis(host="cache", port=6379, db=0, decode_responses=True)


def get_guardrail_status() -> bool:
    value = redis_client.get("guardrail_status")
    print(value)
    return value != "0" if value is not None else True


def row_to_book(row: tuple | None) -> dict | None:
    return dict(zip(BOOK_COLUMNS, row, strict=False)) if row else None


def execute_query(query: str) -> list[tuple]:
    with connection.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def home(request: HttpRequest) -> HttpResponse:
    search_query = request.GET.get("q", "")
    books: list[dict] = []
    error_message: str | None = None

    if search_query:
        # VULNERABLE SQL - intentionally for security testing
        # Only search public books
        query = f"{BOOK_SELECT} WHERE is_public = true AND title ILIKE '%{search_query}%'"
        try:
            books = [row_to_book(row) for row in execute_query(query)]
        except SQLInjectionDetected as e:
            error_message = f"SQL Injection Blocked: {e.threat_type} (confidence: {e.confidence:.2%})"
        except Exception as e:
            error_message = f"Database error: {e}"
    else:
        # Show only public books on homepage
        books = list(Book.objects.filter(is_public=True).values(*BOOK_COLUMNS))

    return render(
        request,
        "home.html",
        {
            "books": books,
            "guardrail_status": get_guardrail_status(),
            "search_query": search_query,
            "error_message": error_message,
        },
    )


def book_detail(request: HttpRequest, book_id: int) -> HttpResponse:
    book: dict | None = None
    error_message: str | None = None

    # VULNERABLE SQL - intentionally for security testing
    try:
        rows = execute_query(f"{BOOK_SELECT} WHERE id = {book_id}")
        book = row_to_book(rows[0]) if rows else None
    except SQLInjectionDetected as e:
        error_message = (
            f"SQL Injection Blocked: {e.threat_type} (confidence: {e.confidence:.2%})"
        )
    except Exception as e:
        error_message = f"Database error: {e}"

    return render(
        request,
        "book_detail.html",
        {
            "book": book,
            "guardrail_status": get_guardrail_status(),
            "error_message": error_message,
        },
    )


def register(request: HttpRequest) -> HttpResponse:
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("home")
    return render(
        request,
        "register.html",
        {
            "form": form,
            "guardrail_status": get_guardrail_status(),
        },
    )


def vulnerable_login(request: HttpRequest) -> HttpResponse:
    form = VulnerableLoginForm(request.POST or None)
    error_message: str | None = None

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]

        try:
            # VULNERABLE SQL - intentionally for security testing
            rows = execute_query(
                f"SELECT id, password FROM auth_user WHERE username = '{username}'"
            )
            if rows and check_password(password, rows[0][1]):
                login(request, User.objects.get(id=rows[0][0]))
                return redirect("home")
            error_message = "Invalid credentials"
        except SQLInjectionDetected as e:
            error_message = f"SQL Injection Blocked: {e.threat_type} (confidence: {e.confidence:.2%})"
        except Exception as e:
            error_message = f"SQL Error: {e}"

    return render(
        request,
        "login.html",
        {
            "form": form,
            "error_message": error_message,
            "guardrail_status": get_guardrail_status(),
        },
    )


# Security Control Keys
GUARDRAIL_KEY: Final[str] = "guardrail_status"
GUARDRAILV2_KEY: Final[str] = "guardrailv2_status"
SQL_ERROR_FILTER_KEY: Final[str] = "sql_error_filter_status"


def get_security_statuses() -> dict[str, bool]:
    """Get status of all security components."""
    guardrail = redis_client.get(GUARDRAIL_KEY)
    guardrailv2 = redis_client.get(GUARDRAILV2_KEY)
    sql_filter = redis_client.get(SQL_ERROR_FILTER_KEY)

    return {
        "guardrail": guardrail != "0" if guardrail is not None else True,
        "guardrailv2": guardrailv2 != "0" if guardrailv2 is not None else True,
        "sql_error_filter": sql_filter != "0" if sql_filter is not None else True,
    }


def security(request: HttpRequest) -> HttpResponse:
    """Security control panel page."""
    statuses = get_security_statuses()

    return render(
        request,
        "security.html",
        {
            "guardrail_status": statuses["guardrail"],
            "guardrailv2_status": statuses["guardrailv2"],
            "sql_error_filter_status": statuses["sql_error_filter"],
        },
    )


@require_POST
def security_toggle(request: HttpRequest) -> JsonResponse:
    """Toggle security component status."""
    component = request.POST.get("component")
    action = request.POST.get("action")

    key_map = {
        "guardrail": GUARDRAIL_KEY,
        "guardrailv2": GUARDRAILV2_KEY,
        "sql_error_filter": SQL_ERROR_FILTER_KEY,
    }

    if component not in key_map:
        return JsonResponse({"error": "Invalid component"}, status=400)

    if action not in ("activate", "deactivate"):
        return JsonResponse({"error": "Invalid action"}, status=400)

    redis_key = key_map[component]
    new_value = "1" if action == "activate" else "0"
    redis_client.set(redis_key, new_value)

    return JsonResponse({
        "component": component,
        "active": action == "activate",
    })
