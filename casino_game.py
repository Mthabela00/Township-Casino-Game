"""
South African Casino Card Game
A complete implementation of the fishing-style card game popular in South Africa
with unique rules: 40-card deck, face-up capture piles, and opponent pile interactions.
"""

import random
from typing import List, Dict, Tuple, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import copy

class Suit(Enum):
    """Card suits with their display symbols"""
    SPADES = '♠'
    HEARTS = '♥'
    DIAMONDS = '♦'
    CLUBS = '♣'

class Card:
    """Represents a playing card with South African Casino specific values"""
    
    def __init__(self, rank: str, suit: Suit):
        self.rank = rank
        self.suit = suit
        self._set_values()
    
    def _set_values(self):
        """Set the numerical values for gameplay"""
        if self.rank == 'A':
            self.values = [1, 14]  # Ace can be 1 or 14
            self.display_rank = 'A'
            self.numeric_value = 1
        elif self.rank in ['J', 'Q', 'K']:
            self.display_rank = self.rank
            if self.rank == 'J':
                self.values = [11]
                self.numeric_value = 11
            elif self.rank == 'Q':
                self.values = [12]
                self.numeric_value = 12
            else:  # K
                self.values = [13]
                self.numeric_value = 13
        else:  # 2-10
            self.display_rank = self.rank
            value = int(self.rank)
            self.values = [value]
            self.numeric_value = value
    
    def __repr__(self):
        return f"{self.display_rank}{self.suit.value}"
    
    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit
    
    def __hash__(self):
        return hash((self.rank, self.suit))

@dataclass
class Build:
    """Represents a build (single or augmented) in the layout"""
    cards: List[Card]
    total_value: int
    owner: int  # Player index who owns/created this build
    is_augmented: bool = False
    
    def __repr__(self):
        build_type = "Augmented" if self.is_augmented else "Single"
        return f"{build_type}Build({self.cards}, value={self.total_value}, owner={self.owner})"

class Player:
    """Represents a player in the game"""
    
    def __init__(self, name: str, player_id: int, is_ai: bool = False):
        self.name = name
        self.id = player_id
        self.hand: List[Card] = []
        self.capture_pile: List[Card] = []  # Face-up in South African rules!
        self.score = 0
        self.is_ai = is_ai
        self.last_capture = False
    
    def add_to_hand(self, card: Card):
        """Add a card to player's hand"""
        self.hand.append(card)
    
    def play_card(self, card_index: int) -> Card:
        """Play a card from hand by index"""
        if 0 <= card_index < len(self.hand):
            return self.hand.pop(card_index)
        raise IndexError("Invalid card index")
    
    def capture_cards(self, cards: List[Card]):
        """Add captured cards to face-up pile (top card visible)"""
        self.capture_pile.extend(cards)
    
    def get_top_card(self) -> Optional[Card]:
        """Get the top card of the capture pile (visible to opponents)"""
        if self.capture_pile:
            return self.capture_pile[-1]
        return None
    
    def count_cards(self) -> int:
        """Count total cards in capture pile"""
        return len(self.capture_pile)
    
    def count_spades(self) -> int:
        """Count spades in capture pile"""
        return sum(1 for card in self.capture_pile if card.suit == Suit.SPADES)
    
    def has_card(self, card: Card) -> bool:
        """Check if player has specific card in hand"""
        return any(c == card for c in self.hand)
    
    def __repr__(self):
        return f"Player({self.name}, cards={len(self.hand)}, captures={len(self.capture_pile)})"

