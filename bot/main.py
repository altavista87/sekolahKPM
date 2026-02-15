"""Main Telegram Bot Application."""

import logging
import asyncio
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, assume env vars are set externally

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from .config import BotConfig
from .ocr_engine import OCREngine, AdvancedOCREngine
from .ai_processor import AIProcessor
from .handlers import (
    OnboardingHandler,
    HomeworkHandler,
    ParentHandler,
    TeacherHandler,
    ReminderHandler,
)
from .models import UserRole
from .logging_config import setup_secure_logging
from .image_utils import check_heic_support

# Configure secure logging with token redaction
setup_secure_logging(logging.INFO)
logger = logging.getLogger(__name__)

# Log HEIC support status
if check_heic_support():
    logger.info("✅ HEIC image support enabled")
else:
    logger.warning("⚠️ HEIC support disabled - install pillow-heif for iPhone photo support")


class EduSyncBot:
    """Main Telegram Bot class."""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.application: Optional[Application] = None
        
        # Initialize components - use Advanced OCR with ensemble support
        self.ocr = AdvancedOCREngine(
            tesseract_cmd=config.tesseract_cmd,
            ocr_language=config.ocr_language,
            use_easyocr=True,
            use_tesseract=True,
            gpu=config.easyocr_gpu,
            # Vision LLM APIs
            together_api_key=config.together_api_key,
            together_model=config.together_vision_model,
            gemini_api_key=config.gemini_api_key,
            gemini_model=config.gemini_model,
            deepseek_api_key=config.deepseek_api_key,
            # Advanced settings
            preferred_mode=config.ocr_preferred_mode,
            enable_ensemble=config.ocr_enable_ensemble,
        )
        
        self.ai = None
        if config.enable_ai_enhancement:
            # Try OpenAI first, fallback to Gemini
            if config.openai_api_key:
                self.ai = AIProcessor(
                    api_key=config.openai_api_key,
                    model=config.openai_model,
                    max_tokens=config.openai_max_tokens,
                    temperature=config.openai_temperature,
                    provider="openai",
                )
                logger.info("Using OpenAI for AI enhancement")
            elif config.gemini_api_key:
                self.ai = AIProcessor(
                    api_key=config.gemini_api_key,
                    model=config.gemini_model,
                    provider="gemini",
                )
                logger.info("Using Gemini for AI enhancement")
        
        # Initialize handlers
        self.onboarding_handler = OnboardingHandler(self.ocr, self.ai)
        self.homework_handler = HomeworkHandler(self.ocr, self.ai)
        self.parent_handler = ParentHandler(self.ocr, self.ai)
        self.teacher_handler = TeacherHandler(self.ocr, self.ai)
        self.reminder_handler = ReminderHandler(self.ocr, self.ai)
    
    def setup(self):
        """Setup the bot application."""
        self.application = Application.builder().token(self.config.bot_token).build()
        
        # Register command handlers
        self._register_commands()
        
        # Register message handlers
        self._register_messages()
        
        # Register callback handlers
        self._register_callbacks()
        
        # Register error handler
        self.application.add_error_handler(self._error_handler)
        
        logger.info("Bot setup complete")
    
    def _register_commands(self):
        """Register command handlers."""
        # Universal commands
        self.application.add_handler(CommandHandler("start", self.onboarding_handler.cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("switch_role", self.onboarding_handler.cmd_switch_role))
        
        # Parent commands
        self.application.add_handler(CommandHandler("homework", self._route_homework))
        self.application.add_handler(CommandHandler("reminders", self._route_reminders))
        
        # Teacher commands
        self.application.add_handler(CommandHandler("post", self.teacher_handler.cmd_post_homework))
        self.application.add_handler(CommandHandler("classes", self.teacher_handler.cmd_my_classes))
        self.application.add_handler(CommandHandler("overview", self.teacher_handler.cmd_class_overview))
        self.application.add_handler(CommandHandler("notify", self.teacher_handler.cmd_send_notification))
        
        # Common commands
        self.application.add_handler(CommandHandler("settings", self._cmd_settings))
        self.application.add_handler(CommandHandler("cancel", self._cmd_cancel))
    
    def _register_messages(self):
        """Register message handlers."""
        # Photo handler - routes to teacher or parent flow
        self.application.add_handler(
            MessageHandler(filters.PHOTO, self.homework_handler.handle_photo)
        )
        
        # Document handler
        self.application.add_handler(
            MessageHandler(filters.Document.ALL, self._handle_document)
        )
        
        # Text handler
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text)
        )
    
    def _register_callbacks(self):
        """Register callback query handlers."""
        self.application.add_handler(
            CallbackQueryHandler(self._callback_router)
        )
    
    async def _callback_router(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route callback queries to appropriate handlers."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = update.effective_user
        
        # Role selection
        if data in ["role_parent", "role_teacher"]:
            await self.onboarding_handler.handle_role_selection(update, context)
            return
        
        # Get user role for routing
        role = await self.onboarding_handler.get_user_role(user.id, context)
        
        # Universal callbacks
        if data == "cancel":
            await self._handle_cancel(update, context, role)
        elif data == "main_menu":
            await self._show_main_menu(update, context, role)
        elif data == "settings":
            await self._cmd_settings(update, context)
        
        # Parent-specific callbacks
        elif data == "submit_hw":
            await query.edit_message_text(
                "📸 Please send me a photo of your child's homework.",
                reply_markup=None,
            )
        elif data == "list_hw":
            await self.parent_handler.cmd_homework(update, context)
        elif data == "my_children":
            await self._handle_my_children(update, context)
        elif data == "reminders":
            await self.parent_handler.cmd_reminders(update, context)
        elif data == "save_hw_parent":
            await self._handle_save_homework_parent(update, context)
        elif data == "edit_hw":
            await self._handle_edit_homework(update, context)
        
        # Teacher-specific callbacks
        elif data == "post_hw":
            await self.teacher_handler.cmd_post_homework(update, context)
        elif data == "my_classes":
            await self.teacher_handler.cmd_my_classes(update, context)
        elif data == "class_overview":
            await self.teacher_handler.cmd_class_overview(update, context)
        elif data == "send_reminder":
            await self.teacher_handler.cmd_send_notification(update, context)
        elif data.startswith("post_class_"):
            class_id = data.replace("post_class_", "")
            await self.teacher_handler.post_homework_to_class(update, context, class_id)
        elif data.startswith("class_"):
            class_id = data.replace("class_", "")
            await self._handle_class_selection(update, context, class_id)
        elif data == "add_class":
            await self._handle_add_class(update, context)
        elif data == "edit_post":
            await self._handle_edit_post(update, context)
        
        # Reminder settings
        elif data.startswith("remind_"):
            await self._handle_reminder_setting(update, context, data)
        
        # Edit callbacks
        elif data.startswith("edit_") and data not in ["edit_hw", "edit_post"]:
            field = data.replace("edit_", "")
            await self.homework_handler.handle_edit_callback(update, context, field)
        
        # Settings callbacks  
        elif data == "set_language":
            from .settings_handlers import SettingsHandler
            settings_handler = SettingsHandler()
            await settings_handler.handle_language_setting(update, context)
        elif data.startswith("lang_"):
            lang = data.replace("lang_", "")
            from .settings_handlers import SettingsHandler
            settings_handler = SettingsHandler()
            await settings_handler.save_setting(update, context, "lang", lang)
        elif data == "set_notifications":
            from .settings_handlers import SettingsHandler
            settings_handler = SettingsHandler()
            await settings_handler.handle_notification_setting(update, context)
        elif data.startswith("notif_"):
            notif_type = data.replace("notif_", "")
            from .settings_handlers import SettingsHandler
            settings_handler = SettingsHandler()
            await settings_handler.save_setting(update, context, "notif", notif_type)
        elif data == "set_timezone":
            from .settings_handlers import SettingsHandler
            settings_handler = SettingsHandler()
            await settings_handler.handle_timezone_setting(update, context)
        elif data.startswith("tz_"):
            tz = data.replace("tz_", "")
            from .settings_handlers import SettingsHandler
            settings_handler = SettingsHandler()
            await settings_handler.save_setting(update, context, "tz", tz)
        elif data == "manage_children":
            await self._handle_manage_children(update, context)
        elif data == "teacher_profile":
            await self._handle_teacher_profile(update, context)
        elif data == "link_whatsapp":
            await self._handle_link_whatsapp(update, context)

        # Add child flow
        elif data == "add_child":
            await self.parent_handler.cmd_add_child(update, context)

        # Cancel edit
        elif data == "cancel_edit":
            context.user_data.pop("editing_field", None)
            context.user_data.pop("editing_homework", None)
            await query.edit_message_text(
                "❌ Edit cancelled.",
                reply_markup=self.onboarding_handler.get_main_menu(
                    await self.onboarding_handler.get_user_role(user.id, context)
                )
            )
        
        else:
            await query.edit_message_text(
                f"Unknown action: {data}",
                reply_markup=self.onboarding_handler.get_main_menu(role),
            )
    
    async def _route_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route /homework command based on user role."""
        user = update.effective_user
        role = await self.onboarding_handler.get_user_role(user.id, context)
        
        if role == UserRole.TEACHER:
            await self.teacher_handler.cmd_class_overview(update, context)
        else:
            await self.parent_handler.cmd_homework(update, context)
    
    async def _route_reminders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route /reminders command based on user role."""
        user = update.effective_user
        role = await self.onboarding_handler.get_user_role(user.id, context)
        
        if role == UserRole.TEACHER:
            await self.teacher_handler.cmd_send_notification(update, context)
        else:
            await self.parent_handler.cmd_reminders(update, context)
    
    async def _handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE, role: UserRole):
        """Handle cancel callback - preserves essential user data."""
        query = update.callback_query
        
        # Preserve essential user data
        essential_keys = ["role", "onboarded", "user_id"]
        preserved = {k: context.user_data.get(k) for k in essential_keys if k in context.user_data}
        
        # Clear temporary/state data
        context.user_data.clear()
        
        # Restore essential data
        context.user_data.update(preserved)
        
        await query.edit_message_text(
            "❌ Cancelled. What would you like to do?",
            reply_markup=self.onboarding_handler.get_main_menu(role),
        )
    
    async def _show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, role: UserRole):
        """Show main menu."""
        query = update.callback_query
        await query.edit_message_text(
            "What would you like to do?",
            reply_markup=self.onboarding_handler.get_main_menu(role),
        )
    
    async def _handle_my_children(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle my children callback."""
        query = update.callback_query
        await query.edit_message_text(
            "👨‍👩‍👧 <b>My Children</b>\n\n"
            "No children added yet.\n\n"
            "Use /add_child to add your children.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Child", callback_data="add_child")],
                [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
            ]),
            parse_mode="HTML",
        )
    
    async def _handle_save_homework_parent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle save homework for parent."""
        query = update.callback_query
        await query.edit_message_text(
            "✅ Homework saved! You'll receive reminders before the due date.",
            reply_markup=self.onboarding_handler.get_main_menu(UserRole.PARENT),
        )
    
    async def _handle_edit_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle edit homework callback."""
        query = update.callback_query
        await query.edit_message_text(
            "✏️ <b>Edit Homework</b>\n\n"
            "What would you like to edit?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Subject", callback_data="edit_subject")],
                [InlineKeyboardButton("Title", callback_data="edit_title")],
                [InlineKeyboardButton("Due Date", callback_data="edit_due_date")],
                [InlineKeyboardButton("Description", callback_data="edit_description")],
                [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
            ]),
            parse_mode="HTML",
        )
    
    async def _handle_class_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, class_id: str):
        """Handle class selection."""
        query = update.callback_query
        await query.edit_message_text(
            f"📚 <b>Class {class_id.upper()}</b>\n\n"
            f"Select an action:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Post Homework", callback_data="post_hw")],
                [InlineKeyboardButton("📊 View Progress", callback_data="class_overview")],
                [InlineKeyboardButton("📢 Send Notification", callback_data="send_reminder")],
                [InlineKeyboardButton("⬅️ Back", callback_data="my_classes")],
            ]),
            parse_mode="HTML",
        )
    
    async def _handle_add_class(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle add class callback."""
        query = update.callback_query
        await query.edit_message_text(
            "➕ <b>Add New Class</b>\n\n"
            "Please enter the class name:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
            ]),
            parse_mode="HTML",
        )
        context.user_data["awaiting_class_name"] = True
    
    async def _handle_edit_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle edit post callback."""
        query = update.callback_query
        await query.edit_message_text(
            "✏️ <b>Edit Before Posting</b>\n\n"
            "What would you like to edit?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Subject", callback_data="edit_post_subject")],
                [InlineKeyboardButton("Title", callback_data="edit_post_title")],
                [InlineKeyboardButton("Due Date", callback_data="edit_post_due")],
                [InlineKeyboardButton("Description", callback_data="edit_post_desc")],
                [InlineKeyboardButton("✅ Post Now", callback_data="post_class_select")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
            ]),
            parse_mode="HTML",
        )
    
    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages with state validation."""
        user = update.effective_user
        role = await self.onboarding_handler.get_user_role(user.id, context)
        
        # Check for editing state
        if context.user_data.get("editing_homework"):
            await self.homework_handler.handle_edit_input(update, context)
            return

        if context.user_data.get("awaiting_child_name"):
            await self.parent_handler.handle_child_name_input(update, context)
            return

        if context.user_data.get("awaiting_child_class"):
            await self.parent_handler.handle_child_class_input(update, context)
            return
        
        # Check for specific input modes with atomic state clearing
        if context.user_data.get("awaiting_due_date"):
            # Clear state before processing to prevent race conditions
            context.user_data["awaiting_due_date"] = False
            await self.homework_handler.handle_due_date(update, context)
            return
        
        if context.user_data.get("awaiting_class_name"):
            # Clear state before processing to prevent race conditions
            context.user_data["awaiting_class_name"] = False
            await self._handle_class_name_input(update, context)
            return
        
        # Check if user is in a conversation state that expects specific input
        if context.user_data.get("awaiting_homework_post"):
            # User sent text when photo was expected
            await self.onboarding_handler.send_message(
                update,
                "📸 Please send a photo of the homework, or click Cancel to go back.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
                ])
            )
            return
        
        # Default text handling
        await self.onboarding_handler.send_message(
            update,
            "I received your message. How can I help you today?",
            reply_markup=self.onboarding_handler.get_main_menu(role),
        )
    
    async def _handle_class_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle class name input."""
        class_name = update.message.text
        await self.onboarding_handler.send_message(
            update,
            f"✅ Class '{class_name}' created!\n\n"
            f"You can now post homework to this class.",
            reply_markup=self.onboarding_handler.get_main_menu(UserRole.TEACHER),
        )
    
    async def _handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads."""
        user = update.effective_user
        role = await self.onboarding_handler.get_user_role(user.id, context)
        
        await self.onboarding_handler.send_message(
            update,
            "📄 I received your document. Processing...",
            reply_markup=self.onboarding_handler.get_main_menu(role),
        )
    
    async def _handle_reminder_setting(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        data: str,
    ):
        """Handle reminder setting callback."""
        query = update.callback_query
        setting = data.replace("remind_", "")
        
        settings_map = {
            "1day": "1 day before due date",
            "same_day": "Same day morning",
            "custom": "Custom time (you'll be asked)",
        }
        
        await query.edit_message_text(
            f"✅ Reminder set: {settings_map.get(setting, 'Unknown')}\n\n"
            "I'll notify you accordingly!",
            reply_markup=self.onboarding_handler.get_main_menu(UserRole.PARENT),
        )
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        user = update.effective_user
        role = await self.onboarding_handler.get_user_role(user.id, context)
        
        if role == UserRole.TEACHER:
            help_text = """📚 <b>EduSync - Teacher Help</b>

<b>Commands:</b>
/start - Start the bot
/post - Post homework to class
/classes - View your classes
/overview - Class overview & stats
/notify - Send notification to parents
/switch_role - Switch to parent mode
/settings - Change settings
/cancel - Cancel current action

<b>How to post homework:</b>
1. Use /post or click "📤 Post Homework"
2. Send a photo of the homework
3. Review the extracted details
4. Select which class to post to
5. Parents will be notified automatically!

Need help? Contact support@edusync.app"""
        else:
            help_text = """📚 <b>EduSync - Parent Help</b>

<b>Commands:</b>
/start - Start the bot
/homework - View your child's homework
/reminders - Set reminder preferences
/switch_role - Switch to teacher mode
/settings - Change settings
/cancel - Cancel current action

<b>How to track homework:</b>
1. Send a photo of your child's homework
2. I'll extract the details automatically
3. Set reminders for due dates
4. Get notified before deadlines!

Need help? Contact support@edusync.app"""
        
        await self.onboarding_handler.send_message(update, help_text)
    
    async def _cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command."""
        user = update.effective_user
        role = await self.onboarding_handler.get_user_role(user.id, context)
        
        # If called from callback query, use SettingsHandler
        if update.callback_query:
            from .settings_handlers import SettingsHandler
            settings_handler = SettingsHandler()
            await settings_handler.show_settings(update, context, role)
            return
        
        settings_text = """⚙️ <b>Settings</b>

