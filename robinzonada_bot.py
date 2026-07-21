import os
import random
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS
# ============================================================================

class CardType(Enum):
    WATER_BOTTLE = "water_bottle"
    FRUIT_BASKET = "fruit_basket"
    DIRTY_WATER = "dirty_water"
    SANDWICH = "sandwich"
    SPROTS = "sprots"
    COCONUT = "coconut"
    ROTTEN_FISH = "rotten_fish"
    FISHING_ROD = "fishing_rod"
    AXE = "axe"
    FLASK = "flask"
    CLUB = "club"
    REVOLVER = "revolver"
    BULLET = "bullet"
    METAL_PLATE = "metal_plate"
    ANTIDOTE = "antidote"
    SLEEPING_PILLS = "sleeping_pills"
    MATCHES = "matches"
    COFFEE = "coffee"
    BAROMETER = "barometer"
    FLASHLIGHT = "flashlight"
    SPYGLASS = "spyglass"
    CRYSTAL_BALL = "crystal_ball"
    PENDULUM = "pendulum"
    VOODOO_DOLL = "voodoo_doll"
    CANNIBAL_STEW = "cannibal_stew"
    OLD_UNDERWEAR = "old_underwear"
    BOARD_GAME = "board_game"
    LOTTERY_TICKET = "lottery_ticket"
    TOILET_BRUSH = "toilet_brush"
    CAR_KEYS = "car_keys"
    SHELL = "shell"
    ALARM_CLOCK = "alarm_clock"
    PLANK = "plank"
    TIKI_STATUE = "tiki_statue"

class WeatherType(Enum):
    SUN_0 = "sun_0"
    SUN_1 = "sun_1"
    CLOUD_2 = "cloud_2"
    RAIN_3 = "rain_3"
    HURRICANE = "hurricane"

# ============================================================================
# DECKS CONFIGURATION
# ============================================================================

WEATHER_DECK_CONFIG = [
    (WeatherType.SUN_0, 4),
    (WeatherType.SUN_1, 3),
    (WeatherType.CLOUD_2, 3),
    (WeatherType.RAIN_3, 2),
    (WeatherType.HURRICANE, 1),
]

WRECKAGE_DECK_CONFIG = [
    (CardType.WATER_BOTTLE, 7), (CardType.SANDWICH, 7),
    (CardType.SPROTS, 1), (CardType.COCONUT, 1),
    (CardType.ROTTEN_FISH, 1), (CardType.DIRTY_WATER, 1),
    (CardType.FRUIT_BASKET, 1),
    (CardType.FISHING_ROD, 1), (CardType.AXE, 1),
    (CardType.FLASK, 1), (CardType.CLUB, 1),
    (CardType.REVOLVER, 3), (CardType.BULLET, 6),
    (CardType.METAL_PLATE, 2),
    (CardType.ANTIDOTE, 1), (CardType.SLEEPING_PILLS, 1),
    (CardType.MATCHES, 1), (CardType.COFFEE, 1),
    (CardType.BAROMETER, 1), (CardType.FLASHLIGHT, 1),
    (CardType.SPYGLASS, 1), (CardType.CRYSTAL_BALL, 1),
    (CardType.PENDULUM, 1), (CardType.VOODOO_DOLL, 1),
    (CardType.CANNIBAL_STEW, 1),
    (CardType.OLD_UNDERWEAR, 1), (CardType.BOARD_GAME, 1),
    (CardType.LOTTERY_TICKET, 1), (CardType.TOILET_BRUSH, 1),
    (CardType.CAR_KEYS, 1),
    (CardType.SHELL, 1), (CardType.ALARM_CLOCK, 1),
    (CardType.PLANK, 1),
]

