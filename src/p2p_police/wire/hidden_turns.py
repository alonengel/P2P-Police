"""Half-turn handlers + audit finish for the HiddenRuntime (split from
hidden_runtime.py for the 150-code-line cap; `rt` carries all the state).

Reference cadence (verified against the demo): the THIEF opens every round
— its runtime seeds turn 1 before the receive-respond loop — and each side
numbers its OWN steps 1, 2, 3... (demo own_state.apply_move). The thief's
step ticks the round clock: survival counts the thief's own steps (demo
rules.thief_result reads state.step_number), so the boundary — the
book-model update on this peer's OWN field, run BEFORE serializing — fires
on the thief's action on both peers.
"""

import contextlib

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import GamePhase, Move, Outcome, Role
from p2p_police.peer.deadline import Deadline, DeadlineExpiredError
from p2p_police.report.lookup import geometry
from p2p_police.wire import audit, audit_foreign, claims, codec, step_zero


def my_half_turn(rt) -> None:
    rt.my_step += 1  # per-sender numbering: MY moves count 1, 2, 3...
    step = rt.my_step
    rt.fsm.transition(GamePhase.COMPUTING_MOVE)
    # Belief is the ONLY rival estimate — OwnState holds no rival position,
    # so "exact" play is structurally impossible on this wire (rules 8-9).
    action = rt.brain.decide(rt.own, rt.perception.belief)
    moved = action["move"] if action["type"] == "move" else "STAY"
    claim, truth = rt.deceiver.plan_hint(rt.own, rt.perception, Move[moved], step)
    hint = rt.talk.render(claim, step)
    rt.fsm.transition(GamePhase.COMMITTING)
    barrier = rt.own.apply_own_action(action)
    captured = rt.role is Role.THIEF and rt.own.i_am_captured()
    win = None
    if rt.role is Role.THIEF and not captured:
        rt.own.close_full_turn()  # the thief's step ticks the round clock
        # survival claimed at MY 35th step (demo timing)
        win = {"type": "survival"} if rt.own.survival_reached() else None
    response, rt.pending_claim_response = rt.pending_claim_response, None
    response = claims.concede_declaration(rt.own) if captured else response  # honest
    commit = rt.exchange.seal_step(rt.own.digest(), step, action, hint, truth)
    rt.exchange.send_message(codec.build_turn_message(
        step, rt.role.value, hint, codec.serialize_scent(rt.own.scent[rt.role]),
        commit, barrier_placed=[barrier[0], barrier[1]] if barrier else None,
        capture_claim=(claims.capture_claim_for(action, rt.own, rt.perception, rt.config)
                       if rt.role is Role.POLICE else None),
        claim_response=response, win_claim=win))
    rt.fsm.transition(GamePhase.AWAITING_REVEAL)  # reveal deferred to audit
    rt.deceiver.observe_own(rt.own, claim)
    rt.fsm.transition(GamePhase.VERIFYING)
    rt.fsm.transition(GamePhase.WAITING_FOR_OPPONENT)
    if captured:
        rt.own.outcome = Outcome.CAPTURE
    elif win:
        rt.own.outcome = Outcome.SURVIVAL
    rt.perception.emit(rt.own, step)


def their_half_turn(rt) -> None:
    """Absorb the rival's next own-numbered message (their_step + 1)."""
    rt.their_step += 1  # the rival's steps count 1, 2, 3... independently
    message = codec.parse_turn_message(rt.exchange.receive_turn(rt.their_step))
    rival = Role(message["sender"])
    placed = message["barrier_placed"]
    # Only a NEW declaration is evidence; redeliveries are transport noise.
    fresh_wall = bool(placed) and not rt.own.board.is_barrier((placed[0], placed[1]))
    if placed:
        rt.own.note_rival_barrier(placed)  # quota-checked (Table 15)
    rt.own.scent[rival].absorb(message["smell_grid"])
    rt.own.note_rival_half_turn()
    # Only the THIEF's truth-duty flow can concede OUR capture (rules 21-22:
    # the cop claims, the thief answers about its own cell). A police-role
    # caught=True is no concession — it must never fabricate a capture.
    conceded = bool((message["claim_response"] or {}).get("caught")) and rival is Role.THIEF
    if rt.role is Role.POLICE and not conceded:
        rt.own.close_full_turn()  # the rival (thief) just ticked the round
    if not conceded:
        # NEVER JUDGE THE FINAL (settled convention with imreec): a conceded
        # final is mid-round and action-free, and its smell_grid legitimately
        # varies by implementation - ours re-sends the last boundary's field
        # (zero-step), the reference's unconditional send() advances one more
        # step. No one frame-to-frame law explains both, so judging it books
        # a FALSE refused-reading against an honest rival (E2E g90 finding).
        # The game is over on receipt: expect no particular final, judge none.
        rt.perception.observe(rt.own, rival, message["hint"],
                              barrier_cell=(placed[0], placed[1]) if fresh_wall else None,
                              claim_cell=message["capture_claim"])
    if conceded:
        rt.own.outcome = Outcome.CAPTURE  # rival honestly declared itself caught
    elif message["win_claim"]:
        rt.own.outcome = Outcome.SURVIVAL  # re-verified at the audit replay
    elif rt.role is Role.POLICE and rt.own.survival_reached():
        rt.own.outcome = Outcome.SURVIVAL  # the boundary verdict is automatic
    if rt.role is Role.THIEF and rt.own.outcome is Outcome.ONGOING:
        if message["capture_claim"] is not None:
            # STRUCTURAL truth duty (rules 21-22): the answer is a pure
            # function of our own cell; no strategy input can reach it.
            rt.pending_claim_response = claims.answer_capture_claim(
                rt.own, message["capture_claim"])
        hit = bool(rt.pending_claim_response and rt.pending_claim_response["caught"])
        if hit or rt.own.i_am_captured():
            if not hit:
                rt.pending_claim_response = claims.concede_declaration(rt.own)
            rt.own.outcome = Outcome.CAPTURE
            send_concede(rt)
    rt.perception.emit(rt.own, rt.their_step)


