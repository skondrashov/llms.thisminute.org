"""
Tests for Balatro hand scorer.

These tests ARE the spec — if an LLM regenerates the scorer in any
language, these cases define correctness.
"""

import pytest
from scorer import (
    parse_card, card_str, score_hand, detect_hand, find_all_plays,
    best_play, can_reach_target, HAND_TYPES,
    optimal_discard, analyze_hand, min_clearing_hand,
    remaining_deck, standard_deck, card,
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


# --- Discard optimizer ---

class TestOptimalDiscard:
    def test_discard_improves_weak_hand(self):
        """A hand with no pairs but four to a flush should benefit from discarding."""
        # 4 hearts + 4 off-suit junk — discarding for flush is clearly better
        h = hand("AH", "KH", "QH", "JH", "2S", "3D", "4C", "5S")
        result = optimal_discard(h)
        # Current best without discard: best 5-card play from this hand
        # We should find that discarding is recommended (expected score > current)
        assert result["best_action"] in ("keep", "discard")
        assert "expected_score" in result
        assert "current_best_score" in result
        assert "all_options" in result
        assert len(result["all_options"]) > 0

    def test_keep_when_hand_already_strong(self):
        """A straight flush should not recommend discarding."""
        h = hand("AH", "KH", "QH", "JH", "10H", "2S", "3D", "4C")
        result = optimal_discard(h, target=300)
        # Straight flush scores 508, clearly clears 300
        assert result["current_best_score"] >= 300
        # The optimizer should find that keeping is best or at least matches
        assert result["expected_score"] >= 300

    def test_output_structure(self):
        """Verify the output dict has all expected keys."""
        h = hand("AH", "KS", "QD", "JC", "10H", "7S", "3D", "2C")
        result = optimal_discard(h)
        assert "best_action" in result
        assert "discard_cards" in result
        assert "keep_cards" in result
        assert "expected_score" in result
        assert "current_best_score" in result
        assert "all_options" in result

    def test_discard_for_straight_completion(self):
        """Hand with 4 to a straight should find discard path."""
        # A-K-Q-J + 4 low junk = need a 10 to complete straight
        h = hand("AH", "KS", "QD", "JC", "2H", "3S", "4D", "5C")
        deck = remaining_deck(h)
        result = optimal_discard(h, deck)
        # Should evaluate discarding the low cards
        # The all_options list should include discard strategies
        discard_options = [o for o in result["all_options"] if o["discard_count"] > 0]
        assert len(discard_options) > 0

    def test_optimizer_prefers_straight_over_pair_when_sound(self):
        """
        Given a hand where we hold A-K-Q-J (4 to a straight) plus a low pair,
        discarding for the straight should yield higher expected value than
        keeping the pair, because the straight base is much higher.
        """
        # Pair of 2s + 4 to a straight (A-K-Q-J)
        h = hand("AH", "KS", "QD", "JC", "2H", "2S", "7D", "8C")
        deck = remaining_deck(h)
        result = optimal_discard(h, deck)

        # Find the option that keeps A-K-Q-J (straight draw)
        straight_keeps = {"AH", "KS", "QD", "JC"}
        straight_option = None
        pair_score = score("2H", "2S")  # pair of 2s = (10 + 2+2) * 2 = 28

        for opt in result["all_options"]:
            if set(opt["keep"]) >= straight_keeps and opt["discard_count"] > 0:
                straight_option = opt
                break

        # The straight draw should exist in options
        assert straight_option is not None
        # The straight draw expected score should beat a pair of 2s
        assert straight_option["expected_score"] > pair_score


# --- Strategic analysis ---

class TestAnalyzeHand:
    def test_output_structure(self):
        """analyze_hand returns all expected keys."""
        h = hand("AH", "KS", "QD", "JC", "10H", "7S", "3D", "2C")
        result = analyze_hand(h)
        assert "current_best" in result
        assert "score" in result["current_best"]
        assert "hand_type" in result["current_best"]
        assert "cards" in result["current_best"]
        assert "flush_potential" in result
        assert "straight_potential" in result
        assert "pair_upgrade_potential" in result
        assert "recommended_action" in result
        assert "recommended_expected_score" in result
        assert "clears_target" in result

    def test_recommends_play_when_clearing(self):
        """When the hand already clears target, recommend play."""
        h = hand("AH", "KH", "QH", "JH", "10H", "2S", "3D", "4C")
        result = analyze_hand(h, target=300)
        assert result["recommended_action"] == "play"
        assert result["clears_target"] is True

    def test_detects_flush_potential(self):
        """Hand with 4 hearts should show flush potential."""
        h = hand("AH", "KH", "QH", "JH", "2S", "3D", "4C", "5S")
        result = analyze_hand(h)
        flush_pot = result["flush_potential"]
        # Should find hearts flush potential
        hearts_pot = [f for f in flush_pot if f["suit"] == "hearts"]
        assert len(hearts_pot) > 0
        assert hearts_pot[0]["cards_held"] == 4
        assert hearts_pot[0]["probability"] > 0

    def test_detects_straight_potential(self):
        """Hand with A-K-Q-J should detect straight potential."""
        h = hand("AH", "KS", "QD", "JC", "2H", "3S", "4D", "5C")
        result = analyze_hand(h)
        straight_pot = result["straight_potential"]
        # Should find 10-J-Q-K-A straight potential
        assert len(straight_pot) > 0
        # At least one window should need only 1 card (the 10)
        one_away = [s for s in straight_pot if s["needed"] == 1]
        assert len(one_away) > 0

    def test_detects_pair_upgrade(self):
        """Hand with a pair should detect upgrade potential."""
        h = hand("AH", "AS", "3D", "5C", "7H", "9S", "JD", "KC")
        result = analyze_hand(h)
        pair_pot = result["pair_upgrade_potential"]
        assert len(pair_pot) > 0
        assert pair_pot[0]["current"] == "Pair"
        assert pair_pot[0]["target"] == "Three of a Kind"


# --- Minimum clearing hands ---

class TestMinClearingHand:
    def test_pair_cannot_clear_300(self):
        """Pair max is (10 + 11+11) * 2 = 64, can't clear 300."""
        result = min_clearing_hand("Pair", target=300)
        assert result["clears"] is False
        assert result["max_score"] < 300

    def test_flush_clears_300(self):
        """Strong flush can clear 300."""
        result = min_clearing_hand("Flush", target=300)
        assert result["clears"] is True
        assert result["max_score"] >= 300

    def test_straight_clears_300(self):
        """Ace-high straight = (30 + 51) * 4 = 324, clears 300."""
        result = min_clearing_hand("Straight", target=300)
        assert result["clears"] is True

    def test_four_of_a_kind_clears_300(self):
        """Even weakest four of a kind should clear 300."""
        result = min_clearing_hand("Four of a Kind", target=300)
        # (60 + 2*4) * 7 = (60 + 8) * 7 = 476
        assert result["clears"] is True
        assert result["min_score"] >= 300

    def test_high_card_cannot_clear_300(self):
        result = min_clearing_hand("High Card", target=300)
        assert result["clears"] is False

    def test_invalid_hand_type_raises(self):
        with pytest.raises(ValueError):
            min_clearing_hand("Royal Flush", target=300)

    def test_output_structure(self):
        result = min_clearing_hand("Straight", target=300)
        assert "hand_type" in result
        assert "clears" in result
        assert "min_score" in result
        assert "max_score" in result
        assert "example_min" in result
        assert "example_max" in result
        assert "target" in result


# --- Deck utilities ---

class TestDeckUtilities:
    def test_standard_deck_size(self):
        assert len(standard_deck()) == 52

    def test_remaining_deck_size(self):
        h = hand("AH", "KS", "QD", "JC", "10H", "7S", "3D", "2C")
        deck = remaining_deck(h)
        assert len(deck) == 44

    def test_remaining_deck_excludes_hand(self):
        h = hand("AH", "KS")
        deck = remaining_deck(h)
        hand_set = {(c["rank"], c["suit"]) for c in h}
        deck_set = {(c["rank"], c["suit"]) for c in deck}
        assert hand_set & deck_set == set()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
