"""
Adaptive threshold strategy that opportunistically exceeds target score when safe.

This strategy combines threshold-based decision making with probability awareness.
It uses the normal score threshold, but continues hitting beyond the threshold
when bust probability is low (safe opportunity).
"""

from typing import List, Optional

from flip_7.data.models import NumberCard
from flip_7.simulation.strategy import BaseStrategy, StrategyContext


class AdaptiveThresholdStrategy(BaseStrategy):
    """
    Strategy that uses score threshold but adapts based on bust probability.

    This strategy improves upon basic ThresholdStrategy by:
    - Using normal threshold logic as baseline
    - Being MORE aggressive when bust probability is low (safe to continue)
    - Falling back to threshold when bust probability is higher

    The goal is to achieve higher scores than ThresholdStrategy while
    maintaining similar or lower bust rates.

    Attributes:
        target_score: Base score threshold (like ThresholdStrategy)
        safe_probability_threshold: Max bust probability to continue hitting beyond target
    """

    def __init__(
        self,
        name: Optional[str] = None,
        target_score: int = 100,
        safe_probability_threshold: float = 0.10
    ):
        """
        Initialize adaptive threshold strategy.

        Args:
            name: Optional custom name
            target_score: Base score threshold (default: 100)
            safe_probability_threshold: Max bust probability to consider "safe" (default: 0.10)

        Raises:
            ValueError: If safe_probability_threshold not in [0.0, 1.0]
        """
        if not 0.0 <= safe_probability_threshold <= 1.0:
            raise ValueError(
                f"safe_probability_threshold must be between 0.0 and 1.0, "
                f"got {safe_probability_threshold}"
            )

        if name is None:
            pct = int(safe_probability_threshold * 100)
            name = f"Adaptive_{target_score}@{pct}%"

        super().__init__(name)
        self.target_score = target_score
        self.safe_probability_threshold = safe_probability_threshold

    def decide_hit_or_stay(self, context: StrategyContext) -> bool:
        """
        Decide whether to hit or stay using adaptive logic.

        Decision logic:
        1. If flip_three active, must hit (no choice)
        2. If already won (total_score >= 200), stay
        3. Calculate bust probability
        4. If bust probability is LOW (safe), continue hitting even above threshold
        5. Otherwise, use normal threshold logic (hit if below target, stay if above)

        This allows the strategy to be opportunistic when conditions are favorable.

        Args:
            context: Complete game context

        Returns:
            True to HIT, False to STAY
        """
        # If flip_three is active, must hit
        if context.my_flip_three_active and context.my_flip_three_count > 0:
            return True

        # If already won, stay
        if context.my_total_score >= 200:
            return False

        # Calculate bust probability
        bust_probability = self._calculate_bust_probability(context)

        # OPPORTUNITY: If bust probability is LOW, continue hitting even above threshold
        # This is the key improvement over basic ThresholdStrategy
        if bust_probability < self.safe_probability_threshold:
            return True  # Safe to continue, go for higher score!

        # FALLBACK: Use normal threshold logic when not in safe zone
        # This provides stability and prevents excessive risk-taking
        return context.my_round_score < self.target_score

    def _calculate_bust_probability(self, context: StrategyContext) -> float:
        """
        Calculate probability of busting on next card draw.

        Uses the context's helper method to calculate duplicate probabilities
        for each number value in hand, then returns the maximum probability
        (worst case for any single value).

        Args:
            context: Game context with visible cards and hand information

        Returns:
            Maximum bust probability across all number values in hand (0.0-1.0)
        """
        # Get duplicate probabilities for each value in hand
        dup_probs = context.calculate_duplicate_probability()

        # If no probabilities (no number cards in hand), bust probability is 0
        if not dup_probs:
            return 0.0

        # Return maximum probability (worst case)
        return max(dup_probs.values())

    def decide_second_chance_discard(
        self,
        context: StrategyContext,
        duplicate_value: int,
        duplicate_cards: List[NumberCard]
    ) -> NumberCard:
        """
        Decide which duplicate to discard when using Second Chance.

        Strategy: Discard the most recently drawn card (last in list).
        This is equivalent for most purposes since both cards have the same value.

        Args:
            context: Game context
            duplicate_value: The duplicated value
            duplicate_cards: List of duplicate cards (exactly 2)

        Returns:
            The most recently drawn duplicate card
        """
        # Discard the most recently drawn (last in list)
        return duplicate_cards[-1]

    def decide_flip_three_target(
        self,
        context: StrategyContext,
        possible_targets: List[str]
    ) -> str:
        """
        Decide who receives the Flip Three effect.

        Strategy:
        - If no opponents available, apply to self
        - Otherwise, apply to opponent with highest total score (force them to risk)

        Args:
            context: Game context
            possible_targets: List of eligible player IDs

        Returns:
            Player ID to receive Flip Three effect
        """
        # Filter to get only opponents (not self)
        opponent_ids = [
            opp.player_id for opp in context.opponents
            if opp.player_id in possible_targets
        ]

        # If no opponents available, must apply to self
        if not opponent_ids:
            return context.my_player_id

        # Apply to opponent with highest total score
        opponent_scores = {
            opp.player_id: opp.total_score
            for opp in context.opponents
            if opp.player_id in opponent_ids
        }
        return max(opponent_scores.keys(), key=lambda pid: opponent_scores[pid])

    def decide_freeze_target(
        self,
        context: StrategyContext,
        possible_targets: List[str]
    ) -> str:
        """
        Decide who gets frozen.

        Strategy:
        - If my round score >= target threshold, freeze self (bank good score)
        - Otherwise, freeze opponent with highest total score (prevent improvement)

        Args:
            context: Game context
            possible_targets: List of eligible player IDs

        Returns:
            Player ID to freeze
        """
        # If I have a good score, freeze myself to bank it
        if context.my_round_score >= self.target_score:
            return context.my_player_id

        # Otherwise, freeze opponent with highest total score
        opponent_ids = [
            opp.player_id for opp in context.opponents
            if opp.player_id in possible_targets
        ]

        # If no opponents available, freeze self
        if not opponent_ids:
            return context.my_player_id

        # Freeze opponent with highest total score
        opponent_scores = {
            opp.player_id: opp.total_score
            for opp in context.opponents
            if opp.player_id in opponent_ids
        }
        return max(opponent_scores.keys(), key=lambda pid: opponent_scores[pid])