def send_concede(rt) -> None:
    """The mandatory sealed 'you got me' closure: action-free (STAY), the
    honest caught=True response attached; no boundary fires (mid-round).
    Numbered as OUR next own step — the receiver keys any caught=True final
    to its live expectation, so the demo's last-step re-use also lands."""
    rt.my_step += 1
    response, rt.pending_claim_response = rt.pending_claim_response, None
    action = {"type": "move", "move": "STAY"}
    commit = rt.exchange.seal_step(
        rt.own.digest(), rt.my_step, action, codec.FINAL_CAUGHT_HINT, True)
    rt.exchange.send_message(codec.build_turn_message(
        rt.my_step, rt.role.value, codec.FINAL_CAUGHT_HINT,
        codec.serialize_scent(rt.own.scent[rt.role]), commit,
        claim_response=response))


def finish(rt) -> dict:
    """Mutual audit, three tiers: (a) the commit criterion over the rival's
    reveals; (b) the strict full physics reconstruction — but ONLY when the
    rival's payloads parse as OUR schema (payload schema is a per-team
    choice, not an interop contract); a foreign-schema half degrades to the
    derivable checks instead of reading TAMPERED; (c) the digest comparison
    only where one construction exists on both sides — foreign pairs report
    digest_match as not-comparable (None), never false."""
    with contextlib.suppress(DeadlineExpiredError):
        rt.transport.send_audit(
            audit.build_audit_payload(rt.exchange, rt.role.value, rt.own.outcome.value),
            Deadline(rt.config.turn_timeout_seconds))
        rt.audit_sent = True  # normal-path disclosure done (rules 35-36)
    verdict, digest_match, end_digest = "not received", False, rt.own.digest()
    try:
        theirs = rt._wait(rt.inboxes.audits, "opponent audit (records + nonces)")
        step_zero.read_for(rt, theirs)  # rival's sealed commit declaration
        verdict = rt.exchange.audit_reveals(theirs.get("records", []))
        if verdict == "Verified OK":
            if audit_foreign.parses_as_ours(rt.exchange.their_records):
                reconstruction = audit.reconstruct(
                    rt.exchange.own_records, rt.exchange.their_records,
                    rt.config.shared, expected_sub_game=rt.exchange.sub_game)
                end_digest = reconstruction["digest"]
                rt.disputed_capture = reconstruction.get("disputed_capture")
                digest_match = audit.consistent(
                    reconstruction, rt.own.outcome, rt.own.turns_completed)
            else:
                # rules 46/47 ride along: a barrier capture is self-declared
                # live, so THEIR reveal is the only place we can prove it
                verdict, digest_match, rt.disputed_capture = audit_foreign.foreign_verdict(
                    rt.exchange, geometry(rt.config.shared)[0], rt.own.outcome.value)
    except DeadlineExpiredError:
        pass
    except GameRuleError:
        verdict = "TAMPERED"  # illegal revealed physics voids the audit
    percep = getattr(rt, "perception", None)
    return {
        "role": rt.role.value,
        "started_at": getattr(rt, "started_at", None),
        "outcome": rt.own.outcome.value,
        "turns_completed": rt.own.turns_completed,
        "end_state_digest": end_digest,
        "digest_match": digest_match,
        "audit": verdict,
        "steps_sealed": len(rt.exchange.own_records),
        # Evidence for the mutual audit (rule 36): how many transmitted trail
        # readings we refused as physically impossible. Zero on every honest
        # game ever measured; non-zero is a claim a third party can check.
        "scent_readings_refused": getattr(percep, "refused_readings", 0),
        # Where the rival's OWN transmitted trail placed it each turn (the
        # emitter that solves its frame transition under the signed update
        # law). Diffed at audit against the positions it reveals: an honest
        # trail reproduces the rival's path, one turn behind.
        "rival_trail_track": getattr(percep, "trail_track", []),
        "opponent_group_id": getattr(rt, "opponent_group_id", "unknown"),
        "opponent_info": getattr(rt, "opponent_info", {}),
        # The rival's SEALED commit-id declaration (its revealed step-zero)
        # + the two-channel verdict vs its negotiate identity (a mismatch is
        # rule-36 evidence; the series report prefers the sealed copy).
        **step_zero.evidence(rt),
        # Rule-36 evidence: a capture their own reveal proves, that their peer
        # never conceded. Recorded for the logs to settle (rule 35), never a
        # unilateral outcome rewrite - absent on every honest game.
        "disputed_capture": getattr(rt, "disputed_capture", None),
    }