class SouthAfricanCasinoGame:
    """Main game engine implementing South African Casino rules"""
    
    def __init__(self, num_players: int = 2, use_40_card_deck: bool = True, 
                 partnerships: Optional[List[Tuple[int, int]]] = None):
        """
        Initialize a new game of South African Casino
        
        Args:
            num_players: 2, 3, or 4 players
            use_40_card_deck: If True, removes J, Q, K (South African variant)
            partnerships: List of tuples for 4-player partnerships
        """
        if num_players not in [2, 3, 4]:
            raise ValueError("Number of players must be 2, 3, or 4")
        
        self.num_players = num_players
        self.use_40_card_deck = use_40_card_deck
        self.partnerships = partnerships
        self.is_partnership_game = partnerships is not None
        
        # Game state
        self.deck: List[Card] = []
        self.players: List[Player] = []
        self.layout: List[Union[Card, Build]] = []  # Can contain loose cards or builds
        self.current_player = 0
        self.game_phase = "setup"  # setup, playing, scoring
        self.turn_history = []
        
        # Special cards for scoring
        self.spy_two = Card('2', Suit.SPADES)
        self.big_ten = Card('10', Suit.DIAMONDS)
        
        # Statistics
        self.captures_this_turn = []
        self.builds_created = []
        
        self._create_deck()
        self._create_players()
    
    def _create_deck(self):
        """Create and shuffle the deck (52 or 40 cards)"""
        suits = [Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS]
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        
        if self.use_40_card_deck:
            # Remove Jacks, Queens, and Kings for South African variant
            ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'A']
        
        self.deck = [Card(rank, suit) for suit in suits for rank in ranks]
        random.shuffle(self.deck)
    
    def _create_players(self):
        """Create player objects"""
        player_names = ["Player 1", "Player 2", "Player 3", "Player 4"]
        for i in range(self.num_players):
            is_ai = False  # Can be extended for AI opponents
            self.players.append(Player(player_names[i], i, is_ai))
    
    def _cut_deck(self) -> List[Card]:
        """Cut four cards from the middle for initial layout (South African rule)"""
        middle = len(self.deck) // 2
        start = middle - 2
        end = middle + 2
        return [self.deck.pop(start) for _ in range(4)]
    
    def setup_game(self):
        """Set up the initial game state"""
        # Create initial layout by cutting 4 cards from middle
        layout_cards = self._cut_deck()
        self.layout.extend(layout_cards)
        
        # Deal remaining cards to players
        while self.deck:
            for player in self.players:
                if self.deck:
                    player.add_to_hand(self.deck.pop())
        
        # Determine starting player (right of dealer)
        self.current_player = 0
        self.game_phase = "playing"
        
        print("Game setup complete!")
        print(f"Initial layout: {self.layout}")
        for player in self.players:
            print(f"{player.name}: {len(player.hand)} cards")
    
    def get_loose_cards(self) -> List[Card]:
        """Get all loose cards (not in builds) from layout"""
        return [item for item in self.layout if isinstance(item, Card)]
    
    def get_builds(self) -> List[Build]:
        """Get all builds from layout"""
        return [item for item in self.layout if isinstance(item, Build)]
    
    def get_owned_builds(self, player_id: int) -> List[Build]:
        """Get builds owned by specific player"""
        return [build for build in self.get_builds() if build.owner == player_id]
    
    def calculate_total(self, cards: List[Card]) -> List[int]:
        """
        Calculate all possible total values from cards.
        Ace can count as 1 or 14.
        """
        totals = set([0])
        
        for card in cards:
            new_totals = set()
            for total in totals:
                for value in card.values:
                    new_totals.add(total + value)
            totals = new_totals
        
        return sorted(list(totals))
    
    def find_captures(self, played_card: Card, player: Player) -> List[List[Union[Card, Build]]]:
        """
        Find all possible captures with the played card.
        Returns list of capture groups (cards/builds that can be captured together).
        """
        capture_groups = []
        
        # Get all possible capture targets
        all_targets = self.get_loose_cards() + self.get_builds()
        
        # Check for single card matches
        for target in all_targets:
            if isinstance(target, Card):
                if played_card.numeric_value == target.numeric_value:
                    capture_groups.append([target])
            elif isinstance(target, Build):  # Can capture any build regardless of owner
                if played_card.numeric_value == target.total_value:
                    capture_groups.append([target])
        
        # Check for multiple loose cards that sum to played card value
        loose_cards = self.get_loose_cards()
        n = len(loose_cards)
        
        # Check all combinations of loose cards
        from itertools import combinations
        for r in range(2, n + 1):
            for combo in combinations(loose_cards, r):
                combo_list = list(combo)
                totals = self.calculate_total(combo_list)
                if played_card.numeric_value in totals:
                    capture_groups.append(combo_list)
        
        # Check for combinations including builds
        for build in self.get_builds():
            # Build + loose cards
            for combo in combinations(loose_cards, 1):  # Start with 1 loose card
                combo_list = list(combo) + [build]
                totals = self.calculate_total([c for c in combo_list if isinstance(c, Card)])
                # Add build value
                adjusted_totals = [t + build.total_value for t in totals]
                if played_card.numeric_value in adjusted_totals:
                    capture_groups.append(combo_list)
        
        return capture_groups
    
    def can_create_build(self, played_card: Card, player: Player) -> List[Dict]:
        """
        Check if player can create a build with the played card.
        Returns list of possible build configurations.
        """
        possible_builds = []
        loose_cards = self.get_loose_cards()
        
        # Check all combinations of loose cards + played card
        from itertools import combinations
        
        # Player must have a card in hand to capture the build later
        available_capture_values = [card.numeric_value for card in player.hand 
                                   if card != played_card]
        
        for r in range(1, len(loose_cards) + 1):
            for combo in combinations(loose_cards, r):
                combo_cards = list(combo)
                all_cards = combo_cards + [played_card]
                
                # Calculate all possible totals
                totals = self.calculate_total(all_cards)
                
                # Check if player has a card to capture any of these totals
                for total in totals:
                    if total in available_capture_values:
                        possible_builds.append({
                            'cards': combo_cards,
                            'played_card': played_card,
                            'total_value': total,
                            'type': 'single'
                        })
                        break
        
        return possible_builds
    
    def can_augment_build(self, played_card: Card, player: Player) -> List[Dict]:
        """
        Check if player can augment an existing build.
        Can use own/partner's build or opponent's build (changing ownership).
        """
        possible_augmentations = []
        builds = self.get_builds()
        
        # Get top cards from opponents' capture piles (South African rule!)
        opponent_top_cards = []
        for i, opp_player in enumerate(self.players):
            if i != player.id and (not self.is_partnership_game or 
                                  not self._are_partners(player.id, i)):
                top_card = opp_player.get_top_card()
                if top_card:
                    opponent_top_cards.append(top_card)
        
        # Check each build
        for build in builds:
            # For opponent's builds: we can change value and take ownership
            if build.owner != player.id and (not self.is_partnership_game or 
                                           not self._are_partners(player.id, build.owner)):
                
                # Calculate new possible totals with played card
                # Player must have a card matching the new total
                new_totals = self.calculate_total(build.cards + [played_card])
                available_capture_values = [card.numeric_value for card in player.hand 
                                           if card != played_card]
                
                for new_total in new_totals:
                    if new_total in available_capture_values:
                        possible_augmentations.append({
                            'build': build,
                            'played_card': played_card,
                            'new_total': new_total,
                            'action': 'change_opponent_build',
                            'cards_used': [played_card]
                        })
            
            # For own/partner's builds: can augment with equal values
            if build.owner == player.id or (self.is_partnership_game and 
                                          self._are_partners(player.id, build.owner)):
                
                # Can use opponent's top card or loose cards
                available_cards = self.get_loose_cards() + opponent_top_cards
                
                # Find cards that equal the build's current value
                for card in available_cards:
                    if isinstance(card, Card):
                        # Check if this card equals the build value
                        for card_value in card.values:
                            if card_value == build.total_value:
                                possible_augmentations.append({
                                    'build': build,
                                    'played_card': played_card,
                                    'action': 'augment_own_build',
                                    'augmenting_card': card,
                                    'cards_used': [played_card, card]
                                })
        
        return possible_augmentations
    
    def _are_partners(self, player1_id: int, player2_id: int) -> bool:
        """Check if two players are partners"""
        if not self.partnerships:
            return False
        return any(set(pair) == {player1_id, player2_id} for pair in self.partnerships)
    
    def execute_capture(self, player: Player, played_card: Card, 
                       capture_group: List[Union[Card, Build]]) -> bool:
        """
        Execute a capture move.
        Returns True if successful.
        """
        if not capture_group:
            return False
        
        # Remove captured items from layout
        cards_to_capture = []
        for item in capture_group:
            if isinstance(item, Card):
                cards_to_capture.append(item)
                self.layout.remove(item)
            elif isinstance(item, Build):
                # Capture all cards in the build
                cards_to_capture.extend(item.cards)
                self.layout.remove(item)
        
        # Add played card and captured cards to player's pile
        all_captured = [played_card] + cards_to_capture
        player.capture_cards(all_captured)
        
        # Mark player as last to capture
        for p in self.players:
            p.last_capture = False
        player.last_capture = True
        
        self.captures_this_turn.append({
            'player': player.id,
            'played_card': played_card,
            'captured': cards_to_capture
        })
        
        return True
    
    def execute_build(self, player: Player, played_card: Card, 
                     build_config: Dict) -> bool:
        """
        Execute a build creation or augmentation.
        Returns True if successful.
        """
        build_type = build_config.get('type', 'single')
        
        if build_type == 'single':
            # Create new single build
            build_cards = build_config['cards'].copy()
            build_cards.append(played_card)
            
            new_build = Build(
                cards=build_cards,
                total_value=build_config['total_value'],
                owner=player.id,
                is_augmented=False
            )
            
            # Remove used cards from layout
            for card in build_config['cards']:
                self.layout.remove(card)
            
            # Add new build to layout
            self.layout.append(new_build)
            self.builds_created.append(new_build)
            
            return True
        
        elif 'action' in build_config:
            action = build_config['action']
            
            if action == 'change_opponent_build':
                # Change opponent's build value and take ownership
                build = build_config['build']
                
                # Add played card to build
                build.cards.append(played_card)
                build.total_value = build_config['new_total']
                build.owner = player.id  # Change ownership
                
                return True
            
            elif action == 'augment_own_build':
                # Augment own/partner's build
                build = build_config['build']
                augmenting_card = build_config['augmenting_card']
                
                # Check if we need to remove augmenting card from layout
                if augmenting_card in self.get_loose_cards():
                    self.layout.remove(augmenting_card)
                
                # Add cards to build
                build.cards.append(played_card)
                build.cards.append(augmenting_card)
                build.is_augmented = True
                
                return True
        
        return False
    
    def discard_card(self, player: Player, played_card: Card):
        """Discard a card to the layout"""
        self.layout.append(played_card)
        print(f"{player.name} discarded {played_card}")
    
    def get_ai_move(self, player: Player) -> Tuple[Optional[int], Optional[Union[List, Dict]]]:
        """
        Simple AI to make moves. Returns (card_index, action_details).
        Can be expanded for more sophisticated AI.
        """
        # For now, play first card with simple logic
        if not player.hand:
            return None, None
        
        # Try to find captures first
        for i, card in enumerate(player.hand):
            captures = self.find_captures(card, player)
            if captures:
                # Take the first capture option
                return i, {'type': 'capture', 'target': captures[0]}
        
        # Try to create a build
        for i, card in enumerate(player.hand):
            builds = self.can_create_build(card, player)
            if builds:
                return i, {'type': 'build', 'config': builds[0]}
        
        # Default: discard first card
        return 0, {'type': 'discard'}
    
    def play_turn(self, player: Player):
        """Execute one player's turn"""
        print(f"\n--- {player.name}'s turn ---")
        print(f"Layout: {self.layout}")
        print(f"Your hand: {player.hand}")
        print(f"Your capture pile: {player.capture_pile[-3:] if player.capture_pile else []}")
        
        # Reset turn tracking
        self.captures_this_turn = []
        
        # Get player's move
        if player.is_ai:
            card_index, action = self.get_ai_move(player)
            if card_index is None:
                print("AI has no cards to play!")
                return
            played_card = player.play_card(card_index)
            print(f"AI plays {played_card}")
        else:
            # Human player
            print("Choose a card to play (0-indexed):")
            for i, card in enumerate(player.hand):
                print(f"{i}: {card}")
            
            try:
                card_index = int(input("Enter card number: "))
                played_card = player.play_card(card_index)
                print(f"You play {played_card}")
            except (ValueError, IndexError):
                print("Invalid choice, playing first card")
                played_card = player.play_card(0)
        
        # Check for possible actions
        possible_captures = self.find_captures(played_card, player)
        possible_builds = self.can_create_build(played_card, player)
        possible_augments = self.can_augment_build(played_card, player)
        
        # For AI, use predetermined action
        if player.is_ai:
            if action['type'] == 'capture' and possible_captures:
                self.execute_capture(player, played_card, action['target'])
            elif action['type'] == 'build' and possible_builds:
                self.execute_build(player, played_card, action['config'])
            else:
                self.discard_card(player, played_card)
            return
        
        # For human player, show options
        print("\nPossible actions:")
        actions = []
        
        # Capture options
        for i, capture_group in enumerate(possible_captures):
            print(f"{len(actions)}: Capture {capture_group}")
            actions.append(('capture', capture_group))
        
        # Build options
        for i, build_config in enumerate(possible_builds):
            print(f"{len(actions)}: Create build {build_config}")
            actions.append(('build', build_config))
        
        # Augment options
        for i, augment_config in enumerate(possible_augments):
            print(f"{len(actions)}: Augment build {augment_config}")
            actions.append(('augment', augment_config))
        
        # Discard option
        print(f"{len(actions)}: Discard card")
        actions.append(('discard', None))
        
        if actions:
            try:
                choice = int(input("Choose action: "))
                if 0 <= choice < len(actions):
                    action_type, action_data = actions[choice]
                    
                    if action_type == 'capture':
                        self.execute_capture(player, played_card, action_data)
                        print(f"Captured {action_data}")
                    elif action_type == 'build':
                        if self.execute_build(player, played_card, action_data):
                            print(f"Created build: {action_data}")
                    elif action_type == 'augment':
                        if self.execute_build(player, played_card, action_data):
                            print(f"Augmented build: {action_data}")
                    else:  # discard
                        self.discard_card(player, played_card)
                else:
                    print("Invalid choice, discarding")
                    self.discard_card(player, played_card)
            except ValueError:
                print("Invalid input, discarding")
                self.discard_card(player, played_card)
        else:
            print("No actions available, discarding")
            self.discard_card(player, played_card)
    
    def calculate_scores(self) -> Dict[int, int]:
        """
        Calculate scores according to South African Casino rules.
        Returns dictionary of player_id -> score.
        """
        scores = {player.id: 0 for player in self.players}
        
        if self.is_partnership_game or self.num_players == 2:
            # 2-player or partnership: 11 points total
            # Most cards (2 points), most spades (2 points), 
            # spy two (1), big ten (2), aces (1 each)
            total_points = 11
        else:
            # 3 or 4 solo players: 7 points total
            # Only specific cards: spy two (1), big ten (2), aces (1 each)
            total_points = 7
        
        # Count cards and spades for each player/partnership
        card_counts = defaultdict(int)
        spade_counts = defaultdict(int)
        special_scores = defaultdict(int)
        
        for player in self.players:
            # For partnerships, combine counts
            if self.is_partnership_game:
                partner_id = self._get_partner_id(player.id)
                key = tuple(sorted([player.id, partner_id]))
            else:
                key = player.id
            
            card_counts[key] += player.count_cards()
            spade_counts[key] += player.count_spades()
            
            # Check for special cards
            if player.has_card(self.spy_two) or self.spy_two in player.capture_pile:
                special_scores[key] += 1
            
            if player.has_card(self.big_ten) or self.big_ten in player.capture_pile:
                special_scores[key] += 2
            
            # Count aces
            ace_count = sum(1 for card in player.capture_pile if card.rank == 'A')
            special_scores[key] += ace_count
        
        # Award points for most cards (if applicable)
        if total_points == 11:  # 2-player or partnership game
            # Most cards (2 points)
            max_cards = max(card_counts.values())
            winners = [k for k, v in card_counts.items() if v == max_cards]
            if len(winners) == 1:
                if isinstance(winners[0], tuple):  # Partnership
                    for pid in winners[0]:
                        scores[pid] += 2
                else:
                    scores[winners[0]] += 2
            else:  # Tie
                for winner in winners:
                    if isinstance(winner, tuple):
                        for pid in winner:
                            scores[pid] += 1
                    else:
                        scores[winner] += 1
            
            # Most spades (2 points)
            max_spades = max(spade_counts.values())
            winners = [k for k, v in spade_counts.items() if v == max_spades]
            if len(winners) == 1:
                if isinstance(winners[0], tuple):
                    for pid in winners[0]:
                        scores[pid] += 2
                else:
                    scores[winners[0]] += 2
            else:  # Tie
                for winner in winners:
                    if isinstance(winner, tuple):
                        for pid in winner:
                            scores[pid] += 1
                    else:
                        scores[winner] += 1
        
        # Add special card scores
        for key, points in special_scores.items():
            if isinstance(key, tuple):
                for pid in key:
                    scores[pid] += points
            else:
                scores[key] += points
        
        return scores
    
    def _get_partner_id(self, player_id: int) -> Optional[int]:
        """Get partner ID for a player in partnership game"""
        if not self.partnerships:
            return None
        
        for p1, p2 in self.partnerships:
            if p1 == player_id:
                return p2
            elif p2 == player_id:
                return p1
        return None
    
    def check_game_over(self) -> bool:
        """Check if game is over (all hands empty)"""
        return all(len(player.hand) == 0 for player in self.players)
    
    def end_of_hand_cleanup(self):
        """Clean up at end of hand - last capturer gets remaining layout"""
        last_capturer = None
        for player in self.players:
            if player.last_capture:
                last_capturer = player
                break
        
        if last_capturer and self.layout:
            # Capture all remaining cards
            remaining_cards = []
            for item in self.layout:
                if isinstance(item, Card):
                    remaining_cards.append(item)
                elif isinstance(item, Build):
                    remaining_cards.extend(item.cards)
            
            if remaining_cards:
                last_capturer.capture_cards(remaining_cards)
                print(f"{last_capturer.name} captures remaining layout: {remaining_cards}")
            
            self.layout.clear()
    
    def play_full_game(self):
        """Play a complete game from start to finish"""
        print("=" * 50)
        print("Starting South African Casino Game!")
        print("=" * 50)
        
        self.setup_game()
        
        # Main game loop
        round_num = 1
        while not self.check_game_over():
            print(f"\n{'='*30}")
            print(f"Round {round_num}")
            print(f"{'='*30}")
            
            # Each player takes a turn
            for i in range(self.num_players):
                player = self.players[(self.current_player + i) % self.num_players]
                if player.hand:  # Only play if has cards
                    self.play_turn(player)
            
            self.current_player = (self.current_player + 1) % self.num_players
            round_num += 1
        
        # End of hand cleanup
        self.end_of_hand_cleanup()
        
        # Calculate scores
        print("\n" + "="*50)
        print("Game Over! Calculating scores...")
        print("="*50)
        
        scores = self.calculate_scores()
        
        for player in self.players:
            print(f"{player.name}:")
            print(f"  Cards captured: {player.count_cards()}")
            print(f"  Spades captured: {player.count_spades()}")
            print(f"  Score: {scores[player.id]}")
            print(f"  Capture pile: {player.capture_pile}")
        
        # Determine winner
        max_score = max(scores.values())
        winners = [player.name for player in self.players if scores[player.id] == max_score]
        
        if len(winners) == 1:
            print(f"\n🎉 Winner: {winners[0]} with {max_score} points! 🎉")
        else:
            print(f"\n🤝 Tie between {', '.join(winners)} with {max_score} points each!")

