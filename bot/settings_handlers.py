"""Settings configuration handlers."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .models import UserRole

logger = logging.getLogger(__name__)


class SettingsHandler:
    """Handler for user settings."""
    
    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, role: UserRole):
        """Show settings menu."""
        query = update.callback_query
        
        settings_text = """⚙️ <b>Settings</b>

What would you like to change?"""
        
        keyboard = [
            [InlineKeyboardButton("🌐 Language", callback_data="set_language")],
            [InlineKeyboardButton("🔔 Notification Preferences", callback_data="set_notifications")],
            [InlineKeyboardButton("⏰ Timezone", callback_data="set_timezone")],
            [InlineKeyboardButton("🔗 Link WhatsApp", callback_data="link_whatsapp")],
        ]
        
        if role == UserRole.TEACHER:
            keyboard.insert(0, [InlineKeyboardButton("👨‍🏫 Teacher Profile", callback_data="teacher_profile")])
        else:
            keyboard.insert(0, [InlineKeyboardButton("👨‍👩‍👧 Manage Children", callback_data="manage_children")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        
        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    
    async def handle_language_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle language selection."""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🌐 <b>Select Language</b>\n\n"
            "Choose your preferred language:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
                [InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh")],
                [InlineKeyboardButton("🇲🇾 Bahasa Melayu", callback_data="lang_ms")],
                [InlineKeyboardButton("⬅️ Back", callback_data="settings")],
            ]),
            parse_mode="HTML"
        )
    
    async def handle_notification_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle notification preferences."""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🔔 <b>Notification Preferences</b>\n\n"
            "When would you like to be reminded about homework?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 1 Day Before Due Date", callback_data="notif_1day")],
                [InlineKeyboardButton("🌅 Same Day Morning", callback_data="notif_same_day")],
                [InlineKeyboardButton("⏰ Custom Time", callback_data="notif_custom")],
                [InlineKeyboardButton("🔕 Disable All", callback_data="notif_off")],
                [InlineKeyboardButton("⬅️ Back", callback_data="settings")],
            ]),
            parse_mode="HTML"
        )
    
    async def handle_timezone_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle timezone selection."""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "⏰ <b>Select Timezone</b>\n\n"
            "Choose your timezone:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇲🇾 Kuala Lumpur (GMT+8)", callback_data="tz_kl")],
                [InlineKeyboardButton("🇸🇬 Singapore (GMT+8)", callback_data="tz_sg")],
                [InlineKeyboardButton("🌐 Other", callback_data="tz_other")],
                [InlineKeyboardButton("⬅️ Back", callback_data="settings")],
            ]),
            parse_mode="HTML"
        )
    
    async def save_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE, setting_type: str, value: str):
        """Save setting to database."""
        query = update.callback_query
        await query.answer()
        
        # TODO: Save to database
        # For now, just store in context
        if "settings" not in context.user_data:
            context.user_data["settings"] = {}
        context.user_data["settings"][setting_type] = value
        
        setting_names = {
            "lang": "Language",
            "notif": "Notification preference", 
            "tz": "Timezone"
        }
        
        # Get user role for proper menu
        from .handlers import OnboardingHandler
        onboarding = OnboardingHandler(None, None)
        role = await onboarding.get_user_role(update.effective_user.id, context)
        
        await query.edit_message_text(
            f"✅ <b>{setting_names.get(setting_type, 'Setting')} updated!</b>\n\n"
            f"New value: {value}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ More Settings", callback_data="settings")],
                [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
            ]),
            parse_mode="HTML"
        )
