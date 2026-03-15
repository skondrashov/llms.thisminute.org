"""
Balatro Hand Scorer — First Blind Optimizer

Evaluates all possible plays from an 8-card hand and finds the optimal
strategy to reach a target score (default: 300 for Ante 1 Small Blind).

SPEC
====
Balatro scores a played hand (1-5 cards) as:

    score = (base_chips + sum(scored_card_chips)) * base_mult

Where:
- base_chips and base_mult come from the poker hand type (see HAND_TYPES)
- scored_card_chips are the chip values of cards that CONTRIBUTE to the hand
  (e.g., in a Pair of 7s played with a King, only the two 7s are scored)
- Card chip values: Ace=11, K/Q/J/10=10, 9=9, ..., 2=2

Hand detection priority (best first):
  Flush Five > Flush House > Five of a Kind > Straight Flush >
  Four of a Kind > Full House > Flush > Straight >
  Three of a Kind > Two Pair > Pair > High Card

Special rules:
- Ace can be high (10-J-Q-K-A) or low (A-2-3-4-5) in straights
- Only played cards matter (you choose 1-5 from your 8-card hand)

Ante 1 targets: Small Blind=300, Big Blind=450, Boss Blind=600
Default hand count: 4 hands, 3 discards per round
Starting hand size: 8 cards

This tool does NOT handle jokers, enhancements, editions, or seals.
Those modify scoring in ways that depend on the specific run state.
This is the base-game arithmetic only.
"""

from itertools import combinations
from collections import Counter


# --- Constants ---

HAND_TYPES = {
    #                    base_chips, base_mult
    "Flush Five":        (160, 16),
    "Flush House":       (140, 14),
    "Five of a Kind":    (120, 12),
    "Straight Flush":    (100, 8),
    "Four of a Kind":    (60,  7),
    "Full House":        (40,  4),
    "Flush":             (35,  4),
    "Straight":          (30,  4),
    "Three of a Kind":   (30,  3),
    "Two Pair":          (20,  2),
    "Pair":              (10,  2),
    "High Card":         (5,   1),
}

RANK_CHIPS = {
    14: 11,  # Ace
    13: 10,  # King
    12: 10,  # Queen
    11: 10,  # Jack
    10: 10,
    9: 9, 8: 8, 7: 7, 6: 6, 5: 5, 4: 4, 3: 3, 2: 2,
}

RANK_NAMES = {
    14: "A", 13: "K", 12: "Q", 11: "J", 10: "10",
    9: "9", 8: "8", 7: "7", 6: "6", 5: "5", 4: "4", 3: "3", 2: "2",
}

SUIT_SYMBOLS = {"hearts": "H", "diamonds": "D", "clubs": "C", "spades": "S"}

ANTE_1_TARGETS = {"small": 300, "big": 450, "boss": 600}


# --- Card representation ---

def card(rank, suit):
    """Create a card. rank: 2-14 (14=Ace), suit: hearts/diamonds/clubs/spades."""
    return {"rank": rank, "suit": suit}


def card_str(c):
    return f"{RANK_NAMES[c['rank']]}{SUIT_SYMBOLS[c['suit']]}"


def parse_card(s):
    """Parse 'AH', '10S', '2D' etc. into a card dict."""
    s = s.strip().upper()
    suit_map = {"H": "hearts", "D": "diamonds", "C": "clubs", "S": "spades"}
    suit = suit_map[s[-1]]
    rank_str = s[:-1]
    rank_map = {"A": 14, "K": 13, "Q": 12, "J": 11}
    rank = rank_map.get(rank_str) or int(rank_str)
    return card(rank, suit)


# --- Hand detection ---

