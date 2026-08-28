"""
AI Copilot API View endpoints.
"""
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .ai_agent import run_ai_copilot


@login_required
@require_POST
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

        # Append to history
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": ai_reply})
        request.session["ai_chat_history"] = chat_history[-12:]  # keep recent turns
        request.session.modified = True

        return JsonResponse({
            "reply": ai_reply,
            "status": "success"
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def ai_clear_history(request):
    """Clears the AI session conversation history."""
    request.session["ai_chat_history"] = []
    request.session.modified = True
    return JsonResponse({"status": "cleared"})