# Example usage and test functions
def run_example_game():
    """Run an example 2-player game"""
    print("South African Casino - Example Game")
    print("This is a 2-player game with the 40-card variant.")
    
    game = SouthAfricanCasinoGame(num_players=2, use_40_card_deck=True)
    game.play_full_game()

def run_partnership_game():
    """Run a 4-player partnership game"""
    print("South African Casino - Partnership Game")
    print("4 players in partnerships: (0,2) vs (1,3)")
    
    partnerships = [(0, 2), (1, 3)]
    game = SouthAfricanCasinoGame(num_players=4, use_40_card_deck=True, 
                                  partnerships=partnerships)
    game.play_full_game()

def test_specific_scenario():
    """Test a specific game scenario for debugging"""
    print("Testing specific game scenario...")
    
    # Create a controlled game state
    game = SouthAfricanCasinoGame(num_players=2, use_40_card_deck=True)
    
    # Manually set up a test scenario
    test_layout = [
        Card('7', Suit.HEARTS),
        Card('3', Suit.SPADES),
        Card('4', Suit.DIAMONDS)
    ]
    game.layout = test_layout
    
    test_player = game.players[0]
    test_player.hand = [Card('7', Suit.CLUBS), Card('A', Suit.HEARTS)]
    
    # Test captures
    test_card = Card('7', Suit.CLUBS)
    captures = game.find_captures(test_card, test_player)
    print(f"Possible captures with {test_card}: {captures}")
    
    # Test build creation
    builds = game.can_create_build(test_card, test_player)
    print(f"Possible builds with {test_card}: {builds}")

if __name__ == "__main__":
    # Run an example game
    run_example_game()
    
    # Uncomment to run other examples:
    # run_partnership_game()
    # test_specific_scenario()
