"""End-to-end smoke test for the adaptation pipeline.

Walks through: /context -> /adapt/decide -> (optional) HITL approve ->
/adapt/execute -> /policy/update, then /metrics. Designed to be run against
a live server on http://127.0.0.1:8000.
"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            payload = r.read().decode()
            if not payload:
                return {}
            return json.loads(payload)
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        raise SystemExit(f"{method} {path} -> {e.code}: {msg}")


def section(label: str) -> None:
    print("\n=== " + label + " ===")


def main() -> int:
    section("Health")
    print(call("GET", "/api/health"))

    section("Available actions")
    actions = call("GET", "/api/actions")
    for a in actions:
        print(f"  {a['id']}: {a['label']}")

    section("Scenario A - default user, normal context")
    ctx_a = call(
        "POST",
        "/api/context",
        {
            "user_id": "smoke-user",
            "session_id": "sess-A",
            "context_features": {
                "user_profile": {
                    "assistive_tech": False,
                    "visual_pref": 0.0,
                    "motor_pref": 0.0,
                    "cognitive_pref": 0.0,
                },
                "session_behavior": {
                    "click_latency_ms": 600,
                    "error_count": 0,
                    "scroll_depth": 0.4,
                    "task_stage": 1,
                    "total_steps": 4,
                },
            },
            "ui_state": {
                "font_scale": 1.0,
                "contrast_level": "normal",
                "density": "default",
                "theme": "light",
                "hit_target_min_px": 32,
                "reduced_motion": False,
            },
        },
    )
    print("context_id:", ctx_a["context_id"])

    decision_a = call("POST", "/api/adapt/decide", {"context_id": ctx_a["context_id"]})
    print("decision A:", decision_a["action_id"], "conf=", round(decision_a["confidence"], 3))
    print("  validation:", decision_a["validation"]["status"], "violations=", len(decision_a["validation"]["violations"]))
    print("  requires_hitl:", decision_a["requires_hitl"], "trigger=", decision_a["hitl_trigger"])

    if decision_a["requires_hitl"]:
        call(
            "POST",
            "/api/hitl/review",
            {
                "decision_id": decision_a["decision_id"],
                "decision": "approve",
                "reviewer_id": "smoke-reviewer",
                "reviewer_role": "accessibility_reviewer",
                "reason": "smoke-test approval",
            },
        )
        print("  HITL approved")

    exec_a = call("POST", "/api/adapt/execute", {"decision_id": decision_a["decision_id"]})
    print("  applied:", exec_a["applied_action_id"], "blocked=", exec_a["was_blocked"], "fallback=", exec_a["was_fallback"])

    upd_a = call(
        "POST",
        "/api/policy/update",
        {
            "decision_id": decision_a["decision_id"],
            "task_completed": True,
            "completion_time_ms": 4200,
            "time_budget_ms": 60000,
            "error_count": 0,
            "error_budget": 4,
            "trust_score": 0.8,
        },
    )
    print("  policy update -> v", upd_a["model_version"], "reward=", round(upd_a["final_reward"], 3))

    section("Scenario B - low-vision user (high impact -> HITL)")
    ctx_b = call(
        "POST",
        "/api/context",
        {
            "user_id": "smoke-user",
            "session_id": "sess-B",
            "context_features": {
                "user_profile": {
                    "assistive_tech": False,
                    "visual_pref": 0.85,
                    "motor_pref": 0.1,
                    "cognitive_pref": 0.0,
                    "vulnerable": True,
                },
                "session_behavior": {
                    "click_latency_ms": 1500,
                    "error_count": 2,
                    "scroll_depth": 0.2,
                    "task_stage": 0,
                    "total_steps": 4,
                },
            },
            "ui_state": {
                "font_scale": 1.0,
                "contrast_level": "low",
                "density": "default",
                "theme": "light",
                "hit_target_min_px": 32,
                "reduced_motion": False,
            },
        },
    )
    decision_b = call("POST", "/api/adapt/decide", {"context_id": ctx_b["context_id"]})
    print("decision B:", decision_b["action_id"], "conf=", round(decision_b["confidence"], 3))
    print("  requires_hitl:", decision_b["requires_hitl"], "trigger=", decision_b["hitl_trigger"])
    print("  validation status:", decision_b["validation"]["status"])
    if decision_b["validation"]["violations"]:
        for v in decision_b["validation"]["violations"]:
            print(f"    - [{v['severity']}] {v['rule_name']}: {v['message']}")

    queue = call("GET", "/api/hitl/queue")
    print("HITL queue length:", len(queue))

    section("Scenario C - reject path")
    if queue:
        first = queue[0]
        call(
            "POST",
            "/api/hitl/review",
            {
                "decision_id": first["decision_id"],
                "decision": "reject",
                "reviewer_id": "smoke-reviewer",
                "reviewer_role": "accessibility_reviewer",
                "reason": "smoke reject -> safe fallback",
            },
        )
        exec_b = call("POST", "/api/adapt/execute", {"decision_id": first["decision_id"]})
        print("  rejected -> applied:", exec_b["applied_action_id"], "fallback=", exec_b["was_fallback"], "reason=", exec_b["block_reason"])

    section("Metrics")
    m = call("GET", "/api/metrics")
    print(json.dumps(m, indent=2))

    section("Smoke test PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
