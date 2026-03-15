"""
Tests for Balatro hand scorer.

These tests ARE the spec — if an LLM regenerates the scorer in any
language, these cases define correctness.
"""

import pytest
from scorer import (
    parse_card, card_str, score_hand, detect_hand, find_all_plays,
    best_play, can_reach_target, HAND_TYPES,
)


# --- Helpers ---

def hand(*card_strs):
    return [parse_card(s) for s in card_strs]


def score(*card_strs):
    return score_hand(hand(*card_strs))[0]


def hand_type(*card_strs):
    return score_hand(hand(*card_strs))[1]


# --- Card parsing ---

class TestParsing:
    def test_ace_of_hearts(self):
        c = parse_card("AH")
        assert c["rank"] == 14 and c["suit"] == "hearts"

    def test_ten_of_spades(self):
        c = parse_card("10S")
        assert c["rank"] == 10 and c["suit"] == "spades"

    def test_two_of_diamonds(self):
        c = parse_card("2D")
        assert c["rank"] == 2 and c["suit"] == "diamonds"

    def test_roundtrip(self):
        for s in ["AH", "KS", "QD", "JC", "10H", "9S", "2D"]:
            assert card_str(parse_card(s)) == s


# --- Hand detection ---

class TestHandDetection:
    def test_high_card(self):
        assert hand_type("AH", "KS", "QD", "JC", "9H") == "High Card"

    def test_pair(self):
        assert hand_type("AH", "AS", "KD", "QC", "JH") == "Pair"

    def test_two_pair(self):
        assert hand_type("AH", "AS", "KD", "KC", "QH") == "Two Pair"

    def test_three_of_a_kind(self):
        assert hand_type("AH", "AS", "AD", "KC", "QH") == "Three of a Kind"

    def test_straight(self):
        assert hand_type("AH", "KS", "QD", "JC", "10H") == "Straight"

    def test_straight_ace_low(self):
        assert hand_type("AH", "2S", "3D", "4C", "5H") == "Straight"

    def test_flush(self):
        assert hand_type("AH", "KH", "QH", "JH", "9H") == "Flush"

    def test_full_house(self):
        assert hand_type("AH", "AS", "AD", "KC", "KH") == "Full House"

    def test_four_of_a_kind(self):
        assert hand_type("AH", "AS", "AD", "AC", "KH") == "Four of a Kind"

    def test_straight_flush(self):
        assert hand_type("AH", "KH", "QH", "JH", "10H") == "Straight Flush"

    def test_not_straight_wrap(self):
        # Q-K-A-2-3 is NOT a straight
        assert hand_type("QH", "KS", "AD", "2C", "3H") != "Straight"


# --- Scoring arithmetic ---

class TestScoring:
    def test_pair_of_kings(self):
        # Pair: 10 base + (10+10) card chips = 30, * 2 mult = 60
        assert score("KH", "KS", "QD", "JC", "9H") == 60

    def test_pair_of_aces(self):
        # Pair: 10 base + (11+11) card chips = 32, * 2 mult = 64
        assert score("AH", "AS", "KD", "QC", "JH") == 64

    def test_flush_high(self):
        # Flush: 35 base + (11+10+10+10+9) card chips = 85, * 4 mult = 340
        assert score("AH", "KH", "QH", "JH", "9H") == 340

    def test_four_aces(self):
        # Four of a Kind: 60 base + (11*4) card chips = 104, * 7 mult = 728
        assert score("AH", "AS", "AD", "AC", "KH") == 728

    def test_high_card_single(self):
        # High Card: 5 base + 11 card chips = 16, * 1 mult = 16
        assert score("AH") == 16

    def test_straight_ace_high(self):
        # Straight: 30 base + (11+10+10+10+10) card chips = 81, * 4 mult = 324
        assert score("AH", "KS", "QD", "JC", "10H") == 324

    def test_straight_ace_low(self):
        # Straight: 30 base + (11+2+3+4+5) card chips = 55, * 4 mult = 220
        assert score("AH", "2S", "3D", "4C", "5H") == 220

    def test_full_house(self):
        # Full House: 40 base + (11+11+11+10+10) card chips = 93, * 4 mult = 372
        assert score("AH", "AS", "AD", "KC", "KH") == 372

    def test_three_of_a_kind_scoring_cards(self):
        # Only the three matching cards score chips
        # Three of a Kind: 30 base + (7+7+7) card chips = 51, * 3 mult = 153
        assert score("7H", "7S", "7D", "KC", "QH") == 153


# --- Optimizer ---

class TestOptimizer:
    def test_finds_best_play(self):
        h = hand("AH", "KH", "QH", "JH", "10H", "2S", "3D", "4C")
        result = best_play(h)
        assert result[0] >= 300  # Straight flush should clear
        assert result[1] == "Straight Flush"

    def test_all_plays_sorted_descending(self):
        h = hand("AH", "KS", "QD", "JC", "10H", "7S", "3D", "2C")
        plays = find_all_plays(h)
        scores = [p[0] for p in plays]
        assert scores == sorted(scores, reverse=True)

    def test_can_reach_target_true(self):
        h = hand("AH", "KH", "QH", "JH", "10H", "2S", "3D", "4C")
        result = can_reach_target(h, target=300)
        assert result["one_shot"] is True

    def test_can_reach_target_weak_hand(self):
        h = hand("2H", "3S", "4D", "5C", "7H", "8S", "9D", "JC")
        result = can_reach_target(h, target=300)
        # No pairs, no flush — probably can't one-shot 300
        # but should still return a best play


# --- Edge cases ---

class TestEdgeCases:
    def test_single_card_play(self):
        total, ht, _, _, _ = score_hand(hand("AH"))
        assert ht == "High Card"
        assert total == 16

    def test_two_card_pair(self):
        total, ht, _, _, _ = score_hand(hand("AH", "AS"))
        assert ht == "Pair"
        assert total == 64  # (10 + 11 + 11) * 2

    def test_base_values_match_spec(self):
        assert HAND_TYPES["Straight Flush"] == (100, 8)
        assert HAND_TYPES["Four of a Kind"] == (60, 7)
        assert HAND_TYPES["Full House"] == (40, 4)
        assert HAND_TYPES["Flush"] == (35, 4)
        assert HAND_TYPES["Straight"] == (30, 4)
        assert HAND_TYPES["Three of a Kind"] == (30, 3)
        assert HAND_TYPES["Two Pair"] == (20, 2)
        assert HAND_TYPES["Pair"] == (10, 2)
        assert HAND_TYPES["High Card"] == (5, 1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
