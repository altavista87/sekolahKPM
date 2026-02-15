"""Telegram Bot Message Handlers."""

import logging
import os
import html
from typing import Optional, Dict, Any, List
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select

from .models import UserRole, HomeworkStatus, ConversationState
from .ocr_engine import OCREngine, AdvancedOCREngine
from .ai_processor import AIProcessor
from .utils import parse_date, format_date, get_priority_emoji, get_status_emoji

# Database imports
from database.connection import get_db_context
from database.models import User as UserModel, Student, Homework, Class, UserConsent

# Ensure uploads directory exists
os.makedirs("./uploads", exist_ok=True)

logger = logging.getLogger(__name__)


class BaseHandler:
    """Base handler with common functionality."""
    
    def __init__(self, ocr_engine: OCREngine, ai_processor: Optional[AIProcessor] = None):
        self.ocr = ocr_engine
        self.ai = ai_processor
    
    async def _check_ai_consent(self, user_id: int) -> bool:
        """Check if user has consented to AI processing."""
        async with get_db_context() as db:
            # Get user from telegram_id
            result = await db.execute(
                select(UserModel).where(UserModel.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            consent_result = await db.execute(
                select(UserConsent).where(
                    UserConsent.user_id == user.id,
                    UserConsent.consent_type == "ai_processing"
                )
            )
            consent = consent_result.scalar_one_or_none()
            return consent is not None and consent.granted
    
    async def _request_ai_consent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Request consent for AI processing."""
        await self.send_message(
            update,
            "🤖 <b>AI Processing Consent</b>\n\n"
            "To extract homework details from your photo, we use AI services "
            "(Gemini, OpenAI) to analyze the image.\n\n"
            "✓ Your data is processed securely\n"
            "✓ Personal information is redacted\n"
            "✓ Data is not used to train AI models\n\n"
            "Do you consent to AI processing?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, I Consent", callback_data="consent_ai_yes")],
                [InlineKeyboardButton("❌ No, Use OCR Only", callback_data="consent_ai_no")],
            ])
        )
    
    async def send_message(
        self,
        update: Update,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ):
        """Send message with error handling."""
        try:
            await update.effective_message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    def get_main_menu(self, role: UserRole) -> InlineKeyboardMarkup:
        """Get main menu keyboard based on user role."""
        if role == UserRole.TEACHER:
            buttons = [
                [InlineKeyboardButton("📤 Post Homework", callback_data="post_hw")],
                [InlineKeyboardButton("📋 My Classes", callback_data="my_classes")],
                [InlineKeyboardButton("📊 Class Overview", callback_data="class_overview")],
                [InlineKeyboardButton("🔔 Send Reminders", callback_data="send_reminder")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            ]
        else:  # PARENT or default
            buttons = [
                [InlineKeyboardButton("📸 Submit Homework", callback_data="submit_hw")],
                [InlineKeyboardButton("📋 My Homework", callback_data="list_hw")],
                [InlineKeyboardButton("👨‍👩‍👧 My Children", callback_data="my_children")],
                [InlineKeyboardButton("🔔 Reminders", callback_data="reminders")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            ]
        
        return InlineKeyboardMarkup(buttons)
    
    async def get_user_role(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> UserRole:
        """Get user role from database or context."""
        # First check context (session storage)
        role_str = context.user_data.get("role")
        if role_str:
            try:
                return UserRole(role_str)
            except ValueError:
                pass
        
        # Check database
        async with get_db_context() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                role = UserRole(user.role)
                context.user_data["role"] = role.value
                return role
        
        # Default to parent
        return UserRole.PARENT
    
    async def set_user_role(self, user_id: int, role: UserRole, context: ContextTypes.DEFAULT_TYPE):
        """Set user role in context and database."""
        context.user_data["role"] = role.value
        
        # Save to database
        async with get_db_context() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.role = role.value
            else:
                # Create new user
                from telegram import User as TelegramUser
                user_info = context._application.bot.get_chat(user_id)
                new_user = UserModel(
                    telegram_id=user_id,
                    name=user_info.first_name if user_info else "Unknown",
                    role=role.value,
                    preferred_language="en",
                )
                db.add(new_user)
        
        logger.info(f"User {user_id} role set to {role.value}")


class OnboardingHandler(BaseHandler):
    """Handler for user onboarding and role selection."""
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with role selection."""
        user = update.effective_user
        
        # Check if user already has a role
        existing_role = await self.get_user_role(user.id, context)
        
        # If returning user, show appropriate welcome
        if context.user_data.get("onboarded"):
            await self._show_welcome_back(update, context, existing_role)
            return
        
        # New user - show role selection
        welcome_text = f"""👋 <b>Welcome to EduSync, {user.first_name}!</b>

I'm your homework assistant bot.

<b>Who are you?</b>"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👨‍👩‍👧 I'm a Parent", callback_data="role_parent")],
            [InlineKeyboardButton("👨‍🏫 I'm a Teacher", callback_data="role_teacher")],
        ])
        
        await self.send_message(update, welcome_text, reply_markup=keyboard)
    
    async def handle_role_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle role selection callback."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        data = query.data
        
        if data == "role_parent":
            await self.set_user_role(user.id, UserRole.PARENT, context)
            await self._onboard_parent(update, context)
        elif data == "role_teacher":
            await self.set_user_role(user.id, UserRole.TEACHER, context)
            await self._onboard_teacher(update, context)
    
    async def handle_consent_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle AI consent callback responses."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        data = query.data
        
        if data == "consent_ai_yes":
            # Save consent to database
            async with get_db_context() as db:
                result = await db.execute(
                    select(UserModel).where(UserModel.telegram_id == user.id)
                )
                db_user = result.scalar_one_or_none()
                
                if db_user:
                    consent = UserConsent(
                        user_id=db_user.id,
                        consent_type="ai_processing",
                        granted=True,
                        granted_at=datetime.utcnow(),
                    )
                    db.add(consent)
                    await db.commit()
            
            context.user_data["ai_consent"] = True
            context.user_data.pop("awaiting_ai_consent", None)
            
            await query.edit_message_text(
                "✅ <b>AI Processing Consent Granted</b>\n\n"
                "You can now use AI-powered homework extraction. "
                "Your data will be processed securely with PII redaction.",
                parse_mode="HTML"
            )
            
        elif data == "consent_ai_no":
            context.user_data["ai_consent"] = False
            context.user_data.pop("awaiting_ai_consent", None)
            
            await query.edit_message_text(
                "❌ <b>AI Processing Declined</b>\n\n"
                "You can still use the bot with OCR-only mode. "
                "AI features will not be available for homework extraction.",
                parse_mode="HTML"
            )
    
    async def _onboard_parent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Complete parent onboarding."""
        query = update.callback_query
        
        text = """👨‍👩‍👧 <b>Parent Mode Activated!</b>

I can help you:
• 📸 Track your child's homework by taking photos
• 🔔 Get reminders before deadlines
• 📊 Monitor your child's progress
• 📱 Receive updates via Telegram

<b>Next steps:</b>
1. Add your children
2. Connect to their school/class
3. Start tracking homework!

Send me a photo of homework to get started!"""
        
        context.user_data["onboarded"] = True
        
        await query.edit_message_text(
            text,
            reply_markup=self.get_main_menu(UserRole.PARENT),
            parse_mode="HTML",
        )
        
        # Request AI processing consent
        await self._request_ai_consent(update, context)
        context.user_data["awaiting_ai_consent"] = True
    
    async def _onboard_teacher(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Complete teacher onboarding."""
        query = update.callback_query
        
        text = """👨‍🏫 <b>Teacher Mode Activated!</b>

I can help you:
• 📤 Post homework to your classes
• 📊 Track student completion
• 🔔 Send reminders to parents
• 📈 View class analytics

<b>Next steps:</b>
1. Set up your classes
2. Add students
3. Start posting homework!

Use /post to create your first homework assignment!"""
        
        context.user_data["onboarded"] = True
        context.user_data["awaiting_class_setup"] = True
        
        await query.edit_message_text(
            text,
            reply_markup=self.get_main_menu(UserRole.TEACHER),
            parse_mode="HTML",
        )
        
        # Request AI processing consent
        await self._request_ai_consent(update, context)
        context.user_data["awaiting_ai_consent"] = True
    
    async def _show_welcome_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE, role: UserRole):
        """Show welcome back message for returning users."""
        user = update.effective_user
        
        role_name = "Teacher" if role == UserRole.TEACHER else "Parent"
        
        text = f"""👋 <b>Welcome back, {user.first_name}!</b>

You're in <b>{role_name}</b> mode.

What would you like to do?"""
        
        await self.send_message(
            update,
            text,
            reply_markup=self.get_main_menu(role),
        )
    
    async def cmd_switch_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Allow user to switch role."""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👨‍👩‍👧 Switch to Parent", callback_data="role_parent")],
            [InlineKeyboardButton("👨‍🏫 Switch to Teacher", callback_data="role_teacher")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        ])
        
        await self.send_message(
            update,
            "🔄 <b>Switch Role</b>\n\nSelect your new role:",
            reply_markup=keyboard,
        )


class HomeworkHandler(BaseHandler):
    """Handler for homework-related commands."""
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle homework photo submission - different flow for parent vs teacher."""
        user = update.effective_user
        role = await self.get_user_role(user.id, context)
        
        if role == UserRole.TEACHER:
            await self._handle_teacher_photo(update, context)
        else:
            await self._handle_parent_photo(update, context)
    
    async def _handle_parent_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo from parent (track child's homework)."""
        user = update.effective_user
        
        # Check if role is selected
        role = await self.get_user_role(user.id, context)
        if not context.user_data.get("onboarded"):
            await self.send_message(
                update,
                "👋 Welcome! Please select your role first by using /start",
            )
            return
        
        await self.send_message(
            update,
            "📸 I received the photo. Processing for homework tracking...",
        )
        
        # Download and process photo
        photo = update.message.photo[-1]
        
        # Validate file size (20MB limit)
        if photo.file_size and photo.file_size > 20 * 1024 * 1024:
            await self.send_message(
                update,
                "❌ File too large. Please send an image under 20MB.",
            )
            return
        
        file = await photo.get_file()
        
        # Sanitize user_id for filename
        safe_user_id = str(user.id).replace("..", "").replace("/", "").replace("\\", "")
        upload_path = f"./uploads/parent_{safe_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        try:
            await file.download_to_drive(upload_path)
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            await self.send_message(
                update,
                "❌ Failed to download image. Please try again.",
            )
            return
        
        # Process with OCR
        try:
            ocr_result = await self.ocr.process_image(upload_path)
            
            # Check if user has consented to AI processing
            ai_consent = context.user_data.get("ai_consent", False)
            if not ai_consent:
                # Check database for consent
                ai_consent = await self._check_ai_consent(user.id)
                context.user_data["ai_consent"] = ai_consent
            
            if self.ai and ai_consent:
                ai_result = await self.ai.extract_homework(ocr_result.text, language="en")
                
                # Validate AI extraction has meaningful content
                if not ai_result.subject and not ai_result.title and len(ai_result.description) < 20:
                    await self.send_message(
                        update,
                        "⚠️ <b>Could not extract homework details clearly.</b>\n\n"
                        "Please try:\n"
                        "• Taking a clearer photo\n"
                        "• Ensuring the homework is well-lit\n"
                        "• Making sure text is readable",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Try Again", callback_data="submit_hw")],
                            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")],
                        ])
                    )
                    # Clean up file
                    self._cleanup_file(upload_path)
                    return
                
                context.user_data["homework_draft"] = {
                    "image_path": upload_path,
                    "ocr_text": ocr_result.text,
                    "extracted": ai_result,
                }
                
                summary = self._format_extraction(ai_result)
                await self.send_message(
                    update,
                    f"✅ <b>Homework Detected!</b>\n\n{summary}\n\n"
                    f"<b>Which child is this for?</b>\n"
                    f"(You can add children in settings)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Confirm & Save", callback_data="save_hw_parent")],
                        [InlineKeyboardButton("✏️ Edit Details", callback_data="edit_hw")],
                        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
                    ])
                )
            else:
                await self.send_message(
                    update,
                    f"📄 <b>Extracted Text:</b>\n\n<code>{ocr_result.text[:500]}</code>",
                )
                # Clean up file after processing
                self._cleanup_file(upload_path)
                
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            await self.send_message(
                update,
                "❌ Sorry, I couldn't process that image. Please try again or type the details manually."
            )
            # Clean up file on error
            self._cleanup_file(upload_path)
    
    async def _handle_teacher_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo from teacher (post homework to class)."""
        user = update.effective_user
        
        # Check if role is selected
        role = await self.get_user_role(user.id, context)
        if not context.user_data.get("onboarded"):
            await self.send_message(
                update,
                "👋 Welcome! Please select your role first by using /start",
            )
            return
        
        await self.send_message(
            update,
            "📸 I received the photo. Processing for class posting...",
        )
        
        # Download photo
        photo = update.message.photo[-1]
        
        # Validate file size (20MB limit)
        if photo.file_size and photo.file_size > 20 * 1024 * 1024:
            await self.send_message(
                update,
                "❌ File too large. Please send an image under 20MB.",
            )
            return
        
        file = await photo.get_file()
        
        # Sanitize user_id for filename
        safe_user_id = str(user.id).replace("..", "").replace("/", "").replace("\\", "")
        upload_path = f"./uploads/teacher_{safe_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        try:
            await file.download_to_drive(upload_path)
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            await self.send_message(
                update,
                "❌ Failed to download image. Please try again.",
            )
            return
        
        # Process with OCR
        try:
            ocr_result = await self.ocr.process_image(upload_path)
            
            # Check if user has consented to AI processing
            ai_consent = context.user_data.get("ai_consent", False)
            if not ai_consent:
                # Check database for consent
                ai_consent = await self._check_ai_consent(user.id)
                context.user_data["ai_consent"] = ai_consent
            
            if self.ai and ai_consent:
                ai_result = await self.ai.extract_homework(ocr_result.text, language="en")
                
                # Validate AI extraction has meaningful content
                if not ai_result.subject and not ai_result.title and len(ai_result.description) < 20:
                    await self.send_message(
                        update,
                        "⚠️ <b>Could not extract homework details clearly.</b>\n\n"
                        "Please try:\n"
                        "• Taking a clearer photo\n"
                        "• Ensuring the homework is well-lit\n"
                        "• Making sure text is readable",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Try Again", callback_data="post_hw")],
                            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")],
                        ])
                    )
                    # Clean up file
                    self._cleanup_file(upload_path)
                    return
                
                context.user_data["homework_post"] = {
                    "image_path": upload_path,
                    "ocr_text": ocr_result.text,
                    "extracted": ai_result,
                }
                
                summary = self._format_extraction(ai_result)
                await self.send_message(
                    update,
                    f"📤 <b>Ready to Post to Class!</b>\n\n{summary}\n\n"
                    f"<b>Select class to post to:</b>",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Class 5A", callback_data="post_class_5a")],
                        [InlineKeyboardButton("Class 5B", callback_data="post_class_5b")],
                        [InlineKeyboardButton("✏️ Edit Before Posting", callback_data="edit_post")],
                        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
                    ])
                )
            else:
                await self.send_message(
                    update,
                    f"📄 <b>Extracted Text:</b>\n\n<code>{ocr_result.text[:500]}</code>",
                )
                # Clean up file after processing
                self._cleanup_file(upload_path)
                
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            await self.send_message(
                update,
                "❌ Sorry, I couldn't process that image. Please try again or type the details manually."
            )
            # Clean up file on error
            self._cleanup_file(upload_path)
    
    async def handle_due_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle due date input."""
        text = update.message.text
        due_date = parse_date(text)
        
        # Validate that homework_draft exists
        if "homework_draft" not in context.user_data:
            await self.send_message(
                update,
                "❌ No active homework draft found. Please send a photo first.",
                reply_markup=self.get_main_menu(UserRole.PARENT)
            )
            return
        
        if due_date:
            context.user_data["homework_draft"]["due_date"] = due_date
            await self.send_message(
                update,
                f"📅 Due date set: {format_date(due_date)}\n\nHomework saved successfully! ✅"
            )
            await self._save_homework(update, context)
        else:
            await self.send_message(
                update,
                "❌ I couldn't understand that date. Please try again (e.g., 'tomorrow', '25 Dec')."
            )
    
    def _format_extraction(self, result) -> str:
        """Format AI extraction result for display with HTML escaping."""
        
        def escape(text: str) -> str:
            """Escape HTML special characters."""
            if not text:
                return ""
            return html.escape(str(text))
        
        lines = [
            f"<b>📚 Subject:</b> {escape(result.subject) or 'Not detected'}",
        ]
        
        # Homework Type Badge
        if result.homework_type_display:
            lines.append(f"<b>📖 Type:</b> {escape(result.homework_type_display)}")
        elif result.homework_type:
            type_emoji = {
                "buku_teks": "📕",
                "buku_latihan": "📗", 
                "worksheet": "📄",
                "project": "📋",
                "other": "📝"
            }.get(result.homework_type, "📝")
            lines.append(f"<b>{type_emoji} Type:</b> {result.homework_type.replace('_', ' ').title()}")
        
        # AI Suggested Names
        if result.potential_names:
            names_str = " | ".join([f"<code>{escape(name)}</code>" for name in result.potential_names[:3]])
            lines.append(f"<b>💡 Suggested Names:</b> {names_str}")
        
        # Title
        lines.append(f"<b>📝 Title:</b> {escape(result.title) or 'Not detected'}")
        
        # What to Achieve (Learning Objectives)
        if result.what_to_achieve:
            lines.append(f"<b>🎯 Objective:</b> {escape(result.what_to_achieve)}")
        
        # Description
        desc = result.description[:200] + '...' if len(result.description) > 200 else result.description
        lines.append(f"<b>📄 Description:</b> {escape(desc)}")
        
        # Page Numbers
        if result.page_numbers:
            lines.append(f"<b>📄 Pages:</b> {escape(result.page_numbers)}")
        
        # Exercises List
        if result.exercises_list:
            exercises_str = ", ".join([escape(ex) for ex in result.exercises_list[:5]])
            if len(result.exercises_list) > 5:
                exercises_str += f" (+{len(result.exercises_list) - 5} more)"
            lines.append(f"<b>✏️ Exercises:</b> {exercises_str}")
        
        # Textbook/Workbook Info
        if result.textbook_title:
            lines.append(f"<b>📕 Textbook:</b> {escape(result.textbook_title)}")
        if result.workbook_title:
            lines.append(f"<b>📗 Workbook:</b> {escape(result.workbook_title)}")
        
        # Due Date
        if result.due_date:
            lines.append(f"<b>📅 Due Date:</b> {escape(result.due_date)}")
        
        # Estimated Time
        if result.estimated_time_minutes:
            lines.append(f"<b>⏱️ Est. Time:</b> {result.estimated_time_minutes} minutes")
        
        # Materials Needed
        if result.materials_needed:
            materials_str = ", ".join([escape(m) for m in result.materials_needed])
            lines.append(f"<b>🛠️ Materials:</b> {materials_str}")
        
        return "\n".join(lines)
    
    def _cleanup_file(self, file_path: str):
        """Clean up uploaded file after processing."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up file {file_path}: {e}")
    
    async def _get_conversation_state(self, user_id: int) -> ConversationState:
        """Get user's conversation state."""
        return ConversationState(user_id=str(user_id), state="idle")
    
    async def _save_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Save homework to database."""
        user = update.effective_user
        homework_draft = context.user_data.get("homework_draft", {})
        extracted = homework_draft.get("extracted")
        
        if not extracted:
            await self.send_message(
                update,
                "❌ No homework data to save.",
            )
            return
        
        async with get_db_context() as db:
            # Get or create user
            result = await db.execute(
                select(UserModel).where(UserModel.telegram_id == user.id)
            )
            db_user = result.scalar_one_or_none()
            
            if not db_user:
                # Create new user
                db_user = UserModel(
                    telegram_id=user.id,
                    name=user.first_name or "Unknown",
                    role="parent",
                )
                db.add(db_user)
                await db.flush()
            
            # Get child (for now, use first child or create default)
            students_result = await db.execute(
                select(Student).where(Student.parent_id == db_user.id)
            )
            student = students_result.scalar_one_or_none()
            
            if not student:
                await self.send_message(
                    update,
                    "⚠️ Please add a child first using '👨‍👩‍👧 My Children'",
                    reply_markup=self.get_main_menu(UserRole.PARENT)
                )
                return
            
            # Parse due date if provided
            due_date = homework_draft.get("due_date")
            if hasattr(extracted, 'due_date') and extracted.due_date and not due_date:
                due_date = parse_date(extracted.due_date)
            
            # Create homework entry
            homework = Homework(
                student_id=student.id,
                subject=extracted.subject or "Unknown",
                title=extracted.title or "Untitled Homework",
                description=extracted.description or "",
                raw_text=homework_draft.get("ocr_text", ""),
                due_date=due_date,
                priority=extracted.priority if hasattr(extracted, 'priority') else 3,
                status="pending",
                ai_enhanced=True,
                ai_summary=extracted.what_to_achieve if hasattr(extracted, 'what_to_achieve') else None,
            )
            db.add(homework)
            await db.commit()
            
            await self.send_message(
                update,
                f"✅ Homework saved for {student.name}!\n\n"
                f"📚 {homework.subject}: {homework.title}\n"
                f"I'll remind you before the due date.",
                reply_markup=self.get_main_menu(UserRole.PARENT)
            )
            
            # Clean up draft
            context.user_data.pop("homework_draft", None)


class ParentHandler(BaseHandler):
    """Handler for parent-specific commands."""
    
    async def cmd_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /homework command for parents."""
        homework_list = await self._get_homework(update.effective_user.id)
        
        if not homework_list:
            await self.send_message(
                update,
                "📭 No homework found. Take a photo to add new homework!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📸 Add Homework", callback_data="submit_hw")]
                ])
            )
            return
        
        lines = ["📚 <b>Your Child's Homework:</b>\n"]
        
        for hw in homework_list[:10]:
            emoji = get_status_emoji(hw.status)
            priority = get_priority_emoji(hw.priority)
            due = format_date(hw.due_date) if hw.due_date else "No due date"
            
            lines.append(
                f"{emoji} <b>{hw.subject}</b>: {hw.title}\n"
                f"   {priority} Due: {due}\n"
            )
        
        await self.send_message(
            update,
            "\n".join(lines),
            reply_markup=self.get_main_menu(UserRole.PARENT)
        )
    
    async def cmd_reminders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reminders command for parents."""
        await self.send_message(
            update,
            "🔔 <b>Reminder Settings</b>\n\n"
            "Choose when you'd like to be reminded:\n"
            "• 1 day before due date\n"
            "• Same day morning\n"
            "• Custom time",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1 Day Before", callback_data="remind_1day")],
                [InlineKeyboardButton("Same Day", callback_data="remind_same_day")],
                [InlineKeyboardButton("Custom", callback_data="remind_custom")],
            ])
        )
    
    async def _get_homework(self, user_id: int) -> list:
        """Fetch homework for parent's children from database."""
        async with get_db_context() as db:
            # Get user by telegram_id
            result = await db.execute(
                select(UserModel).where(UserModel.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return []
            
            # Get all students for this parent
            students_result = await db.execute(
                select(Student).where(Student.parent_id == user.id)
            )
            students = students_result.scalars().all()
            
            if not students:
                return []
            
            # Get homework for all children
            student_ids = [s.id for s in students]
            homework_result = await db.execute(
                select(Homework)
                .where(Homework.student_id.in_(student_ids))
                .order_by(Homework.due_date)
            )
            return list(homework_result.scalars().all())


class TeacherHandler(BaseHandler):
    """Handler for teacher-specific commands."""
    
    async def cmd_post_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /post command - start posting homework."""
        await self.send_message(
            update,
            "📤 <b>Post Homework</b>\n\n"
            "Send me a photo of the homework assignment, or type the details.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
            ])
        )
        context.user_data["awaiting_homework_post"] = True
    
    async def cmd_my_classes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show teacher's classes."""
        classes = await self._get_classes(update.effective_user.id)
        
        if not classes:
            await self.send_message(
                update,
                "📭 No classes found.\n\n"
                "Use /setup_class to create your first class!",
                reply_markup=self.get_main_menu(UserRole.TEACHER)
            )
            return
        
        lines = ["📚 <b>Your Classes:</b>\n"]
        buttons = []
        
        for cls in classes:
            lines.append(f"• <b>{cls['name']}</b> - {cls['student_count']} students")
            buttons.append([InlineKeyboardButton(f"📋 {cls['name']}", callback_data=f"class_{cls['id']}")])
        
        buttons.append([InlineKeyboardButton("➕ Add New Class", callback_data="add_class")])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        
        await self.send_message(
            update,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    async def cmd_class_overview(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle class overview command for teachers."""
        stats = await self._get_class_stats(update.effective_user.id)
        
        text = f"""📊 <b>Class Overview</b>

<b>Total Students:</b> {stats.get('total_students', 0)}
<b>Active Homework:</b> {stats.get('active_homework', 0)}
<b>Completion Rate:</b> {stats.get('completion_rate', 0)}%

<b>Recent Activity:</b>
• Submitted today: {stats.get('submitted_today', 0)}
• Overdue: {stats.get('overdue_count', 0)}
• Due this week: {stats.get('due_this_week', 0)}"""
        
        await self.send_message(
            update,
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 View Details", callback_data="class_details")],
                [InlineKeyboardButton("📤 Send Reminder", callback_data="send_reminder")],
                [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
            ])
        )
    
    async def cmd_send_notification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send notification to parents."""
        await self.send_message(
            update,
            "📢 <b>Send Notification to Parents</b>\n\n"
            "Select which class to notify:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Class 5A", callback_data="notify_class_5a")],
                [InlineKeyboardButton("Class 5B", callback_data="notify_class_5b")],
                [InlineKeyboardButton("All Classes", callback_data="notify_all")],
                [InlineKeyboardButton("⬅️ Cancel", callback_data="cancel")],
            ])
        )
    
    async def _get_classes(self, teacher_id: int) -> list:
        """Fetch teacher's classes from database."""
        async with get_db_context() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.telegram_id == teacher_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return []
            
            classes_result = await db.execute(
                select(Class)
                .where(Class.teacher_id == user.id)
                .order_by(Class.name)
            )
            classes = classes_result.scalars().all()
            
            return [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "student_count": len(c.students) if c.students else 0
                }
                for c in classes
            ]
    
    async def _get_class_stats(self, teacher_id: int) -> dict:
        """Fetch class statistics from database."""
        async with get_db_context() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.telegram_id == teacher_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    "total_students": 0,
                    "active_homework": 0,
                    "completion_rate": 0,
                    "submitted_today": 0,
                    "overdue_count": 0,
                    "due_this_week": 0,
                }
            
            # Get all classes for this teacher
            classes_result = await db.execute(
                select(Class).where(Class.teacher_id == user.id)
            )
            classes = classes_result.scalars().all()
            
            if not classes:
                return {
                    "total_students": 0,
                    "active_homework": 0,
                    "completion_rate": 0,
                    "submitted_today": 0,
                    "overdue_count": 0,
                    "due_this_week": 0,
                }
            
            class_ids = [c.id for c in classes]
            
            # Get students in these classes
            students_result = await db.execute(
                select(Student).where(Student.class_id.in_(class_ids))
            )
            students = students_result.scalars().all()
            student_ids = [s.id for s in students]
            total_students = len(students)
            
            # Get homework stats
            if student_ids:
                homework_result = await db.execute(
                    select(Homework).where(Homework.student_id.in_(student_ids))
                )
                homework_list = homework_result.scalars().all()
                
                active_homework = len([h for h in homework_list if h.status in ("pending", "in_progress")])
                completed = len([h for h in homework_list if h.status == "completed"])
                total = len(homework_list)
                completion_rate = int((completed / total * 100)) if total > 0 else 0
                
                from datetime import timedelta
                today = datetime.utcnow()
                overdue = len([h for h in homework_list if h.due_date and h.due_date < today and h.status != "completed"])
                due_this_week = len([h for h in homework_list if h.due_date and h.due_date <= today + timedelta(days=7)])
                
                # Submitted today (completed_at is today)
                submitted_today = len([h for h in homework_list if h.completed_at and h.completed_at.date() == today.date()])
            else:
                active_homework = 0
                completion_rate = 0
                overdue = 0
                due_this_week = 0
                submitted_today = 0
            
            return {
                "total_students": total_students,
                "active_homework": active_homework,
                "completion_rate": completion_rate,
                "submitted_today": submitted_today,
                "overdue_count": overdue,
                "due_this_week": due_this_week,
            }
    
    async def post_homework_to_class(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        class_id: str,
    ):
        """Post homework to a specific class and notify parents."""
        homework_data = context.user_data.get("homework_post")
        
        if not homework_data:
            await self.send_message(
                update,
                "❌ No homework data found. Please send a photo first.",
            )
            return
        
        extracted = homework_data["extracted"]
        
        async with get_db_context() as db:
            # Get the class
            result = await db.execute(
                select(Class).where(Class.id == class_id)
            )
            class_obj = result.scalar_one_or_none()
            
            if not class_obj:
                await self.send_message(
                    update,
                    "❌ Class not found.",
                )
                return
            
            # Get students in class
            students_result = await db.execute(
                select(Student).where(Student.class_id == class_id)
            )
            students = students_result.scalars().all()
            
            # Create homework for each student
            for student in students:
                homework = Homework(
                    student_id=student.id,
                    subject=extracted.subject or "Unknown",
                    title=extracted.title or "Untitled Homework",
                    description=extracted.description or "",
                    raw_text=homework_data.get("ocr_text", ""),
                    due_date=parse_date(extracted.due_date) if hasattr(extracted, 'due_date') and extracted.due_date else None,
                    priority=extracted.priority if hasattr(extracted, 'priority') else 3,
                    status="pending",
                    ai_enhanced=True,
                    ai_summary=extracted.what_to_achieve if hasattr(extracted, 'what_to_achieve') else None,
                )
                db.add(homework)
            
            await db.commit()
        
        await self.send_message(
            update,
            f"✅ <b>Homework Posted to Class {class_id.upper()}!</b>\n\n"
            f"<b>Subject:</b> {extracted.subject}\n"
            f"<b>Title:</b> {extracted.title}\n\n"
            f"📢 <b>Parents have been notified!</b>",
            reply_markup=self.get_main_menu(UserRole.TEACHER)
        )
        
        # Clean up
        context.user_data.pop("homework_post", None)


