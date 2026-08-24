"""Outage drills D3/D4 (split from chaos_drills.py, 150-line cap).

Both kill the opponent endpoint mid-game via the FlappyProxy; D3 heals it
inside the retry budget (the game must complete), D4 leaves it dead past the
full budget (a clean classified technical loss, never a hang or crash).
"""

import threading
import time

import chaos_lib
from chaos_lib import EvidenceLog

from p2p_police.domain.primitives import Outcome


def _flap(net: dict, chaos: dict, evidence: EvidenceLog, name: str,
          inject_at: dict, heal: bool) -> threading.Thread:
    """Kill the proxy once MY runtime reaches the configured full turn."""
    def trigger():
        engine = net["mine"].engine
        while (engine.turns_completed < chaos["flap_after_full_turns"]
               and engine.outcome is Outcome.ONGOING):
            time.sleep(0.02)
        inject_at["t"] = time.perf_counter()
        inject_at["at_full_turn"] = engine.turns_completed
        evidence.event(name, "inject", fault="endpoint_down", heal_planned=heal,
                       at_full_turn=engine.turns_completed)
        # heal=False is a PERMANENT outage: blackhole it so the peer meets
        # silence and the deadline is what classifies, identically on every
        # OS. A healing flap still closes and re-opens the listener.
        net["proxy"].stop() if heal else net["proxy"].blackhole()
        if heal:
            time.sleep(chaos["flap_seconds"])
            net["proxy"].start()
            inject_at["turns_at_heal"] = engine.turns_completed
            evidence.event(name, "observe", healed_after_sec=chaos["flap_seconds"],
                           turns_at_heal=engine.turns_completed)
    thread = threading.Thread(target=trigger, name=f"{name}-trigger", daemon=True)
    thread.start()
    return thread


def drill_d3(config, evidence: EvidenceLog) -> dict:
    name, chaos = "d3_transport_flap_heal", config.private["chaos"]
    net = chaos_lib.wire_pair(config, chaos, use_proxy=True)
    evidence.event(name, "start", flap_after_full_turns=chaos["flap_after_full_turns"],
                   flap_seconds=chaos["flap_seconds"],
                   retry_backoff_sec=chaos["retry_backoff_sec"])
    inject_at: dict = {}
    trigger = _flap(net, chaos, evidence, name, inject_at, heal=True)
    thread, stub_box = chaos_lib.play_in_thread(net["stub"], name)
    mine = chaos_lib.run_classified(net["mine"])
    trigger.join(timeout=10)
    thread.join(timeout=chaos["turn_timeout_seconds"] * 3)
    # observed heal mechanism: the persistent session holds the in-flight call
    # through the outage (SDK-internal reconnect); the outer retry loop is the
    # backstop for error-flavored failures - either way the game must freeze
    # during the outage and then complete.
    stalled = inject_at.get("turns_at_heal", 99) - inject_at.get("at_full_turn", 0)
    evidence.event(name, "observe", retries=net["retries"].retries, stall_full_turns=stalled)
    row = chaos_lib.finish_row(evidence, name, mine, stub_box,
                               {"retries": net["retries"].retries, "stall_full_turns": stalled})
    row["passed"] = (row["outcome"] != "technical_loss" and row["digest_match"]
                     and row["audit"] == "Verified OK" and stalled <= 1
                     and inject_at.get("at_full_turn", 99) < row["turns_completed"])
    return row


def drill_d4(config, evidence: EvidenceLog) -> dict:
    name, chaos = "d4_budget_exhaustion", config.private["chaos"]
    net = chaos_lib.wire_pair(config, chaos, use_proxy=True)
    inject_at: dict = {}
    evidence.event(name, "start", flap_after_full_turns=chaos["flap_after_full_turns"],
                   turn_timeout_sec=chaos["turn_timeout_seconds"])
    trigger = _flap(net, chaos, evidence, name, inject_at, heal=False)
    thread, stub_box = chaos_lib.play_in_thread(net["stub"], name)
    mine = chaos_lib.run_classified(net["mine"])
    seconds_to_classify = round(time.perf_counter() - inject_at.get("t", time.perf_counter()), 3)
    trigger.join(timeout=10)
    thread.join(timeout=chaos["turn_timeout_seconds"] * 3)
    evidence.event(name, "observe", seconds_to_classify=seconds_to_classify,
                   retries=net["retries"].retries, stub_thread_exited=not thread.is_alive())
    row = chaos_lib.finish_row(evidence, name, mine, stub_box,
                               {"seconds_to_classify": seconds_to_classify,
                                "retries": net["retries"].retries})
    # the FSM may legally sit in a phase with no TECHNICAL_LOSS edge (book
    # table); the classification lives in the engine outcome + error type
    row["passed"] = (row["outcome"] == "technical_loss"
                     and "DeadlineExpiredError" in (mine["error"] or "")
                     and seconds_to_classify <= chaos["turn_timeout_seconds"] + 3.0
                     and not thread.is_alive())
    return row
