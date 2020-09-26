import logging

from mech.mania.starter_pack.domain.model.characters.character_decision import CharacterDecision
from mech.mania.starter_pack.domain.model.characters.position import Position
from mech.mania.starter_pack.domain.model.game_state import GameState
from mech.mania.starter_pack.domain.api import API
import math

class Strategy:
    def __init__(self, memory):
        self.memory = memory
        self.logger = logging.getLogger('strategy')
        self.logger.setLevel(logging.DEBUG)
        logging.basicConfig(level = logging.INFO)
    
    def path_find(self, board, start, end):
        #self.logger.info(board)
        board[start.x][start.y] = 0
        board[end.x][end.y] = 1
        iter = 0
        while (board[start.x][start.y] == 0):
            for i in range(len(board)):
                for j in range(len(board[0])):
                    if (board[i][j] > 0):
                        if self.checkBounds(board, i + 1, j):
                            if board[i + 1][j] > board[i][j] + 1 or board[i + 1][j] == 0:
                                board[i + 1][j] = board[i][j] + 1
                        if self.checkBounds(board, i - 1, j):
                            if board[i - 1][j] > board[i][j] + 1 or board[i - 1][j] == 0:
                                board[i - 1][j] = board[i][j] + 1
                        if self.checkBounds(board, i, j+1):
                            if board[i][j+1] > board[i][j] + 1 or board[i][j+1] == 0:
                                board[i][j+1] = board[i][j] + 1
                        if self.checkBounds(board, i, j-1):
                            if board[i][j-1] > board[i][j] + 1 or board[i][j-1] == 0:
                                board[i][j-1] = board[i][j] + 1

        i = start.x
        j = start.y
        self.logger.info((i,j))

        dict_move = {}
        if self.checkBounds(board, i + 1, j):
            if board[i + 1][j] > 0:
                self.logger.info("going right")
                dict_move[board[i+1][j]] = Position.create(i + 1,j, start.get_board_id())
                #return Position.create(i+1,j, start.get_board_id())
                #return Position.create(j, i+1, start.get_board_id())
        if self.checkBounds(board, i - 1, j):
            if board[i - 1][j] > 0:
                self.logger.info("going left")
                dict_move[board[i-1][j]] = Position.create(i - 1,j, start.get_board_id())
                #return Position.create(i-1,j, start.get_board_id())
                #return Position.create(j, i - 1, start.get_board_id())

        if self.checkBounds(board, i, j + 1):
            if board[i][j +1] > 0:
                self.logger.info("going down")
                dict_move[board[i][j+1]] = Position.create(i,j+1, start.get_board_id())
                #return Position.create(i,j+1, start.get_board_id())
                #return Position.create(j+1, i, start.get_board_id())

        if self.checkBounds(board, i, j - 1):
            if board[i][j -1] > 0:
                self.logger.info("going up")
                dict_move[board[i][j-1]] = Position.create(i,j-1, start.get_board_id())
                #return Position.create(i,j-1, start.get_board_id())
                #return Position.create(j-1, i, start.get_board_id())
        self.logger.info(dict_move)
        minimum = min(dict_move)
        self.logger.info(minimum)
        for j in range(len(board[0])):
            row = []
            for i in range(len(board)):
                row.append("%02d" % board[i][j])
            self.logger.info(row)
        return dict_move[minimum]


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
        #processed_grid = [[tile.get_type() == "IMPASSIBLE" for tile in row] for row in grid]
        return processed_grid

    def move_toward(self, target):
        pos = self.path_find(self.process_board(self.board), self.curr_pos, target)
        return CharacterDecision(
            decision_type = "MOVE",
            action_position = Position(Position.create(pos.get_x(), 
                                                        pos.get_y(), 
                                                        pos.get_board_id())),
            action_index = 0
        )
    
    def cost_of_monster(self, monster):
        distance_cost = self.curr_pos.manhattan_distance(monster.get_position())
        experience_gained = self.calc_exp_by_killing(monster)
        return distance_cost - experience_gained

    def cost_of_item(self, item):
        percent_attack_change = item.get_stats().get_percent_attack_change()
        return -1*(percent_attack_change)

    def calc_exp_by_killing(self, monster):
        return 10 * monster.get_level() * (self.my_player.get_level() / (self.my_player.get_level() + abs(self.my_player.get_level() - monster.get_level())))
        
    def can_kill(self, monster):
        num_turns_to_kill = math.ciel(monster.get_current_health() / self.my_player.get_attack())
        num_turns_to_die = math.ciel(self.my_player.get_current_health() / monster.get_attack())
        return num_turns_to_kill > num_turns_to_die

    def find_best_monster(self, living_monsters):
        return min(living_monsters, lambda monster: self.cost_of_monster(monster))

    def get_item_dict(self):
        tiles = {}
        for x in range(len(self.board.get_grid())):
            for y in range (len(self.board.get_grid()[x])):
                current_position = Position.create(x, y, self.curr_pos.get_board_id())
                for item in self.board.get_tile_at(x,y).get_items():
                    tiles[item] = current_position
        return tiles

    def make_decision(self, player_name: str, game_state: GameState) -> CharacterDecision:
        """
        Parameters:
        player_name (string): The name of your player
        game_state (GameState): The current game state
        """
        self.api = API(game_state, player_name)
        self.my_player = game_state.get_all_players()[player_name]
        #self.board = game_state.get_pvp_board()
        self.curr_pos = self.my_player.get_position()

        self.board = game_state.get_board(self.curr_pos.get_board_id())

        self.logger.info("In make_decision")

        self.logger.info('X: ' + str(self.curr_pos.get_x()))
        self.logger.info('Y: ' + str(self.curr_pos.get_y()))
        
        board_id = self.curr_pos.get_board_id()
        

        # Equip last item picked up
        last_action, type = self.memory.get_value("last_action", str)
        if last_action is not None and last_action == "PICKUP":
            self.memory.set_value("last_action", "EQUIP")
            return CharacterDecision(
                decision_type="EQUIP",
                action_position=None,
                action_index=self.my_player.get_free_inventory_index()
            )

        # Pick up item if on current tile
        tile_items = self.board.get_tile_at(self.curr_pos).items
        if tile_items is not None or len(tile_items) > 0:
            self.memory.set_value("last_action", "PICKUP")
            return CharacterDecision(
                decision_type="PICKUP",
                action_position=None,
                action_index=0
            )

        # Go to nearest best item
        items_dict = self.get_item_dict()
        if items_dict.keys() is not None:
            nearest_item = min(items_dict.keys(), lambda item: self.cost_of_item(item))
            move_position = self.path_find(self.board, self.curr_pos, items_dict[nearest_item])
            return CharacterDecision(
                decision_type="MOVE",
                action_position=move_position,
                action_index=0
            )


        living_monsters = [monster for monster in game_state.get_monsters_on_board(board_id) if monster.is_dead()]

        best_monster = self.find_best_monster(living_monsters)

        if (self.within_range(best_monster.get_position())):
            self.memory.set_value("last_action", "ATTACK")
            return CharacterDecision(
                decision_type="ATTACK",
                action_position=best_monster.get_position(),
                action_index=0
            )
        else:
            self.memory.set_value("last_action", "MOVE")
            move_position = self.path_find(self.board, self.curr_pos, best_monster.get_position())
            return CharacterDecision(
                decision_type="MOVE",
                action_position=move_position,
                action_index=0
            )

        #self.logger.info("MONSTERS: ")
        #for monster in monsters:
        #    self.logger.info(monster.get_name())
        #    if monster.get_position().manhattan_distance(self.curr_pos) == 1:
        #        return CharacterDecision(
        #            decision_type = "ATTACK",
        #            action_position = monster.get_position(),
        #            action_index = 0
        #        )

        
        portals = self.board.get_portals()
        
        if board_id == 'chairsquestionmark':
            self.logger.info('In home board, time to move toward the portal')
            try:
                self.logger.info(self.find_position_to_move(self.curr_pos, self.api.find_closest_portal(self.curr_pos)))
            except:
                self.logger.info("uh oh!")
            #self.logger.info(self.find_position_to_move(self.curr_pos, portals[0]))
            return self.move_toward(portals[0])
        else:
            self.logger.info('In pvp board, time to move toward monsters[0]')
            return self.move_toward(monsters[0])
        
        # if x == 19:
        #     self.logger.info('Move down')
        #     return CharacterDecision(
        #         decision_type = "MOVE",
        #         action_position = Position(Position.create(x, 
        #                                                    y + 1, 
        #                                                    board_id)),
        #         action_index = 0
        #     )
        # else:
        #     self.logger.info('Move right')
        #     return CharacterDecision(
        #         decision_type = "MOVE",
        #         action_position = Position(Position.create(x + 1, 
        #                                                    y, 
        #                                                    board_id)),
        #         action_index = 0
        #     )

    
        game_state.get_monsters_on_board(self.curr_pos.get_board_id)
        
        # Just move to the nearest portal (API doesn't work lul)
        return CharacterDecision(
                    decision_type="MOVE",
                    action_position=self.find_position_to_move(self.curr_pos, self.api.find_closest_portal(self.curr_pos)),
                    action_index=0
                )

        # Move to the nearest monster
        monster_locations = self.api.find_enemies_by_distance(self.curr_pos)

        #Other code

        

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
            action_position=self.find_position_to_move(self.my_player, enemy_pos),
            action_index=None
        )

        return decision


    # feel free to write as many helper functions as you need!
    def find_position_to_move(self, player: Position, destination: Position) -> Position:
        path = self.api.find_path(player, destination)
        self.logger.info(path)
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
    
    def checkBounds(self, board, i, j):
        #self.logger.info((i,j))
        if i < 0 or j < 0:
            return False
        if i >= len(board) or j >= len(board[0]):
            return False
        if board[i][j] == -1:
            return False
        return True
