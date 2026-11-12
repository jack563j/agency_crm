"""
AI Copilot API View endpoints.
Never redirects to HTML — always returns JSON so the chat widget can handle
any error gracefully without hitting "Unexpected token '<'".
"""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .ai_agent import run_ai_copilot


def _json_login_required(view_fn):
    """Like @login_required but returns JSON 401 instead of redirecting to HTML."""
    from functools import wraps

    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Session expired. Please refresh the page and log in again."},
                status=401,
            )
        return view_fn(request, *args, **kwargs)

    return wrapper


@csrf_exempt
@require_POST
@_json_login_required
def ai_chat_endpoint(request):
    """Handles conversational chat messages and returns AI response."""
    try:
        data = json.loads(request.body.decode("utf-8"))
        message = data.get("message", "").strip()

        if not message:
            return JsonResponse({"error": "Empty message"}, status=400)

        # Get or init session chat history
        chat_history = request.session.get("ai_chat_history", [])

        # Run AI Copilot
        ai_reply, updated_history = run_ai_copilot(message, chat_history, request.user)

        # Persist history (keep last 12 turns)
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": ai_reply})
        request.session["ai_chat_history"] = chat_history[-12:]
        request.session.modified = True

        return JsonResponse({"reply": ai_reply, "status": "success"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
@_json_login_required
def ai_clear_history(request):
    """Clears the AI session conversation history."""
    request.session["ai_chat_history"] = []
    request.session.modified = True
    return JsonResponse({"status": "cleared"})