STARTING_RESOURCES = {
    3: (5, 6), 4: (7, 8), 5: (8, 10), 6: (10, 12),
    7: (12, 14), 8: (13, 16), 9: (15, 18), 10: (16, 20),
    11: (18, 22), 12: (20, 24)
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Player:
    user_id: int
    username: str
    first_name: str
    hand: List[CardType] = field(default_factory=list)
    permanent_cards: List[CardType] = field(default_factory=list)
    is_alive: bool = True
    is_sick: bool = False
    has_voted: bool = False
    action_taken: bool = False
    vote_target: Optional[int] = None
    protected_from_shot: bool = False
    coffee_active: bool = False

@dataclass
class GameState:
    chat_id: int
    phase: str = "lobby"
    players: Dict[int, Player] = field(default_factory=dict)
    player_order: List[int] = field(default_factory=list)
    first_player_idx: int = 0
    current_player_idx: int = 0
    food: int = 0
    water: int = 0
    wood: int = 0
    raft_cards: int = 0
    weather_deck: List[WeatherType] = field(default_factory=list)
    weather_discard: List[WeatherType] = field(default_factory=list)
    wreckage_deck: List[CardType] = field(default_factory=list)
    wreckage_discard: List[CardType] = field(default_factory=list)
    current_weather: Optional[WeatherType] = None
    round_num: int = 0
    actions_this_round: int = 0
    hurricane_triggered: bool = False
    game_over: bool = False
    winners: List[int] = field(default_factory=list)
    votes: Dict[int, int] = field(default_factory=dict)
    voting_reason: str = ""
    pending_action: Optional[str] = None
    pending_user: Optional[int] = None

============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_weather_deck():
    deck = []
    for w_type, count in WEATHER_DECK_CONFIG:
        deck.extend([w_type] * count)
    random.shuffle(deck)
    return deck

def create_wreckage_deck():
    deck = []
    for card_type, count in WRECKAGE_DECK_CONFIG:
        deck.extend([card_type] * count)
    random.shuffle(deck)
    return deck

def get_card_name(card_type):
    names = {
        CardType.WATER_BOTTLE: "💧 Бутылка воды",
        CardType.FRUIT_BASKET: "🍎 Корзина фруктов",
        CardType.DIRTY_WATER: "☣️ Грязная вода",
        CardType.SANDWICH: "🥪 Сэндвич",
        CardType.SPROTS: "🐟 Шпроты",
        CardType.COCONUT: "🥥 Кокос",
        CardType.ROTTEN_FISH: "🤢 Тухлая рыба",
        CardType.FISHING_ROD: "🎣 Удочка",
        CardType.AXE: "🪓 Топор",
        CardType.FLASK: "🏺 Фляжка",
        CardType.CLUB: "🏏 Дубина",
        CardType.REVOLVER: "🔫 Револьвер",
        CardType.BULLET: "🔴 Пуля",
        CardType.METAL_PLATE: "🛡️ Кусок металла",
        CardType.ANTIDOTE: "💊 Противоядие",
        CardType.SLEEPING_PILLS: "💤 Снотворное",
        CardType.MATCHES: "🔥 Спички",
        CardType.COFFEE: "☕ Кофе",
        CardType.BAROMETER: "🌡️ Барометр",
        CardType.FLASHLIGHT: "🔦 Фонарик",
        CardType.SPYGLASS: "🔭 Подзорная труба",
        CardType.CRYSTAL_BALL: "🔮 Хрустальный шар",
        CardType.PENDULUM: "🌀 Маятник",
        CardType.VOODOO_DOLL: "🧸 Кукла вуду",
        CardType.CANNIBAL_STEW: "🍲 Рагу из робинзона",
        CardType.OLD_UNDERWEAR: "🩲 Старые трусы",
        CardType.BOARD_GAME: "🎲 Настольная игра",
        CardType.LOTTERY_TICKET: "🎫 Лотерейный билет",
        CardType.TOILET_BRUSH: "🚽 Ёршик",
        CardType.CAR_KEYS: "🚗 Ключи от машины",
        CardType.SHELL: "🐚 Раковина",
        CardType.ALARM_CLOCK: "⏰ Будильник",
        CardType.PLANK: "🪵 Доска",
        CardType.TIKI_STATUE: "🗿 Тотем",
    }
    return names.get(card_type, card_type.value)

def get_card_description(card_type):
    descriptions = {
        CardType.WATER_BOTTLE: "1 порция воды",
        CardType.FRUIT_BASKET: "Все игнорируют смерть от голода/жажды этот раунд",
        CardType.DIRTY_WATER: "1 порция воды + болезнь",
        CardType.SANDWICH: "1 порция еды",
        CardType.SPROTS: "3 порции еды",
        CardType.COCONUT: "3 порции воды",
        CardType.ROTTEN_FISH: "1 порция еды + болезнь",
        CardType.FISHING_ROD: "При рыбалке +2 рыбки (постоянный)",
        CardType.AXE: "При сборе древесины +2 куска (постоянный)",
        CardType.FLASK: "Собираете в 2 раза больше воды (постоянный)",
        CardType.CLUB: "Ваш голос = 2 (постоянный)",
        CardType.REVOLVER: "Можете застрелить любого игрока (нужна пуля)",
        CardType.BULLET: "Патрон для револьвера",
        CardType.METAL_PLATE: "Защита от 1 выстрела",
        CardType.ANTIDOTE: "Отменяет болезнь",
        CardType.SLEEPING_PILLS: "Украдите 1 случайную карту у игрока",
        CardType.MATCHES: "Грязная вода/тухлая рыба без болезни",
        CardType.COFFEE: "2 действия за ход",
        CardType.BAROMETER: "Посмотрите 2 верхние карты погоды",
        CardType.FLASHLIGHT: "Посмотрите 3 верхние карты обломков",
        CardType.SPYGLASS: "Посмотрите чужие обломки",
        CardType.CRYSTAL_BALL: "Голосуете последним",
        CardType.PENDULUM: "Навяжите действие игроку",
        CardType.VOODOO_DOLL: "Воскресите погибшего",
        CardType.CANNIBAL_STEW: "+2 еды за каждого погибшего в раунде",
        CardType.OLD_UNDERWEAR: "Бесполезно... но утешает",
        CardType.BOARD_GAME: "Бесполезно, но весело",
        CardType.LOTTERY_TICKET: "Бесполезно. Мечты о богатстве",
        CardType.TOILET_BRUSH: "Бесполезно (по крайней мере здесь)",
        CardType.CAR_KEYS: "Бесполезно. Но можно покрасоваться",
        CardType.SHELL: "Вы - лидер. Никто не голосует против вас",
        CardType.ALARM_CLOCK: "Назначьте первого игрока",
        CardType.PLANK: "+1 место на плоту",
    }
    return descriptions.get(card_type, "Особая карта")

def get_weather_emoji(weather):
    return {
        WeatherType.SUN_0: "☀️",
        WeatherType.SUN_1: "🌤️",
        WeatherType.CLOUD_2: "☁️",
        WeatherType.RAIN_3: "🌧️",
        WeatherType.HURRICANE: "🌪️",
    }.get(weather, "❓")

def get_weather_rain(weather):
    return {
        WeatherType.SUN_0: 0,
        WeatherType.SUN_1: 1,
        WeatherType.CLOUD_2: 2,
        WeatherType.RAIN_3: 3,
        WeatherType.HURRICANE: 2,
    }.get(weather, 0)

def alive_players(game):
    return [p for p in game.players.values() if p.is_alive]

def alive_count(game):
    return len(alive_players(game))

def get_current_player(game):
    if not game.player_order:
        return None
    for i in range(len(game.player_order)):
        idx = (game.current_player_idx + i) % len(game.player_order)
        pid = game.player_order[idx]
        p = game.players.get(pid)
        if p and p.is_alive:
            return p
    return None

def get_next_alive_idx(game, idx):
    n = len(game.player_order)
    for i in range(1, n + 1):
        nidx = (idx + i) % n
        pid = game.player_order[nidx]
        if game.players[pid].is_alive:
            return nidx
    return idx

def draw_wreckage(game, count=1):
    drawn = []
    for _ in range(count):
        if not game.wreckage_deck:
            if game.wreckage_discard:
                game.wreckage_deck = game.wreckage_discard
                game.wreckage_discard = []
                random.shuffle(game.wreckage_deck)
            else:
                break
        if game.wreckage_deck:
            drawn.append(game.wreckage_deck.pop())
    return drawn

def format_resources(game):
    return f"📊 Ресурсы: 🐟{game.food} | 💧{game.water} | 🪵{game.wood} | 🛶{game.raft_cards}/12 | 👥{alive_count(game)}"

def format_player_hand(player):
    if not player.hand:
        return "🎒 У вас нет карт обломков."
    lines = [f"🎒 Ваши карты ({len(player.hand)}):"]
    for i, card in enumerate(player.hand, 1):
        lines.append(f"{i}. {get_card_name(card)}")
    if player.permanent_cards:
        lines.append("\n⚡ Постоянные эффекты:")
        for card in player.permanent_cards:
            lines.append(f"• {get_card_name(card)}")
    return "\n".join(lines)

def format_players_list(game):
    lines = ["👥 Игроки:"]
    for pid in game.player_order:
        p = game.players[pid]
        status = "🟢" if p.is_alive else "💀"
        sick = " 🤒" if p.is_sick else ""
        leader = " 👑" if game.player_order[game.first_player_idx] == pid else ""
        cur = get_current_player(game)
        current = " ▶️" if cur == p else ""
        lines.append(f"{status} {p.first_name}{sick}{leader}{current}")
    return "\n".join(lines)

============================================================================
# GAME LOGIC FUNCTIONS
# ============================================================================

async def start_game_logic(context, chat_id):
    game = context.chat_data.get('game')
    if not game or len(game.players) < 3:
        await context.bot.send_message(chat_id, "❌ Нужно минимум 3 игрока!")
        return
    
    game.phase = "setup"
    num_players = len(game.players)
    
    food, water = STARTING_RESOURCES.get(num_players, (10, 12))
    game.food = food
    game.water = water
    game.wood = 0
    game.raft_cards = 0
    
    game.weather_deck = create_weather_deck()
    game.wreckage_deck = create_wreckage_deck()
    game.weather_discard = []
    game.wreckage_discard = []
    
    cards_per_player = 4 if num_players <= 8 else 3
    for pid in game.player_order:
        player = game.players[pid]
        player.hand = draw_wreckage(game, cards_per_player)
    
    game.round_num = 1
    game.first_player_idx = 0
    game.current_player_idx = 0
    game.hurricane_triggered = False
    
    first_name = game.players[game.player_order[0]].first_name
    
    await context.bot.send_message(
        chat_id,
        f"🌴 РОБИНЗОНАДА НАЧИНАЕТСЯ! 🌴\n\n"
        f"👥 Игроков: {num_players}\n"
        f"🎲 Карт в руке: {cards_per_player}\n"
        f"📦 В колоде обломков: {len(game.wreckage_deck)} карт\n"
        f"{format_resources(game)}\n\n"
        f"{format_players_list(game)}\n\n"
        f"🎣 Первый игрок: {first_name}"
    )
    
    await start_round(context, chat_id)

async def start_round(context, chat_id):
    game = context.chat_data.get('game')
    if not game or game.game_over:
        return
    
    game.phase = "action"
    game.actions_this_round = 0
    game.current_weather = None
    
    for p in game.players.values():
        p.action_taken = False
        p.has_voted = False
        p.vote_target = None
        p.protected_from_shot = False
        p.coffee_active = False
    
    if game.round_num > 1:
        game.first_player_idx = get_next_alive_idx(game, game.first_player_idx)
    
    game.current_player_idx = game.first_player_idx
    
    if not game.weather_deck:
        game.weather_deck = game.weather_discard
        game.weather_discard = []
        random.shuffle(game.weather_deck)
    
    game.current_weather = game.weather_deck.pop()
    game.weather_discard.append(game.current_weather)
    
    weather_texts = {
        WeatherType.SUN_0: "Жаркий солнечный день! Собирать воду нельзя!",
        WeatherType.SUN_1: "Солнечно, небольшая роса",
        WeatherType.CLOUD_2: "Облачно, хороший сбор воды",
        WeatherType.RAIN_3: "🌧️ Идёт дождь! Много воды!",
        WeatherType.HURRICANE: "🌪️ УРАГАН! Все на плот! Это конец игры!",
    }
    
    first_name = game.players[game.player_order[game.first_player_idx]].first_name
    
    await context.bot.send_message(
        chat_id,
        f"📅 Раунд {game.round_num}\n"
        f"{get_weather_emoji(game.current_weather)} Погода: {weather_texts.get(game.current_weather, '')}\n"
        f"💧 Осадков: {get_weather_rain(game.current_weather)}\n\n"
        f"{format_resources(game)}\n\n"
        f"👑 Первый игрок: {first_name}"
    )
    
    if game.current_weather == WeatherType.HURRICANE:
        game.hurricane_triggered = True
        game.phase = "end"
        await check_end_game(context, chat_id)
        return
    
    await notify_current_player(context, chat_id)

async def notify_current_player(context, chat_id):
    game = context.chat_data.get('game')
    if not game:
        return
    
    player = get_current_player(game)
    if not player or not player.is_alive:
        await next_player(context, chat_id)
        return
    
    if player.is_sick:
        await context.bot.send_message(
            chat_id,
            f"🤒 {player.first_name} болен и пропускает ход."
        )
        player.is_sick = False
        await next_player(context, chat_id)
        return
    
    try:
        await context.bot.send_message(
            player.user_id,
            f"🎯 Ваш ход! Раунд {game.round_num}\n\n"
            f"{format_resources(game)}\n\n"
            f"{format_player_hand(player)}\n\n"
            f"Выберите действие в групповом чате."
        )
    except Exception:
        pass
    
    keyboard = [
        [InlineKeyboardButton("🎣 Поймать рыбу", callback_data=f"act_fish_{player.user_id}")],
        [InlineKeyboardButton("💧 Собрать воду", callback_data=f"act_water_{player.user_id}")],
        [InlineKeyboardButton("🪵 Найти древесину", callback_data=f"act_wood_{player.user_id}")],
        [InlineKeyboardButton("📦 Обыскать обломки", callback_data=f"act_search_{player.user_id}")],
    ]
    
    if player.hand:
        keyboard.append([InlineKeyboardButton("🃏 Использовать карту", callback_data=f"act_usecard_{player.user_id}")])
    
    if CardType.REVOLVER in player.permanent_cards and CardType.BULLET in player.hand:
        keyboard.append([InlineKeyboardButton("🔫 Выстрелить в игрока", callback_data=f"act_shoot_{player.user_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id,
        f"▶️ Ходит {player.first_name}!\nВыберите действие:",
        reply_markup=reply_markup
    )

async def next_player(context, chat_id):
    game = context.chat_data.get('game')
    if not game:
        return
    
    game.current_player_idx = get_next_alive_idx(game, game.current_player_idx)
    game.actions_this_round += 1
    
    alive = alive_count(game)
    if game.actions_this_round >= alive:
        await survival_check(context, chat_id)
    else:
        await notify_current_player(context, chat_id)

============================================================================
# ACTION HANDLERS
# ============================================================================

async def handle_action(update, context):
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    
    if not game or game.phase != "action":
        await query.edit_message_text("❌ Сейчас не фаза действий.")
        return
    
    data = query.data
    parts = data.split("_")
    action = parts[1]
    target_id = int(parts[2])
    
    current = get_current_player(game)
    if not current or current.user_id != target_id:
        await query.answer("❌ Сейчас не ваш ход!", show_alert=True)
        return
    
    if current.action_taken and not current.coffee_active:
        await query.answer("❌ Вы уже сходили!", show_alert=True)
        return
    
    if action == "fish":
        await action_fish(query, context, game, current, chat_id)
    elif action == "water":
        await action_water(query, context, game, current, chat_id)
    elif action == "wood":
        await action_wood(query, context, game, current, chat_id)
    elif action == "search":
        await action_search(query, context, game, current, chat_id)
    elif action == "usecard":
        await show_usable_cards(query, context, game, current, chat_id)
    elif action == "shoot":
        await show_shoot_targets(query, context, game, current, chat_id)

async def action_fish(query, context, game, player, chat_id):
    base_fish = random.randint(1, 3)
    bonus = 2 if CardType.FISHING_ROD in player.permanent_cards else 0
    total = base_fish + bonus
    
    game.food += total
    player.action_taken = True
    
    bonus_text = f" (+{bonus} от удочки)" if bonus else ""
    
    await query.edit_message_text(
        f"🎣 {player.first_name} поймал рыбу!\n"
        f"🐟 Вылов: {base_fish}{bonus_text} = {total} рыбки\n"
        f"📊 Запас еды: {game.food}"
    )
    
    await next_player(context, chat_id)

async def action_water(query, context, game, player, chat_id):
    rain = get_weather_rain(game.current_weather)
    
    if rain == 0:
        await query.answer("☀️ Слишком жарко для сбора воды! Выберите другое действие.", show_alert=True)
        return
    
    multiplier = 2 if CardType.FLASK in player.permanent_cards else 1
    total = rain * multiplier
    
    game.water += total
    player.action_taken = True
    
    mult_text = " x2 (фляжка)" if multiplier > 1 else ""
    
    await query.edit_message_text(
        f"💧 {player.first_name} собрал воду!\n"
        f"🌧️ Осадков: {rain}{mult_text} = {total} порций\n"
        f"📊 Запас воды: {game.water}"
    )
    
    await next_player(context, chat_id)

async def action_wood(query, context, game, player, chat_id):
    base_wood = 1
    bonus = 2 if CardType.AXE in player.permanent_cards else 0
    
    snake_bite = random.random() < 0.2
    
    if snake_bite:
        player.is_sick = True
        game.wood += base_wood
        player.action_taken = True
        await query.edit_message_text(
            f"🪵 {player.first_name} собрал древесину, но его укусила змея! 🐍\n"
            f"🪵 Древесина: +{base_wood}\n"
            f"🤒 Вы заболели и пропустите следующий ход!\n"
            f"📊 Древесина: {game.wood}/6"
        )
    else:
        extra = random.randint(0, 2)
        total = base_wood + bonus + extra
        game.wood += total
        player.action_taken = True
        
        bonus_text = f" +{bonus} (топор)" if bonus else ""
        extra_text = f" +{extra} (удача)" if extra else ""
        
        raft_built = ""
        if game.wood >= 6:
            game.wood -= 6
            game.raft_cards += 1
            raft_built = f"\n🛶 Построена новая секция плота! ({game.raft_cards}/12)"
        
        await query.edit_message_text(
            f"🪵 {player.first_name} нашёл древесину!\n"
            f"🪵 Собрано: {base_wood}{bonus_text}{extra_text} = {total}\n"
            f"📊 Древесина: {game.wood}/6{raft_built}"
        )
    
    await next_player(context, chat_id)

async def action_search(query, context, game, player, chat_id):
    cards = draw_wreckage(game, 1)
    if cards:
        card = cards[0]
        player.hand.append(card)
        player.action_taken = True
        
        await query.edit_message_text(
            f"📦 {player.first_name} обыскал обломки и нашёл:\n"
            f"✨ {get_card_name(card)}\n"
            f"_{get_card_description(card)}_"
        )
    else:
        await query.edit_message_text(
            f"📦 {player.first_name} обыскал обломки, но ничего не нашёл."
        )
        player.action_taken = True
    
    await next_player(context, chat_id)

============================================================================
# CARD USAGE HANDLERS
# ============================================================================

async def show_usable_cards(query, context, game, player, chat_id):
    if not player.hand:
        await query.answer("У вас нет карт!", show_alert=True)
        return
    
    keyboard = []
    for i, card in enumerate(player.hand):
        keyboard.append([InlineKeyboardButton(
            get_card_name(card),
            callback_data=f"usecard_{i}_{player.user_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("↩️ Отмена", callback_data=f"cancel_use_{player.user_id}")])
    
    await query.edit_message_text(
        f"🃏 Выберите карту для использования:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_use_card(update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("cancel_use_"):
        await query.edit_message_text("❌ Отменено.")
        return
    
    parts = data.split("_")
    card_idx = int(parts[1])
    user_id = int(parts[2])
    
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    if not game:
        return
    
    player = game.players.get(user_id)
    if not player or card_idx >= len(player.hand):
        return
    
    card = player.hand.pop(card_idx)
    
    if card == CardType.WATER_BOTTLE:
        game.water += 1
        await query.edit_message_text(
            f"💧 {player.first_name} использовал бутылку воды!\n📊 Вода: {game.water}"
        )
    elif card == CardType.SANDWICH:
        game.food += 1
        await query.edit_message_text(
            f"🥪 {player.first_name} съел сэндвич!\n📊 Еда: {game.food}"
        )
    elif card == CardType.SPROTS:
        game.food += 3
        await query.edit_message_text(
            f"🐟 {player.first_name} открыл шпроты!\n📊 Еда: +3 = {game.food}"
        )
    elif card == CardType.COCONUT:
        game.water += 3
        await query.edit_message_text(
            f"🥥 {player.first_name} выпил кокосовой воды!\n📊 Вода: +3 = {game.water}"
        )
    elif card == CardType.DIRTY_WATER:
        game.water += 1
        player.is_sick = True
        await query.edit_message_text(
            f"☣️ {player.first_name} выпил грязную воду!\n"
            f"💧 Вода: +1 = {game.water}\n🤒 Вы заболели от инфекции!"
        )
    elif card == CardType.ROTTEN_FISH:
        game.food += 1
        player.is_sick = True
        await query.edit_message_text(
            f"🤢 {player.first_name} съел тухлую рыбу!\n"
            f"🐟 Еда: +1 = {game.food}\n🤒 Вы отравились!"
        )
    elif card == CardType.ANTIDOTE:
        player.is_sick = False
        await query.edit_message_text(
            f"💊 {player.first_name} принял противоядие!\n✅ Вы излечились."
        )
    elif card == CardType.BAROMETER:
        next_weather = []
        deck_copy = list(game.weather_deck)
        for i in range(min(2, len(deck_copy))):
            w = deck_copy[i]
            next_weather.append(f"• {get_weather_emoji(w)} {w.value} ({get_weather_rain(w)} осадков)")
        weather_text = "\n".join(next_weather) if next_weather else "Колода пуста"
        await query.edit_message_text(
            f"🌡️ {player.first_name} использовал барометр!\n"
            f"🔮 Следующие карты погоды:\n{weather_text}"
        )
    elif card == CardType.FLASHLIGHT:
        next_cards = draw_wreckage(game, 3)
        game.wreckage_deck.extend(next_cards)
        cards_text = "\n".join([f"• {get_card_name(c)}" for c in next_cards])
        await query.edit_message_text(
            f"🔦 {player.first_name} посветил фонариком в обломки!\n"
            f"👀 Верхние 3 карты:\n{cards_text}"
        )
    elif card == CardType.PLANK:
        game.raft_cards += 1
        await query.edit_message_text(
            f"🪵 {player.first_name} добавил доску на плот!\n"
            f"🛶 Мест на плоту: +1 = {game.raft_cards}"
        )
    elif card == CardType.ALARM_CLOCK:
        keyboard = []
        for pid in game.player_order:
            p = game.players[pid]
            if p.is_alive:
                keyboard.append([InlineKeyboardButton(
                    p.first_name,
                    callback_data=f"alarm_{pid}_{player.user_id}"
                )])
        await query.edit_message_text(
            f"⏰ {player.first_name} завёл будильник!\n"
            f"Выберите, кто будет первым в следующем раунде:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    elif card in [CardType.FISHING_ROD, CardType.AXE, CardType.FLASK, CardType.CLUB]:
        player.permanent_cards.append(card)
        await query.edit_message_text(
            f"⚡ {player.first_name} экипировал {get_card_name(card)}!\n"
            f"Эффект активирован на постоянной основе."
        )
    elif card == CardType.REVOLVER:
        player.permanent_cards.append(card)
        await query.edit_message_text(
            f"🔫 {player.first_name} достал револьвер!\n"
            f"Теперь вы можете застрелить любого игрока, если есть пуля."
        )
    elif card == CardType.METAL_PLATE:
        player.permanent_cards.append(card)
        player.protected_from_shot = True
        await query.edit_message_text(
            f"🛡️ {player.first_name} надел бронежилет из металла!\n"
            f"Защита от 1 выстрела активирована."
        )
    elif card == CardType.SLEEPING_PILLS:
        targets = [p for p in alive_players(game) if p.user_id != player.user_id and p.hand]
        if targets:
            target = random.choice(targets)
            stolen = random.choice(target.hand)
            target.hand.remove(stolen)
            player.hand.append(stolen)
            await query.edit_message_text(
                f"💤 {player.first_name} подсыпал снотворное {target.first_name}!\n"
                f"🃏 Украдена карта: {get_card_name(stolen)}!"
            )
        else:
            await query.edit_message_text(
                f"💤 {player.first_name} хотел украсть карту, но некому."
            )
    elif card == CardType.VOODOO_DOLL:
        dead = [p for p in game.players.values() if not p.is_alive]
        if dead:
            keyboard = []
            for p in dead:
                keyboard.append([InlineKeyboardButton(
                    p.first_name,
                    callback_data=f"revive_{p.user_id}_{player.user_id}"
                )])
            await query.edit_message_text(
                f"🧸 {player.first_name} достал куклу вуду!\n"
                f"Выберите, кого воскресить:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        else:
            await query.edit_message_text(
                f"🧸 {player.first_name} достал куклу вуду, но некого воскрешать."
            )
    elif card == CardType.CANNIBAL_STEW:
        dead_this_round = len([p for p in game.players.values() if not p.is_alive])
        food_gain = dead_this_round * 2
        game.food += food_gain
        await query.edit_message_text(
            f"🍲 {player.first_name} сварил рагу из робинзона!\n"
            f"🤢 Мрачно, но эффективно: +{food_gain} еды = {game.food}"
        )
    elif card == CardType.COFFEE:
        player.coffee_active = True
        await query.edit_message_text(
            f"☕ {player.first_name} выпил кофе!\n"
            f"⚡ В этом раунде вы можете выполнить 2 действия!"
        )
        player.action_taken = False  # Может сходить ещё раз
        await notify_current_player(context, chat_id)
        return
    elif card == CardType.FRUIT_BASKET:
        await query.edit_message_text(
            f"🍎 {player.first_name} разделил корзину фруктов!\n"
            f"✨ Все робинзоны игнорируют смерть от голода/жажды в этом раунде."
        )
        # Эффект применяется автоматически в survival_check
    elif card == CardType.MATCHES:
        await query.edit_message_text(
            f"🔥 {player.first_name} зажёг спички!\n"
            f"✨ Теперь можно пить грязную воду и есть тухлую рыбу без болезни."
        )
    elif card == CardType.SPYGLASS:
        targets = [p for p in alive_players(game) if p.user_id != player.user_id and p.hand]
        if targets:
            target = random.choice(targets)
            cards_text = "\n".join([f"• {get_card_name(c)}" for c in target.hand])
            await query.edit_message_text(
                f"🔭 {player.first_name} посмотрел в подзорную трубу!\n"
                f"👀 Карты {target.first_name}:\n{cards_text}"
            )
        else:
            await query.edit_message_text(
                f"🔭 {player.first_name} посмотрел в подзорную трубу, но ничего не увидел."
            )
    elif card == CardType.PENDULUM:
        targets = [p for p in alive_players(game) if p.user_id != player.user_id]
        if targets:
            keyboard = []
            for p in targets:
                keyboard.append([InlineKeyboardButton(
                    p.first_name,
                    callback_data=f"pendulum_{p.user_id}_{player.user_id}"
                )])
            await query.edit_message_text(
                f"🌀 {player.first_name} достал маятник!\n"
                f"Выберите, кому навязать действие:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        else:
            await query.edit_message_text(
                f"🌀 {player.first_name} достал маятник, но некому навязать действие."
            )
    else:
        game.wreckage_discard.append(card)
        await query.edit_message_text(
            f"🃏 {player.first_name} использовал {get_card_name(card)}."
        )
    
    if not player.coffee_active:
        player.action_taken = True
    else:
        player.coffee_active = False
        player.action_taken = True
    
    await next_player(context, chat_id)

============================================================================
# SPECIAL CALLBACK HANDLERS
# ============================================================================

async def handle_alarm_choice(update, context):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    target_pid = int(parts[1])
    user_id = int(parts[2])
    
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    if not game:
        return
    
    for i, pid in enumerate(game.player_order):
        if pid == target_pid:
            game.first_player_idx = i
            break
    
    target = game.players.get(target_pid)
    await query.edit_message_text(
        f"⏰ Будильник установлен! {target.first_name} будет первым в следующем раунде."
    )
    
    player = game.players.get(user_id)
    if player:
        player.action_taken = True
    await next_player(context, chat_id)

async def handle_revive(update, context):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    target_pid = int(parts[1])
    user_id = int(parts[2])
    
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    if not game:
        return
    
    target = game.players.get(target_pid)
    if target:
        target.is_alive = True
        target.is_sick = False
        target.hand = draw_wreckage(game, 2)
        
        await query.edit_message_text(
            f"🧸 Кукла вуду сработала!\n"
            f"✨ {target.first_name} воскрешён из мёртвых!\n"
            f"🎲 Получено 2 новые карты обломков."
        )
    
    player = game.players.get(user_id)
    if player:
        player.action_taken = True
    await next_player(context, chat_id)

async def handle_pendulum(update, context):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    target_pid = int(parts[1])
    user_id = int(parts[2])
    
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    if not game:
        return
    
    target = game.players.get(target_pid)
    caster = game.players.get(user_id)
    
    if target and caster:
        await query.edit_message_text(
            f"🌀 {caster.first_name} навязал действие {target.first_name}!\n"
            f"{target.first_name}, выберите действие в групповом чате."
        )
        # Устанавливаем текущего игрока на цель
        for i, pid in enumerate(game.player_order):
            if pid == target_pid:
                game.current_player_idx = i
                target.action_taken = False
                break
        await notify_current_player(context, chat_id)

async def show_shoot_targets(query, context, game, player, chat_id):
    targets = [p for p in alive_players(game) if p.user_id != player.user_id]
    if not targets:
        await query.answer("Некого стрелять!", show_alert=True)
        return
    
    keyboard = []
    for target in targets:
        keyboard.append([InlineKeyboardButton(
            f"🔫 {target.first_name}",
            callback_data=f"shoot_{target.user_id}_{player.user_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("↩️ Отмена", callback_data=f"cancel_shoot_{player.user_id}")])
    
    await query.edit_message_text(
        f"🔫 {player.first_name} направил револьвер...\n"
        f"Выберите жертву:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_shoot(update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("cancel_shoot_"):
        await query.edit_message_text("❌ Выстрел отменён.")
        return
    
    parts = data.split("_")
    target_id = int(parts[1])
    shooter_id = int(parts[2])
    
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    if not game:
        return
    
    shooter = game.players.get(shooter_id)
    target = game.players.get(target_id)
    
    if not shooter or not target:
        return
    
    # Проверяем наличие пули
    if CardType.BULLET not in shooter.hand:
        await query.edit_message_text("❌ Нет патронов!")
        return
    
    shooter.hand.remove(CardType.BULLET)
    
    # Проверяем защиту
    if target.protected_from_shot or CardType.METAL_PLATE in target.permanent_cards:
        target.protected_from_shot = False
        # Удаляем металл
        if CardType.METAL_PLATE in target.permanent_cards:
            target.permanent_cards.remove(CardType.METAL_PLATE)
        await query.edit_message_text(
            f"🔫 {shooter.first_name} выстрелил в {target.first_name}!\n"
            f"🛡️ Но {target.first_name} защищён металлической пластиной!\n"
            f"💥 Пуля отрикошетила..."
        )
    else:
        target.is_alive = False
        # Передача карт
        game.wreckage_discard.extend(target.hand)
        target.hand = []
        for card in target.permanent_cards:
            if card != CardType.REVOLVER:
                game.wreckage_discard.append(card)
        target.permanent_cards = []
        
        await query.edit_message_text(
            f"🔫 {shooter.first_name} выстрелил в {target.first_name}!\n"
            f"💀 {target.first_name} погибает от выстрела...\n"
            f"🪦 Покойся с миром, робинзон."
        )
    
    shooter.action_taken = True
    await next_player(context, chat_id)

# ============================================================================
# SURVIVAL CHECK & VOTING
# ============================================================================

async def survival_check(context, chat_id):
    game = context.chat_data.get('game')
    if not game:
        return
    
    alive = alive_players(game)
    num_alive = len(alive)
    
    await context.bot.send_message(
        chat_id,
        f"🌅 Конец раунда {game.round_num} - проверка выживания!\n"
        f"{format_resources(game)}\n\n"
        f"💧 Распределение воды ({num_alive} робинзонов)"
    )
    
    if game.water >= num_alive:
        game.water -= num_alive
        await context.bot.send_message(
            chat_id,
            f"✅ Воды хватило всем! Осталось: {game.water}"
        )
        await distribute_food(context, chat_id)
    else:
        game.phase = "voting_water"
        game.voting_reason = "water"
        game.votes = {}
        await start_voting(context, chat_id, "water", num_alive - game.water)

async def distribute_food(context, chat_id):
    game = context.chat_data.get('game')
    if not game:
        return
    
    alive = alive_players(game)
    num_alive = len(alive)
    
    await context.bot.send_message(
        chat_id,
        f"🐟 Распределение еды ({num_alive} робинзонов)"
    )
    
    if game.food >= num_alive:
        game.food -= num_alive
        await context.bot.send_message(
            chat_id,
            f"✅ Еды хватило всем! Осталось: {game.food}"
        )
        await check_end_game(context, chat_id)
    else:
        game.phase = "voting_food"
        game.voting_reason = "food"
        game.votes = {}
        await start_voting(context, chat_id, "food", num_alive - game.food)

async def start_voting(context, chat_id, reason, shortage):
    game = context.chat_data.get('game')
    if not game:
        return
    
    alive = [p for p in alive_players(game)]
    reason_text = "💧 воды" if reason == "water" else "🐟 еды"
    
    await context.bot.send_message(
        chat_id,
        f"⚠️ НЕХВАТКА {reason_text.upper()}!\n"
        f"Не хватает на {shortage} робинзонов!\n"
        f"🗳️ Начинается голосование - кого изгнать?\n\n"
        f"Каждый живой игрок должен проголосовать."
    )
    
    for voter in alive:
        keyboard = []
        for target in alive:
            if target.user_id != voter.user_id:
                keyboard.append([InlineKeyboardButton(
                    f"Изгнать {target.first_name}",
                    callback_data=f"vote_{target.user_id}_{voter.user_id}_{reason}"
                )])
        
        try:
            await context.bot.send_message(
                voter.user_id,
                f"🗳️ Голосование за изгнание\n"
                f"Причина: нехватка {reason_text}\n"
                f"Выберите, кого изгнать:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await context.bot.send_message(
                chat_id,
                f"@{voter.username or voter.user_id} - ваш голос (отправлено в ЛС, проверьте):"
            )
async def handle_vote(update, context):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    target_id = int(parts[1])
    voter_id = int(parts[2])
    reason = parts[3]
    
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    if not game or game.phase not in ["voting_water", "voting_food"]:
        return
    
    voter = game.players.get(voter_id)
    target = game.players.get(target_id)
    
    if not voter or not voter.is_alive or voter.has_voted:
        await query.answer("❌ Вы уже проголосовали или не можете голосовать!", show_alert=True)
        return
    
    vote_weight = 2 if CardType.CLUB in voter.permanent_cards else 1
    
    game.votes[target_id] = game.votes.get(target_id, 0) + vote_weight
    voter.has_voted = True
    voter.vote_target = target_id
    
    await query.edit_message_text(
        f"✅ Вы проголосовали за изгнание {target.first_name}!"
    )
    
    alive_voters = [p for p in alive_players(game) if not p.has_voted]
    if not alive_voters:
        await resolve_voting(context, chat_id, reason)

async def resolve_voting(context, chat_id, reason):
    game = context.chat_data.get('game')
    if not game:
        return
    
    if not game.votes:
        await context.bot.send_message(chat_id, "🤔 Никто не проголосовал. Странно...")
        await after_voting(context, chat_id, reason)
        return
    
    max_votes = max(game.votes.values())
    candidates = [pid for pid, v in game.votes.items() if v == max_votes]
    
    if len(candidates) > 1:
        first_player = game.players[game.player_order[game.first_player_idx]]
        expelled_id = candidates[0]
        tie_text = f"🤝 Ничья! Решает первый игрок {first_player.first_name}."
        await context.bot.send_message(chat_id, tie_text)
    else:
        expelled_id = candidates[0]
    
    expelled = game.players.get(expelled_id)
    if not expelled:
        await after_voting(context, chat_id, reason)
        return
    
    # Проверяем раковину
    has_shell = CardType.SHELL in expelled.hand
    if has_shell:
        await context.bot.send_message(
            chat_id,
            f"🐚 {expelled.first_name} показал раковину!\n"
            f"👑 Никто не может голосовать против лидера! Голосование отменено."
        )
        await after_voting(context, chat_id, reason)
        return
    
    # Проверяем защиту от металла
    if expelled.protected_from_shot:
        await context.bot.send_message(
            chat_id,
            f"🛡️ {expelled.first_name} защищён металлической пластиной!"
        )
        expelled.protected_from_shot = False
        await after_voting(context, chat_id, reason)
        return
    
    # Изгнание
    expelled.is_alive = False
    
    # Сброс карт
    for card in expelled.permanent_cards:
        if card == CardType.REVOLVER:
            game.wreckage_discard.append(card)
        else:
            game.wreckage_discard.append(card)
    
    expelled.permanent_cards = []
    game.wreckage_discard.extend(expelled.hand)
    expelled.hand = []
    
    reason_text = "жажды" if reason == "water" else "голода"
    
    await context.bot.send_message(
        chat_id,
        f"💀 {expelled.first_name} ИЗГНАН!\n"
        f"Причина: нехватка {reason_text}.\n"
        f"Он погибает в одиночестве...\n\n"
        f"{format_players_list(game)}"
    )
    
    await after_voting(context, chat_id, reason)

async def after_voting(context, chat_id, reason):
    game = context.chat_data.get('game')
    if not game:
        return
    
    alive = alive_players(game)
    if len(alive) == 0:
        await context.bot.send_message(
            chat_id,
            f"💀 ВСЕ ПОГИБЛИ!\n"
            f"Остров поглотил последних робинзонов...\n"
            f"🪦 Игра окончена. Никто не выжил."
        )
        game.game_over = True
        return
    
    # Проверяем, нужно ли ещё голосовать
    if reason == "water":
        # После голосования за воду проверяем еду
        await distribute_food(context, chat_id)
    else:
        await check_end_game(context, chat_id)

# ============================================================================
# END GAME CHECK
# ============================================================================

async def check_end_game(context, chat_id):
    game = context.chat_data.get('game')
    if not game:
        return
    
    alive = alive_players(game)
    num_alive = len(alive)
    
    if num_alive == 0:
        await context.bot.send_message(
            chat_id,
            "💀 ВСЕ ПОГИБЛИ!\n"
            "🪦 Игра окончена. Никто не выжил."
        )
        game.game_over = True
        return
    
    # Условия победы (покидание острова)
    # 1. Есть достаточно карт плота
    # 2. Есть по 1 порции воды и еды на каждого
    can_leave = (
        game.raft_cards >= num_alive and
        game.water >= num_alive and
        game.food >= num_alive
    )
    
    if can_leave and not game.hurricane_triggered:
        await context.bot.send_message(
            chat_id,
            f"🛶 ПЛОТ ГОТОВ!\n\n"
            f"{format_resources(game)}\n\n"
            f"Робинзоны могут покинуть остров!\n"
            f"Хотите уплыть сейчас или продолжить игру?\n\n"
            f"Голосуйте: /leave или /stay"
        )
        game.phase = "decision"
        return
    
    if game.hurricane_triggered:
        # Проверяем, можно ли уплыть при урагане
        if can_leave:
            game.winners = [p.user_id for p in alive]
            winner_names = ", ".join([p.first_name for p in alive])
            await context.bot.send_message(
                chat_id,
                f"🌪️ УРАГАН НАСТУПАЕТ!\n"
                f"🏃‍♂️ Робинзоны бегут к плоту!\n\n"
                f"🎉 ПОБЕДИТЕЛИ: {winner_names}!\n"
                f"Все выжившие покидают остров!"
            )
            game.game_over = True
            return
        else:
            # Нужно голосовать, чтобы осталось меньше людей
            needed = min(num_alive, game.raft_cards)
            to_expel = num_alive - needed
            if to_expel > 0:
                await context.bot.send_message(
                    chat_id,
                    f"🌪️ УРАГАН! Не хватает мест на плоту!\n"
                    f"Нужно изгнать {to_expel} робинзонов, чтобы остальные выжили."
                )
                game.phase = "voting_water"
                game.voting_reason = "hurricane"
                game.votes = {}
                await start_voting(context, chat_id, "hurricane", to_expel)
                return
            else:
                await context.bot.send_message(
                    chat_id,
                    f"🌪️ УРАГАН ПОГЛОТИЛ ВСЕХ!\n"
                    f"💀 Никому не удалось выжить..."
                )
                game.game_over = True
                return
    
    # Новый раунд
    game.round_num += 1
    await context.bot.send_message(
        chat_id,
        f"🌅 Раунд {game.round_num - 1} завершён.\n"
        f"{format_resources(game)}\n\n"
        f"Начинается новый раунд..."
    )
    await start_round(context, chat_id)

============================================================================
# TELEGRAM COMMAND HANDLERS
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌴 Добро пожаловать в РОБИНЗОНАДУ!\n\n"
        "Настольная игра о выживании на необитаемом острове.\n\n"
        "Команды:\n"
        "/newgame - Создать новую игру\n"
        "/join - Присоединиться к игре\n"
        "/startgame - Начать игру (нужно 3+ игроков)\n"
        "/rules - Правила игры\n"
        "/status - Статус текущей игры\n"
        "/hand - Посмотреть свои карты (в ЛС боту)\n\n"
        "Для начала создайте игру командой /newgame и пригласите друзей!"
    )

async def newgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Игра создаётся только в групповом чате!")
        return
    
    game = GameState(chat_id=chat_id)
    player = Player(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name
    )
    game.players[user.id] = player
    game.player_order.append(user.id)
    context.chat_data['game'] = game
    
    await update.message.reply_text(
        f"🌴 НОВАЯ ИГРА СОЗДАНА!\n\n"
        f"👤 Организатор: {user.first_name}\n"
        f"👥 Игроков: 1/12\n\n"
        f"Присоединяйтесь командой /join!\n"
        f"Начать игру: /startgame (минимум 3 игрока)"
    )

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = context.chat_data.get('game')
    
    if not game:
        await update.message.reply_text("❌ Сначала создайте игру командой /newgame")
        return
    
    if game.phase != "lobby":
        await update.message.reply_text("❌ Игра уже идёт! Дождитесь окончания.")
        return
    
    if user.id in game.players:
        await update.message.reply_text("❌ Вы уже в игре!")
        return
    
    if len(game.players) >= 12:
        await update.message.reply_text("❌ Достигнут максимум игроков (12)!")
        return
    
    player = Player(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name
    )
    game.players[user.id] = player
    game.player_order.append(user.id)
    
    await update.message.reply_text(
        f"✅ {user.first_name} присоединился!\n"
        f"👥 Игроков: {len(game.players)}/12"
    )

async def startgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    
    if not game:
        await update.message.reply_text("❌ Сначала создайте игру: /newgame")
        return
    
    if game.phase != "lobby":
        await update.message.reply_text("❌ Игра уже идёт!")
        return
    
    await start_game_logic(context, chat_id)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    
    if not game:
        await update.message.reply_text("❌ Нет активной игры. Создайте: /newgame")
        return
    
    if game.phase == "lobby":
        await update.message.reply_text(
            f"🌴 Лобби игры\n\n"
            f"{format_players_list(game)}\n\n"
            f"Игроков: {len(game.players)}/12\n"
            f"Начать: /startgame (нужно 3+)"
        )
        return
    
    await update.message.reply_text(
        f"📅 Раунд {game.round_num} | Фаза: {game.phase}\n\n"
        f"{format_resources(game)}\n\n"
        f"{format_players_list(game)}\n\n"
        f"🌤️ Текущая погода: {get_weather_emoji(game.current_weather)} ({get_weather_rain(game.current_weather)} осадков)"
    )

async def hand_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Ищем игру в чате
    game = None
    for chat_data in context.application.chat_data.values():
        g = chat_data.get('game')
        if g and user.id in g.players:
            game = g
            break
    
    if not game:
        await update.message.reply_text("❌ Вы не участвуете ни в одной игре.")
        return
    
    player = game.players.get(user.id)
    if not player:
        await update.message.reply_text("❌ Вы не в игре.")
        return
    
    await update.message.reply_text(format_player_hand(player))

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 ПРАВИЛА РОБИНЗОНАДЫ\n\n"
        "🎯 Цель: Выжить и покинуть остров на плоту.\n\n"
        "👥 Игроки: 3-12 робинзонов\n\n"
        "📅 Раунд состоит из:\n"
        "1️⃣ Смена первого игрока\n"
        "2️⃣ Открытие карты погоды\n"
        "3️⃣ Действия игроков (по часовой стрелке)\n"
        "4️⃣ Распределение воды и еды\n"
        "5️⃣ Проверка конца игры\n\n"
        "🎣 Действия:\n"
        "• Рыбалка — случайно 1-3 рыбки\n"
        "• Сбор воды — по осадкам на карте погоды (0-3)\n"
        "• Древесина — +1 к плоту, риск укуса змеи\n"
        "• Обыск — взять карту обломков\n\n"
        "⚠️ Если ресурсов не хватает — голосование!\n"
        "Игрок с наибольшим числом голосов изгоняется.\n\n"
        "🏆 Победа: построить плот (6 древесины = 1 карта),\n"
        "накопить по 1 воды и еды на каждого.\n\n"
        "🌪️ Ураган — экстренное покидание острова!\n\n"
        "🃏 Карты обломков дают бонусы, оружие, защиту.\n"
        "Используйте их с умом!"
    )

async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    
    if not game or game.phase != "decision":
        await update.message.reply_text("❌ Сейчас нельзя покинуть остров.")
        return
    
    alive = alive_players(game)
    winner_names = ", ".join([p.first_name for p in alive])
    await update.message.reply_text(
        f"🛶 Робинзоны покидают остров!\n\n"
        f"🎉 ПОБЕДИТЕЛИ: {winner_names}!\n"
        f"Все выжившие спасены!"
    )
    game.game_over = True

async def stay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = context.chat_data.get('game')
    
    if not game or game.phase != "decision":
        await update.message.reply_text("❌ Сейчас нельзя остаться.")
        return
    
    game.phase = "action"
    game.round_num += 1
    await update.message.reply_text(
        "🏝️ Робинзоны решают остаться!\n"
        "Продолжаем выживание..."
    )
    await start_round(context, chat_id)

# ============================================================================
# MAIN APPLICATION SETUP
# ============================================================================

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Укажите BOT_TOKEN в файле .env!")
        print("Создайте бота через @BotFather и получите токен.")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("newgame", newgame_command))
    application.add_handler(CommandHandler("join", join_command))
    application.add_handler(CommandHandler("startgame", startgame_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("hand", hand_command))
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("leave", leave_command))
    application.add_handler(CommandHandler("stay", stay_command))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(handle_action, pattern=r"^act_"))
    application.add_handler(CallbackQueryHandler(handle_use_card, pattern=r"^usecard_"))
    application.add_handler(CallbackQueryHandler(handle_use_card, pattern=r"^cancel_use_"))
    application.add_handler(CallbackQueryHandler(handle_alarm_choice, pattern=r"^alarm_"))
    application.add_handler(CallbackQueryHandler(handle_revive, pattern=r"^revive_"))
    application.add_handler(CallbackQueryHandler(handle_pendulum, pattern=r"^pendulum_"))
    application.add_handler(CallbackQueryHandler(handle_shoot, pattern=r"^shoot_"))
    application.add_handler(CallbackQueryHandler(handle_shoot, pattern=r"^cancel_shoot_"))
    application.add_handler(CallbackQueryHandler(handle_vote, pattern=r"^vote_"))
    
    # Bot commands menu
    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("newgame", "Создать новую игру"),
        BotCommand("join", "Присоединиться к игре"),
        BotCommand("startgame", "Начать игру"),
        BotCommand("status", "Статус игры"),
        BotCommand("hand", "Мои карты (в ЛС)"),
        BotCommand("rules", "Правила игры"),
    ]
    
    async def post_init(app):
        await app.bot.set_my_commands(commands)
    
    application.post_init = post_init
    
    print("🌴 Робинзонада бот запущен!")
    print("Нажмите Ctrl+C для остановки.")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