What would you like to change?"""
        
        keyboard = [
            [InlineKeyboardButton("🌐 Language", callback_data="set_language")],
            [InlineKeyboardButton("🔔 Notifications", callback_data="set_notifications")],
            [InlineKeyboardButton("⏰ Timezone", callback_data="set_timezone")],
            [InlineKeyboardButton("🔗 Link WhatsApp", callback_data="link_whatsapp")],
        ]
        
        if role == UserRole.TEACHER:
            keyboard.insert(0, [InlineKeyboardButton("👨‍🏫 Teacher Profile", callback_data="teacher_profile")])
        else:
            keyboard.insert(0, [InlineKeyboardButton("👨‍👩‍👧 Manage Children", callback_data="manage_children")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        
        await self.onboarding_handler.send_message(
            update,
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    
    async def _cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command - preserves essential user data."""
        user = update.effective_user
        role = await self.onboarding_handler.get_user_role(user.id, context)
        
        # Preserve essential user data
        essential_keys = ["role", "onboarded", "user_id"]
        preserved = {k: context.user_data.get(k) for k in essential_keys if k in context.user_data}
        
        # Clear temporary/state data
        context.user_data.clear()
        
        # Restore essential data
        context.user_data.update(preserved)
        
        await self.onboarding_handler.send_message(
            update,
            "❌ Cancelled. What would you like to do?",
            reply_markup=self.onboarding_handler.get_main_menu(role),
        )
    
    async def _handle_manage_children(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle manage children callback."""
        query = update.callback_query
        
        children = context.user_data.get("children", [])
        
        if not children:
            await query.edit_message_text(
                "👨‍👩‍👧 <b>Manage Children</b>\n\n"
                "No children added yet.\n\n"
                "Add your children to track their homework:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Add Child", callback_data="add_child")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="settings")],
                ]),
                parse_mode="HTML",
            )
        else:
            lines = ["👨‍👩‍👧 <b>Your Children:</b>\n"]
            buttons = []
            
            for child in children:
                lines.append(f"• <b>{child['name']}</b> - Class {child['class']}")
                buttons.append([InlineKeyboardButton(f"✏️ Edit {child['name']}", callback_data=f"edit_child_{child['name']}")])
            
            buttons.append([InlineKeyboardButton("➕ Add Another Child", callback_data="add_child")])
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="settings")])
            
            await query.edit_message_text(
                "\n".join(lines),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML",
            )
    
    async def _handle_teacher_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle teacher profile callback."""
        query = update.callback_query
        await query.edit_message_text(
            "👨‍🏫 <b>Teacher Profile</b>\n\n"
            "Manage your teacher profile settings:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Edit Name", callback_data="edit_teacher_name")],
                [InlineKeyboardButton("🏫 Edit School", callback_data="edit_school")],
                [InlineKeyboardButton("📚 My Subjects", callback_data="my_subjects")],
                [InlineKeyboardButton("⬅️ Back", callback_data="settings")],
            ]),
            parse_mode="HTML",
        )
    
    async def _handle_link_whatsapp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle link WhatsApp callback."""
        query = update.callback_query
        await query.edit_message_text(
            "🔗 <b>Link WhatsApp</b>\n\n"
            "To receive notifications on WhatsApp:\n\n"
            "1. Save our number: +60 12-345 6789\n"
            "2. Send 'START' to that number\n"
            "3. Your accounts will be linked automatically\n\n"
            "<i>WhatsApp integration coming soon!</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="settings")],
            ]),
            parse_mode="HTML",
        )
    
    async def _error_handler(self, update: Optional[Update], context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later or contact support."
            )
    
    def run(self):
        """Run the bot."""
        self.setup()
        
        if self.config.use_webhook and self.config.webhook_url:
            logger.info(f"Starting bot with webhook: {self.config.webhook_url}")
            self.application.run_webhook(
                listen="0.0.0.0",
                port=8080,
                webhook_url=self.config.webhook_url,
                secret_token=self.config.webhook_secret,
            )
        else:
            logger.info("Starting bot with polling")
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point."""
    config = BotConfig.from_env()
    
    if not config.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    bot = EduSyncBot(config)
    bot.run()


if __name__ == "__main__":
    main()
