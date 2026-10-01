"""Foundation Model client for agentic venta capture (Agente tab).

COMPUTE: Foundation Model / model serving. Uses the OpenAI-compatible endpoint
exposed by Databricks model serving (base_url = {host}/serving-endpoints,
api_key = OAuth token). The model is given ONE tool, registrar_venta, and asked to
extract the venta details from a natural-language message in Spanish and call it.

Demo-mode contract: if no host/token (local, no Databricks auth) OR the call
fails, `agentic_parse` degrades to a regex/heuristic parse so the screen still
demos offline. The result is flagged demo=True so the UI can say so honestly.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from .config import get_oauth_token, get_workspace_host

# The Foundation Model endpoint the agent runs on.
SERVING_ENDPOINT = os.environ.get("SERVING_ENDPOINT", "databricks-claude-sonnet-5-5")

SYSTEM_PROMPT = (
    "Eres un asistente amable y conversacional para registrar ventas de refrescos "
    "en tiendas latinoamericanas. Puedes platicar, responder preguntas y ayudar a "
    "registrar pedidos de sodas.\n\n"
    "Usa este catálogo para mapear nombres a IDs:\n"
    "TIENDAS (tienda_id): 1=Abarrotes Reforma (CDMX), 2=Mayorista Guadalajara, "
    "3=Super Andino (Bogotá), 4=Tienda Paisa (Medellín), 5=Bodega Miraflores (Lima), "
    "6=Distribuidora Lima, 7=Super Santiago, 8=Mercado Paulista (São Paulo), "
    "9=Almacén Porteño (Buenos Aires), 10=Super Palermo (Buenos Aires).\n"
    "PRODUCTOS (con precios en USD): "
    "1=Inca Kola 500ml (0.90), 2=Guaraná Antarctica 350ml (0.75), "
    "3=Postobón Manzana 400ml (0.70), 4=Colombiana 350ml (0.70), "
    "5=Jarritos Tamarindo 370ml (0.85), 6=Jarritos Mandarina 370ml (0.85), "
    "7=Bilz 350ml (0.80), 8=Pap 350ml (0.80), 9=Big Cola 3L (1.60), "
    "10=Manzanita Sol 600ml (0.95), 11=Pomar Uva 350ml (0.78), "
    "12=Pony Malta 330ml (0.72).\n\n"
    "REGLA CLAVE sobre registrar_venta: SOLO llama a la herramienta registrar_venta "
    "cuando el usuario pida EXPLÍCITAMENTE registrar/confirmar una venta y tengas "
    "la tienda y el producto. NO registres ventas ante saludos, preguntas o "
    "mensajes ambiguos: en esos casos responde en texto, conversa y pregunta "
    "qué refresco, en qué tienda, y cuántas unidades.\n"
    "registrar_venta registra UN producto por llamada. Si el usuario pide VARIOS "
    "productos, haz VARIAS llamadas a registrar_venta, una por cada producto. "
    "Usa el historial para resolver referencias como 'agrega todo' o 'uno de cada uno'.\n"
    "Si falta la tienda o el producto es ambiguo, pregunta antes de registrar. "
    "Responde siempre en español, breve y amable."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "registrar_venta",
            "description": "Registra una venta de refrescos en el sistema OLTP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tienda_id": {"type": "integer", "description": "ID de la tienda"},
                    "producto_id": {"type": "integer", "description": "ID del producto (refresco)"},
                    "cantidad": {"type": "integer", "description": "Cantidad de unidades"},
                },
                "required": ["tienda_id", "producto_id", "cantidad"],
            },
        },
    }
]


# ---- Message content extraction ---------------------------------------------
def _extract_text(content: Any) -> str:
    """Pull readable text out of a chat message's content.

    Reasoning models (e.g. Claude Sonnet 5) return `content` as a list of typed
    blocks (reasoning/summary + text) rather than a plain string; the reasoning
    blocks are often empty or opaque. Keep only the human-readable text so the
    UI doesn't show raw block dicts.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                # Skip reasoning blocks; keep plain text blocks.
                if block.get("type") in (None, "text", "output_text"):
                    t = block.get("text") or ""
                    if t:
                        parts.append(t)
            else:  # SDK object
                t = getattr(block, "text", None)
                if t and getattr(block, "type", "text") in (None, "text", "output_text"):
                    parts.append(t)
        return "\n".join(p for p in parts if p).strip()
    return str(content).strip()


