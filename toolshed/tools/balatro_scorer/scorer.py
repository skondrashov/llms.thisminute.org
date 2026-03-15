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
from math import comb
import random


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


# --- Deck utilities ---

def standard_deck():
    """Return a full 52-card standard deck."""
    suits = ["hearts", "diamonds", "clubs", "spades"]
    return [card(rank, suit) for suit in suits for rank in range(2, 15)]


def remaining_deck(hand):
    """Return the deck minus the cards in the given hand."""
    hand_set = {(c["rank"], c["suit"]) for c in hand}
    return [c for c in standard_deck() if (c["rank"], c["suit"]) not in hand_set]


# --- Discard optimizer ---

# Threshold: if the total number of best_play evaluations for a given discard
# count (combos * draws_per_combo) is below this, use exact enumeration.
# Otherwise, use Monte Carlo sampling.
_EXACT_EVAL_BUDGET = 2000

# Total Monte Carlo evaluation budget across all combos for a given discard
# count.  Each evaluation = one best_play() call (~0.7ms), so 10,000 evals
# takes ~7 seconds.  Budget is shared: more combos => fewer samples each.
_TOTAL_MC_BUDGET = 10000


def _best_score_from_hand(hand):
    """Return the best achievable score from a hand (the score of the best play)."""
    result = best_play(hand)
    return result[0] if result else 0


def _expected_score_after_discard(keep, discard_count, deck, samples=None):
    """
    Calculate the expected best score after discarding `discard_count` cards
    and drawing replacements from `deck`.

    If `samples` is None and the draw space is small (<=_EXACT_THRESHOLD),
    use exact enumeration. Otherwise, randomly sample `samples` draws.

    Returns the average best score across all possible/sampled draws.
    """
    if discard_count == 0:
        return float(_best_score_from_hand(keep))

    total_combos = comb(len(deck), discard_count)

    if samples is None and total_combos <= _EXACT_EVAL_BUDGET:
        # Exact enumeration
        total_score = 0
        count = 0
        for drawn in combinations(deck, discard_count):
            new_hand = keep + list(drawn)
            total_score += _best_score_from_hand(new_hand)
            count += 1
        return total_score / count if count > 0 else 0.0
    else:
        # Monte Carlo sampling
        n_samples = samples if samples is not None else min(500, total_combos)
        total_score = 0
        for _ in range(n_samples):
            drawn = random.sample(deck, discard_count)
            new_hand = keep + drawn
            total_score += _best_score_from_hand(new_hand)
        return total_score / n_samples


