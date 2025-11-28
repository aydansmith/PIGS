"""
Bustable-threshold strategy for flip_7 simulation.

This strategy only counts NumberCards (cards that can cause a bust) when
deciding whether to hit or stay. It ignores bonus/modifier cards in the
threshold calculation.
"""

from typing import List, Optional

from flip_7.data.models import NumberCard
from flip_7.simulation.strategy import BaseStrategy, StrategyContext


class BustableThresholdStrategy(BaseStrategy):
    """
    Strategy that hits until the sum of NumberCards reaches a threshold.

    Unlike ThresholdStrategy which uses the full round score (including
    bonuses, multipliers, and Flip 7 bonus), this strategy only counts
    the base NumberCard total. This represents the "bust-able" portion
    of the score since only NumberCards can cause a bust.

    Attributes:
        target_bustable_total: NumberCard sum threshold before staying
    """

    def __init__(
        self,
        name: Optional[str] = None,
        target_bustable_total: int = 50
    ):
        """
        Initialize bustable threshold strategy.

        Args:
            name: Optional custom name
            target_bustable_total: Sum of NumberCards to reach before staying (default: 50)
        """
        if name is None:
            name = f"BustableThreshold({target_bustable_total})"

        super().__init__(name)
        self.target_bustable_total = target_bustable_total

    def _calculate_bustable_total(self, context: StrategyContext) -> int:
        """
        Calculate the sum of all NumberCard values in hand.

        This is the portion of the score that can cause a bust if
        duplicates are drawn.

        Args:
            context: Game context

        Returns:
            Sum of NumberCard values
        """
        return sum(
            card.value for card in context.my_cards
            if isinstance(card, NumberCard)
        )

    def decide_hit_or_stay(self, context: StrategyContext) -> bool:
        """
        Decide whether to hit or stay based on bustable card total.

        Decision logic:
        1. If flip_three active, must hit (no choice)
        2. If NumberCard sum below target, hit
        3. Otherwise, stay

        Args:
            context: Complete game context

        Returns:
            True to HIT, False to STAY
        """
        # If flip_three is active, must hit
        if context.my_flip_three_active and context.my_flip_three_count > 0:
            return True

        # Calculate only the bust-able total (NumberCards only)
        bustable_total = self._calculate_bustable_total(context)

        # Hit if below threshold, otherwise stay
        return bustable_total < self.target_bustable_total

    def decide_second_chance_discard(
        self,
        context: StrategyContext,
        duplicate_value: int,
        duplicate_cards: List[NumberCard]
    ) -> NumberCard:
        """
        Decide which duplicate to discard when using Second Chance.

        Strategy: Discard the most recently drawn card (last in list).

        Args:
            context: Game context
            duplicate_value: The duplicated value
            duplicate_cards: List of duplicate cards (exactly 2)

        Returns:
            The most recently drawn duplicate card
        """
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
        - Otherwise, apply to opponent with highest total score

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
        - If bustable total >= target threshold, freeze self (bank good score)
        - Otherwise, freeze opponent with highest total score

        Args:
            context: Game context
            possible_targets: List of eligible player IDs

        Returns:
            Player ID to freeze
        """
        # Calculate bustable total
        bustable_total = self._calculate_bustable_total(context)

        # If I have reached my bustable target, freeze myself to bank it
        if bustable_total >= self.target_bustable_total:
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