def detect_hand(cards):
    """
    Detect the best poker hand type from 1-5 cards.
    Returns (hand_type_name, scoring_cards) where scoring_cards
    are the cards that contribute chip values to the score.
    """
    n = len(cards)
    ranks = [c["rank"] for c in cards]
    suits = [c["suit"] for c in cards]
    rank_counts = Counter(ranks)
    most_common = rank_counts.most_common()

    is_flush = n >= 5 and len(set(suits)) == 1
    is_straight = _check_straight(ranks) if n >= 5 else False

    # Five-card hands
    if n == 5:
        five_of_a_kind = most_common[0][1] == 5
        four_of_a_kind = most_common[0][1] == 4
        is_full_house = len(most_common) == 2 and most_common[0][1] == 3
        is_three = most_common[0][1] == 3 and not is_full_house
        is_two_pair = len([r for r, c in most_common if c == 2]) == 2
        is_pair = most_common[0][1] == 2 and not is_two_pair

        if five_of_a_kind and is_flush:
            return "Flush Five", cards
        if is_full_house and is_flush:
            return "Flush House", cards
        if five_of_a_kind:
            return "Five of a Kind", cards
        if is_straight and is_flush:
            return "Straight Flush", cards
        if four_of_a_kind:
            scoring = [c for c in cards if c["rank"] == most_common[0][0]]
            return "Four of a Kind", scoring
        if is_full_house:
            return "Full House", cards
        if is_flush:
            return "Flush", cards
        if is_straight:
            return "Straight", cards
        if is_three:
            scoring = [c for c in cards if c["rank"] == most_common[0][0]]
            return "Three of a Kind", scoring
        if is_two_pair:
            pair_ranks = [r for r, c in most_common if c == 2]
            scoring = [c for c in cards if c["rank"] in pair_ranks]
            return "Two Pair", scoring
        if is_pair:
            pair_rank = most_common[0][0]
            scoring = [c for c in cards if c["rank"] == pair_rank]
            return "Pair", scoring
        # High card — only the highest card scores
        best = max(cards, key=lambda c: c["rank"])
        return "High Card", [best]

    # Sub-5-card hands (no straights or flushes possible)
    if n == 4:
        four_of_a_kind = most_common[0][1] == 4
        if four_of_a_kind:
            return "Four of a Kind", cards
        is_three = most_common[0][1] == 3
        if is_three:
            scoring = [c for c in cards if c["rank"] == most_common[0][0]]
            return "Three of a Kind", scoring
        is_two_pair = len([r for r, c in most_common if c == 2]) == 2
        if is_two_pair:
            pair_ranks = [r for r, c in most_common if c == 2]
            scoring = [c for c in cards if c["rank"] in pair_ranks]
            return "Two Pair", scoring
        is_pair = most_common[0][1] == 2
        if is_pair:
            pair_rank = most_common[0][0]
            scoring = [c for c in cards if c["rank"] == pair_rank]
            return "Pair", scoring
        best = max(cards, key=lambda c: c["rank"])
        return "High Card", [best]

    if n == 3:
        if most_common[0][1] == 3:
            return "Three of a Kind", cards
        if most_common[0][1] == 2:
            pair_rank = most_common[0][0]
            scoring = [c for c in cards if c["rank"] == pair_rank]
            return "Pair", scoring
        best = max(cards, key=lambda c: c["rank"])
        return "High Card", [best]

    if n == 2:
        if most_common[0][1] == 2:
            return "Pair", cards
        best = max(cards, key=lambda c: c["rank"])
        return "High Card", [best]

    if n == 1:
        return "High Card", cards

    return "High Card", cards[:1]


def _check_straight(ranks):
    """Check if 5 ranks form a straight (ace-high or ace-low)."""
    unique = sorted(set(ranks))
    if len(unique) != 5:
        return False
    # Normal straight
    if unique[-1] - unique[0] == 4:
        return True
    # Ace-low: A-2-3-4-5
    if set(unique) == {14, 2, 3, 4, 5}:
        return True
    return False


# --- Scoring ---

def score_hand(cards):
    """
    Score a played hand of 1-5 cards.
    Returns (score, hand_type, base_chips, base_mult, card_chips).
    """
    hand_type, scoring_cards = detect_hand(cards)
    base_chips, base_mult = HAND_TYPES[hand_type]
    card_chips = sum(RANK_CHIPS[c["rank"]] for c in scoring_cards)
    total = (base_chips + card_chips) * base_mult
    return total, hand_type, base_chips, base_mult, card_chips


# --- Optimizer ---

def find_all_plays(hand):
    """
    Evaluate every possible 1-5 card play from the given hand.
    Returns list of (score, hand_type, cards_played) sorted by score descending.
    """
    plays = []
    for size in range(1, min(6, len(hand) + 1)):
        for combo in combinations(hand, size):
            combo_list = list(combo)
            total, hand_type, _, _, _ = score_hand(combo_list)
            plays.append((total, hand_type, combo_list))
    plays.sort(key=lambda x: x[0], reverse=True)
    return plays


def best_play(hand):
    """Find the single highest-scoring play from a hand."""
    plays = find_all_plays(hand)
    return plays[0] if plays else None


def can_reach_target(hand, target=300, hands_remaining=4):
    """
    Check if the target score can be reached with the remaining hands.
    Returns the best play and whether it's a one-shot kill.
    """
    score, hand_type, cards = best_play(hand)
    return {
        "best_score": score,
        "hand_type": hand_type,
        "cards": [card_str(c) for c in cards],
        "one_shot": score >= target,
        "hands_needed_estimate": max(1, -(-target // score)) if score > 0 else None,
    }


# --- CLI ---

def main():
    """CLI: pass cards as arguments like 'AH KS QD JC 10H 7S 3D 2C'."""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python scorer.py AH KS QD JC 10H 7S 3D 2C")
        print("       Cards: rank + suit (A/K/Q/J/10-2 + H/D/C/S)")
        print()
        print("Evaluates all possible plays and shows the best options.")
        sys.exit(1)

    hand = [parse_card(s) for s in sys.argv[1:]]
    print(f"Hand: {' '.join(card_str(c) for c in hand)}")
    print(f"Target: {ANTE_1_TARGETS['small']} (Ante 1 Small Blind)")
    print()

    plays = find_all_plays(hand)
    seen_types = set()
    print("Top plays:")
    for i, (score, hand_type, cards) in enumerate(plays[:10]):
        cards_str = " ".join(card_str(c) for c in cards)
        marker = " <<< CLEARS" if score >= 300 else ""
        print(f"  {score:>5}  {hand_type:<18}  {cards_str}{marker}")

    result = can_reach_target(hand)
    print()
    if result["one_shot"]:
        print(f"One-shot: play {' '.join(result['cards'])} "
              f"({result['hand_type']}, {result['best_score']} pts)")
    else:
        print(f"Best single play: {result['best_score']} pts "
              f"({result['hand_type']}) — need ~{result['hands_needed_estimate']} hands")


if __name__ == "__main__":
    main()
