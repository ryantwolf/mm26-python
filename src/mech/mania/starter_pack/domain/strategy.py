import logging

from mech.mania.starter_pack.domain.model.characters.character_decision import CharacterDecision
from mech.mania.starter_pack.domain.model.characters.position import Position
from mech.mania.starter_pack.domain.model.game_state import GameState
from mech.mania.starter_pack.domain.api import API
from mech.mania.starter_pack.domain.model.board import Board

class Strategy:
    def __init__(self, memory):
        self.memory = memory
        self.logger = logging.getLogger('strategy')
        self.logger.setLevel(logging.DEBUG)
        logging.basicConfig(level = logging.INFO)

    def make_decision(self, player_name: str, game_state: GameState) -> CharacterDecision:
        """
        Parameters:
        player_name (string): The name of your player
        game_state (GameState): The current game state
        """
        self.api = API(game_state, player_name)
        self.my_player = game_state.get_all_players()[player_name]
        self.board = game_state.get_pvp_board()
        self.curr_pos = self.my_player.get_position()

        self.logger.info("In make_decision")

        monster_position = game_state.get_monsters_on_board

        processed_board = self.process_board(game_state.get_board(self.curr_pos.board_id))
        monster_location = self.find_closest(game_state.get_monsters_on_board())

        if self.within_range(monster_location):
            return CharacterDecision(
                decision_type="ATTACK",
                action_position=monster_location,
                action_index=None
            )
        else:
            move_position = self.path_find(processed_board, self.curr_pos, monster_location)
            return CharacterDecision(
                decision_type="MOVE",
                action_position=move_position,
                action_index=None
            )

        last_action, type = self.memory.get_value("last_action", str)
        if last_action is not None and last_action == "PICKUP":
            self.memory.set_value("last_action", "EQUIP")
            return CharacterDecision(
                decision_type="EQUIP",
                action_position=None,
                action_index=self.my_player.get_free_inventory_index()
            )

        tile_items = self.board.get_tile_at(self.curr_pos).items
        if tile_items is not None or len(tile_items) > 0:
            self.memory.set_value("last_action", "PICKUP")
            return CharacterDecision(
                decision_type="PICKUP",
                action_position=None,
                action_index=0
            )

        weapon = self.my_player.get_weapon()
        enemies = self.api.find_enemies(self.curr_pos)
        if enemies is None or len(enemies) > 0:
            self.memory.set_value("last_action", "MOVE")
            return CharacterDecision(
                decision_type="MOVE",
                action_position=self.my_player.get_spawn_point(),
                action_index=None
            )

        enemy_pos = enemies[0].get_position()
        if self.curr_pos.manhattan_distance(enemy_pos) <= weapon.get_range():
            self.memory.set_value("last_action", "ATTACK")
            return CharacterDecision(
                decision_type="ATTACK",
                action_position=enemy_pos,
                action_index=None
            )

        self.memory.set_value("last_action", "MOVE")
        decision = CharacterDecision(
            decision_type="MOVE",
            action_position=find_position_to_move(self.my_player, enemy_pos),
            action_index=None
        )

        # Begining of my code
        decision = CharacterDecision(
            decision_type="MOVE",
            action_position=find_position_to_move(self.my_player, self.api.find_closest_portal(self.my_player)),
            action_index=None
        )

        return decision


    # feel free to write as many helper functions as you need!
    def find_position_to_move(self, player: Position, destination: Position) -> Position:
        path = self.api.find_path(player.get_position(), destination)
        pos = None
        if len(path) < player.get_speed():
            pos = path[-1]
        else:
            pos = path[player.get_speed() - 1]
        return pos

    def move_to(self, start: Position, end: Position):
        if start.x < end.x:
            return Position.create(start.x+1, start.y, start.board_id)
        elif start.x > end.x:
            return Position.create(start.x-1, start.y, start.board_id)
        elif start.y < end.y:
            return Position.create(start.x, start.y+1, start.board_id)
        elif start.y > end.y:
            return Position.create(start.x, start.y-1, start.board_id)
        else:
            return None

    def process_board(self, board: Board):
        grid = board.get_grid()
        processed_grid = [[tile.get_type() == "IMPASSIBLE" for tile in row] for row in grid]
        return processed_grid

    def dist(self, start, end):
        return abs(self.x - end.x) + abs(self.y-end.y)

    def find_closest(self, characters: list):
        return min(characters, lambda character: dist(character.position))

    def within_range(self, position: Position):
        return self.my_player.get_weapon().get_range() >= self.dist(self.curr_pos, position)