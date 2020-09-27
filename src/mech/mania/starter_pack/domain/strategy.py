import logging

from mech.mania.starter_pack.domain.model.characters.character_decision import CharacterDecision
from mech.mania.starter_pack.domain.model.characters.position import Position
from mech.mania.starter_pack.domain.model.characters.player import Player
from mech.mania.starter_pack.domain.model.game_state import GameState
from mech.mania.starter_pack.domain.api import API
import math
from mech.mania.starter_pack.domain.model.items.wearable import Wearable
from mech.mania.starter_pack.domain.model.items.weapon import Weapon
from mech.mania.starter_pack.domain.model.items.consumable import Consumable
from mech.mania.starter_pack.domain.model.items.accessory import Accessory
from mech.mania.starter_pack.domain.model.items.clothes import Clothes
from mech.mania.starter_pack.domain.model.items.hat import Hat
from mech.mania.starter_pack.domain.model.items.shoes import Shoes

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
        self.curr_pos = self.my_player.get_position()
        self.board = game_state.get_board(self.curr_pos.get_board_id())
        board_id = self.curr_pos.get_board_id()

        self.logger.info("\n\nSTARTING NEW TURN\n")
        self.logger.info("Current Position: ")
        self.logger.info('X: ' + str(self.curr_pos.get_x()))
        self.logger.info('Y: ' + str(self.curr_pos.get_y()))
        self.logger.info(f'\nInventory: {str(self.my_player.get_inventory())}')

        living_monsters = [monster for monster in game_state.get_monsters_on_board(board_id) if not monster.is_dead()]
        best_monster = self.find_best_monster(living_monsters)

        # Attack if monster is in range
        if (self.within_range(best_monster.get_position())):
            self.logger.info("Attacking monster")
            self.memory.set_value("last_action", "ATTACK")
            return CharacterDecision(
                decision_type="ATTACK",
                action_position=best_monster.get_position(),
                action_index=0
            )

        inventory = self.my_player.get_inventory()

        self.logger.info("MaxHP : " + str(self.my_player.get_max_health()))
        self.logger.info("Current defense: " + str(self.my_player.get_defense()))
        self.logger.info("Current speed: " + str(self.my_player.get_speed()))
        self.logger.info("Current attack: " + str(self.my_player.get_attack()))
        self.logger.info("Current experience: " + str(self.my_player.get_experience()))
        self.logger.info("Current level: " + str(self.my_player.get_level()))
        
        for i in range(len(inventory)):
            if self.is_better_item(inventory[i]):
                return self.equip(i)
            
        # Equip last item picked up
        last_action, type = self.memory.get_value("last_action", str)
        self.logger.info(f"Last_action: '{last_action}'")

        if last_action is not None and last_action == "PICKUP":
            self.logger.info("Equipping an item")
            self.memory.set_value("last_action", "EQUIP")
            return CharacterDecision(
                decision_type="EQUIP",
                action_position=None,
                action_index=0  # self.my_player.get_free_inventory_index()
            )
        if last_action is None:
            self.logger.info("The Last action was None")

        # Getting items on current times and picking up
        tile_items = self.board.get_tile_at(self.curr_pos).get_items()
        if tile_items is not None and len(tile_items) > 0 and len(self.my_player.get_inventory()) < 16:
            self.logger.info("\nThere are items on my tile, picking up item")
            self.logger.info("Items on this tile: " + str(tile_items))
            self.memory.set_value("last_action", "PICKUP")
            return CharacterDecision(
                decision_type="PICKUP",
                action_position=None,
                action_index=0
            )

        # Go to nearest best item
        items_dict = self.get_item_dict()
        self.logger.info("Items on board " + str(items_dict))
        if items_dict is not None and len(items_dict) > 0:
            self.logger.info("Going to item")
            nearest_item = min(items_dict, key=lambda item: self.cost_of_item(item))
            move_position = self.path_find(self.process_board(self.board), self.curr_pos, items_dict[nearest_item])
            return CharacterDecision(
                decision_type="MOVE",
                action_position=move_position,
                action_index=0
            )

        # Moving to best monster, no agro considered
        self.logger.info("Navigating to monster")
        self.memory.set_value("last_action", "MOVE")
        processed_board = self.process_board(self.board)
        move_position = self.path_find(processed_board, self.curr_pos, best_monster.get_position())
        return CharacterDecision(
            decision_type="MOVE",
            action_position=move_position,
            action_index=0
        )

    def is_better_item(self, item):
        if isinstance(item, Weapon):
            if self.my_player.get_weapon() == None or item.get_stats().get_flat_attack_change() > self.my_player.get_weapon().get_stats().get_flat_attack_change():
                return True
        if isinstance(item, Shoes):
            if self.my_player.get_shoes() == None or item.get_stats().get_flat_defense_change() > self.my_player.get_shoes().get_stats().get_flat_defense_change():
                return True
        if isinstance(item, Hat):
            if self.my_player.get_hat() == None or item.get_stats().get_flat_attack_change() > self.my_player.get_hat().get_stats().get_flat_attack_change():
                return True
        if isinstance(item, Clothes):
            if self.my_player.get_clothes() == None or item.get_stats().get_flat_attack_change() > self.my_player.get_clothes().get_stats().get_flat_attack_change():
                return True
        if isinstance(item, Accessory):
            if self.my_player.get_accessory() == None or item.get_stats().get_flat_attack_change() > self.my_player.get_accessory().get_stats().get_flat_attack_change():
                return True
        if isinstance(item, Consumable):
            return True
        return False

    # Returns the the next step to take on the optimal path to the endpoint form start point with given speed
    def path_find_with_speed(self, board, start, end, speed):
        self.logger.info("Finding Optimal Path")
        board[start.x][start.y] = 0
        board[end.x][end.y] = 1

        iter = 0  # Used to verify I don't go into infinite steps because of impossible path
        while board[start.x][start.y] == 0 and iter < len(board) * len(board[0]):
            for i in range(len(board)):
                for j in range(len(board[0])):
                    board = self.update_board_step(board, i, j)
            iter += 1

        i = start.x
        j = start.y
        # impossible to reach the end point
        if board[i][j] == 0:
            return None

        self.logger.info("Starting position for this move: " + str((i, j)))
        pos = None

        for m in range(speed):
            i, j, pos = self.get_next_move_from_opt_board(board, i, j, start)

        self.logger.info("I am moving to: " + str((i, j)))

        #self.print_2D_grid(board)
        return pos
    
    def path_find(self, board, start, end):
        return self.path_find_with_speed(board, start, end, self.my_player.get_speed())

    def update_board_step(self, board, i, j):
        if board[i][j] > 0:
            if self.check_bounds(board, i + 1, j):
                if board[i + 1][j] > board[i][j] + 1 or board[i + 1][j] == 0:
                    board[i + 1][j] = board[i][j] + 1
            if self.check_bounds(board, i - 1, j):
                if board[i - 1][j] > board[i][j] + 1 or board[i - 1][j] == 0:
                    board[i - 1][j] = board[i][j] + 1
            if self.check_bounds(board, i, j + 1):
                if board[i][j + 1] > board[i][j] + 1 or board[i][j + 1] == 0:
                    board[i][j + 1] = board[i][j] + 1
            if self.check_bounds(board, i, j - 1):
                if board[i][j - 1] > board[i][j] + 1 or board[i][j - 1] == 0:
                    board[i][j - 1] = board[i][j] + 1
        return board

    def get_next_move_from_opt_board(self, board, i, j, start):
        dict_move = {}
        if self.check_bounds(board, i + 1, j):
            if board[i + 1][j] > 0:
                dict_move[board[i + 1][j]] = Position.create(i + 1, j, start.get_board_id())

        if self.check_bounds(board, i - 1, j):
            if board[i - 1][j] > 0:
                dict_move[board[i - 1][j]] = Position.create(i - 1, j, start.get_board_id())

        if self.check_bounds(board, i, j + 1):
            if board[i][j + 1] > 0:
                dict_move[board[i][j + 1]] = Position.create(i, j + 1, start.get_board_id())

        if self.check_bounds(board, i, j - 1):
            if board[i][j - 1] > 0:
                dict_move[board[i][j - 1]] = Position.create(i, j - 1, start.get_board_id())
        dict_move[board[i][j]] = Position.create(i, j, start.get_board_id())
        minimum = min(dict_move)
        pos = dict_move[minimum]
        i = pos.x
        j = pos.y
        return i, j, pos

    def process_board(self, board):
        grid = board.get_grid()
        processed_grid = []
        for row in grid:
            processed_row = []
            for tile in row:
                if tile.get_type() == "IMPASSIBLE":
                    processed_row.append(-1)
                else:
                    processed_row.append(0)
            processed_grid.append(processed_row)
        return processed_grid

    def process_board_with_agro(self, board, target_monster, all_monsters):
        grid = board.get_grid()
        processed_grid = []
        for row in grid:
            processed_row = []
            for tile in row:
                y = len(processed_grid)
                x = len(row)
                for mon in all_monsters:
                    if mon != target_monster:
                        current_position = Position.create(x, y, mon.get_position().get_board_id())
                        in_range = mon.get_position().manhattan_distance(current_position) <= mon.get_aggro_range()
                        if in_range:
                            processed_row.append(-1)
                            break
                else:
                    if tile.get_type() == "IMPASSIBLE":
                        processed_row.append(-1)
                    else:
                        processed_row.append(0)
            processed_grid.append(processed_row)
        return processed_grid
    
    def cost_of_monster(self, monster):
        distance_cost = self.curr_pos.manhattan_distance(monster.get_position())
        experience_gained_per_hp = self.calc_exp_by_killing(monster)/monster.get_current_health()
        kill_rounds = monster.get_current_health() / self.my_player.get_attack()
        die_rounds = self.my_player.get_current_health() / monster.get_attack()
        return distance_cost - experience_gained_per_hp * 5 + 3*abs(monster.get_level()-self.my_player.get_level())
        
    def cost_of_item(self, item):
        if item is Wearable:
            if item is Weapon:
                return -1*item.get_attack()
            percent_attack_change = item.get_stats().get_percent_attack_change()
            return -1*(percent_attack_change)
        return 0

    def calc_exp_by_killing(self, monster):
        return 10 * monster.get_level() * (self.my_player.get_level() / (self.my_player.get_level() + abs(self.my_player.get_level() - monster.get_level())))
    
    def has_monster(self, x, y, game_state):
        monsters = [m for m in game_state.get_monsters_on_board(self.curr_pos.get_board_id()) if not m.is_dead()]
        for monster in monsters:
            if monster.get_position().get_x() == x and monster.get_position().get_y() == y:
                return True
        return False
        
    def can_kill(self, monster):
        num_turns_to_kill = math.ciel(monster.get_current_health() / self.my_player.get_attack())
        num_turns_to_die = math.ciel(self.my_player.get_current_health() / monster.get_attack())
        return num_turns_to_kill > num_turns_to_die

    def find_best_monster(self, living_monsters):
        return min(living_monsters, key=lambda monster: self.cost_of_monster(monster))

    def get_item_dict(self):
        tiles = {}
        #self.logger.info(self.board.get_grid())
        for x in range(len(self.board.get_grid())):
            for y in range (len(self.board.get_grid()[x])):
                current_position = Position.create(x, y, self.curr_pos.get_board_id())
                for item in self.board.get_tile_at(current_position).get_items():
                    tiles[item] = current_position
        return tiles

    # feel free to write as many helper functions as you need!
    def find_position_to_move(self, player: Player, destination: Position) -> Position:
        path = self.api.find_path(player.get_position(), destination)
        # path can be empty if player.get_position() == destination
        if len(path) == 0:
            return player.get_position()
        pos = None
        if len(path) < player.get_speed():
            pos = path[-1]
        else:
            pos = path[player.get_speed() - 1]
        return pos

    def move_to(self, start: Position, end: Position):
        if start.x < end.x:
            return Position.create(start.x + 1, start.y, start.board_id)
        elif start.x > end.x:
            return Position.create(start.x - 1, start.y, start.board_id)
        elif start.y < end.y:
            return Position.create(start.x, start.y + 1, start.board_id)
        elif start.y > end.y:
            return Position.create(start.x, start.y - 1, start.board_id)
        else:
            return None

    def find_closest(self, characters: list):
        return min(characters, lambda character: self.curr_pos.manhattan_distance(character.position))

    def within_range(self, position: Position):
        return self.my_player.get_weapon().get_range() >= self.curr_pos.manhattan_distance(position)
    
    def check_bounds(self, board, i, j):
        if i < 0 or j < 0:
            return False
        if i >= len(board) or j >= len(board[0]):
            return False
        if board[i][j] == -1:
            return False
        return True

    def goTo(self, toPosition):
        board = self.process_board(self.board)
        nextMove = self.path_find(board, self.curr_pos, toPosition)
        return CharacterDecision(
                    decision_type="MOVE",
                    action_position=nextMove,
                    action_index=0
                )

    def goTo(self, toPosition, monsters):
        board = self.process_board_with_agro(self.board, toPosition, monsters)
        nextMove = self.path_find(board, self.curr_pos, toPosition)
        return CharacterDecision(
            decision_type="MOVE",
            action_position=nextMove,
            action_index=0
        )

    # Prints a 2D grade of 2-digit numbers
    def print_2D_grid(self, grid):
        for j in range(len(grid[0])):
            row = []
            for i in range(len(grid)):
                row.append("%02d" % grid[i][j])
            self.logger.info(row)

    def equip(self, index):
        return CharacterDecision(
            decision_type = "EQUIP",
            action_position = None,
            action_index = index
        )