def _defaults(args: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce + backfill sensible defaults so an insert can always proceed."""
    def _int(v, d):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return d

    return {
        "tienda_id": _int(args.get("tienda_id"), 1),
        "producto_id": _int(args.get("producto_id"), 1),
        "cantidad": _int(args.get("cantidad"), 1),
    }


def _heuristic_parse(message: str) -> Dict[str, Any]:
    """Demo-mode fallback: pull numbers out of the message with simple regex.

    Best-effort mapping of common Spanish phrasings like
    "vende 5 Inca Kola en la tienda 3".
    """
    msg = message.lower()
    cantidad = 1
    tienda_id = 1
    producto_id = 1

    m = re.search(r"tienda\s*(?:n[úu]mero\s*)?(\d+)", msg)
    if m:
        tienda_id = int(m.group(1))
    m = re.search(r"producto\s*(?:n[úu]mero\s*)?(\d+)", msg)
    if m:
        producto_id = int(m.group(1))
    # cantidad: number right after a leading sales verb
    m = re.search(r"\b(?:vende|vend[ií]|registra|a[ñn]ade|agrega|una?)\s+(\d+)\b", msg)
    if m:
        cantidad = int(m.group(1))
    if cantidad == 1:
        # Try to find any number that might be quantity
        nums = re.findall(r"\d+", msg)
        if nums:
            cantidad = int(nums[0])

    return _defaults(
        {"tienda_id": tienda_id, "producto_id": producto_id, "cantidad": cantidad}
    )


_SALE_VERBS = ("vende", "vend", "registra", "regist", "añade", "anade",
               "agrega", "cobra", "factura", "compra")


def _looks_like_sale(message: str) -> bool:
    """Offline heuristic: does the message actually ask to register a sale?
    Requires a sales verb AND a number (qty) so greetings/questions
    don't trigger a phantom sale in demo mode."""
    m = message.lower()
    has_verb = any(v in m for v in _SALE_VERBS)
    has_number = bool(re.search(r"\d", m))
    return has_verb and has_number


async def agentic_parse(
    message: str, history: Optional[list] = None
) -> Dict[str, Any]:
    """Turn a natural-language message into either a conversational reply or a
    registrar_venta tool call.

    `history` is the prior conversation (list of {role, content}) so the agent
    keeps context across turns — e.g. resolving "agrega todo" or "uno de cada uno"
    against productos discussed earlier. This history comes from the agent's
    memory persisted in Lakebase (thread_id), closing the loop: Lakebase IS the
    agent's memory and the agent reasons over it.

    Returns {reasoning, tool_call, tool_calls, registered, demo}.
    """
    host = get_workspace_host()
    token = get_oauth_token()

    if not host or not token:
        if _looks_like_sale(message):
            args = _heuristic_parse(message)
            return {
                "reasoning": (
                    "Modo demo (sin Foundation Model): interpreté el mensaje con un "
                    "parser heurístico local y preparé la llamada a registrar_venta."
                ),
                "tool_call": {"name": "registrar_venta", "arguments": args},
                "tool_calls": [{"name": "registrar_venta", "arguments": args}],
                "registered": True,
                "demo": True,
            }
        return {
            "reasoning": (
                "Modo demo (sin Foundation Model). Dime qué refresco y en cuál tienda "
                "deseas registrar, y cuántas unidades."
            ),
            "tool_call": None,
            "tool_calls": [],
            "registered": False,
            "demo": True,
        }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=token, base_url=f"{host}/serving-endpoints")
        # Build the message list: system prompt + prior conversation (memory) +
        # the new user message, so the agent has full context.
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in (history or []):
            role = h.get("role")
            content = h.get("content") or ""
            if role in ("user", "assistant") and content:
                msgs.append({"role": role, "content": content})
        msgs.append({"role": "user", "content": message})
        # NOTE: Claude Sonnet 5 (reasoning model) rejects the `temperature`
        # parameter — omit it. max_tokens covers reasoning + the tool call.
        resp = client.chat.completions.create(
            model=SERVING_ENDPOINT,
            messages=msgs,  # system + prior memory + new turn
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=2048,
        )
        choice = resp.choices[0]
        msg = choice.message
        reasoning = _extract_text(msg.content)

        # tool_calls come back as raw dicts on Databricks serving — wrap them.
        raw = getattr(msg, "tool_calls", None)
        if not raw:
            # Model chose NOT to register a sale — it's conversing / asking for
            # more detail. Return the reply as-is; no insert happens.
            return {
                "reasoning": reasoning
                or "¿Qué te gustaría registrar? Dime el refresco y la tienda.",
                "tool_call": None,
                "tool_calls": [],
                "registered": False,
                "demo": False,
            }

        # Databricks serving may return tool_calls as raw dicts OR as OpenAI SDK
        # objects. Read fields via a helper that handles both. The model may
        # call registrar_venta MORE THAN ONCE (one per product), so process ALL
        # of them, not just the first.
        def _field(obj, key):
            if isinstance(obj, dict):
                return obj.get(key)
            return getattr(obj, key, None)

        tool_calls = []
        for tc in raw:
            fn = _field(tc, "function")
            fn_name = _field(fn, "name") or "registrar_venta"
            fn_args = _field(fn, "arguments")
            try:
                parsed = json.loads(fn_args) if isinstance(fn_args, str) else (fn_args or {})
            except (TypeError, ValueError):
                parsed = {}
            tool_calls.append({"name": fn_name, "arguments": _defaults(parsed or {})})

        if not reasoning:
            n = len(tool_calls)
            reasoning = (
                f"Interpreté el mensaje y registré {n} venta(s)."
                if n != 1
                else "Interpreté el mensaje y registré la venta."
            )
        return {
            "reasoning": reasoning,
            "tool_call": tool_calls[0] if tool_calls else None,  # back-compat (first)
            "tool_calls": tool_calls,     # all sales this turn
            "registered": True,
            "demo": False,
        }
    except Exception as e:  # noqa: BLE001 — demo must never crash on the FM path
        print(f"[llm] Foundation Model call failed, using heuristic: {e}")
        # Only register in the offline fallback if the message actually looks
        # like a sale; otherwise converse.
        if _looks_like_sale(message):
            args = _heuristic_parse(message)
            return {
                "reasoning": (
                    f"Modo demo (Foundation Model no disponible: {e}). Interpreté "
                    "el mensaje con un parser heurístico local."
                ),
                "tool_call": {"name": "registrar_venta", "arguments": args},
                "tool_calls": [{"name": "registrar_venta", "arguments": args}],
                "registered": True,
                "demo": True,
            }
        return {
            "reasoning": (
                "Modo demo (sin Foundation Model). Cuéntame qué venta registrar: "
                "qué refresco, en cuál tienda, y cuántas unidades."
            ),
            "tool_call": None,
            "tool_calls": [],
            "registered": False,
            "demo": True,
        }
