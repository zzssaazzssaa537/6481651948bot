import os
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
import random
import asyncio
import logging
import subprocess
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

# Define the token directly in the code
TOKEN = "7269916681:AAHLLxIeyWYsnzunyFqEBIriqaD0nSb1Spk"
OWNER_ID = 7342561936  # Replace with your own Telegram ID

# Tokens for report and feedback bots
REPORT_BOT_TOKEN = "7261277394:AAEALpqckRG2McndiD8dhuVaqn-veZ_9nbo"
FEEDBACK_BOT_TOKEN = "7426243703:AAG91JEHkvMV417YanjSWhsAmTKTkwCDaag"
RECOMMENDATION_BOT_TOKEN = "7307828512:AAF5R0by_EIT52rHlqt068b9qkvlryguaJQ"

# Create bot instance
bot = Bot(token=TOKEN)

# Directory to hold account files
ACCOUNTS_DIR = 'accounts'

# Essential account files
ESSENTIAL_FILES = ['Valorant.txt', 'league of legends.txt']

# Rate limiting parameters
REQUEST_LIMIT = 10
REQUEST_WINDOW = 60  # Number of seconds per window

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING  # Change this to logging.ERROR to show only errors
)
logger = logging.getLogger(__name__)

# Dictionary to hold all data
data = {
    "shortcuts": {},
    "account_types": ["Valorant", "league of legends"],
    "blocked_users": set(),
    "allowed_channels": set(),
    "allow_all_channels": True,
    "enabled": True,
    "user_daily_limits": {},
    "daily_limit": 5,
    "unlimited_access": False,
    "user_data": {},
    "maintenance_mode": False,
    "premium_users": set(),
    "user_requests": defaultdict(list),
    "premium_daily_limit": 50,
    "unlimited_access_premium_plus": False,
    "premium_plus_users": set(),
    "premium_plus_daily_limit": 100,
    "admins": set(),
}

# Function to install missing libraries
def install_missing_libraries():
    required_libraries = [
        "python-telegram-bot",
        "aiohttp",
        "transformers",
        "torch"
    ]

    with open('requirements.txt', 'w') as file:
        file.write('\n'.join(required_libraries))

    installed_libraries = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze']).decode().split('\n')
    installed_libraries = [pkg.split('==')[0] for pkg in installed_libraries]

    missing_libraries = [lib for lib in required_libraries if lib not in installed_libraries]

    if missing_libraries:
        f = io.StringIO()  # Create a StringIO object to capture stdout and stderr
        with redirect_stdout(f), redirect_stderr(f):
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing_libraries])

# Ensure libraries are installed
install_missing_libraries()

# Clear the screen to hide previous messages
if os.name == 'nt':  # For Windows
    os.system('cls')
else:  # For macOS and Linux
    os.system('clear')

print("The bot is running successfully.")

# Ensure necessary directories and files are present
def ensure_directories_and_files():
    try:
        if not os.path.exists(ACCOUNTS_DIR):
            os.makedirs(ACCOUNTS_DIR)
            print(f"Created directory: {ACCOUNTS_DIR}")
        else:
            print(f"Directory already exists: {ACCOUNTS_DIR}")

        # Create essential txt files if they don't exist
        for filename in ESSENTIAL_FILES:
            file_path = os.path.join(ACCOUNTS_DIR, filename)
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    pass
                print(f"Created file: {file_path}")
            else:
                print(f"File already exists: {file_path}")

        # Create JSON file if it doesn't exist
        if not os.path.exists('data.json'):
            data_to_save = data.copy()
            data_to_save['blocked_users'] = list(data_to_save['blocked_users'])
            data_to_save['allowed_channels'] = list(data_to_save['allowed_channels'])
            data_to_save['premium_users'] = list(data_to_save['premium_users'])
            data_to_save['premium_plus_users'] = list(data_to_save['premium_plus_users'])
            data_to_save['admins'] = list(data_to_save['admins'])
            
            with open('data.json', 'w') as f:
                json.dump(data_to_save, f)
            print("Created file: data.json")
        else:
            print("File already exists: data.json")
    except Exception as e:
        logger.error(f"Error ensuring directories and files: {e}")

# Load data from file
def load_data():
    global data
    try:
        if os.path.exists('data.json'):
            with open('data.json', 'r', encoding='utf-8') as file:
                loaded_data = json.load(file)
                # Update the global data dictionary with loaded data
                data.update(loaded_data)
                # Convert lists back to sets
                data['blocked_users'] = set(data.get('blocked_users', []))
                data['allowed_channels'] = set(data.get('allowed_channels', []))
                data['premium_users'] = set(data.get('premium_users', []))
                data['premium_plus_users'] = set(data.get('premium_plus_users', []))
                data['user_requests'] = defaultdict(list, {int(k): v for k, v in data.get('user_requests', {}).items()})
                data['user_daily_limits'] = {int(k): (datetime.fromisoformat(v[0]), v[1]) for k, v in data.get('user_daily_limits', {}).items()}
                data['admins'] = set(data.get('admins', []))
        else:
            save_data()
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Error loading data: {e}")
        save_data()

# Save data to file
def save_data():
    data_to_save = data.copy()
    data_to_save['blocked_users'] = list(data_to_save['blocked_users'])
    data_to_save['allowed_channels'] = list(data_to_save['allowed_channels'])
    data_to_save['premium_users'] = list(data_to_save['premium_users'])
    data_to_save['premium_plus_users'] = list(data_to_save['premium_plus_users'])
    data_to_save['admins'] = list(data_to_save['admins'])
    data_to_save['user_requests'] = dict(data_to_save['user_requests'])
    data_to_save['user_daily_limits'] = {k: (v[0].isoformat(), v[1]) for k, v in data_to_save['user_daily_limits'].items()}

    with open('data.json', 'w', encoding='utf-8') as file:
        json.dump(data_to_save, file, ensure_ascii=False, indent=4)

# Load data when the bot starts
load_data()

def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    return user_id == OWNER_ID or user_id in data['admins']

def is_blocked(user_id):
    if user_id in data['blocked_users']:
        if 'timeout_end' in data['user_data'].get(user_id, {}):
            timeout_end = datetime.fromisoformat(data['user_data'][user_id]['timeout_end'])
            if datetime.now() < timeout_end:
                return timeout_end
            else:
                del data['user_data'][user_id]['timeout_end']
                data['blocked_users'].discard(user_id)
                save_data()
                return False
        return True
    return False

