# Changelog

## [1.0.1] — 2026-07-30

### Fixed
- **Energy floor protection**: `self.energy = max(0.0, self.energy - cost)` prevents negative energy.
- **Auto-recharge guard**: When energy drops below 10%, agent auto-recharges and skips the round to prevent deadlock.
- **Accurate action statistics**: Replaced string-matching stats with `collections.Counter` for reliable action counting.
- **Empathy summary robustness**: `get_empathy_summary()` now safely handles `None` response times.
- **Personality drift judgment**: When `optimism == 0.0`, reflection reports "Pessimistic tendency" instead of falling through to neutral.

### Added
- `optimism` emotional state variable with endogenous drift dynamics.
- `get_action_summary()` public API for Counter-based action stats.
- Extracted magic numbers into top-level configuration constants.
- Full unit-test suite (`test_egk.py`).

## [1.0.0] — 2026-07-28

### Added
- Initial release: 5-layer embodied cognitive agent.
- MemoryBuffer with tag-based retrieval.
- Stage 9 altruism reproduction script.
- Metacognitive `reflect()` interface.