def optimal_discard(hand, deck_remaining=None, discards_left=3, hands_left=5, target=300):
    """
    Given an 8-card hand, calculate the optimal discard strategy.

    For each possible discard set (0-5 cards from the hand), calculates the
    expected score after drawing replacements from the remaining deck. Uses
    exact combinatorial math for small discard counts and Monte Carlo sampling
    when the number of possible draws exceeds the exact threshold.

    The total computation is budgeted: for each discard count, the Monte Carlo
    sample budget (_TOTAL_MC_BUDGET) is divided evenly across all combos of
    that size.

    Parameters
    ----------
    hand : list[dict]
        The 8-card hand (list of card dicts).
    deck_remaining : list[dict] or None
        The remaining deck. If None, assumes standard 52-card deck minus hand.
    discards_left : int
        Number of discards remaining (max cards to discard per action is 5).
    hands_left : int
        Number of hands remaining to play.
    target : int
        Score target to clear the blind.

    Returns
    -------
    dict with keys:
        - "best_action": "keep" or "discard"
        - "discard_cards": list of card strings to discard (empty if "keep")
        - "keep_cards": list of card strings to keep
        - "expected_score": expected score of the best strategy
        - "current_best_score": best score without discarding
        - "all_options": list of top discard options evaluated, each a dict with
          "discard", "keep", "expected_score", "discard_count"
    """
    if deck_remaining is None:
        deck_remaining = remaining_deck(hand)

    max_discard = min(5, len(hand), discards_left * 5)  # can't discard more than 5 at once

    # Evaluate keeping the current hand (discard 0)
    current_best = _best_score_from_hand(hand)

    options = []
    # Discard 0 (keep current hand)
    options.append({
        "discard": [],
        "keep": [card_str(c) for c in hand],
        "expected_score": float(current_best),
        "discard_count": 0,
    })

    # Evaluate all possible discard sets of size 1..max_discard
    for n_discard in range(1, max_discard + 1):
        n_combos = comb(len(hand), n_discard)
        draws_per_combo = comb(len(deck_remaining), n_discard)

        # Determine samples per combo: use exact if total evals for this
        # discard count fit within budget, otherwise use Monte Carlo with
        # the budget divided evenly across combos.
        total_evals = n_combos * draws_per_combo
        if total_evals <= _EXACT_EVAL_BUDGET:
            samples_per = None  # exact
        else:
            samples_per = max(50, _TOTAL_MC_BUDGET // n_combos)

        for discard_combo in combinations(range(len(hand)), n_discard):
            keep = [hand[i] for i in range(len(hand)) if i not in discard_combo]
            discarded = [hand[i] for i in discard_combo]

            expected = _expected_score_after_discard(
                keep, n_discard, deck_remaining, samples=samples_per
            )

            options.append({
                "discard": [card_str(c) for c in discarded],
                "keep": [card_str(c) for c in keep],
                "expected_score": expected,
                "discard_count": n_discard,
            })

    # Sort by expected score descending
    options.sort(key=lambda x: x["expected_score"], reverse=True)

    best = options[0]
    return {
        "best_action": "keep" if best["discard_count"] == 0 else "discard",
        "discard_cards": best["discard"],
        "keep_cards": best["keep"],
        "expected_score": best["expected_score"],
        "current_best_score": float(current_best),
        "all_options": options[:20],  # top 20 strategies
    }


# --- Strategic analysis ---

def _flush_potential(hand, deck_remaining):
    """
    Analyze flush potential: for each suit, how many cards do we have,
    and what's the probability of completing a flush by discarding non-suit cards.
    """
    suit_cards = {}
    for c in hand:
        suit_cards.setdefault(c["suit"], []).append(c)

    results = []
    for suit, cards_in_suit in suit_cards.items():
        count = len(cards_in_suit)
        if count < 3:
            continue  # need at least 3 of a suit to have realistic flush potential

        needed = 5 - count
        if needed <= 0:
            # Already have 5+ of this suit — flush is available
            results.append({
                "suit": suit,
                "cards_held": count,
                "needed": 0,
                "probability": 1.0,
                "keep": [card_str(c) for c in cards_in_suit[:5]],
            })
            continue

        # Count how many of this suit remain in the deck
        suit_in_deck = sum(1 for c in deck_remaining if c["suit"] == suit)
        deck_size = len(deck_remaining)

        if suit_in_deck < needed:
            prob = 0.0
        else:
            # Probability of drawing at least `needed` of the suit when
            # we discard (8 - count) non-suit cards and draw that many.
            # We discard all non-suit cards: that's (8 - count) cards discarded.
            # But we can only discard up to 5, so:
            n_discard = min(5, len(hand) - count)
            # We need at least `needed` of the suit out of `n_discard` drawn cards.
            # P(X >= needed) where X ~ Hypergeometric(deck_size, suit_in_deck, n_discard)
            # = 1 - P(X < needed) = 1 - sum_{k=0}^{needed-1} P(X=k)
            prob = 0.0
            for k in range(needed, min(suit_in_deck, n_discard) + 1):
                p = (comb(suit_in_deck, k) * comb(deck_size - suit_in_deck, n_discard - k)
                     / comb(deck_size, n_discard))
                prob += p

        results.append({
            "suit": suit,
            "cards_held": count,
            "needed": needed,
            "probability": prob,
            "keep": [card_str(c) for c in cards_in_suit],
        })

    results.sort(key=lambda x: x["probability"], reverse=True)
    return results


def _straight_potential(hand, deck_remaining):
    """
    Analyze straight potential: find runs of consecutive ranks in the hand
    and calculate the probability of completing a 5-card straight.
    """
    ranks = sorted(set(c["rank"] for c in hand))
    deck_size = len(deck_remaining)
    results = []

    # Check all possible 5-card straight windows
    # Windows: A-2-3-4-5 (represented as [14,2,3,4,5]) and normal [r, r+1, ..., r+4]
    windows = []
    for low in range(2, 11):  # 2-6 through 10-A
        windows.append(list(range(low, low + 5)))
    windows.append([14, 2, 3, 4, 5])  # Ace-low straight

    for window in windows:
        window_set = set(window)
        held_ranks = window_set & set(ranks)
        missing_ranks = window_set - set(ranks)
        count_held = len(held_ranks)

        if count_held < 3:
            continue  # need at least 3 of the 5 ranks

        needed = len(missing_ranks)
        # Cards to keep: cards whose rank is in the window (pick one per rank)
        keep_cards = []
        for r in held_ranks:
            for c in hand:
                if c["rank"] == r and c not in keep_cards:
                    keep_cards.append(c)
                    break

        if needed == 0:
            results.append({
                "window": [_rank_name(r) for r in window],
                "held": count_held,
                "needed": 0,
                "probability": 1.0,
                "keep": [card_str(c) for c in keep_cards],
                "missing_ranks": [],
            })
            continue

        # How many cards of each missing rank are in the deck?
        n_discard = min(5, len(hand) - count_held)
        if n_discard < needed:
            continue  # can't discard enough cards

        # For the probability calculation: we need at least one card of each
        # missing rank. This is complex for multiple missing ranks.
        # Simple approach for 1 missing rank:
        if needed == 1:
            missing_rank = list(missing_ranks)[0]
            available = sum(1 for c in deck_remaining if c["rank"] == missing_rank)
            if available == 0:
                prob = 0.0
            else:
                # P(at least 1 of the missing rank in n_discard draws from deck)
                # = 1 - C(deck_size - available, n_discard) / C(deck_size, n_discard)
                prob = 1.0 - comb(deck_size - available, n_discard) / comb(deck_size, n_discard)
        elif needed == 2:
            # Need both missing ranks. Use inclusion-exclusion.
            missing_list = list(missing_ranks)
            avail = [sum(1 for c in deck_remaining if c["rank"] == r) for r in missing_list]
            if any(a == 0 for a in avail):
                prob = 0.0
            else:
                # P(get at least one of rank A AND at least one of rank B)
                # = 1 - P(miss A) - P(miss B) + P(miss A and miss B)
                total_combos = comb(deck_size, n_discard)
                non_a = deck_size - avail[0]
                non_b = deck_size - avail[1]
                non_ab = deck_size - avail[0] - avail[1]
                p_miss_a = comb(non_a, n_discard) / total_combos if non_a >= n_discard else 0
                p_miss_b = comb(non_b, n_discard) / total_combos if non_b >= n_discard else 0
                p_miss_ab = comb(non_ab, n_discard) / total_combos if non_ab >= n_discard else 0
                prob = 1.0 - p_miss_a - p_miss_b + p_miss_ab
        else:
            prob = 0.0  # 3+ missing ranks is very unlikely

        results.append({
            "window": [_rank_name(r) for r in window],
            "held": count_held,
            "needed": needed,
            "probability": prob,
            "keep": [card_str(c) for c in keep_cards],
            "missing_ranks": [_rank_name(r) for r in missing_ranks],
        })

    results.sort(key=lambda x: x["probability"], reverse=True)
    return results


def _rank_name(rank):
    """Convert numeric rank to display name."""
    return RANK_NAMES.get(rank, str(rank))


def _pair_upgrade_potential(hand, deck_remaining):
    """
    Analyze potential to upgrade existing pairs to three-of-a-kind,
    four-of-a-kind, or full house by discarding non-pair cards.
    """
    rank_counts = Counter(c["rank"] for c in hand)
    paired_ranks = {r: cnt for r, cnt in rank_counts.items() if cnt >= 2}

    if not paired_ranks:
        return []

    deck_size = len(deck_remaining)
    results = []

    for rank, count in paired_ranks.items():
        # How many more of this rank are in the deck?
        available = sum(1 for c in deck_remaining if c["rank"] == rank)
        # Cards to keep: the paired cards
        keep_cards = [c for c in hand if c["rank"] == rank]
        n_discard = min(5, len(hand) - count)

        if count == 2 and available >= 1:
            # Chance to upgrade to Three of a Kind
            prob_trips = 1.0 - comb(deck_size - available, n_discard) / comb(deck_size, n_discard)
            results.append({
                "rank": _rank_name(rank),
                "current": "Pair",
                "target": "Three of a Kind",
                "probability": prob_trips,
                "keep": [card_str(c) for c in keep_cards],
                "available_in_deck": available,
            })
        if count == 3 and available >= 1:
            prob_quads = 1.0 - comb(deck_size - available, n_discard) / comb(deck_size, n_discard)
            results.append({
                "rank": _rank_name(rank),
                "current": "Three of a Kind",
                "target": "Four of a Kind",
                "probability": prob_quads,
                "keep": [card_str(c) for c in keep_cards],
                "available_in_deck": available,
            })

    results.sort(key=lambda x: x["probability"], reverse=True)
    return results


def analyze_hand(hand, target=300):
    """
    Return a structured strategic analysis of the hand.

    Parameters
    ----------
    hand : list[dict]
        The 8-card hand.
    target : int
        Score target to clear the blind.

    Returns
    -------
    dict with keys:
        - "current_best": dict with "score", "hand_type", "cards"
        - "flush_potential": list of flush opportunities
        - "straight_potential": list of straight opportunities
        - "pair_upgrade_potential": list of pair upgrade opportunities
        - "recommended_action": "play" or "discard for <target hand>"
        - "recommended_expected_score": expected score for the recommendation
        - "clears_target": whether the recommendation clears the target
    """
    deck = remaining_deck(hand)

    # Current best play
    plays = find_all_plays(hand)
    top_play = plays[0]
    current_score, current_type, current_cards = top_play

    # Potential analyses
    flush_pot = _flush_potential(hand, deck)
    straight_pot = _straight_potential(hand, deck)
    pair_pot = _pair_upgrade_potential(hand, deck)

    # Determine recommendation
    # If current hand clears target, recommend playing
    if current_score >= target:
        rec_action = "play"
        rec_score = float(current_score)
    else:
        # Run the optimizer for the best discard strategy
        opt = optimal_discard(hand, deck, target=target)
        if opt["expected_score"] > current_score * 1.1:
            # Discarding is meaningfully better (>10% improvement)
            # Figure out what we're discarding for
            discard_target = "better hand"
            # Check if the best discard aligns with a flush or straight draw
            if flush_pot and flush_pot[0]["probability"] > 0.3 and flush_pot[0]["needed"] > 0:
                discard_target = "Flush"
            elif straight_pot and straight_pot[0]["probability"] > 0.3 and straight_pot[0]["needed"] > 0:
                discard_target = "Straight"
            elif pair_pot and pair_pot[0]["probability"] > 0.3:
                discard_target = pair_pot[0]["target"]

            rec_action = f"discard for {discard_target}"
            rec_score = opt["expected_score"]
        else:
            rec_action = "play"
            rec_score = float(current_score)

    return {
        "current_best": {
            "score": current_score,
            "hand_type": current_type,
            "cards": [card_str(c) for c in current_cards],
        },
        "flush_potential": flush_pot,
        "straight_potential": straight_pot,
        "pair_upgrade_potential": pair_pot,
        "recommended_action": rec_action,
        "recommended_expected_score": rec_score,
        "clears_target": rec_score >= target,
    }


# --- Minimum clearing hands ---

def min_clearing_hand(hand_type, target=300):
    """
    For a given hand type, find the minimum card combination that clears
    the target score. This shows the weakest hand of each type that still
    reaches the target.

    Parameters
    ----------
    hand_type : str
        One of the hand type names from HAND_TYPES (e.g., "Pair", "Flush").
    target : int
        Score target to clear.

    Returns
    -------
    dict with keys:
        - "hand_type": the hand type queried
        - "clears": bool — whether any hand of this type can clear the target
        - "min_score": the minimum score achievable with this hand type
        - "max_score": the maximum score achievable with this hand type
        - "example_min": card strings for the weakest clearing hand (or weakest overall)
        - "example_max": card strings for the strongest hand of this type
        - "target": the target score
    """
    if hand_type not in HAND_TYPES:
        raise ValueError(f"Unknown hand type: {hand_type}. Valid: {list(HAND_TYPES.keys())}")

    base_chips, base_mult = HAND_TYPES[hand_type]

    # Generate example hands of this type and find min/max scores
    examples = _generate_example_hands(hand_type)
    if not examples:
        return {
            "hand_type": hand_type,
            "clears": False,
            "min_score": 0,
            "max_score": 0,
            "example_min": [],
            "example_max": [],
            "target": target,
        }

    scored = []
    for ex in examples:
        s, ht, _, _, _ = score_hand(ex)
        if ht == hand_type:
            scored.append((s, ex))

    if not scored:
        return {
            "hand_type": hand_type,
            "clears": False,
            "min_score": 0,
            "max_score": 0,
            "example_min": [],
            "example_max": [],
            "target": target,
        }

    scored.sort(key=lambda x: x[0])
    min_score, min_hand = scored[0]
    max_score, max_hand = scored[-1]

    # Find the weakest hand that still clears target
    clearing = [(s, h) for s, h in scored if s >= target]
    if clearing:
        example_min_clear = clearing[0]
    else:
        example_min_clear = (min_score, min_hand)

    return {
        "hand_type": hand_type,
        "clears": max_score >= target,
        "min_score": min_score,
        "max_score": max_score,
        "example_min": [card_str(c) for c in example_min_clear[1]],
        "example_max": [card_str(c) for c in max_hand],
        "target": target,
    }


def _generate_example_hands(hand_type):
    """
    Generate representative example hands of the given type.
    Returns a list of hands (each hand is a list of card dicts).
    Not exhaustive — returns boundary cases (weakest and strongest).
    """
    suits = ["hearts", "diamonds", "clubs", "spades"]

    if hand_type == "High Card":
        # Weakest: single 2. Strongest: single Ace.
        # As 5-card hands: use non-connecting, non-suited cards
        return [
            [card(2, "hearts"), card(3, "diamonds"), card(5, "clubs"),
             card(7, "spades"), card(9, "hearts")],
            [card(14, "hearts"), card(12, "diamonds"), card(10, "clubs"),
             card(8, "spades"), card(6, "hearts")],
        ]

    if hand_type == "Pair":
        results = []
        for rank in [2, 7, 14]:
            results.append([card(rank, "hearts"), card(rank, "diamonds"),
                            card(3 if rank != 3 else 4, "clubs"),
                            card(5 if rank != 5 else 6, "spades"),
                            card(8 if rank != 8 else 9, "hearts")])
        return results

    if hand_type == "Two Pair":
        results = []
        for r1, r2 in [(2, 3), (7, 8), (13, 14)]:
            results.append([card(r1, "hearts"), card(r1, "diamonds"),
                            card(r2, "clubs"), card(r2, "spades"),
                            card(5 if r1 != 5 else 6, "hearts")])
        return results

    if hand_type == "Three of a Kind":
        results = []
        for rank in [2, 7, 14]:
            results.append([card(rank, "hearts"), card(rank, "diamonds"),
                            card(rank, "clubs"),
                            card(3 if rank != 3 else 4, "spades"),
                            card(5 if rank != 5 else 6, "hearts")])
        return results

    if hand_type == "Straight":
        return [
            [card(14, "hearts"), card(2, "diamonds"), card(3, "clubs"),
             card(4, "spades"), card(5, "hearts")],  # Ace-low (weakest)
            [card(2, "hearts"), card(3, "diamonds"), card(4, "clubs"),
             card(5, "spades"), card(6, "hearts")],
            [card(10, "hearts"), card(11, "diamonds"), card(12, "clubs"),
             card(13, "spades"), card(14, "hearts")],  # Ace-high (strongest)
        ]

    if hand_type == "Flush":
        return [
            [card(2, "hearts"), card(3, "hearts"), card(5, "hearts"),
             card(7, "hearts"), card(9, "hearts")],  # weak flush
            [card(14, "hearts"), card(13, "hearts"), card(12, "hearts"),
             card(11, "hearts"), card(9, "hearts")],  # strong flush
        ]

    if hand_type == "Full House":
        results = []
        for r3, r2 in [(2, 3), (7, 8), (14, 13)]:
            results.append([card(r3, "hearts"), card(r3, "diamonds"),
                            card(r3, "clubs"), card(r2, "spades"),
                            card(r2, "hearts")])
        return results

    if hand_type == "Four of a Kind":
        results = []
        for rank in [2, 7, 14]:
            results.append([card(rank, "hearts"), card(rank, "diamonds"),
                            card(rank, "clubs"), card(rank, "spades"),
                            card(3 if rank != 3 else 4, "hearts")])
        return results

    if hand_type == "Straight Flush":
        return [
            [card(14, "hearts"), card(2, "hearts"), card(3, "hearts"),
             card(4, "hearts"), card(5, "hearts")],
            [card(10, "hearts"), card(11, "hearts"), card(12, "hearts"),
             card(13, "hearts"), card(14, "hearts")],
        ]

    if hand_type == "Five of a Kind":
        # Not possible in a standard deck without wild cards; skip
        return []

    if hand_type == "Flush Five":
        return []

    if hand_type == "Flush House":
        return []

    return []


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