def is_allowed_channel(chat_id):
    return data['allow_all_channels'] or chat_id in data['allowed_channels']

def is_rate_limited(user_id):
    if is_owner(user_id):
        return False

    current_time = time.time()
    if user_id in data['user_requests']:
        requests = data['user_requests'][user_id]
        data['user_requests'][user_id] = [req for req in requests if req > current_time - REQUEST_WINDOW]
    else:
        data['user_requests'][user_id] = []

    if len(data['user_requests'][user_id]) >= REQUEST_LIMIT:
        return True

    data['user_requests'][user_id].append(current_time)
    return False

def get_next_accounts(account_type="accounts", quantity=1):
    filename = os.path.join(ACCOUNTS_DIR, f'{account_type}.txt')
    if not os.path.exists(filename):
        return []

    with open(filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    if not lines:
        return []

    accounts = [lines.pop(0).strip() for _ in range(min(quantity, len(lines)))]

    with open(filename, 'w', encoding='utf-8') as file:
        file.writelines(lines)
    return accounts

def get_random_account():
    account_files = [f for f in os.listdir(ACCOUNTS_DIR) if f.endswith('.txt')]
    if not account_files:
        return None, None

    random_file = random.choice(account_files)
    account_type = os.path.splitext(random_file)[0]
    account = get_next_account(account_type)
    return account, account_type

def get_next_account(account_type="accounts"):
    accounts = get_next_accounts(account_type, 1)
    return accounts[0] if accounts else None

def parse_account_info(account_info, account_type):
    if account_type.lower() == "league of legends":
        parts = account_info.split('\n')
        if len(parts) == 4:
            user_pass, region, level, nickname = parts
            return (f"Username: {user_pass.split(':')[0]}\n"
                    f"Password: {user_pass.split(':')[1]}\n"
                    f"Region: {region.split('=')[1].strip()}\n"
                    f"Level: {level.split('=')[1].strip()}\n"
                    f"Nickname: {nickname.split('=')[1].strip()}")
        else:
            return account_info  # Return the raw info if it doesn't match the expected format
    else:
        user_pass = account_info.split(' | ')[0]
        return f"Username: {user_pass.split(':')[0]}\nPassword: {user_pass.split(':')[1]}"

def check_daily_limit(user_id):
    if is_owner(user_id):
        return 0

    current_time = datetime.now()

    if user_id in data['premium_plus_users']:
        if data['unlimited_access_premium_plus']:
            return 0
        limit = data['premium_plus_daily_limit']
    elif user_id in data['premium_users']:
        limit = data['premium_daily_limit']
    else:
        limit = data['daily_limit']

    if user_id in data['user_daily_limits']:
        last_access_time, count = data['user_daily_limits'][user_id]
        if last_access_time.date() == current_time.date():
            return count
        else:
            data['user_daily_limits'][user_id] = (current_time, 0)
            save_data()
            return 0
    else:
        data['user_daily_limits'][user_id] = (current_time, 0)
        save_data()
        return 0

def increment_daily_limit(user_id):
    if is_owner(user_id):
        return

    current_time = datetime.now()
    if user_id in data['user_daily_limits']:
        last_access_time, count = data['user_daily_limits'][user_id]
        if last_access_time.date() == current_time.date():
            data['user_daily_limits'][user_id] = (last_access_time, count + 1)
        else:
            data['user_daily_limits'][user_id] = (current_time, 1)
    else:
        data['user_daily_limits'][user_id] = (current_time, 1)
    save_data()

def reset_user_limit(user_id):
    if user_id in data['user_daily_limits']:
        del data['user_daily_limits'][user_id]
        save_data()

def reset_all_free_limits():
    global data
    data['user_daily_limits'] = {k: v for k, v in data['user_daily_limits'].items() if k in data['premium_users'] or k in data['premium_plus_users']}
    save_data()

def reset_all_premium_limits():
    global data
    for user_id in data['premium_users']:
        if user_id in data['user_daily_limits']:
            del data['user_daily_limits'][user_id]
    save_data()

def reset_all_premium_plus_limits():
    global data
    for user_id in data['premium_plus_users']:
        if user_id in data['user_daily_limits']:
            del data['user_daily_limits'][user_id]
    save_data()

def update_user_data(user_id, username):
    current_time = datetime.now().isoformat()
    if user_id not in data['user_data']:
        data['user_data'][user_id] = {
            "username": username,
            "first_use": current_time,
            "last_use": current_time,
            "use_count": 1,
            "last_activity": current_time  # إضافة حقل last_activity
        }
    else:
        user_data = data['user_data'][user_id]
        user_data["username"] = username  # تأكد من تحديث اسم المستخدم
        user_data["last_use"] = current_time
        user_data["use_count"] = user_data.get("use_count", 0) + 1
        user_data["last_activity"] = current_time  # تحديث last_activity
    save_data()

def update_last_activity(user_id):
    current_time = datetime.now().isoformat()
    if user_id in data['user_data']:
        data['user_data'][user_id]['last_activity'] = current_time
    else:
        data['user_data'][user_id] = {"last_activity": current_time}
    save_data()

def log_activity(update):
    user = update.message.from_user
    logger.info(f"User {user.id} - {user.username}: {update.message.text}")

def detect_unusual_activity(user_id):
    if is_owner(user_id):
        return False
    
    if user_id not in data['user_data']:
        return False
    
    user_data = data['user_data'][user_id]
    current_time = datetime.now()

    # Check if the user is sending too many requests
    if is_rate_limited(user_id):
        return True
    
    # Check if the user account is new (e.g., created within the last 2 days)
    account_age_limit = timedelta(days=data.get('fake_account_age_limit', 2))
    account_creation_time = datetime.fromisoformat(user_data.get('first_use', current_time.isoformat()))
    if current_time - account_creation_time < account_age_limit:
        return True
    
    return False

def get_statistics():
    current_time = datetime.now()
    active_users = sum(1 for user_info in data['user_data'].values() if 'last_activity' in user_info and datetime.fromisoformat(user_info['last_activity']) > current_time - timedelta(minutes=10))
    total_users = len(data['user_data'])
    return total_users, active_users

async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    username = update.message.from_user.username

    timeout_end = is_blocked(user_id)
    if timeout_end:
        await update.message.reply_text(f"You are currently in timeout until {timeout_end}. Please try again later.")
        return

    if data['maintenance_mode'] and not is_owner(user_id):
        await update.message.reply_text("The bot is currently under maintenance. Please try again later.")
        return

    update_user_data(user_id, username)

    await update.message.reply_text("Hello! Use /free to get an account or /feedbackmenu to report an issue or give feedback.")

async def premium(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if is_admin(user_id):
        await update.message.reply_text("Welcome Admin! This is the premium section.")
        await show_premium_menu(update, context)
    elif user_id in data['premium_users']:
        await update.message.reply_text(f"Welcome {update.message.from_user.username}! This is the premium section. Here are your available account types.")
        await show_premium_menu(update, context)
    else:
        await update.message.reply_text("You are not a premium user. Please upgrade to access this section.")

async def premium_plus(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if is_admin(user_id) or user_id in data['premium_plus_users']:
        await update.message.reply_text(f"Welcome {update.message.from_user.mention_html()}! This is the premium plus section. Please choose a premium plus account type:", parse_mode=ParseMode.HTML)
        await show_premium_plus_menu(update, context)
    else:
        await update.message.reply_text("You are not a premium plus user. Please upgrade to access this section.")

async def block_user(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This command is for admins only.")
        return

    target_user = int(context.args[0])
    data['blocked_users'].add(target_user)
    save_data()
    await update.message.reply_text(f"User with ID {target_user} has been blocked.")
    try:
        await context.bot.send_message(chat_id=target_user, text="You have been blocked by the bot.")
    except Exception as e:
        logger.error(f"Failed to send block message to user {target_user}: {e}")

async def unblock_user(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This command is for admins only.")
        return

    target_user = int(context.args[0])
    data['blocked_users'].discard(target_user)
    save_data()
    await update.message.reply_text(f"User with ID {target_user} has been unblocked.")
    try:
        await context.bot.send_message(chat_id=target_user, text="Your block has been removed. You can use the bot again.")
    except Exception as e:
        logger.error(f"Failed to send unblock message to user {target_user}: {e}")

async def timeout_user(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This command is for admins only.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Please provide user ID and duration (e.g., 12345 1h for 1 hour timeout).")
        return

    try:
        target_user_id = int(args[0])
        duration_str = args[1]

        if duration_str.endswith('m'):
            timeout_duration = timedelta(minutes=int(duration_str[:-1]))
        elif duration_str.endswith('h'):
            timeout_duration = timedelta(hours=int(duration_str[:-1]))
        elif duration_str.endswith('d'):
            timeout_duration = timedelta(days=int(duration_str[:-1]))
        else:
            await update.message.reply_text("Invalid duration format. Use 'm' for minutes, 'h' for hours, or 'd' for days (e.g., 1h for 1 hour).")
            return

        end_time = datetime.now() + timeout_duration
        data['blocked_users'].add(target_user_id)
        if target_user_id not in data['user_data']:
            data['user_data'][target_user_id] = {}
        data['user_data'][target_user_id]['timeout_end'] = end_time.isoformat()
        save_data()
        await update.message.reply_text(f"User with ID {target_user_id} has been timed out until {end_time}.")
        try:
            await context.bot.send_message(chat_id=target_user_id, text=f"You are timed out until {end_time}.")
        except Exception as e:
            logger.error(f"Failed to send timeout message to user {target_user_id}: {e}")
    except ValueError:
        await update.message.reply_text("Invalid user ID or duration format.")

async def remove_timeout(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This command is for admins only.")
        return

    target_user_id = int(context.args[0])
    if 'timeout_end' in data['user_data'].get(target_user_id, {}):
        del data['user_data'][target_user_id]['timeout_end']
    data['blocked_users'].discard(target_user_id)
    save_data()
    await update.message.reply_text(f"Timeout removed for user with ID {target_user_id}.")
    try:
        await context.bot.send_message(chat_id=target_user_id, text="Your timeout has been removed. You can use the bot again.")
    except Exception as e:
        logger.error(f"Failed to send timeout removal message to user {target_user_id}: {e}")

async def list_blocked(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This command is for admins only.")
        return

    if data['blocked_users']:
        blocked_list = "\n".join(str(user_id) for user_id in data['blocked_users'])
        await update.message.reply_text(f"Blocked Users:\n{blocked_list}")
    else:
        await update.message.reply_text("There are no users currently blocked from using the bot.")

async def add_section(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This command is for admins only.")
        return

    section_name = ' '.join(context.args)
    if not section_name:
        await update.message.reply_text("Please specify a section name.")
        return

    section_file = os.path.join(ACCOUNTS_DIR, f'{section_name}.txt')
    if not os.path.exists(section_file):
        open(section_file, 'w').close()
        data['account_types'].append(section_name)
        save_data()
        await update.message.reply_text(f"Section '{section_name}' has been added.")
    else:
        await update.message.reply_text(f"Section '{section_name}' already exists.")

async def delete_section(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This command is for admins only.")
        return

    section_name = ' '.join(context.args)
    if not section_name:
        await update.message.reply_text("Please specify a section name.")
        return

    section_file = os.path.join(ACCOUNTS_DIR, f'{section_name}.txt')
    if os.path.exists(section_file):
        os.remove(section_file)
        if section_name in data['account_types']:
            data['account_types'].remove(section_name)
            save_data()
        await update.message.reply_text(f"Section '{section_name}' has been deleted.")
    else:
        await update.message.reply_text(f"Section '{section_name}' does not exist.")

async def handle_upload_section(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This command is for admins only.")
        return

    await update.message.reply_text("Please specify the section name to add the accounts to:")
    context.user_data['awaiting_section_name'] = True

async def handle_owner_commands(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This menu is for admins only.")
        return

    if context.user_data.get('awaiting_section_name'):
        section_name = update.message.text.strip()
        section_file = os.path.join(ACCOUNTS_DIR, f'{section_name}.txt')

        if not section_file:
            await update.message.reply_text(f"Section '{section_name}' does not exist. Please create the section first.")
            return

        context.user_data['section_name'] = section_name
        await update.message.reply_text(f"Section '{section_name}' selected. Now, please upload the txt file with accounts:")
        context.user_data['awaiting_upload'] = True
        context.user_data['awaiting_section_name'] = False
    elif context.user_data.get('awaiting_reset_user_limit'):
        await update.message.reply_text("Please upload the txt file with accounts.")
    else:
        total_users, active_users = get_statistics()
        keyboard = [
            [InlineKeyboardButton("Block User", callback_data='block_user')],
            [InlineKeyboardButton("Unblock User", callback_data='unblock_user')],
            [InlineKeyboardButton("Timeout User", callback_data='timeout_user')],
            [InlineKeyboardButton("Remove Timeout", callback_data='remove_timeout')],
            [InlineKeyboardButton("List Blocked Users", callback_data='list_blocked')],
            [InlineKeyboardButton("Add Section", callback_data='add_section')],
            [InlineKeyboardButton("Delete Section", callback_data='delete_section')],
            [InlineKeyboardButton("Upload Accounts", callback_data='upload_accounts')],
            [InlineKeyboardButton("Free User Management", callback_data='free_user_management')],
            [InlineKeyboardButton("Premium User Management", callback_data='premium_user_management')],
            [InlineKeyboardButton("Premium Plus User Management", callback_data='premium_plus_user_management')],
            [InlineKeyboardButton("Enable Maintenance Mode", callback_data='enable_maintenance')],
            [InlineKeyboardButton("Disable Maintenance Mode", callback_data='disable_maintenance')],
            [InlineKeyboardButton("Add Admin", callback_data='add_admin')],
            [InlineKeyboardButton("Remove Admin", callback_data='remove_admin')],
            [InlineKeyboardButton("Monitoring", callback_data='monitoring')],
            [InlineKeyboardButton("View Sections", callback_data='view_sections')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f'Owner Commands:\nTotal Users: {total_users}\nActive Users: {active_users}', reply_markup=reply_markup)

async def handle_free_user_management(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Set Daily Limit", callback_data='set_daily_limit')],
        [InlineKeyboardButton("Set Unlimited Access", callback_data='set_unlimited_access')],
        [InlineKeyboardButton("Reset Free User Limits", callback_data='reset_all_free_limits')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text('Free User Management:', reply_markup=reply_markup)

async def handle_premium_user_management(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Add Premium User", callback_data='add_premium_user')],
        [InlineKeyboardButton("Remove Premium User", callback_data='remove_premium_user')],
        [InlineKeyboardButton("Set Premium Daily Limit", callback_data='set_premium_daily_limit')],
        [InlineKeyboardButton("Reset Premium User Limits", callback_data='reset_all_premium_limits')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text('Premium User Management:', reply_markup=reply_markup)

async def handle_premium_plus_user_management(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Add Premium Plus User", callback_data='add_premium_plus_user')],
        [InlineKeyboardButton("Remove Premium Plus User", callback_data='remove_premium_plus_user')],
        [InlineKeyboardButton("Set Premium Plus Daily Limit", callback_data='set_premium_plus_daily_limit')],
        [InlineKeyboardButton("Reset Premium Plus User Limits", callback_data='reset_all_premium_plus_limits')],
        [InlineKeyboardButton("Unlimited Access", callback_data='set_unlimited_access_premium_plus')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text('Premium Plus User Management:', reply_markup=reply_markup)

async def upload_accounts(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This command is for admins only.")
        return

    await update.message.reply_text("Please specify the section name to add the accounts to:")
    context.user_data['awaiting_section_name'] = True

async def handle_document(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("This command is for admins only.")
        return

    if context.user_data.get('awaiting_upload'):
        document = update.message.document
        section_name = context.user_data.get('section_name')

        if not section_name:
            await update.message.reply_text("No section specified. Please specify the section name first.")
            return

        section_file = os.path.join(ACCOUNTS_DIR, f'{section_name}.txt')
        if not os.path.exists(section_file):
            await update.message.reply_text(f"Section '{section_name}' does not exist.")
            return

        file_path = os.path.join(ACCOUNTS_DIR, f'temp_{user_id}.txt')
        new_file = await context.bot.get_file(document.file_id)
        await new_file.download_to_drive(file_path)

        with open(file_path, 'r', encoding='utf-8') as temp_file:
            accounts = temp_file.readlines()

        with open(section_file, 'a', encoding='utf-8') as section_file:
            section_file.writelines(accounts)

        os.remove(file_path)
        del context.user_data['section_name']
        context.user_data['awaiting_upload'] = False

        await update.message.reply_text(f"Accounts have been added to section '{section_name}'.")

# Function to show the custom menu
async def show_menu(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if data['maintenance_mode'] and not is_owner(user_id):
        await update.message.reply_text("The bot is currently under maintenance. Please try again later.")
        return
    if is_rate_limited(user_id):
        await update.message.reply_text("You are being rate limited. Please try again later.")
        return

    if user_id in data['premium_users']:
        await update.message.reply_text("You are a premium user. Please use the /premium command to access premium accounts.")
        return

    if user_id in data['premium_plus_users']:
        await update.message.reply_text("You are a premium plus user. Please use the /premium_plus command to access premium plus accounts.")
        return

    keyboard = [[InlineKeyboardButton(account_type, callback_data=f'get_account_{account_type}')] for account_type in data['account_types']]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose an option:', reply_markup=reply_markup)

# Function to show the premium menu
async def show_premium_menu(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if data['maintenance_mode'] and not is_owner(user_id):
        await update.message.reply_text("The bot is currently under maintenance. Please try again later.")
        return
    if is_rate_limited(user_id):
        await update.message.reply_text("You are being rate limited. Please try again later.")
        return

    keyboard = [[InlineKeyboardButton(account_type, callback_data=f'get_premium_account_{account_type}')] for account_type in data['account_types']]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose a premium account type:', reply_markup=reply_markup)

# Function to show the premium plus menu
async def show_premium_plus_menu(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if data['maintenance_mode'] and not is_owner(user_id):
        await update.message.reply_text("The bot is currently under maintenance. Please try again later.")
        return
    if is_rate_limited(user_id):
        await update.message.reply_text("You are being rate limited. Please try again later.")
        return

    keyboard = [[InlineKeyboardButton(account_type, callback_data=f'get_premium_plus_account_{account_type}')] for account_type in data['account_types']]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text=f'Welcome {update.message.from_user.mention_html()}! This is the premium plus section. Please choose a premium plus account type:', reply_markup=reply_markup, parse_mode=ParseMode.HTML)

# Function to show the feedback menu
async def show_feedback_menu(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if data['maintenance_mode'] and not is_owner(user_id):
        await update.message.reply_text("The bot is currently under maintenance. Please try again later.")
        return
    if is_rate_limited(user_id):
        await update.message.reply_text("You are being rate limited. Please try again later.")
        return

    keyboard = [
        [InlineKeyboardButton("Report Issue", callback_data='report_issue')],
        [InlineKeyboardButton("Give Feedback", callback_data='give_feedback')],
        [InlineKeyboardButton("Submit Recommendation", callback_data='submit_recommendation')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose an option:', reply_markup=reply_markup)

async def handle_menu_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    choice = query.data

    user_id = query.from_user.id

    timeout_end = is_blocked(user_id)
    if timeout_end:
        await query.edit_message_text(f"You are currently in timeout until {timeout_end}. Please try again later.")
        return

    global data
    if data['maintenance_mode'] and not is_owner(user_id):
        await query.message.reply_text("The bot is currently under maintenance. Please try again later.")
        return

    if not is_admin(user_id) and choice in ['block_user', 'unblock_user', 'timeout_user', 'remove_timeout', 'list_blocked', 'add_section', 'delete_section', 'upload_accounts', 'set_daily_limit', 'set_unlimited_access', 'reset_all_free_limits', 'reset_all_premium_limits', 'reset_all_premium_plus_limits', 'enable_maintenance', 'disable_maintenance', 'free_user_management', 'premium_user_management', 'premium_plus_user_management', 'add_premium_user', 'remove_premium_user', 'set_premium_daily_limit', 'add_premium_plus_user', 'remove_premium_plus_user', 'set_premium_plus_daily_limit', 'set_unlimited_access_premium_plus', 'add_admin', 'remove_admin', 'monitoring', 'view_sections']:
        await query.message.reply_text("You do not have the necessary permissions to access this command.")
        return

    if choice == 'monitoring':
        total_users, active_users = get_statistics()
        await query.message.reply_text(f'Monitoring:\nTotal Users: {total_users}\nActive Users: {active_users}')
    elif choice == 'view_sections':
        await view_sections(update, context)
    elif choice.startswith('get_account_'):
        account_type = choice.split('get_account_')[1]
        username = query.from_user.username

        daily_limit_count = check_daily_limit(user_id)
        if user_id not in data['premium_users'] and user_id not in data['premium_plus_users'] and daily_limit_count >= data['daily_limit'] and not data['unlimited_access']:
            last_access_time, _ = data['user_daily_limits'][user_id]
            next_access_time = last_access_time + timedelta(days=(1))
            await query.message.reply_text(f"You have reached your daily limit. You can use the bot again at {next_access_time.strftime('%Y-%m-%d %H:%M:%S')}.")
            return
        elif user_id in data['premium_users'] and daily_limit_count >= data['premium_daily_limit']:
            await query.message.reply_text("You have reached your daily limit for premium requests. Please try again tomorrow.")
            return
        elif user_id in data['premium_plus_users'] and daily_limit_count >= data['premium_plus_daily_limit']:
            await query.message.reply_text("You have reached your daily limit for premium plus requests. Please try again tomorrow.")
            return

        account = get_next_account(account_type)
        if account:
            parsed_info = parse_account_info(account, account_type)
            await query.message.reply_text(f"Account Info:\n{parsed_info}\nAccount Type: {account_type}")
            await query.message.reply_text(
                f"Thank you for using the bot. Here is your account information:\n{query.from_user.first_name}!\n"
                "Check out our main channel: https://t.me/S_D_C_D"
            )
            increment_daily_limit(user_id)
            update_user_data(user_id, username)
        else:
            await query.edit_message_text(f"No accounts available for {account_type}.")
    elif choice.startswith('get_premium_account_'):
        if user_id not in data['premium_users'] and not is_owner(user_id):
            await query.message.reply_text("You do not have access to this section.")
            return

        account_type = choice.split('get_premium_account_')[1]
        username = query.from_user.username

        daily_limit_count = check_daily_limit(user_id)
        if daily_limit_count >= data['premium_daily_limit']:
            await query.message.reply_text("You have reached your daily limit for premium requests. Please try again tomorrow.")
            return

        account = get_next_account(account_type)
        if account:
            parsed_info = parse_account_info(account, account_type)
            await query.message.reply_text(f"Premium Account Info:\n{parsed_info}\nAccount Type: {account_type}")
            await query.message.reply_text(
                f"Thank you for using the premium section. Here is your account information:\n{query.from_user.first_name}!\n"
                "Check out our main channel: https://t.me/S_D_C_D"
            )
            increment_daily_limit(user_id)
            update_user_data(user_id, username)
        else:
            await query.edit_message_text(f"No premium accounts available for {account_type}.")
    elif choice.startswith('get_premium_plus_account_'):
        if user_id not in data['premium_plus_users'] and not is_owner(user_id):
            await query.message.reply_text("You do not have access to this section.")
            return

        account_type = choice.split('get_premium_plus_account_')[1]
        username = query.from_user.username

        daily_limit_count = check_daily_limit(user_id)
        if daily_limit_count >= data['premium_plus_daily_limit']:
            await query.message.reply_text("You have reached your daily limit for premium plus requests. Please try again tomorrow.")
            return

        account = get_next_account(account_type)
        if account:
            parsed_info = parse_account_info(account, account_type)
            await query.message.reply_text(f"Premium Plus Account Info:\n{parsed_info}\nAccount Type: {account_type}")
            await query.message.reply_text(
                f"Thank you for using the premium plus section. Here is your account information:\n{query.from_user.first_name}!\n"
                "Check out our main channel: https://t.me/S_D_C_D"
            )
            increment_daily_limit(user_id)
            update_user_data(user_id, username)
        else:
            await query.edit_message_text(f"No premium plus accounts available for {account_type}.")
    elif choice == 'premium_plus':
        await premium_plus(update, context)
    elif choice == 'premium':
        await premium(update, context)
    elif choice == 'report_issue':
        await query.message.reply_text("Please describe the issue you are facing:")
        context.user_data['awaiting_issue'] = True
    elif choice == 'give_feedback':
        await query.message.reply_text("Please provide your feedback:")
        context.user_data['awaiting_feedback'] = True
    elif choice == 'submit_recommendation':
        await query.message.reply_text("Please provide your recommendation:")
        context.user_data['awaiting_recommendation'] = True
    elif choice == 'block_user':
        await query.message.reply_text("Please enter the user ID to block:")
        context.user_data['awaiting_block_user_id'] = True
    elif choice == 'unblock_user':
        await query.message.reply_text("Please enter the user ID to unblock:")
        context.user_data['awaiting_unblock_user_id'] = True
    elif choice == 'timeout_user':
        await query.message.reply_text("Please enter the user ID and duration (e.g., 12345 1h for 1 hour timeout):")
        context.user_data['awaiting_timeout_user'] = True
    elif choice == 'remove_timeout':
        await query.message.reply_text("Please enter the user ID to remove the timeout:")
        context.user_data['awaiting_remove_timeout_user'] = True
    elif choice == 'list_blocked':
        if data['blocked_users']:
            blocked_list = "\n".join(str(user_id) for user_id in data['blocked_users'])
            await query.message.reply_text(f"Blocked Users:\n{blocked_list}")
        else:
            await query.message.reply_text("There are no users currently blocked from using the bot.")
    elif choice == 'add_section':
        await query.message.reply_text("Please enter the name of the new section:")
        context.user_data['awaiting_add_section'] = True
    elif choice == 'delete_section':
        await query.message.reply_text("Please enter the name of the section to delete:")
        context.user_data['awaiting_delete_section'] = True
    elif choice == 'upload_accounts':
        await query.message.reply_text("Please specify the section name to add the accounts to:")
        context.user_data['awaiting_section_name'] = True
    elif choice == 'set_daily_limit':
        await query.message.reply_text("Please enter the new daily limit for free users:")
        context.user_data['awaiting_daily_limit'] = True
    elif choice == 'set_unlimited_access':
        await query.message.reply_text("Please enter 'on' to enable unlimited access or 'off' to disable unlimited access:")
        context.user_data['awaiting_unlimited_access'] = True
    elif choice == 'reset_all_free_limits':
        reset_all_free_limits()
        await query.message.reply_text("All free user daily limits have been reset.")
    elif choice == 'reset_all_premium_limits':
        reset_all_premium_limits()
        await query.message.reply_text("All premium user daily limits have been reset.")
    elif choice == 'reset_all_premium_plus_limits':
        reset_all_premium_plus_limits()
        await query.message.reply_text("All premium plus user daily limits have been reset.")
    elif choice == 'enable_maintenance':
        data['maintenance_mode'] = True
        save_data()
        await query.message.reply_text("The bot is now in maintenance mode.")
        # Notify all users about maintenance mode
        for user_id in data['user_data'].keys():
            if user_id != OWNER_ID:
                try:
                    await bot.send_message(chat_id=user_id, text="The bot is currently under maintenance. Please try again later.")
                except Exception as e:
                    logger.error(f"Failed to send maintenance message to user {user_id}: {e}")
    elif choice == 'disable_maintenance':
        data['maintenance_mode'] = False
        save_data()
        await query.message.reply_text("The bot is now out of maintenance mode.")
        # Notify all users about end of maintenance mode
        for user_id in data['user_data'].keys():
            if user_id != OWNER_ID:
                try:
                    await bot.send_message(chat_id=user_id, text="The bot is now available. You can use it again.")
                except Exception as e:
                    logger.error(f"Failed to send availability message to user {user_id}: {e}")
    elif choice == 'free_user_management':
        await handle_free_user_management(update, context)
    elif choice == 'premium_user_management':
        await handle_premium_user_management(update, context)
    elif choice == 'premium_plus_user_management':
        await handle_premium_plus_user_management(update, context)
    elif choice == 'add_premium_user':
        await query.message.reply_text("Please enter the user ID to add as premium:")
        context.user_data['awaiting_add_premium_user'] = True
    elif choice == 'remove_premium_user':
        await query.message.reply_text("Please enter the user ID to remove from premium:")
        context.user_data['awaiting_remove_premium_user'] = True
    elif choice == 'set_premium_daily_limit':
        await query.message.reply_text("Please enter the new daily limit for premium users:")
        context.user_data['awaiting_set_premium_daily_limit'] = True
    elif choice == 'add_premium_plus_user':
        await query.message.reply_text("Please enter the user ID to add as premium plus:")
        context.user_data['awaiting_add_premium_plus_user'] = True
    elif choice == 'remove_premium_plus_user':
        await query.message.reply_text("Please enter the user ID to remove from premium plus:")
        context.user_data['awaiting_remove_premium_plus_user'] = True
    elif choice == 'set_premium_plus_daily_limit':
        await query.message.reply_text("Please enter the new daily limit for premium plus users:")
        context.user_data['awaiting_set_premium_plus_daily_limit'] = True
    elif choice == 'set_unlimited_access_premium_plus':
        await query.message.reply_text("Please enter 'on' to enable unlimited access for premium plus users or 'off' to disable unlimited access:")
        context.user_data['awaiting_unlimited_access_premium_plus'] = True
    elif choice == 'add_admin':
        await query.message.reply_text("Please enter the user ID to add as admin:")
        context.user_data['awaiting_add_admin'] = True
    elif choice == 'remove_admin':
        await query.message.reply_text("Please enter the user ID to remove from admin:")
        context.user_data['awaiting_remove_admin'] = True

async def handle_user_input(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    update_last_activity(user_id)
    log_activity(update)
    if detect_unusual_activity(user_id):
        data['blocked_users'].add(user_id)
        save_data()
        reason = "Unusual activity detected"
        await context.bot.send_message(chat_id=OWNER_ID, text=f"User with ID {user_id} has been blocked.\nReason: {reason}")
        await update.message.reply_text("Suspicious activity detected. You have been blocked. The owner has been notified.")
        return

    timeout_end = is_blocked(user_id)
    if timeout_end:
        await update.message.reply_text(f"You are currently in timeout until {timeout_end}. Please try again later.")
        return

    if data['maintenance_mode'] and not is_admin(user_id):
        await update.message.reply_text("The bot is currently under maintenance. Please try again later.")
        return

    if context.user_data.get('awaiting_block_user_id'):
        target_user_id = int(text)
        data['blocked_users'].add(target_user_id)
        save_data()
        context.user_data['awaiting_block_user_id'] = False
        await update.message.reply_text(f"User with ID {target_user_id} has been blocked.")
        try:
            await context.bot.send_message(chat_id=target_user_id, text="You have been blocked by the bot.")
        except Exception as e:
            logger.error(f"Failed to send block message to user {target_user_id}: {e}")
    elif context.user_data.get('awaiting_unblock_user_id'):
        target_user_id = int(text)
        data['blocked_users'].discard(target_user_id)
        save_data()
        context.user_data['awaiting_unblock_user_id'] = False
        await update.message.reply_text(f"User with ID {target_user_id} has been unblocked.")
        try:
            await context.bot.send_message(chat_id=target_user_id, text="Your block has been removed. You can use the bot again.")
        except Exception as e:
            logger.error(f"Failed to send unblock message to user {target_user_id}: {e}")
    elif context.user_data.get('awaiting_timeout_user'):
        try:
            target_user_id, duration_str = text.split()
            target_user_id = int(target_user_id)
            if duration_str.endswith('m'):
                timeout_duration = timedelta(minutes=int(duration_str[:-1]))
            elif duration_str.endswith('h'):
                timeout_duration = timedelta(hours=int(duration_str[:-1]))
            elif duration_str.endswith('d'):
                timeout_duration = timedelta(days=int(duration_str[:-1]))
            else:
                await update.message.reply_text("Invalid duration format. Use 'm' for minutes, 'h' for hours, or 'd' for days (e.g., 1h for 1 hour).")
                return

            end_time = datetime.now() + timeout_duration
            data['blocked_users'].add(target_user_id)
            if target_user_id not in data['user_data']:
                data['user_data'][target_user_id] = {}
            data['user_data'][target_user_id]['timeout_end'] = end_time.isoformat()
            save_data()
            await update.message.reply_text(f"User with ID {target_user_id} has been timed out until {end_time}.")
            try:
                await context.bot.send_message(chat_id=target_user_id, text=f"You are timed out until {end_time}.")
            except Exception as e:
                logger.error(f"Failed to send timeout message to user {target_user_id}: {e}")
        except ValueError:
            await update.message.reply_text("Invalid input. Please provide user ID and duration (e.g., 12345 1h).")
        context.user_data['awaiting_timeout_user'] = False
    elif context.user_data.get('awaiting_remove_timeout_user'):
        target_user_id = int(text)
        if 'timeout_end' in data['user_data'].get(target_user_id, {}):
            del data['user_data'][target_user_id]['timeout_end']
        data['blocked_users'].discard(target_user_id)
        save_data()
        context.user_data['awaiting_remove_timeout_user'] = False
        await update.message.reply_text(f"Timeout removed for user with ID {target_user_id}.")
        try:
            await context.bot.send_message(chat_id=target_user_id, text="Your timeout has been removed. You can use the bot again.")
        except Exception as e:
            logger.error(f"Failed to send timeout removal message to user {target_user_id}: {e}")
    elif context.user_data.get('awaiting_add_section'):
        section_name = text.strip()
        section_file = os.path.join(ACCOUNTS_DIR, f'{section_name}.txt')
        if not os.path.exists(section_file):
            open(section_file, 'w').close()
            data['account_types'].append(section_name)
            save_data()
            await update.message.reply_text(f"Section '{section_name}' has been added.")
        else:
            await update.message.reply_text(f"Section '{section_name}' already exists.")
        context.user_data['awaiting_add_section'] = False
    elif context.user_data.get('awaiting_delete_section'):
        section_name = text.strip()
        section_file = os.path.join(ACCOUNTS_DIR, f'{section_name}.txt')
        if os.path.exists(section_file):
            os.remove(section_file)
            if section_name in data['account_types']:
                data['account_types'].remove(section_name)
                save_data()
            await update.message.reply_text(f"Section '{section_name}' has been deleted.")
        else:
            await update.message.reply_text(f"Section '{section_name}' does not exist.")
        context.user_data['awaiting_delete_section'] = False
    elif context.user_data.get('awaiting_section_name'):
        section_name = text.strip()
        context.user_data['section_name'] = section_name
        await update.message.reply_text(f"Section '{section_name}' selected. Now, please upload the txt file with accounts:")
        context.user_data['awaiting_upload'] = True
    elif context.user_data.get('awaiting_daily_limit'):
        data['daily_limit'] = int(text)
        save_data()
        await update.message.reply_text(f"Daily limit for free users set to {data['daily_limit']} accounts per day.")
        context.user_data['awaiting_daily_limit'] = False
    elif context.user_data.get('awaiting_unlimited_access'):
        if text.lower() == 'on':
            data['unlimited_access'] = True
            await update.message.reply_text("Unlimited access enabled.")
        elif text.lower() == 'off':
            data['unlimited_access'] = False
            await update.message.reply_text("Unlimited access disabled.")
        else:
            await update.message.reply_text("Invalid input. Please enter 'on' or 'off'.")
        save_data()
        context.user_data['awaiting_unlimited_access'] = False
    elif context.user_data.get('awaiting_reset_user_limit'):
        target_user_id = int(text)
        reset_user_limit(target_user_id)
        context.user_data['awaiting_reset_user_limit'] = False
        await update.message.reply_text(f"Daily limit for user with ID {target_user_id} has been reset.")
    elif context.user_data.get('awaiting_issue'):
        issue = text.strip()
        report_bot = Bot(token=REPORT_BOT_TOKEN)
        await report_bot.send_message(chat_id=OWNER_ID, text=f"Issue Report from User ID {user_id}:\n{issue}")
        context.user_data['awaiting_issue'] = False
        await update.message.reply_text("Thank you for reporting the issue. It has been forwarded to the support team.")
    elif context.user_data.get('awaiting_feedback'):
        feedback = text.strip()
        feedback_bot = Bot(token=FEEDBACK_BOT_TOKEN)
        await feedback_bot.send_message(chat_id=OWNER_ID, text=f"Feedback from User ID {user_id}:\n{feedback}")
        context.user_data['awaiting_feedback'] = False
        await update.message.reply_text("Thank you for your feedback. It has been forwarded to the team.")
    elif context.user_data.get('awaiting_add_premium_user'):
        target_user_id = int(text)
        data['premium_users'].add(target_user_id)
        reset_user_limit(target_user_id)  # Reset limit when user is added to premium
        save_data()
        context.user_data['awaiting_add_premium_user'] = False
        await update.message.reply_text(f"User with ID {target_user_id} has been added as premium.")
    elif context.user_data.get('awaiting_reset_user_limit'):
        target_user_id = int(text)
        data['premium_users'].discard(target_user_id)
        reset_user_limit(target_user_id)  # Reset limit when user is removed from premium
        save_data()
        context.user_data['awaiting_remove_premium_user'] = False
        await update.message.reply_text(f"User with ID {target_user_id} has been removed from premium.")
    elif context.user_data.get('awaiting_set_premium_daily_limit'):
        data['premium_daily_limit'] = int(text)
        save_data()
        context.user_data['awaiting_set_premium_daily_limit'] = False
        await update.message.reply_text(f"Premium daily limit set to {data['premium_daily_limit']} accounts per day.")
    elif context.user_data.get('awaiting_add_premium_plus_user'):
        target_user_id = int(text)
        data['premium_plus_users'].add(target_user_id)
        reset_user_limit(target_user_id)  # Reset limit when user is added to premium plus
        save_data()
        context.user_data['awaiting_add_premium_plus_user'] = False
        await update.message.reply_text(f"User with ID {target_user_id} has been added as premium plus.")
    elif context.user_data.get('awaiting_remove_premium_plus_user'):
        target_user_id = int(text)
        data['premium_plus_users'].discard(target_user_id)
        reset_user_limit(target_user_id)  # Reset limit when user is removed from premium plus
        save_data()
        context.user_data['awaiting_remove_premium_plus_user'] = False
        await update.message.reply_text(f"User with ID {target_user_id} has been removed from premium plus.")
    elif context.user_data.get('awaiting_set_premium_plus_daily_limit'):
        data['premium_plus_daily_limit'] = int(text)
        save_data()
        context.user_data['awaiting_set_premium_plus_daily_limit'] = False
        await update.message.reply_text(f"Premium plus daily limit set to {data['premium_plus_daily_limit']} accounts per day.")
    elif context.user_data.get('awaiting_unlimited_access_premium_plus'):
        if text.lower() == 'on':
            data['unlimited_access_premium_plus'] = True
            await update.message.reply_text("Unlimited access for premium plus users enabled.")
        elif text.lower() == 'off':
            data['unlimited_access_premium_plus'] = False
            await update.message.reply_text("Unlimited access for premium plus users disabled.")
        else:
            await update.message.reply_text("Invalid input. Please enter 'on' or 'off'.")
        save_data()
        context.user_data['awaiting_unlimited_access_premium_plus'] = False
    elif context.user_data.get('awaiting_add_admin'):
        target_user_id = int(text)
        if target_user_id == OWNER_ID:
            await update.message.reply_text("Cannot add the owner as admin.")
        else:
            data['admins'].add(target_user_id)
            save_data()
            context.user_data['awaiting_add_admin'] = False
            await update.message.reply_text(f"User with ID {target_user_id} has been added as admin.")
    elif context.user_data.get('awaiting_remove_admin'):
        target_user_id = int(text)
        if target_user_id == OWNER_ID:
            await update.message.reply_text("Cannot remove the owner from admin.")
        else:
            data['admins'].discard(target_user_id)
            save_data()
            context.user_data['awaiting_remove_admin'] = False
            await update.message.reply_text(f"User with ID {target_user_id} has been removed from admin.")
    elif context.user_data.get('awaiting_recommendation'):
        recommendation = text.strip()
        recommendation_bot = Bot(token=RECOMMENDATION_BOT_TOKEN)
        await recommendation_bot.send_message(chat_id=OWNER_ID, text=f"Recommendation from User ID {user_id}:\n{recommendation}")
        context.user_data['awaiting_recommendation'] = False
        await update.message.reply_text("Thank you for your recommendation. It has been forwarded to the team.")

async def view_sections(update: Update, context: CallbackContext):
    query = update.callback_query
    sections = data['account_types']
    if sections:
        sections_list = "\n".join(f"{section}: {count_accounts(section)} accounts" for section in sections)
        await query.message.reply_text(f"Available Sections:\n{sections_list}")
    else:
        await query.message.reply_text("No sections available.")

def count_accounts(section_name):
    section_file = os.path.join(ACCOUNTS_DIR, f'{section_name}.txt')
    if os.path.exists(section_file):
        with open(section_file, 'r', encoding='utf-8') as file:
            return len(file.readlines())
    return 0

async def handle_button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    choice = query.data

    user_id = query.from_user.id
    timeout_end = is_blocked(user_id)
    if timeout_end:
        await query.message.reply_text(f"You are currently in timeout until {timeout_end}. Please try again later.")
        return

    if data['maintenance_mode'] and not is_owner(user_id):
        await query.message.reply_text("The bot is currently under maintenance. Please try again later.")
        return

    if choice == 'block_user':
        await block_user(update, context)
    elif choice == 'unblock_user':
        await unblock_user(update, context)
    elif choice == 'timeout_user':
        await timeout_user(update, context)
    elif choice == 'remove_timeout':
        await remove_timeout(update, context)
    elif choice == 'list_blocked':
        await list_blocked(update, context)
    elif choice == 'add_section':
        await add_section(update, context)
    elif choice == 'delete_section':
        await delete_section(update, context)
    elif choice == 'upload_accounts':
        await handle_upload_section(update, context)
    elif choice == 'free_user_management':
        await handle_free_user_management(update, context)
    elif choice == 'premium_user_management':
        await handle_premium_user_management(update, context)
    elif choice == 'premium_plus_user_management':
        await handle_premium_plus_user_management(update, context)
    elif choice == 'enable_maintenance':
        data['maintenance_mode'] = True
        save_data()
        await query.message.reply_text("The bot is now in maintenance mode.")
    elif choice == 'disable_maintenance':
        data['maintenance_mode'] = False
        save_data()
        await query.message.reply_text("The bot is now out of maintenance mode.")
    elif choice == 'add_admin':
        await query.message.reply_text("Please enter the user ID to add as admin:")
        context.user_data['awaiting_add_admin'] = True
    elif choice == 'remove_admin':
        await query.message.reply_text("Please enter the user ID to remove from admin:")
        context.user_data['awaiting_remove_admin'] = True
    elif choice == 'view_sections':
        await view_sections(update, context)

def main():
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('premium', premium))
    application.add_handler(CommandHandler('premium_plus', premium_plus))
    application.add_handler(CommandHandler('feedbackmenu', show_feedback_menu))
    application.add_handler(CommandHandler('ownermenu', handle_owner_commands))
    application.add_handler(CommandHandler('free', show_menu))

    # Register message handler for user input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    # Register handler for callback queries
    application.add_handler(CallbackQueryHandler(handle_menu_choice))

    # Register handler for button clicks
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # Register handler for document uploads
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    ensure_directories_and_files()
    main()
