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

        EXPERIENCE_CHANGE_WEIGHT = 10
        ATTACK_CHANGE_WEIGHT = 5
        HEALTH_CHANGE_WEIGHT = 1
        DEFENSE_CHANGE_WEIGHT = 2
        SPEED_CHANGE_WEIGHT = 1

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

        inventory = self.my_player.get_inventory()

        #print info
        self.logger.info("\n\nMaxHP : " + str(self.my_player.get_max_health()))
        self.logger.info("Current defense: " + str(self.my_player.get_defense()))
        self.logger.info("Current speed: " + str(self.my_player.get_speed()))
        self.logger.info("Current attack: " + str(self.my_player.get_attack()))
        self.logger.info("Current experience: " + str(self.my_player.get_experience()))
        self.logger.info("Current level: " + str(self.my_player.get_level()) + "\n")
        self.logger.info("Weapon damage: " + str(self.my_player.get_weapon().get_attack()))

        total_experience_boost = 0

        # iterate through inventory to see if there is a better item to equip
        if len(inventory) > 0:
            self.logger.info("Looking through inventory to see for better items!")
            best_item = None
            best_idx = 0
            for i in range(len(inventory)):
                total_experience_boost += inventory[i].get_stats().get_flat_experience_change()

                if isinstance(inventory[i], Hat):
                    self.logger.info("I see a hat! The regen is: " + str(inventory[i].get_stats().get_flat_regen_per_turn()))

                if isinstance(inventory[i], Clothes):
                    self.logger.info("I see clothes! The regen is: " + str(inventory[i].get_stats().get_flat_regen_per_turn()))

                if isinstance(inventory[i], Shoes):
                    self.logger.info("I see shoes! The regen is: " + str(inventory[i].get_stats().get_flat_regen_per_turn()))

                if isinstance(inventory[i], Weapon):
                    self.logger.info("I see a weapon! Attack is: " + str(inventory[i].get_attack()))

                if self.is_better_item(inventory[i], ATTACK_CHANGE_WEIGHT, DEFENSE_CHANGE_WEIGHT, SPEED_CHANGE_WEIGHT,
                                       HEALTH_CHANGE_WEIGHT, EXPERIENCE_CHANGE_WEIGHT):
                    if isinstance(inventory[i], Weapon):
                        self.logger.info("I see a weapon that is better than my current weapon!")

                    if self.is_better_item_compare(inventory[i], best_item, ATTACK_CHANGE_WEIGHT, DEFENSE_CHANGE_WEIGHT, SPEED_CHANGE_WEIGHT,
                                       HEALTH_CHANGE_WEIGHT, EXPERIENCE_CHANGE_WEIGHT):
                        best_item = inventory[i]
                        best_idx = i

                    else:
                        self.logger.info("The item " + str(inventory[i].get_stats()) + " is not better!")

            if best_item is not None:
                self.logger.info("Equipping item now!")
                return self.equip(best_idx)
            else:
                self.logger.info("No better item was found!")

        self.logger.info("Total experience boost in inventory: " + str(total_experience_boost))

        # Getting items on current tile and picking up
        tile_items = self.board.get_tile_at(self.curr_pos).get_items()
        good_tile_items = [i for i in range(len(tile_items)) if self.is_better_item(tile_items[i], ATTACK_CHANGE_WEIGHT, DEFENSE_CHANGE_WEIGHT, SPEED_CHANGE_WEIGHT,
                                       HEALTH_CHANGE_WEIGHT, EXPERIENCE_CHANGE_WEIGHT)]

        if good_tile_items is not None and len(good_tile_items) > 0:
            if len(self.my_player.get_inventory()) < 16:
                self.logger.info("\nThere are items on my tile, picking up item")
                self.logger.info("Items on this tile: " + str(good_tile_items))
                self.memory.set_value("last_action", "PICKUP")
                return CharacterDecision(
                    decision_type="PICKUP",
                    action_position=None,
                    action_index=good_tile_items[0]
                )
            else:
                self.logger.info("Dropping item")
                return CharacterDecision(
                    decision_type="DROP",
                    action_position=None,
                    action_index=0
                )

        # Go to nearest best item
        items_dict = self.get_item_dict()
        good_items_dict = [key for key in items_dict.keys() if self.is_better_item(key, ATTACK_CHANGE_WEIGHT, DEFENSE_CHANGE_WEIGHT, SPEED_CHANGE_WEIGHT,
                                       HEALTH_CHANGE_WEIGHT, EXPERIENCE_CHANGE_WEIGHT)]

        self.logger.info("Good items on board " + str(good_items_dict))
        if good_items_dict is not None and len(good_items_dict) > 0:
            if len(self.my_player.get_inventory()) < 16:
                self.logger.info("Going to item")
                nearest_item = min(good_items_dict, key=lambda item: self.cost_of_item(item))
                move_position = self.path_find(self.process_board(self.board), self.curr_pos, items_dict[nearest_item])
                return CharacterDecision(
                    decision_type="MOVE",
                    action_position=move_position,
                    action_index=0
                )
            else:
                self.logger.info("Dropping item")
                return CharacterDecision(
                    decision_type="DROP",
                    action_position=None,
                    action_index=0
                )

        # Attack if monster is in range
        if (self.within_range(best_monster.get_position())):
            self.logger.info("ATTACKING MONSTER")
            self.memory.set_value("last_action", "ATTACK")
            return CharacterDecision(
                decision_type="ATTACK",
                action_position=best_monster.get_position(),
                action_index=0
            )

        # Moving to best monster, no agro considered
        living_monsters = [monster for monster in game_state.get_monsters_on_board(board_id) if not monster.is_dead()]
        best_monster = self.find_best_monster(living_monsters)

        self.logger.info("Navigating to monster")
        self.memory.set_value("last_action", "MOVE")
        processed_board = self.process_board(self.board)
        move_position = self.path_find(processed_board, self.curr_pos, best_monster.get_position())
        return CharacterDecision(
            decision_type="MOVE",
            action_position=move_position,
            action_index=0
        )

    def is_better_item(self, item1, flat_attack_weight, flat_defense_weight, flat_speed_weight, flat_health_weight, experience_weight):

        if isinstance(item1, Consumable):
            return False

        item_flat_attack_change = item1.get_stats().get_flat_attack_change() * flat_attack_weight
        item_flat_defense_change = item1.get_stats().get_flat_defense_change() * flat_defense_weight
        item_flat_speed_change = item1.get_stats().get_flat_speed_change() * flat_speed_weight
        item_flat_health_change = item1.get_stats().get_flat_health_change() * flat_health_weight
        item_flat_experience_change = item1.get_stats().get_flat_experience_change() * experience_weight

        # item_percent_attack_change = item1.get_stats().get_percent_attack_change()
        # item_percent_defense_change = item1.get_stats().get_percent_defense_change()
        # item_percent_speed_change = item1.get_stats().get_percent_speed_change()
        # item_percent_health_change = item1.get_stats().get_percent_health_change()
        # item_percent_experience_change = item1.get_stats().get_percent_experience_change()

        item_sum_stats = item_flat_attack_change + item_flat_defense_change + item_flat_speed_change + item_flat_health_change+item_flat_experience_change
        # item_sum_percentage_change = item_percent_attack_change + item_percent_defense_change + item_percent_speed_change + item_percent_health_change + item_percent_experience_change

        if isinstance(item1, Weapon):
            #item_sum_stats += item1.get_attack()*weapon_attack_weight

            #player_flat_attack_change = self.my_player.get_weapon().get_stats().get_flat_attack_change() * flat_attack_weight
            player_weapon_attack = self.my_player.get_weapon().get_attack()

            # player_percent_attack_change = self.my_player.get_weapon().get_stats().get_percent_attack_change()
            # player_percent_defense_change = self.my_player.get_weapon().get_stats().get_percent_defense_change()
            # player_percent_speed_change = self.my_player.get_weapon().get_stats().get_percent_speed_change()
            # player_percent_health_change = self.my_player.get_weapon().get_stats().get_percent_health_change()
            # player_percent_experience_change = self.my_player.get_weapon().get_stats().get_percent_experience_change()

            #current_player_weapon_sum_stats = player_flat_attack_change + player_flat_defense_change + player_flat_speed_change + player_flat_health_change+player_weapon_attack + player_flat_experience_change
            # current_player_weapon_sum_stats_percent_changes = player_percent_attack_change + player_percent_defense_change + player_percent_speed_change + player_percent_health_change + player_percent_experience_change
            if item1.get_attack() > player_weapon_attack:
                self.logger.info("I think " + str(item1.get_stats()) + " is better than " + str(self.my_player.get_weapon().get_stats()))
                return True

        if isinstance(item1, Shoes):
            player_flat_attack_change = self.my_player.get_shoes().get_stats().get_flat_attack_change() * flat_attack_weight
            player_flat_defense_change = self.my_player.get_shoes().get_stats().get_flat_defense_change() * flat_defense_weight
            player_flat_speed_change = self.my_player.get_shoes().get_stats().get_flat_speed_change() * flat_speed_weight
            player_flat_health_change = self.my_player.get_shoes().get_stats().get_flat_health_change() * flat_health_weight
            player_flat_experience_change = self.my_player.get_shoes().get_stats().get_flat_experience_change() * experience_weight

            # player_percent_attack_change = self.my_player.get_shoes().get_stats().get_percent_attack_change()
            # player_percent_defense_change = self.my_player.get_shoes().get_stats().get_percent_defense_change()
            # player_percent_speed_change = self.my_player.get_shoes().get_stats().get_percent_speed_change()
            # player_percent_health_change = self.my_player.get_shoes().get_stats().get_percent_health_change()
            # player_percent_experience_change = self.my_player.get_shoes().get_stats().get_percent_experience_change()

            current_player_shoes_sum_stats = player_flat_attack_change + player_flat_defense_change + player_flat_speed_change + player_flat_health_change + player_flat_experience_change
            #current_player_shoes_sum_stats_percent_changes = player_percent_attack_change + player_percent_defense_change + player_percent_speed_change + player_percent_health_change + player_percent_experience_change

            if item_sum_stats > current_player_shoes_sum_stats: #and item_sum_percentage_change > current_player_shoes_sum_stats_percent_changes:
                self.logger.info("I think " + str(item1.get_stats()) + " is better than " + str(self.my_player.get_shoes().get_stats()))
                return True

        if isinstance(item1, Hat):
            item_regen = item1.get_stats().get_flat_regen_per_turn()

            player_flat_attack_change = self.my_player.get_hat().get_stats().get_flat_attack_change() * flat_attack_weight
            player_flat_defense_change = self.my_player.get_hat().get_stats().get_flat_defense_change() * flat_defense_weight
            player_flat_speed_change = self.my_player.get_hat().get_stats().get_flat_speed_change() * flat_speed_weight
            player_flat_health_change = self.my_player.get_hat().get_stats().get_flat_health_change() * flat_health_weight
            player_flat_experience_change = self.my_player.get_hat().get_stats().get_flat_experience_change() * experience_weight

            # player_percent_attack_change = self.my_player.get_hat().get_stats().get_percent_attack_change()
            # player_percent_defense_change = self.my_player.get_hat().get_stats().get_percent_defense_change()
            # player_percent_speed_change = self.my_player.get_hat().get_stats().get_percent_speed_change()
            # player_percent_health_change = self.my_player.get_hat().get_stats().get_percent_health_change()
            # player_percent_experience_change = self.my_player.get_hat().get_stats().get_percent_experience_change()

            current_player_hat_sum_stats = player_flat_attack_change + player_flat_defense_change + player_flat_speed_change + player_flat_health_change + player_flat_experience_change
            #current_player_hat_sum_stats_percent_changes = player_percent_attack_change + player_percent_defense_change + player_percent_speed_change + player_percent_health_change + player_percent_experience_change

            if item_sum_stats > current_player_hat_sum_stats and item_regen >= self.my_player.get_hat().get_stats().get_flat_regen_per_turn(): #and item_sum_percentage_change > current_player_hat_sum_stats_percent_changes:
                self.logger.info("I think " + str(item1.get_stats()) + " is better than " + str(self.my_player.get_hat().get_stats()))
                return True

        if isinstance(item1, Clothes):
            item_regen = item1.get_stats().get_flat_regen_per_turn()

            player_flat_attack_change = self.my_player.get_clothes().get_stats().get_flat_attack_change() * flat_attack_weight
            player_flat_defense_change = self.my_player.get_clothes().get_stats().get_flat_defense_change() * flat_defense_weight
            player_flat_speed_change = self.my_player.get_clothes().get_stats().get_flat_speed_change() * flat_speed_weight
            player_flat_health_change = self.my_player.get_clothes().get_stats().get_flat_health_change() * flat_health_weight
            player_flat_experience_change = self.my_player.get_clothes().get_stats().get_flat_experience_change() * experience_weight

            # player_percent_attack_change = self.my_player.get_clothes().get_stats().get_percent_attack_change()
            # player_percent_defense_change = self.my_player.get_clothes().get_stats().get_percent_defense_change()
            # player_percent_speed_change = self.my_player.get_clothes().get_stats().get_percent_speed_change()
            # player_percent_health_change = self.my_player.get_clothes().get_stats().get_percent_health_change()
            # player_percent_experience_change = self.my_player.get_clothes().get_stats().get_percent_experience_change()

            current_player_clothes_sum_stats = player_flat_attack_change + player_flat_defense_change + player_flat_speed_change + player_flat_health_change + player_flat_experience_change
            #current_player_clothes_clothes_stats_percent_changes = player_percent_attack_change + player_percent_defense_change + player_percent_speed_change + player_percent_health_change + player_percent_experience_change

            if item_sum_stats > current_player_clothes_sum_stats and item_regen >= self.my_player.get_clothes().get_stats().get_flat_regen_per_turn(): #and item_sum_stats > current_player_clothes_clothes_stats_percent_changes:
                self.logger.info("I think " + str(item1.get_stats()) + " is better than " + str(self.my_player.get_clothes().get_stats()))
                return True

        if isinstance(item1, Accessory):
            item_regen = item1.get_stats().get_flat_regen_per_turn()

            player_flat_attack_change = self.my_player.get_accessory().get_stats().get_flat_attack_change() * flat_attack_weight
            player_flat_defense_change = self.my_player.get_accessory().get_stats().get_flat_defense_change() * flat_defense_weight
            player_flat_speed_change = self.my_player.get_accessory().get_stats().get_flat_speed_change() * flat_speed_weight
            player_flat_health_change = self.my_player.get_accessory().get_stats().get_flat_health_change() * flat_health_weight
            player_flat_experience_change = self.my_player.get_accessory().get_stats().get_flat_experience_change() * experience_weight

            # player_percent_attack_change = self.my_player.get_accessory().get_stats().get_percent_attack_change()
            # player_percent_defense_change = self.my_player.get_accessory().get_stats().get_percent_defense_change()
            # player_percent_speed_change = self.my_player.get_accessory().get_stats().get_percent_speed_change()
            # player_percent_health_change = self.my_player.get_accessory().get_stats().get_percent_health_change()
            # player_percent_experience_change = self.my_player.get_accessory().get_stats().get_percent_experience_change()

            current_player_accessory_sum_stats = player_flat_attack_change + player_flat_defense_change + player_flat_speed_change + player_flat_health_change + player_flat_experience_change
            #current_player_clothes_clothes_stats_percent_changes = player_percent_attack_change + player_percent_defense_change + player_percent_speed_change + player_percent_health_change + player_percent_experience_change

            if item_sum_stats > current_player_accessory_sum_stats and item_regen >= self.my_player.get_accessory().get_stats().get_flat_regen_per_turn(): #and item_sum_percentage_change > current_player_clothes_clothes_stats_percent_changes:
                self.logger.info("I think " + str(item1.get_stats()) + " is better than " + str(self.my_player.get_accessory().get_stats()))
                return True

        return False

    def is_better_item_compare(self, item1, item2, flat_attack_weight, flat_defense_weight, flat_speed_weight, flat_health_weight, experience_weight):
        if (item2 is None):
            return True
        elif item1 is None:
            return False
        hierarchy = {Weapon: 4, Shoes: 0, Hat: 3, Clothes:1, Accessory:2}
        if type(item1) is type(item2):
            if isinstance(item1, Weapon):
                return item1.get_attack() > item2.get_attack()

            else:
                item_flat_attack_change = item1.get_stats().get_flat_attack_change() * flat_attack_weight
                item_flat_defense_change = item1.get_stats().get_flat_defense_change() * flat_defense_weight
                item_flat_speed_change = item1.get_stats().get_flat_speed_change() * flat_speed_weight
                item_flat_health_change = item1.get_stats().get_flat_health_change() * flat_health_weight
                item_flat_experience_change = item1.get_stats().get_flat_experience_change() * experience_weight

                item_sum_stats = item_flat_attack_change + item_flat_defense_change + item_flat_speed_change + item_flat_health_change + item_flat_experience_change

                player_flat_attack_change = item2.get_stats().get_flat_attack_change() * flat_attack_weight
                player_flat_defense_change = item2.get_stats().get_flat_defense_change() * flat_defense_weight
                player_flat_speed_change = item2.get_stats().get_flat_speed_change() * flat_speed_weight
                player_flat_health_change = item2.get_stats().get_flat_health_change() * flat_health_weight
                player_flat_experience_change = item2.get_stats().get_flat_experience_change() * experience_weight

                current_player_weapon_sum_stats = player_flat_attack_change + player_flat_defense_change + player_flat_speed_change + player_flat_health_change + player_flat_experience_change

                if item_sum_stats > current_player_weapon_sum_stats:
                    return True
        else:
            if hierarchy[type(item1)] > hierarchy[type(item2)]:
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
        cost = 0
        distance_cost = self.curr_pos.manhattan_distance(monster.get_position())
        experience_gained_per_hp = self.calc_exp_by_killing(monster)/monster.get_current_health()
        my_attack = math.floor(self.my_player.get_weapon().get_attack() * (75 + self.my_player.get_attack()) * .01)
        monster_attack = math.floor(monster.get_weapon().get_attack() * (75 + monster.get_attack()) * .01)
        #self.logger.info("Experience factor: " + str(experience_gained_per_hp))
        kill_rounds = monster.get_current_health() / max(my_attack*.2, my_attack-monster.get_defense())
        #self.logger.info("kill factor: " + str(kill_rounds))
        eff_damage = max(1.0, max(.2 * monster_attack, monster_attack - self.my_player.get_defense()))
        die_rounds = self.my_player.get_current_health() / eff_damage
        #self.logger.info("die factor: " + str(die_rounds))
        if (die_rounds < kill_rounds):
            cost += 25
        cost += distance_cost - experience_gained_per_hp * 30 + kill_rounds * .1 - die_rounds * .001
        if monster.get_max_health() == 50 and monster.get_level() == 5:
            self.logger.info("GOING TO BAT!")
            cost -= 3000
        return cost
        
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

    # def goTo(self, toPosition, monsters):
    #     board = self.process_board_with_agro(self.board, toPosition, monsters)
    #     nextMove = self.path_find(board, self.curr_pos, toPosition)
    #     return CharacterDecision(
    #         decision_type="MOVE",
    #         action_position=nextMove,
    #         action_index=0
    #     )

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