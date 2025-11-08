import logging
from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    ValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    APIException
)
from rest_framework.response import Response
from rest_framework import status

# Logger setup (optional but highly recommended)
logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Comprehensive global exception handler for DRF
    providing user-friendly messages and consistent JSON responses.
    """

    # Default DRF handler (for known DRF exceptions)
    response = exception_handler(exc, context)

    # Base structure
    error_response = {
        "success": False,
        "status_code": None,
        "message": "An unexpected error occurred.",
        "details": None
    }

    # 🧠 1. Handle known DRF exceptions
    if isinstance(exc, ValidationError):
        error_response["status_code"] = status.HTTP_400_BAD_REQUEST
        error_response["message"] = "Some fields are invalid. Please correct them and try again."
        error_response["details"] = exc.detail

    elif isinstance(exc, AuthenticationFailed):
        error_response["status_code"] = status.HTTP_401_UNAUTHORIZED
        error_response["message"] = "Invalid credentials. Please log in again."
        error_response["details"] = str(exc)

    elif isinstance(exc, NotAuthenticated):
        error_response["status_code"] = status.HTTP_401_UNAUTHORIZED
        error_response["message"] = "You need to log in to access this resource."
        error_response["details"] = str(exc)

    elif isinstance(exc, PermissionDenied):
        error_response["status_code"] = status.HTTP_403_FORBIDDEN
        error_response["message"] = "You don’t have permission to perform this action."
        error_response["details"] = str(exc)

    elif isinstance(exc, NotFound):
        error_response["status_code"] = status.HTTP_404_NOT_FOUND
        error_response["message"] = "The requested resource was not found."
        error_response["details"] = str(exc)

    # 🧠 2. Handle database or object-related errors
    elif isinstance(exc, ObjectDoesNotExist):
        error_response["status_code"] = status.HTTP_404_NOT_FOUND
        error_response["message"] = "The item you’re looking for doesn’t exist."
        error_response["details"] = str(exc)

    elif isinstance(exc, DatabaseError):
        error_response["status_code"] = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_response["message"] = "A database error occurred. Please try again later."
        error_response["details"] = str(exc)

    # 🧠 3. Handle general API exceptions
    elif isinstance(exc, APIException):
        error_response["status_code"] = exc.status_code
        error_response["message"] = exc.detail if isinstance(
            exc.detail, str) else "An API error occurred."
        error_response["details"] = exc.get_full_details()

    # 🧠 4. Handle all other unexpected exceptions
    else:
        error_response["status_code"] = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_response["message"] = "Something went wrong on our side. Please try again later."
        error_response["details"] = str(exc)
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # If DRF provided a Response (for known exceptions)
    if response is not None:
        response.data = error_response
        response.status_code = error_response["status_code"]
        return response

    # For unhandled exceptions (fallback)
    return Response(error_response, status=error_response["status_code"])


def custom_not_found_view(request, exception):
    return Response({
        "success": False,
        "status_code": 404,
        "message": "The requested resource was not found.",
        "details": str(exception)
    }, status=status.HTTP_404_NOT_FOUND)


def custom_server_error_view(request):
    logger.error("Internal server error", exc_info=True)
    return Response({
        "success": False,
        "status_code": 500,
        "message": "Something went wrong on our side. Please try again later.",
        "details": "Internal server error."
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


handler404 = custom_not_found_view
handler500 = custom_server_error_view