class ReminderHandler(BaseHandler):
    """Handler for reminder-related functionality."""
    
    async def send_reminder_to_parents(
        self,
        homework: Homework,
        parent_ids: List[int],
        context: ContextTypes.DEFAULT_TYPE,
    ):
        """Send reminder to multiple parents."""
        if not self.ai:
            return
        
        # Calculate days until due
        if homework.due_date:
            days_until = (homework.due_date - datetime.utcnow()).days
        else:
            days_until = 0
        
        # Generate message
        message = await self.ai.generate_reminder_message(
            {
                "title": homework.title,
                "subject": homework.subject,
                "due_date": format_date(homework.due_date) if homework.due_date else None,
            },
            days_until,
            language="en",
        )
        
        # Send to all parents
        for parent_id in parent_ids:
            try:
                await context.bot.send_message(
                    chat_id=parent_id,
                    text=message,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to send reminder to {parent_id}: {e}")
    
    async def send_homework_notification(
        self,
        homework: Homework,
        class_id: str,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        """Send new homework notification to parents."""
        from database.models import Student as StudentModel
        
        # Get parent IDs from database for students in class
        async with get_db_context() as db:
            students_result = await db.execute(
                select(StudentModel).where(StudentModel.class_id == class_id)
            )
            students = students_result.scalars().all()
            
            parent_ids = []
            for student in students:
                if student.parent_id:
                    parent_result = await db.execute(
                        select(UserModel).where(UserModel.id == student.parent_id)
                    )
                    parent = parent_result.scalar_one_or_none()
                    if parent and parent.telegram_id:
                        parent_ids.append(parent.telegram_id)
        
        message = f"""📚 <b>New Homework Posted!</b>

<b>Subject:</b> {homework.subject}
<b>Title:</b> {homework.title}
<b>Due Date:</b> {format_date(homework.due_date) if homework.due_date else 'Not specified'}

<b>Description:</b>
{homework.description[:300]}{'...' if len(homework.description) > 300 else ''}

<i>Posted by your child's teacher</i>"""
        
        for parent_id in parent_ids:
            try:
                await context.bot.send_message(
                    chat_id=parent_id,
                    text=message,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to notify parent {parent_id}: {e}")
