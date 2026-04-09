"""
Orquestador del MessageAdapter (versión híbrida).
Mantiene simplicidad y robustez, con mejoras de seguridad sin romper compatibilidad.
"""
import datetime
import logging
from typing import Dict, List, Any
from backend.adapters.message_adapter.intent_detector import detect_intents
from backend.adapters.message_adapter.entity_extractor import extract_entities

logger = logging.getLogger(__name__)

# Límite de caracteres para prevenir ataques de agotamiento de recursos
MAX_INPUT_LENGTH = 1000

# Control de información sensible en debug (no exponer en producción)
DEBUG_MODE = False

class MessageAdapter:
    """Adaptador para procesar mensajes de texto informales y extraer instrucciones."""

    def process(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo de NLP sobre el texto de entrada.
        Args:
            text: Mensaje original del usuario.
            metadata: Diccionario con metadatos (debe incluir 'tenant_id').
        Returns:
            Diccionario con filas canónicas, hallazgos, acciones sugeridas y resumen.
        """
        # Sanitizar tenant_id para evitar Log Injection (escapar saltos de línea)
        raw_tenant = metadata.get("tenant_id", "unknown")
        safe_tenant = repr(raw_tenant)  # Escapa caracteres especiales como \n, \r
        logger.info("Processing message for tenant_id=%s", safe_tenant)

        # Truncar entrada para prevenir abuso de CPU/memoria
        if len(text) > MAX_INPUT_LENGTH:
            logger.warning("Input truncated from %d to %d characters", len(text), MAX_INPUT_LENGTH)
            text = text[:MAX_INPUT_LENGTH]

        primary_intent = "unknown"
        all_intents = []
        canonical_rows = []
        findings = []
        suggested_actions = []
        entities_data = {}
        cleaned_text = ""

        try:
            # Limpieza básica: minúsculas, colapso de espacios, eliminación de emojis básicos
            cleaned_text = self._clean_text(text)

            # Detección de intenciones
            primary_intent, all_intents = detect_intents(cleaned_text)
            logger.info("Primary intent: '%s' | Detected: %s", primary_intent, all_intents)

            # Extracción de entidades
            entities_data = extract_entities(cleaned_text)

            # Mapeo a formato canónico (NO bloqueamos por persona desconocida)
            if primary_intent != "unknown":
                canonical_rows = self._to_canonical(primary_intent, entities_data)

            # Generación de hallazgos y acciones sugeridas
            findings = self._build_findings(canonical_rows)
            suggested_actions = self._build_actions(canonical_rows)

        except Exception as e:
            logger.error("Pipeline failed: %s", str(e), exc_info=True)
            # Continuar con salida degradada pero segura

        summary = {
            "intent": primary_intent,
            "actions_count": len(suggested_actions),
            "entities_found": len(entities_data.get("all_persons", [])),
            "has_amount": bool(entities_data.get("amount", 0.0) > 0),
            "has_date": bool(entities_data.get("date"))
        }

        logger.info(
            "Completed tenant_id=%s | rows=%d | intent=%s",
            safe_tenant, len(canonical_rows), primary_intent
        )

        # Construir respuesta base (contrato fijo)
        response = {
            "tenant_id": raw_tenant,  # Se devuelve el original, no el sanitizado
            "module": "message_adapter",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "canonical_rows": canonical_rows,
            "findings": findings,
            "summary": summary,
            "suggested_actions": suggested_actions,
        }

        # Añadir debug solo si está habilitado explícitamente
        if DEBUG_MODE:
            response["debug"] = {
                "raw_text_preview": text[:300] if text else "",
                "detected_intents": all_intents,
                "extra_entities": {
                    "persons": entities_data.get("all_persons", []),
                    "amounts": entities_data.get("all_amounts", [])
                }
            }

        return response

    @staticmethod
    def _clean_text(text: str) -> str:
        """Limpia el texto preservando contexto numérico y estructural."""
        if not text:
            return ""
        import re
        # Eliminar emojis y símbolos no semánticos, preservar números, letras y puntuación básica
        cleaned = re.sub(r'[^\w\s.,;:()-]', ' ', text.lower()).strip()
        # Colapsar espacios múltiples
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned

    @staticmethod
    def _to_canonical(intent: str, entities: Dict) -> List[Dict]:
        """Mapea intención y entidades a filas canónicas."""
        return [{
            "type": "instruction",
            "action": intent,
            "entity": entities.get("primary_person", "Unknown"),
            "date": entities.get("date", ""),
            "amount": entities.get("amount", 0.0)
        }]

    @staticmethod
    def _build_findings(rows: List[Dict]) -> List[Dict]:
        """Genera hallazgos estructurados."""
        if not rows:
            return []
        findings = []
        for idx, row in enumerate(rows):
            amount = row.get("amount", 0.0)
            is_high = amount > 500.0
            findings.append({
                "type": "pending_action",
                "message": f"Acción '{row.get('action', 'unknown')}' pendiente para {row.get('entity', 'N/A')}",
                "severity": "medium" if is_high else "low",
                "row_index": idx
            })
        return findings

    @staticmethod
    def _build_actions(rows: List[Dict]) -> List[Dict]:
        """Sugiere acciones sin ejecutarlas."""
        if not rows:
            return []
        actions = []
        for row in rows:
            action_type = "enviar_recordatorio" if not row.get("date") else "crear_evento"
            requires_approval = row.get("amount", 0.0) > 1000.0
            actions.append({
                "action_type": action_type,
                "target_entity": row.get("entity", ""),
                "payload": {
                    "action": row.get("action"),
                    "date": row.get("date"),
                    "amount": row.get("amount")
                },
                "status": "suggested",
                "requires_approval": requires_approval
            })
        return actions
