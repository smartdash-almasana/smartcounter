from datetime import datetime, timezone

ACTION_JOBS = {}


def generate_action_id():
    import uuid
    return f"act_{uuid.uuid4().hex[:12]}"


def create_action_jobs(tenant_id: str, suggested_actions: list[dict]) -> list[dict]:
    jobs = []

    for action in suggested_actions:
        action_id = generate_action_id()

        job = {
            "action_id": action_id,
            "tenant_id": tenant_id,
            "action_type": action.get("type"),
            "status": "pending_confirmation",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "draft": {
                "title": action.get("title"),
                "description": action.get("description"),
                "payload": action,
            },
            "confirmation": {
                "confirmed": False,
            },
            "execution": {
                "status": "not_executed",
            },
        }

        ACTION_JOBS[action_id] = job
        jobs.append(job)

    return jobs


def confirm_action(action_id: str, decision: str) -> dict:
    job = ACTION_JOBS.get(action_id)

    if not job:
        raise ValueError("action not found")

    if job.get("status") != "pending_confirmation":
        raise ValueError("invalid state")

    if decision == "confirm":
        job["status"] = "confirmed"
        job["confirmation"]["confirmed"] = True

    elif decision == "cancel":
        job["status"] = "cancelled"

    return job


def execute_action(action_id: str) -> dict:
    job = ACTION_JOBS.get(action_id)

    if not job:
        raise ValueError("action not found")

    if job.get("status") != "confirmed":
        raise ValueError("not confirmed")

    execution = job.get("execution", {})
    if execution.get("status") == "executed":
        raise ValueError("already executed")

    job["execution"]["status"] = "executed"
    job["execution"]["executed_at"] = datetime.now(timezone.utc).isoformat()

    return job
