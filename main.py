from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import logging
import uuid
import requests
import httpx
import random
import sys
import glob
import shutil
import subprocess
import tempfile
import threading
import string
import time
import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from flask import Flask

# إعدادات السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8758971653:AAEZxi14L64gyQNmYOIUXEfGShHhAJ_zOgw"

# مع المتغيرات العالمية في الأعلى
application_instance = None

# إعداد Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# ========== نظام تخزين البيانات في ملف JSON ==========
# اسم ملف التخزين
DATA_FILE = "bot_data.json"

def load_data():
    """تحميل البيانات من ملف JSON"""
    global USER_DATABASE, BLOCKED_USERS, BOT_RATINGS, USER_RATING_DATA
    
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # تحميل قاعدة بيانات المستخدمين
                if 'user_database' in data:
                    USER_DATABASE = set(data['user_database'])
                else:
                    USER_DATABASE = set()
                
                # تحميل المستخدمين المحظورين
                if 'blocked_users' in data:
                    BLOCKED_USERS = set(data['blocked_users'])
                else:
                    BLOCKED_USERS = set()
                
                # تحميل التقييمات
                if 'bot_ratings' in data:
                    BOT_RATINGS = data['bot_ratings']
                else:
                    BOT_RATINGS = {}
                
                # تحميل بيانات التقييم للمستخدمين
                if 'user_rating_data' in data:
                    USER_RATING_DATA = data['user_rating_data']
                else:
                    USER_RATING_DATA = {}
                    
                logger.info(f"✅ تم تحميل البيانات من {DATA_FILE}")
                logger.info(f"👥 عدد المستخدمين: {len(USER_DATABASE)}")
                logger.info(f"🚫 عدد المحظورين: {len(BLOCKED_USERS)}")
                logger.info(f"⭐ عدد التقييمات: {sum(len(ratings) for ratings in BOT_RATINGS.values())}")
                
        else:
            logger.info("📂 ملف البيانات غير موجود، سيتم إنشاء ملف جديد")
            # تهيئة البيانات الفارغة
            USER_DATABASE = set()
            BLOCKED_USERS = set()
            BOT_RATINGS = {}
            USER_RATING_DATA = {}
            save_data()
            
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل البيانات: {e}")
        # تهيئة البيانات الفارغة في حالة الخطأ
        USER_DATABASE = set()
        BLOCKED_USERS = set()
        BOT_RATINGS = {}
        USER_RATING_DATA = {}

def save_data():
    """حفظ البيانات في ملف JSON"""
    try:
        data = {
            'user_database': list(USER_DATABASE),
            'blocked_users': list(BLOCKED_USERS),
            'bot_ratings': BOT_RATINGS,
            'user_rating_data': USER_RATING_DATA,
            'last_save': datetime.now().isoformat(),
            'total_users': len(USER_DATABASE),
            'total_blocked': len(BLOCKED_USERS),
            'total_ratings': sum(len(ratings) for ratings in BOT_RATINGS.values())
        }
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"💾 تم حفظ البيانات في {DATA_FILE}")
        logger.info(f"👥 المستخدمين: {len(USER_DATABASE)}")
        logger.info(f"🚫 المحظورين: {len(BLOCKED_USERS)}")
        logger.info(f"⭐ التقييمات: {sum(len(ratings) for ratings in BOT_RATINGS.values())}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ البيانات: {e}")
        
# ========== لوحة تحكم المطور ==========
async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة أوامر المطور في شكل أزرار"""
    user_id = update.effective_user.id
    
    if not is_developer(user_id):
        await update.message.reply_text("❌ <b>هذا الأمر للمطور فقط!</b>", parse_mode='HTML')
        return
    
    # إنشاء أزرار المطور
    owner_keyboard = [
        [InlineKeyboardButton("🟢 تشغيل البوت", callback_data="owner_start"),
         InlineKeyboardButton("🔴 إيقاف البوت", callback_data="owner_stop")],
        [InlineKeyboardButton("📊 حالة البوت", callback_data="owner_status")],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="owner_block"),
         InlineKeyboardButton("✅ فك حظر مستخدم", callback_data="owner_unblock")],
        [InlineKeyboardButton("📋 قائمة المحظورين", callback_data="owner_list_blocked")],
        [InlineKeyboardButton("📢 إذاعة رسالة", callback_data="owner_broadcast")],
        [InlineKeyboardButton("💾 حفظ البيانات", callback_data="owner_save"),
         InlineKeyboardButton("🔄 تحميل البيانات", callback_data="owner_load")],
        [InlineKeyboardButton("📈 إحصائيات البوت", callback_data="owner_stats")],
        [InlineKeyboardButton("🔙 إغلاق", callback_data="owner_close")]
    ]
    
    reply_markup = InlineKeyboardMarkup(owner_keyboard)
    
    await update.message.reply_text(
        f"👑 <b>لوحة تحكم المطور</b>\n\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"⚙️ <b>حالة البوت:</b> {'🟢 يعمل' if BOT_STATUS == 'running' else '🔴 متوقف'}\n"
        f"👥 <b>المستخدمين:</b> {len(USER_DATABASE)}\n"
        f"🚫 <b>المحظورين:</b> {len(BLOCKED_USERS)}\n\n"
        f"📋 <b>اختر من القائمة:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def owner_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار لوحة المطور"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()
        
        if not is_developer(user_id):
            await query.message.edit_text("❌ <b>هذا الأمر للمطور فقط!</b>", parse_mode='HTML')
            return
        
        data = query.data
        
        if data == "owner_start":
            await owner_start_bot(query)
        elif data == "owner_stop":
            await owner_stop_bot(query)
        elif data == "owner_status":
            await owner_bot_status(query)
        elif data == "owner_block":
            await owner_block_user(query, context)
        elif data == "owner_unblock":
            await owner_unblock_user(query, context)
        elif data == "owner_list_blocked":
            await owner_list_blocked(query)
        elif data == "owner_broadcast":
            await owner_broadcast(query, context)
        elif data == "owner_save":
            save_data()
            await query.answer("✅ تم حفظ البيانات!", show_alert=True)
        elif data == "owner_load":
            load_data()
            await query.answer("✅ تم تحميل البيانات!", show_alert=True)
        elif data == "owner_stats":
            await owner_stats(query)
        elif data == "owner_close":
            await query.message.delete()
        
    except Exception as e:
        logger.error(f"Error in owner_button_click: {e}")

async def owner_start_bot(query):
    """تشغيل البوت"""
    global BOT_STATUS
    BOT_STATUS = "running"
    await query.message.edit_text("✅ <b>تم تشغيل البوت بنجاح!</b>", parse_mode='HTML')

async def owner_stop_bot(query):
    """إيقاف البوت"""
    global BOT_STATUS
    BOT_STATUS = "stopped"
    await query.message.edit_text("🛑 <b>تم إيقاف البوت بنجاح!</b>", parse_mode='HTML')

async def owner_bot_status(query):
    """عرض حالة البوت"""
    status_text = "🟢 <b>يعمل</b>" if BOT_STATUS == "running" else "🔴 <b>متوقف</b>"
    
    await query.message.edit_text(
        f"📊 <b>حالة البوت:</b>\n\n"
        f"⚙️ <b>الحالة:</b> {status_text}\n"
        f"👥 <b>المستخدمين:</b> {len(USER_DATABASE)}\n"
        f"🚫 <b>المحظورين:</b> {len(BLOCKED_USERS)}\n"
        f"🕒 <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        parse_mode='HTML'
    )

async def owner_block_user(query, context):
    """حظر مستخدم"""
    await query.message.edit_text(
        "🚫 <b>أرسل ID المستخدم للحظر:</b>",
        parse_mode='HTML'
    )
    context.user_data['owner_action'] = 'block'

async def owner_unblock_user(query, context):
    """فك حظر مستخدم"""
    await query.message.edit_text(
        "✅ <b>أرسل ID المستخدم لفك الحظر:</b>",
        parse_mode='HTML'
    )
    context.user_data['owner_action'] = 'unblock'

async def owner_list_blocked(query):
    """عرض المحظورين"""
    if not BLOCKED_USERS:
        await query.message.edit_text("✅ <b>لا يوجد محظورين</b>", parse_mode='HTML')
        return
    
    users_list = "\n".join([f"• <code>{uid}</code>" for uid in BLOCKED_USERS])
    await query.message.edit_text(
        f"📋 <b>المحظورين ({len(BLOCKED_USERS)}):</b>\n\n{users_list}",
        parse_mode='HTML'
    )

async def owner_broadcast(query, context):
    """إذاعة رسالة"""
    await query.message.edit_text(
        "📢 <b>أرسل الرسالة للإذاعة:</b>",
        parse_mode='HTML'
    )
    context.user_data['owner_action'] = 'broadcast'

async def owner_stats(query):
    """إحصائيات البوت"""
    total_ratings = sum(len(r) for r in BOT_RATINGS.values())
    
    await query.message.edit_text(
        f"📈 <b>إحصائيات البوت:</b>\n\n"
        f"👥 <b>المستخدمين:</b> {len(USER_DATABASE)}\n"
        f"🚫 <b>المحظورين:</b> {len(BLOCKED_USERS)}\n"
        f"⭐ <b>التقييمات:</b> {total_ratings}\n"
        f"📊 <b>الخدمات:</b> {len(BOT_RATINGS)}",
        parse_mode='HTML'
    )

# تحميل البيانات عند بدء التشغيل
load_data()

# ========== دالة إرسال إشعار للمطور عن مستخدم جديد ==========
async def send_new_user_notification(context: ContextTypes.DEFAULT_TYPE, user_id: int, user_name: str):
    """إرسال إشعار للمطور عند دخول مستخدم جديد"""
    try:
        # استخدام الـcontext مباشرة لإرسال الرسالة
        username = f"@{context.bot.username}" if context.bot.username else "لا يوجد"
        
        notification_message = (
            f"👤 <b>مستخدم جديد استخدم البوت!</b>\n\n"
            f"🆔 <b>ID المستخدم:</b> <code>{user_id}</code>\n"
            f"👑 <b>اسم المستخدم:</b> {user_name}\n"
            f"📱 <b>اليوزر:</b> {username}\n"
            f"🕒 <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👥 <b>إجمالي المستخدمين:</b> {len(USER_DATABASE)}\n\n"
            f"🔗 <b>رابط الملف الشخصي:</b> <a href='tg://user?id={user_id}'>المستخدم</a>"
        )
        
        # إرسال الرسالة للمطور مباشرة باستخدام context.bot
        await context.bot.send_message(
            chat_id=DEVELOPER_ID,
            text=notification_message,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
        logger.info(f"✅ تم إرسال إشعار للمطور عن مستخدم جديد: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال إشعار للمطور: {e}")

# حالة البوت (تشغيل/إيقاف)
BOT_STATUS = "running"  # running, stopped
DEVELOPER_ID = 7305720183

# قائمة المستخدمين الممنوعين (تم تحميلها بالفعل)
# BLOCKED_USERS = set()

# حالة انتظار الإدخال من المطور
DEVELOPER_WAITING_FOR_INPUT = {}

# قائمة المستخدمين الذين تفاعلوا مع البوت (لخدمة الإذاعة) (تم تحميلها بالفعل)
# USER_DATABASE = set()

# تخزين التقييمات (تم تحميلها بالفعل)
# BOT_RATINGS = {}

# تخزين بيانات التقييم للمستخدمين (تم تحميلها بالفعل)
# USER_RATING_DATA = {}

# قائمة الحالات الخاصة - إضافة الحالات الجديدة
SPECIAL_CASES = [
    "waiting_for_link", "waiting_for_name", "contact_developer", 
    "check_link", "temp_email_menu", "track_ip", "video_download_menu",
    "waiting_for_shorten", "image_bomb_site", "full_phone_hack",
    "read_qr_code", "ip_attack", "send_message_to_developer",
    "rate_bot", "more_features", "contacts_app", "fire_apps_menu",
    "xo_game_menu", "tv_hack", "whatsapp_unban", "instagram_ban",
    "tiktok_report", "virtual_numbers", "temp_email_btn", "btn_ttt", "btn_contacts",
    "phone_lock_app", "Dark_web"
]

# بيانات قنوات التلفزيون لكل دولة
tv_channels = {
    "مصر": {
        "links": [
            "تم اختراق 19 قناة 👑: ", 
            "📺 Aghapy TV (1080p)\n🔗 https://5b622f07944df.streamlock.net/aghapy.tv/aghapy.smil/playlist.m3u8",
            "📺 Al Ghad TV (1080p)\n🔗 https://eazyvwqssi.erbvr.com/alghadtv/alghadtv.m3u8",
            "📺 Al Masriyah\n🔗 https://viamotionhsi.netplus.ch/live/eds/almasriyah/browser-HLS8/almasriyah.m3u8",
            "📺 Alfath Sonnah TV (576p)\n🔗 https://alfat7-q.com:5443/LiveApp/streams/986613792230697141226562.m3u8",
            "📺 AlShoub (720p)\n🔗 https://play.tactivemedia.com/memfs/c5919b97-5329-4b84-91b2-613c6ed9953e.m3u8",
            "📺 ATVSat (1080p)\n🔗 https://stream.atvsat.com/atvsatlive/smil:atvsatlive.smil/playlist.m3u8",
            "📺 Coptic TV (720p)\n🔗 https://5aafcc5de91f1.streamlock.net/ctvchannel.tv/ctv.smil/playlist.m3u8",
            "📺 El Radio 9090 FM (480p)\n🔗 https://9090video.mobtada.com/hls/stream.m3u8",
            "📺 Elbeshara GTV (1080p)\n🔗 http://media3.smc-host.com:1935/elbesharagtv.com/gtv.smil/playlist.m3u8",
            "📺 Huda TV (720p)\n🔗 https://cdn.bestream.io:19360/elfaro1/elfaro1.m3u8",
            "📺 Koogi TV (1080p)\n🔗 https://5d658d7e9f562.streamlock.net/koogi.tv/koogi.smil/playlist.m3u8",
            "📺 MBC 1 Egypt (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-1-na/eec141533c90dd34722c503a296dd0d8/index.m3u8",
            "📺 MBC Masr (1080p)\n🔗 https://mbc1-enc.edgenextcdn.net/out/v1/d5036cabf11e45bf9d0db410ca135c18/index.m3u8",
            "📺 MBC Masr 2 (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-masr-2/754931856515075b0aabf0e583495c68/index.m3u8",
            "📺 Mekameleen TV (1080p)\n🔗 https://mn-nl.mncdn.com/mekameleen/smil:mekameleentv.smil/playlist.m3u8",
            "📺 Mix Hollywood (1080p)\n🔗 https://ml-pull-hwc.myco.io/MixTV/hls/index.m3u8",
            "📺 NogoumFMTV (672p)\n🔗 https://nogoumtv.nrpstream.com/hls/stream.m3u8",
            "📺 PNC Drama (1080p)\n🔗 https://d35j504z0x2vu2.cloudfront.net/v1/master/0bc8e8376bd8417a1b6761138aa41c26c7309312/pnc-drama/master.m3u8",
            "📺 Watan TV (1080p)\n🔗 https://rp.tactivemedia.com/watantv_source/live/playlist.m3u8"
        ]
    },
    "السعودية": {
        "links": [
            "تم اختراق 39 قناة 👑: ", 
            "📺 Abdulmajeed Abdullah (1080p)\n🔗 https://d2hng5r56zpsbw.cloudfront.net/out/v1/9c4c990f44bb4767bb46271f326dd574/index.m3u8",
            "📺 Al Arabiya Al Hadath (1080p)\n🔗 https://av.alarabiya.net/alarabiapublish/alhadath.smil/playlist.m3u8",
            "📺 Al Ekhbariya (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-al-ekhbaria/297b3ef1cd0633ad9cfba7473a686a06/index.m3u8",
            "📺 Al Quran Al Kareem TV (360p)\n🔗 https://cdn-globecast.akamaized.net/live/eds/saudi_quran/hls_roku/index.m3u8",
            "📺 Al Riyadh Radio (1080p)\n🔗 https://live.kwikmotion.com/sbrksariyadhradiolive/srpksariyadhradio/playlist.m3u8",
            "📺 Al Saudiya (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-saudi-tv/2ad66056b51fd8c1b624854623112e43/index.m3u8",
            "📺 Al Saudiya Alaan (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-ksa-now/71ed3aa814c643306c0a8bc4fcc7d17f/index.m3u8",
            "📺 Al Sunnah Al Nabawiyah TV (360p)\n🔗 https://cdn-globecast.akamaized.net/live/eds/saudi_sunnah/hls_roku/index.m3u8",
            "📺 Al-Majd Holy Quran\n🔗 https://edge66.magictvbox.com/liveApple/al_majd/tracks-v1a1/mono.m3u8",
            "📺 Alkhuzama Radio (1080p)\n🔗 https://live.kwikmotion.com/sbrksakhuzamaradiolive/srpkhuzama/playlist.m3u8",
            "📺 Asharq Discovery (1080p)\n🔗 https://svs.itworkscdn.net/asharqdiscoverylive/asharqd.smil/playlist_dvr.m3u8",
            "📺 Asharq Documentary (1080p)\n🔗 https://svs.itworkscdn.net/asharqdocumentarylive/asharqdocumentary.smil/playlist_dvr.m3u8",
            "📺 Asharq News (1080p)\n🔗 https://bcovlive-a.akamaihd.net/0b75ef0a49e24704a4ca023d3a82c2df/ap-south-1/6203311941001/playlist.m3u8",
            "📺 Asharq News Portrait (1280p)\n🔗 https://bcovlive-a.akamaized.net/ed81ac1118414d4fa893d3a83ccec9be/eu-central-1/6203311941001/playlist.m3u8",
            "📺 Asharq Radio (1080p)\n🔗 https://svs.itworkscdn.net/asharqradiovlive/asharqradiov/playlist.m3u8",
            "📺 Atfal & Mawaheb TV (1080p)\n🔗 https://5aafcc5de91f1.streamlock.net/atfal1.com/atfal2/playlist.m3u8",
            "📺 Bab Al Hara (1080p)\n🔗 https://shls-live-enc.edgenextcdn.net/out/v1/948c54279b594944adde578c95f1d7d1/index.m3u8",
            "📺 Big Time Plus (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-big-time-plus/924283f994779a311c1389698ff7e736/index.m3u8",
            "📺 Fairuz (1080p)\n🔗 https://shls-live-enc.edgenextcdn.net/out/v1/bba3ef00b71b470fa955d93a9ca8c277/index.m3u8",
            "📺 Iqraa Africa & Europe (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/dlkqw1ftuvuuzkcb4pxdcg/Iqraafasttv1/playlist.m3u8",
            "📺 Iqraa Arabic (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/dlkqw1ftuvuuzkcb4pxdcg/Iqraafasttv3/playlist.m3u8",
            "📺 Iqraa Quran (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/dlkqw1ftuvuuzkcb4pxdcg/Iqraafasttv2/playlist.m3u8",
            "📺 M+ (1080p)\n🔗 https://d35j504z0x2vu2.cloudfront.net/v1/master/0bc8e8376bd8417a1b6761138aa41c26c7309312/m-plus/master.m3u8",
            "📺 Majid Al Mohandis (1080p)\n🔗 https://shls-live-mood-ak.akamaized.net/out/v1/8e2419c6c7494dbba478be025af490ee/index.m3u8",
            "📺 Makkah TV (576p)\n🔗 https://media2.streambrothers.com:1936/8122/8122/playlist.m3u8",
            "📺 Maraya (1080p)\n🔗 https://shls-live-enc.edgenextcdn.net/out/v1/a4a39d8e92e34b0780ca602270a59512/index.m3u8",
            "📺 MBC Loud (1080p)\n🔗 https://d2lfa0y84k5bwn.cloudfront.net/out/v1/86dd4506a70c4d7fb35e2ab50296d9a3/index.m3u8",
            "📺 MBC Masr Drama (1080p)\n🔗 https://shls-live-enc.edgenextcdn.net/out/v1/08eca926a78a41339b8010c882410307/index.m3u8",
            "📺 Mohammed Abdo (1080p)\n🔗 https://d2ow8h651gs7dx.cloudfront.net/out/v1/371fb663da604e659a2fb99bf89d92d4/index.m3u8",
            "📺 Nidae AlIslam Radio (1080p)\n🔗 https://live.kwikmotion.com/sbrksanedaradiolive/srpksanedaradio/playlist.m3u8",
            "📺 Panorama FM (1080p)\n🔗 https://d6izdil55uftn.cloudfront.net/out/v1/0a06d1d6377c47edbd48721ed724bd08/index.m3u8",
            "📺 Quran Radio (1080p)\n🔗 https://live.kwikmotion.com/sbrksaquranradiolive/srpksaquranradio/playlist.m3u8",
            "📺 Rabeh Saqer (1080p)\n🔗 https://shls-live-enc.edgenextcdn.net/out/v1/ea4275b6dc0840c198c17f6dc6f1ec49/index.m3u8",
            "📺 Rashid AlMajed (1080p)\n🔗 https://dphwv2ufgnfsq.cloudfront.net/out/v1/59cd80dfe93a479eb8b4d79bc6f225ca/index.m3u8",
            "📺 Rotana Aflam+ (1080p)\n🔗 https://d35j504z0x2vu2.cloudfront.net/v1/master/0bc8e8376bd8417a1b6761138aa41c26c7309312/rotana-aflam-plus/master.m3u8",
            "📺 Saudi Thaqafiya TV (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-thaqafeyyah/28c0d2a20dbf1dc049ce15d3973f494b/index.m3u8",
            "📺 Saudia Radio (1080p)\n🔗 https://live.kwikmotion.com/sbrksasaudiaradiolive/srpksasaudiaradio/playlist.m3u8",
            "📺 SBC (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-sbc/90e09c0c28db26435799b4a14892a167/index.m3u8",
            "📺 Tarab (1080p)\n🔗 https://shls-live-enc.edgenextcdn.net/out/v1/90143f040feb40589d18c57863d9e829/index.m3u8"
        ]
    },
    "اليمن": {
        "links": [
            "تم اختراق 5 قنوات 👑: ", 
            "🔹 Al Masirah (720p) [Not 24/7]\n🌐https://live.cdnbridge.tv/Almasirah/Almasirah_all/playlist.m3u8",
            "🔹 Al Masirah Mubacher (642p) [Not 24/7]\n🌐https://live2.cdnbridge.tv/AlmasirahMubasher/Mubasher_All/playlist.m3u8", 
            "🔹 Al-Sahat TV (720p)\n🌐https://assahat.b-cdn.net/Assahat/assahatobs/index.m3u8", 
            "🔹 Yemen Shabab Channel (1080p)\n🌐https://starmenajo.com/hls/yemenshabab/index.m3u8", 
            "🔹 Yemen Today TV (480p)\n🌐https://video.yementdy.tv/hls/yementoday.m3u8"
        ]
    },
    "الإمارات": {
        "links": [
            "تم اختراق 35 قناة 👑: ", 
            "🔹 Abu Dhabi Emirates (1080p)\n🔗 https://admn-live-cdn-lb.starzplayarabia.com/out/v1/admn_tv_enc/emarat_tv/emarat_tv_hls_nd/index.m3u8",
            "🔹 Abu Dhabi Sports 1 (1080p)\n🔗 https://admn-live-cdn-lb.starzplayarabia.com/out/v1/admn_tv_enc/abudhabi_sports_1/abudhabi_sports_1_hls_nd/index.m3u8", 
            "🔹 Abu Dhabi Sports 2 (1080p)\n🔗 https://admn-live-cdn-lb.starzplayarabia.com/out/v1/admn_tv_enc/abudhabi_sports_2/abudhabi_sports_2_hls_nd/index.m3u8", 
            "🔹 Abu Dhabi TV (1080p)\n🔗 https://admn-live-cdn-lb.starzplayarabia.com/out/v1/admn_tv_enc/abudhabi_tv/abudhabi_tv_hls_nd/index.m3u8",
            "🔹 Ajman TV (1080p)\n🔗 https://cdn1.logichost.in/ajmantv/live/playlist.m3u8", 
            "🔹 Al Dafrah TV (720p)\n🔗 https://cdn-eu-west-prod-ingest-infra-dacast-com.akamaized.net/23cf2e00-28b0-b7b4-2569-ab7d19233fd7/index.m3u8", 
            "🔹 Al Shallal TV (1080p)\n🔗 https://amg01480-alshallalfze-alshallal-ono-q0hfg.amagi.tv/playlist.m3u8", 
            "🔹 Al Sharqiya Min Kabla (1080p)\n🔗 https://svs.itworkscdn.net/kablatvlive/kabtv1.smil/playlist.m3u8", 
            "🔹 Al Wousta TV (1080p)\n🔗 https://svs.itworkscdn.net/alwoustalive/alwoustatv.smil/playlist.m3u8", 
            "🔹 Al Yaum TV (1080p)\n🔗 https://iko-live.akamaized.net/AlyuamTV/master.m3u8",
            "🔹 Baynounah TV (1080p)\n🔗 https://admn-live-cdn-lb.starzplayarabia.com/out/v1/admn_tv_enc/baynounah/baynounah_hls_nd/index.m3u8", 
            "🔹 CNBC Arabiya (1080p)\n🔗 https://cnbc-live.akamaized.net/cnbc/master.m3u8", 
            "🔹 Dubai Racing (1080p)\n🔗 https://dmisdracta.cdn.mgmlcdn.com/events/smil:events.stream.smil/chunklist.m3u8", 
            "🔹 Dubai Racing 2 (1080p)\n🔗 https://dmithrvllta.cdn.mgmlcdn.com/dubairacing/smil:dubairacing.smil/chunklist.m3u8", 
            "🔹 Dubai Racing 3 (1080p)\n🔗 https://dmithrvllta.cdn.mgmlcdn.com/dubaimubasher/smil:dubaimubasher.smil/chunklist.m3u8", 
            "🔹 Dubai Sports 1 (1080p)\n🔗 https://dmidspta.cdn.mgmlcdn.com/dubaisports/smil:dubaisports.stream.smil/chunklist.m3u8", 
            "🔹 Dubai Sports 2 (720p)\n🔗 https://dmitwlvvll.cdn.mgmlcdn.com/dubaisportshd/smil:dubaisportshd.smil/chunklist.m3u8", 
            "🔹 Dubai Sports 3 (1080p) [Not 24/7]\n🔗 https://dmitwlvvll.cdn.mgmlcdn.com/dubaisportshd5/smil:dubaisportshd5.smil/chunklist.m3u8", 
            "🔹 Dubai TV (1080p)\n🔗 https://dmieigthvllta.cdn.mgmlcdn.com/dubaitvht/smil:dubaitv.stream.smil/chunklist.m3u8", 
            "🔹 Dubai Zaman (1080p) [Not 24/7]\n🔗 https://dmiffthftl.cdn.mangomolo.com/dubaizaman/smil:dubaizaman.stream.smil/chunklist.m3u8", 
            "🔹 Fujairah TV (720p)\n🔗 https://live.kwikmotion.com/fujairahlive/fujairah.smil/playlist.m3u8", 
            "🔹 Majid (1080p)\n🔗 https://admn-live-cdn-lb.starzplayarabia.com/out/v1/admn_tv_enc/majid/majid_hls_nd/index.m3u8", 
            "🔹 MBC Persia (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-persia/818ee8e4b592dc497608f066d825bfb4/index.m3u8", 
            "🔹 Noor Dubai (1080p)\n🔗 https://dmiffthftl.cdn.mangomolo.com/noordubaitv/smil:noordubaitv.smil/chunklist.m3u8", 
            "🔹 Nour TV\n🔗 https://cdn.bestream.io:19360/elfaro4/elfaro4.m3u8", 
            "🔹 Peace TV Chinese (1080p)\n🔗 https://dzkyvlfyge.erbvr.com/PeaceTvChinese/index.m3u8", 
            "🔹 Pulse95 Radio (1080p)\n🔗 https://svs.itworkscdn.net/pulse95live/pulse96/playlist.m3u8", 
            "🔹 Sama Dubai (1080p)\n🔗 https://dmieigthvllta.cdn.mgmlcdn.com/samadubaiht/smil:samadubai.stream.smil/chunklist.m3u8", 
            "🔹 Sharjah 2 (1080p)\n🔗 https://svs.itworkscdn.net/smc2live/smc2tv.smil/playlist.m3u8", 
            "🔹 Sharjah Radio (1080p)\n🔗 https://svs.itworkscdn.net/smcradiolive/smcradiolive/playlist.m3u8", 
            "🔹 Sharjah Radio Quran (1080p)\n🔗 https://live.kwikmotion.com/smcquranlive/quranradiolive/playlist.m3u8", 
            "🔹 Sharjah Sports (1080p) [Geo-blocked]\n🔗 https://svs.itworkscdn.net/smc4sportslive/smc4.smil/playlist.m3u8",
            "🔹 Sharjah TV (1080p)\n🔗 https://live.kwikmotion.com/smc1live/smc1tv.smil/playlist.m3u8", 
            "🔹 Watar Radio (1080p)\n🔗 https://svs.itworkscdn.net/smcwatarlive/smcwatar/playlist.m3u8", 
            "🔹 Yas TV (1080p)\n🔗 https://admn-live-cdn-lb.starzplayarabia.com/out/v1/admn_tv_enc/yas_1/yas_1_hls_nd/index.m3u8"
        ]
    },
    "الاردن": {
        "links": [
            "تم اختراق 26 قناة 👑: ",
            "🔹 Al Mamlaka TV (1080p)\n🔗 https://bcovlive-a.akamaihd.net/4109c7ba30fd4a44ad9afe917c67a8c8/eu-central-1/6415809151001/playlist_dvr.m3u8", 
            "🔹 Alerth Alnabawi Channel (576p)\n🔗 http://82.212.74.2:8000/live/7307.m3u8", 
            "🔹 Alhaqeqa Aldawlia (1080p)\n🔗 https://ghaasiflu.online/alhqeqa/index.m3u8", 
            "🔹 Altaghier TV (1080p)\n🔗 https://jmc-live.ercdn.net/altaghier/altaghier.m3u8", 
            "🔹 Amman TV (720p)\n🔗 https://ammantv-live.ercdn.net/ammantvhd/ammantvhd.m3u8", 
            "🔹 Jordan Archive (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/Archive/playlist.m3u8", 
            "🔹 Jordan Comedy (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/Comedy/playlist.m3u8", 
            "🔹 Jordan Drama (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/Drama/playlist.m3u8", 
            "🔹 Jordan Kitchen (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/cooking/playlist.m3u8", 
            "🔹 Jordan Satellite Channel (1080p)\n🔗 https://jrtv-live.ercdn.net/jordanhd/jordanhd.m3u8", 
            "🔹 Jordan Songs (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/Song/playlist.m3u8", 
            "🔹 Jordan Sport (1080p) [Geo-blocked]\n🔗 https://jrtv-live.ercdn.net/jordansporthd/jordansporthd.m3u8", 
            "🔹 Jordan Sport 2 (1080p) [Geo-blocked]\n🔗 https://jrtv-live.ercdn.net/learning2/learning2.m3u8", 
            "🔹 Jordan Tourism (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/cc0blorawy1ibohhrupraa/Tourism/playlist.m3u8", 
            "🔹 Kaifa TV (576p)\n🔗 http://82.212.74.2:8000/live/7311.m3u8", 
            "🔹 Melody FM Jordan (720p) [Not 24/7]\n🔗 https://cdn3.wowza.com/1/OVRrOWxXUEswS2Yv/eGVxSWZy/hls/live/playlist.m3u8", 
            "🔹 Radio Fann Jordan Studio (1080p) [Not 24/7]\n🔗 http://45.63.116.205/hls2/stream1.m3u8", 
            "🔹 Radio Yaqeen Jordan City View (1080p) [Not 24/7]\n🔗 http://45.63.116.205/hls4/stream1.m3u8", 
            "🔹 Rotana Radio Jordan Studio (1080p) [Not 24/7]\n🔗 http://45.63.116.205/hls/stream1.m3u8", 
            "🔹 Rotana Tarab Jordan City View (720p) [Not 24/7]\n🔗 http://45.63.116.205/hls3/stream1.m3u8", 
            "🔹 Roya Comedy (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/toa2uuhhygheuly7xtuqrg/roya-comedy/playlist.m3u8", 
            "🔹 Roya Drama (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/a2le4pbpa6rpzv147haf4w/drama/playlist.m3u8", 
            "🔹 Roya Kids\n🔗 https://playlist.fasttvcdn.com/pl/ptllxjd03j6g9oxxjdfapg/roya-kids/playlist.m3u8", 
            "🔹 Roya Kids Originals (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/ptllxjd03j6g9oxxjdfapg/roya-kids-originals/playlist.m3u8", 
            "🔹 Roya Kitchen (1080p)\n🔗 https://playlist.fasttvcdn.com/pl/toa2uuhhygheuly7xtuqrg/roya-kitchen/playlist.m3u8", 
            "🔹 Roya TV (1080p) [Not 24/7]\n🔗 https://royatv-live.daioncdn.net/royatv/royatv.m3u8"
            
        ]
    }, 
    "قطر": {
        "links": [
            "تم اختراق 7 قنوات 👑:", 
            "🔹 Al Jazeera Documentary (1080p) [Geo-blocked]\n🔗 https://live-hls-apps-ajd-fa.getaj.net/AJD/index.m3u8", 
            "🔹 Al Maaref (350p)\n🔗 https://672a3a5c8e335.streamlock.net/AlMaaref/smil:almaareflive.smil/playlist.m3u8", 
            "🔹 Al Rayyan (1080p)\n🔗 https://alrayyancdn.vidgyor.com/pub-noalrayy3pwz0l/liveabr/playlist_dvr.m3u8", 
            "🔹 Al Rayyan Al Qadeem (1080p)\n🔗 https://alrayyancdn.vidgyor.com/pub-nooldraybinbdh/liveabr/playlist_dvr.m3u8", 
            "🔹 Alkass Three (720p)\n🔗 https://streamer2.qna.org.qa/148161470_live/148161470_296.sdp/playlist.m3u8", 
            "🔹 Qatar Television (1080p)\n🔗 https://live.kwikmotion.com/qtv1live/qtv1.smil/playlist.m3u8", 
            "🔹 Qatar Television 2 (1080p)\n🔗 https://live.kwikmotion.com/qtv2live/qtv2.smil/playlist.m3u8"
        ] 
    }, 
    "البحرين": {
        "links": [
            "تم اختراق 4 قنوات 👑: ", 
            "🔹 Bahrain Quran (720p) [Not 24/7]\n🔗 https://5c7b683162943.streamlock.net/live/ngrp:bahrainquran_all/playlist.m3u8", 
            "🔹 Bahrain Sports 1 (720p) [Not 24/7]\n🔗 https://5c7b683162943.streamlock.net/live/ngrp:sportsone_all/playlist.m3u8", 
            "🔹 Bahrain Sports 2 (720p) [Not 24/7]\n🔗 https://5c7b683162943.streamlock.net/live/ngrp:bahrainsportstwo_all/playlist.m3u8", 
            "🔹 Bahrain TV (720p) [Not 24/7]\n🔗 https://5c7b683162943.streamlock.net/live/ngrp:bahraintvmain_all/playlist.m3u8"
        ] 
    }, 
    "الكويت": {
        "links": [
            "تم اختراق 11 قناة 👑:", 
            "🔹 Bahry (1080p)\n🔗 https://live.kwikmotion.com/bahry1live/bahry1.smil/playlist.m3u8", 
            "🔹 Ch4Teen\n🔗 https://ch14.tv/live/ch4teenclip/playlist.m3u8", 
            "🔹 KTV 1 (1080p)\n🔗 https://kwtktv1ta.cdn.mangomolo.com/ktv1/smil:ktv1.stream.smil/chunklist.m3u8", 
            "🔹 KTV 2 (1080p)\n🔗 https://kwtktv2ta.cdn.mangomolo.com/ktv2/smil:ktv2.stream.smil/chunklist.m3u8", 
            "🔹 KTV Al Qurain (1080p)\n🔗 https://kwtktvaqta.cdn.mangomolo.com/ktvaq/smil:tktvaq.stream.smil/chunklist.m3u8", 
            "🔹 KTV Arabe (1080p)\n🔗 https://kwtktvata.cdn.mangomolo.com/ktva/smil:tktva.stream.smil/chunklist.m3u8", 
            "🔹 KTV Ethraa (1080p)\n🔗 https://kwtethta.cdn.mangomolo.com/eth/smil:eth.stream.smil/chunklist.m3u8", 
            "🔹 KTV News (1080p)\n🔗 https://kwtkbta.cdn.mangomolo.com/kb/smil:kb.stream.smil/chunklist.m3u8", 
            "🔹 KTV Sport (1080p)\n🔗 https://kwtspta.cdn.mangomolo.com/sp/smil:sp.stream.smil/chunklist.m3u8", 
            "🔹 KTV Sport Plus (1080p)\n🔗 https://kwtsplta.cdn.mangomolo.com/spl/smil:spl.stream.smil/chunklist.m3u8", 
            "🔹 Marina TV (1080p)\n🔗 https://ffs.gulfsat.com/Marina-TV-HD/index.m3u8"
        ] 
    }, 
    "عمان": {
        "links": [
            "تم اختراق 5 قنوات 👑: ", 
            "🔹 Alistiqama TV (576p)\n🔗 https://jmc-live.ercdn.net/alistiqama/alistiqama.m3u8", 
            "🔹 Oman Althakafia (1080p)\n🔗 https://partwota.cdn.mgmlcdn.com/omcultural/smil:omcultural.stream.smil/chunklist.m3u8", 
            "🔹 Oman Mubashir (1080p)\n🔗 https://partwota.cdn.mgmlcdn.com/omlive/smil:omlive.stream.smil/chunklist.m3u8", 
            "🔹 Oman Sports TV (1080p) [Not 24/7]\n🔗 https://partneta.cdn.mgmlcdn.com/omsport/smil:omsport.stream.smil/chunklist.m3u8", 
            "🔹 Oman TV (1080p)\n🔗 https://partneta.cdn.mgmlcdn.com/omantv/smil:omantv.stream.smil/chunklist.m3u8"
        ] 
    }, 
    "لبنان": {
        "links": [
            "تم اختراق 30 قناة 👑: ", 
            "🔹 Aghani Aghani TV (1080p) [Not 24/7]\n🔗 https://streaming-a-1035.cdn.nextologies.com/6zj8y5nemi8a32vyjjbkv0oqx/77pcakd8reik3g8qdqnexlkmq/playlist.m3u8", 
            "🔹 Al Ittihad (552p) [Not 24/7]\n🔗 http://185.105.4.151:8080/_defapp_/ittihad/index.m3u8", 
            "🔹 Al Jadeed (1080p)\n🔗 http://185.9.2.18/chid_391/mono.m3u8", 
            "🔹 Al Manar (576p) [Not 24/7]\n🔗 https://edge.fastpublish.me/live/index.m3u8", 
            "🔹 Al Mayadeen (576p)\n🔗 https://mdnlv.cdn.octivid.com/almdn/smil:mpegts.stream.smil/playlist.m3u8", 
            "🔹 Aliman TV (240p) [Not 24/7]\n🔗 https://svs.itworkscdn.net/alimanlive/imantv.smil/playlist.m3u8", 
            "🔹 ALWifak News TV (720p)\n🔗 http://alwifaklive.info:1935/live/myStream/playlist.m3u8", 
            "🔹 ALWifak News TV (720p)\n🔗 http://alwifaklive.info:1935/live/myStream/playlist.m3u8", 
            "🔹 Arabica TV (720p)\n🔗 http://istream.binarywaves.com:8081/hls/arabica/playlist.m3u8", 
            "🔹 Assirat TV (576p)\n🔗 https://softverse.b-cdn.net/Assirat/assiratobs/playlist.m3u8", 
            "🔹 Charity TV\n🔗 https://652930de05533.streamlock.net/live/ngrp:livestream_all/playlist.m3u8", 
            "🔹 Future TV (1080p)\n🔗 https://live.kwikmotion.com/futurelive/ftv.smil/playlist.m3u8", 
            "🔹 LTV (360p)\n🔗 https://p-ltv.akamaized.net/ltv/ltv.m3u8", 
            "🔹 Nabaa TV (720p) [Not 24/7]\n🔗 http://31.14.40.237:1935/live/Nabaa/playlist.m3u8", 
            "🔹 NBN (1080p)\n🔗 http://5.9.119.146:8883/nbn/index.m3u8", 
            "🔹 Nour Al Koddas (406p) [Not 24/7]\n🔗 https://svs.itworkscdn.net/nour1satlive/livestream/playlist.m3u8", 
            "🔹 Nour Al Sharq (576p)\n🔗 https://svs.itworkscdn.net/nour8satlive/livestream/playlist.m3u8", 
            "🔹 Nour El Shabeb\n🔗 https://svs.itworkscdn.net/nour3satlive/livestream/playlist.m3u8", 
            "🔹 Nour Mariam (576p)\n🔗 https://svs.itworkscdn.net/nour9satlive/livestream/playlist.m3u8", 
            "🔹 NourSAT (576p)\n🔗 https://svs.itworkscdn.net/nour4satlive/livestream/playlist.m3u8", 
            "🔹 Noursat English (576p)\n🔗 https://svs.itworkscdn.net/noursatenglive/noursateng.smil/playlist.m3u8", 
            "🔹 One TV (720p)\n🔗 https://hms.pfs.gdn/v1/broadcast/one/playlist.m3u8", 
            "🔹 OneFM (720p) [Not 24/7]\n🔗 https://hms.pfs.gdn/v1/broadcast/onefm/playlist.m3u8", 
            "🔹 OTV (1080p)\n🔗 https://otv.hibridcdn.net/otv/tv_abr/playlist.m3u8", 
            "🔹 Palestine Al Yawm (720p)\n🔗 https://live.paltodaytv.com/paltv/live/playlist_sfm4s.m3u8", 
            "🔹 Red TV Lebanon (1080p)\n🔗 https://live.kwikmotion.com/redtvlive/redtv.smil/playlist.m3u8", 
            "🔹 Senses TV (1080p)🔹 Senses TV (1080p)\n🔗 http://31.14.41.69:8080/hls/sensesonline/index.m3u8", 
            "🔹 Taha TV\n🔗 https://media1.livaat.com/static/TAHA_TV/playlist.m3u8", 
            "🔹 Tele Liban (720p) [Not 24/7]\n🔗 https://cdn.catiacast.video/abr/ed8f807e2548db4507d2a6f4ba0c4a06/playlist.m3u8", 
            "🔹 UNews\n🔗 https://cdn.catiacast.video/abr/9436b5ab3c1171ab04a59af11951292f/playlist.m3u8", 
            "🔹 Voice of Lebanon (1080p)\n🔗 https://svs.itworkscdn.net/vdltvlive/vdltv.smil/playlist.m3u8"
        ] 
    }, 
    "سوريا": {
        "links": [
            "تم اختراق 8 قنوات 👑:", 
            "🔹 Alalam News Channel Syria (1080p)\n🔗 https://live2.alalam.ir/live/Alalam/index.m3u8", 
            "🔹 Althania (1080p)\n🔗 https://live.kwikmotion.com/syriatv02live/syriatv02.smil/playlist.m3u8", 
            "🔹 Halab Today TV (1080p)\n🔗 https://mn-nl.mncdn.com/halabtoday/livestream/index.m3u8", 
            "🔹 Rojava TV (1080p)\n🔗 https://iko-streamline-live1.akamaized.net/RojavaTV/master.m3u8", 
            "🔹 Ronahi TV (1080p)\n🔗 https://hlspackager.akamaized.net/live/DB/RONAHI_TV/HLS/RONAHI_TV.m3u8", 
            "🔹 Syria One (1080p)\n🔗 https://live.syriaone.tv/live/syriaone.m3u8", 
            "🔹 Syria TV (1080p)\n🔗 https://live.kwikmotion.com/syriatvlive/syriatv.smil/playlist_dvr.m3u8", 
            "🔹 Welat TV (1080i)\n🔗 https://stream.badinan.xyz/welat/tv/playlist.m3u8"
        ] 
    }, 
    "العراق": {
        "links": [
            "تم اختراق 62 قناة 👑: ", 
            "🔹 Abalfadhl TV\n🔗 https://t.northtelecom.org/ABALFADHLTV.m3u8", 
            "🔹 ABNsat (720p)\n🔗 https://mediaserver.abnvideos.com/streams/abnsat.m3u8", 
            "🔹 Afaq TV\n🔗 http://63b03f7689049.streamlock.net:1935/live/1/playlist.m3u8", 
            "🔹 Afarin Baxcha (1080p)\n🔗 https://5dcabf026b188.streamlock.net/afarinTV/livestream/playlist.m3u8", 
            "🔹 Afarin TV (720p) [Not 24/7\n🔗 https://65f16f0fdfc51.streamlock.net/afarinTV/livestream/playlist.m3u8", 
            "🔹 Al Ahad TV\n🔗 http://63b03f7689049.streamlock.net:1935/live/7/playlist.m3u8", 
            "🔹 Al Ayyam TV\n🔗 http://63b03f7689049.streamlock.net:1935/live/6/playlist.m3u8",
            "🔹 Al Eshraq TV\n🔗 http://63b03f7689049.streamlock.net:1935/live/19/playlist.m3u8", 
            "🔹 Al Etejah TV\n🔗 http://63b03f7689049.streamlock.net:1935/live/33/playlist.m3u8",
            "🔹 Al Iraqia (720p)\n🔗 https://cdn.catiacast.video/abr/8d2ffb0aba244e8d9101a9488a7daa05/playlist.m3u8",
            "🔹 Al Iraqia News (720p)\n🔗 https://cdn.catiacast.video/abr/78054972db7708422595bc96c6e024ac/playlist.m3u8",
            "🔹 Al Janoub TV\n🔗 http://63b03f7689049.streamlock.net:1935/live/18/playlist.m3u8", 
            "🔹 Al Nujaba\n🔗 http://63b03f7689049.streamlock.net:1935/live/3/playlist.m3u8", 
            "🔹 Al Rasheed TV (1080p) [Not 24/7]\n🔗 https://media1.livaat.com/static/AL-RASHEED-HD/playlist.m3u8",
            "🔹 Al-Jawadain TV (1080p) [Not 24/7]\n🔗 https://live.aljawadain.org/live/aljawadaintv/playlist.m3u8",
            "🔹 Al-Naeem TV (576p)\n🔗 https://nl2.livekadeh.com/hls2/alnaeem.m3u8",
            "🔹 Al-Sharqiya (1080p)\n🔗 https://5d94523502c2d.streamlock.net/home/mystream/playlist.m3u8", 
            "🔹 Al-Sharqiya News (1080p)\n🔗 https://5d94523502c2d.streamlock.net/alsharqiyalive/mystream/playlist.m3u8", 
            "🔹 Alawla TV (720p)\n🔗 https://63b03f7689049.streamlock.net/live/1tv/playlist.m3u8",
            "🔹 Alhurra (720p)\n🔗 https://mbn-ingest-worldsafe.akamaized.net/hls/live/2038900/MBN_Alhurra_Worldsafe_HLS/master.m3u8", 
            "🔹 Alhurra Iraq (720p)\n🔗 https://mbn-ingest-worldsafe.akamaized.net/hls/live/2038899/MBN_Iraq_Worldsafe_HLS/master.m3u8", 
            "🔹 Alquran (1080p)\n🔗 https://ktvlive.online/stream/hls/ch1.m3u8", 
            "🔹 AVA Family\n🔗 https://familyhls.avatv.live/hls/stream.m3u8", 
            "🔹 Avar TV (1080p)\n🔗 https://avr.host247.net/live/AvarTv/playlist.m3u8", 
            "🔹 Bayyinat TV (404p)\n🔗 https://nl2.livekadeh.com/hls2/Bayyinat.m3u8", 
            "🔹 BeitolAbbas TV Channel (720p)\n🔗 https://live.beitolabbas.tv/live/beitolabbastv.m3u8", 
            "🔹 Channel 8 Kurdish (720p)\n🔗 https://live.channel8.com/Channel8-Kurdish/index.fmp4.m3u8", 
            "🔹 Dijlah TV (1080p)\n🔗 https://ghaasiflu.online/Dijlah/index.m3u8", 
            "🔹 EmanTv (1080p)\n🔗 https://avr.host247.net/live/emantv/playlist.m3u8", 
            "🔹 FarmodaTV (1080p)\n🔗 https://avr.host247.net/live/FarmodaTV/playlist.m3u8", 
            "🔹 Hadi TV Azeri and Russian (720p)\n🔗 https://live.ishiacloud.com/haditv.co.uk/haditv3.m3u8", 
            "🔹 Hadi TV English and Urdu (720p)\n🔗 https://live.ishiacloud.com/haditv.co.uk/haditv1.m3u8", 
            "🔹 Hadi TV Farsi (720p)\n🔗 https://live.ishiacloud.com/haditv.co.uk/haditv4.m3u8", 
            "🔹 Hadi TV Hausa (720p)\n🔗 https://live.ishiacloud.com/haditv.co.uk/haditv5.m3u8", 
            "🔹 Hadi TV Pashto and Persian (720p)\n🔗 https://live.ishiacloud.com/haditv.co.uk/haditv6.m3u8", 
            "🔹 Imam Asr TV (720p)\n🔗 https://iptv.imamasrtv.com/asrfa/playlist.m3u8", 
            "🔹 Imam Hussein TV 1 (1080p) [Not 24/7]\n🔗 https://live.imamhossaintv.com/live/ih1.m3u8", 
            "🔹 Imam Hussein TV 2 (1080p) [Not 24/7]\n🔗 https://live.imamhossaintv.com/live/ih2.m3u8", 
            "🔹 Imam Hussein TV 3 (1080p) [Not 24/7]\n🔗 https://live.imamhossaintv.com/live/ih3.m3u8", 
            "🔹 Imam Hussein TV 4 (1080p) [Not 24/7]\n🔗 https://live.imamhossaintv.com/live/ih4.m3u8", 
            "🔹 iNEWS TV (1080p)\n🔗 https://live.i-news.tv/hls/stream.m3u8", 
            "🔹 Iraq Future\n🔗 https://viewmedia7219.bozztv.com/wmedia/viewmedia100/web_040/Stream/playlist.m3u8", 
            "🔹 Kurdistan 24 (720p)\n🔗 https://d1x82nydcxndze.cloudfront.net/live/index.m3u8", 
            "🔹 Kurdistan TV (720p) [Not 24/7]\n🔗 https://5a3ed7a72ed4b.streamlock.net/live/SMIL:myStream.smil/playlist.m3u8", 
            "🔹 KurdMax Music (720p)\n🔗 https://6476e46b58f91.streamlock.net/music/MUSIC2402/playlist.m3u8", 
            "🔹 KurdMax Show (720p)\n🔗 https://6476e46b58f91.streamlock.net/liveTrans/SHOWS123/playlist.m3u8", 
            "🔹 KurdMax Sorani (1080p)\n🔗 https://6476e46b58f91.streamlock.net/liveTrans/KURDS2211/playlist.m3u8",
            "🔹 Kurdsat (1080p)\n🔗 https://iko-live.akamaized.net/KurdsatTV/master.m3u8", 
            "🔹 Kurdsat News (1080p)\n🔗 https://hlspackager.akamaized.net/live/DB/KURDSAT_NEWS/HLS/KURDSAT_NEWS.m3u8", 
            "🔹 Marjaeyat TV Arabic (1080p)\n🔗 https://livefa.marjaeyattv.com/mtv_ar/playlist.m3u8", 
            "🔹 Marjaeyat TV English (1080p)\n🔗 https://livefa.marjaeyattv.com/mtv_en/playlist.m3u8", 
            "🔹 Marjaeyat TV Persian (240p) [Not 24/7]\n🔗 https://livefa.marjaeyattv.com/mtv_fa/playlist.m3u8",
            "🔹 MBC Iraq (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-iraq/e38c44b1b43474e1c39cb5b90203691e/index.m3u8", 
            "🔹 Mixkurdy (1080p)\n🔗 https://avr.host247.net/live/Mix-kurdy/playlist.m3u8", 
            "🔹 NRT TV (720p) [Not 24/7]\n🔗 https://media.streambrothers.com:1936/8226/8226/playlist.m3u8", 
            "🔹 NUBAR Plus TV (720p)\n🔗 http://stream.nubar.tv:1935/private/NUBARPlus/playlist.m3u8", 
            "🔹 Payam TV (720p) [Not 24/7]\n🔗 https://media2.streambrothers.com:1936/8218/8218/playlist.m3u8", 
            "🔹 Rudaw TV (1080p)\n🔗 https://svs.itworkscdn.net/rudawlive/rudawlive.smil/playlist.m3u8", 
            "🔹 Shams TV (1080p)\n🔗 https://stream.shams.tv/hls/stream.m3u8", 
            "🔹 UTV (1080p)\n🔗 https://mn-nl.mncdn.com/utviraqi2/64c80359/index.m3u8", 
            "🔹 Waar TV (1080p)\n🔗 https://live.kwikmotion.com/waarmedialive/waarmedia.smil/waarmediapublish/waarmedia_source/chunks.m3u8", 
            "🔹 Zagros (720p) [Not 24/7]\n🔗 https://5a3ed7a72ed4b.streamlock.net/zagrostv/SMIL:myStream.smil/playlist.m3u8"
        ]
    },
    "المغرب": {
        "links": [
            "تم اختراق 10 قنوات 👑", 
            "🔹 2M Monde +1 (1080p)\n🔗 https://d2qh3gh0k5vp3v.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-n6pess5lwbghr/2M_ES.m3u8", 
            "🔹 Al Maghribia\n🔗 https://viamotionhsi.netplus.ch/live/eds/almaghribia/browser-dash/almaghribia.mpd", 
            "🔹 Chada TV (720p)\n🔗 https://chadatv.vedge.infomaniak.com/livecast/chadatv/playlist.m3u8", 
            "🔹 CNA (Chaîne Nord Africaine) (360p) [Not 24/7]\n🔗 https://live.creacast.com/cna/smil:cna.smil/playlist.m3u8", 
            "🔹 MBC 5 (1080p)\n🔗 https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-5/ee6b000cee0629411b666ab26cb13e9b/index.m3u8", 
            "🔹 Medi1TV Afrique (1080p)\n🔗 https://cdn.live.easybroadcast.io/abr_corp/83_medi1tv-afrique_tm7tu45/playlist.m3u8", 
            "🔹 Medi 1 TV Arabic (1080p)\n🔗 https://cdn.live.easybroadcast.io/abr_corp/83_medi1tv-arabic_g90v4ec/playlist.m3u8", 
            "🔹 Medi 1 TV Maghreb (1080p)\n🔗 https://cdn.live.easybroadcast.io/abr_corp/83_medi1tv-maghreb_jnbspmg/playlist.m3u8", 
            "🔹 StoryChannel TV (720p)\n🔗 https://136044159.r.cdnsun.net/storychannel.m3u8", 
            "🔹 Tele Maroc (1080p)\n🔗 https://raw.githubusercontent.com/ipstreet312/freeiptv/refs/heads/master/ressources/wld/tlma.m3u8"
        ]
    }, 
    "الجزائر": {
        "links": [
            "تم اختراق 5 قنوات 👑:", 
            "🔹 Amou Yazid TV (576p)\n🔗 http://mkstream.servehttp.com:1940/AmouYazid/ay1/playlist.m3u8",
            "🔹 CNA (Chaîne Nord Africaine) (360p) [Not 24/7]\n🔗 https://live.creacast.com/cna/smil:cna.smil/playlist.m3u8", 
            "🔹 StoryChannel TV (720p)\n🔗 https://136044159.r.cdnsun.net/storychannel.m3u8", 
            "🔹 TV2\n🔗 https://viamotionhsi.netplus.ch/live/eds/canalalgerie/browser-dash/canalalgerie.mpd", 
            "🔹 TV4 Tamazight TV (576p)\n🔗 http://149.62.177.98:8000/play/a01t/index.m3u8"
        ]
    }, 
    "تونس": {
        "links": [
            "تم اختراق 4 قنوات 👑:", 
            "🔹 Jawhara TV (720p) [Not 24/7]\n🔗 http://streaming.toutech.net:1935/live/mp4:jawharafm.sdp/playlist.m3u8", 
            "🔹 Mosaique FM (1080p)\n🔗 https://webcam.mosaiquefm.net/mosatv/_definst_/studio/playlist.m3u8?DVR", 
            "🔹 Nessma El Jadida\n🔗 https://fl1002.bozztv.com/ga-nessmatv/tracks-v1a1/mono.m3u8", 
            "🔹 StoryChannel TV (720p)\n🔗 https://136044159.r.cdnsun.net/storychannel.m3u8"
        ] 
    }, 
    "ليبيا": {
        "links": [
            "تم اختراق 5 قنوات 👑:", 
            "🔹 Al Masar TV (576p)\n🔗 https://starmenajo.com/hls/almasar/index.m3u8", 
            "🔹 February Channel (1080p)\n🔗 https://b01c02nl.mediatriple.net/videoonlylive/mtfknklgwrlive/broadcast_5dc818c793576.smil/playlist.m3u8", 
            "🔹 Libya Al Wataniya (360p)\n🔗 https://cdn-globecast.akamaized.net/live/eds/libya_al_watanya/hls_roku/index.m3u8", 
            "🔹 StoryChannel TV (720p)\n🔗 https://136044159.r.cdnsun.net/storychannel.m3u8",
            "🔹 Tanasuh TV (1080p)\n🔗 https://kilolink.pulsarstarsolutions.com/live/smil:tanasuhtv.smil/manifest.m3u8"
        ] 
    }, 
    "السودان": {
        "links": [
            "تم اختراق 3 قنوات 👑:", 
            "🔹 Al Alamiya 2\n🔗 http://82.212.74.98:8000/live/7815.m3u8", 
            "🔹 Dabanga TV (1080p)\n🔗 https://hls.dabangasudan.org/hls/stream.m3u8", 
            "🔹 Sudan TV (360p)\n🔗 https://cdn-globecast.akamaized.net/live/eds/sudan_tv/hls_roku/index.m3u8"
        ]
    }, 
    "فلسطين": {
        "links": [
            "تم اختراق 16 قناة 👑:", 
            "🔹 Ajyal TV (720p)\n🔗 http://htvmada.mada.ps:8888/ajyal/index.m3u8",
            "🔹 Al Aqsa Channel (416p) [Not 24/7\n🔗 http://167.172.161.13/hls/feedspare/6udfi7v8a3eof6nlps6e9ovfrs65c7l7.m3u8", 
            "🔹 Al Madina (720p)\n🔗 https://streaming.zaytonatube.com:8081/AlMadinatv/almadina21/index.m3u8", 
            "🔹 Al Najah News (720p)\n🔗 https://streaming.najah.edu:8443/hls/AlNajah.m3u8",
            "🔹 Falastini TV (1080p)\n🔗 https://rp.tactivemedia.com/palestiniantv_source/live/playlist.m3u8", 
            "🔹 Hala Ramallah (720p)\n🔗 https://halaramallahtv.com:2053/HRamallah-Tv/HalaRamallah/playlist.m3u8",
            "🔹 Holy Quran Radio Nablus (720p)\n🔗 http://streaming.zaytonatube.com:8080/holyquran/holyquran/video.m3u8", 
            "🔹 Kolalnas TV\n🔗 https://htvint.mada.ps/kolalnas/index.m3u8", 
            "🔹 Nablus TV (1080p)\n🔗 https://htvint.mada.ps/nabluslive/index.m3u8",
            "🔹 Palestine Edu (1080p)\n🔗 https://pbc.furrera.ps/PalestineEDU/index.m3u8", 
            "🔹 Palestine Today (480p) [Geo-blocked]\n🔗 https://live.paltodaytv.com/paltv/live/playlist.m3u8", 
            "🔹 Radio Albalad TV (720p)\n🔗 http://streaming.zaytonatube.com:8080/radioalbalad/radioalbalad/playlist.m3u8", 
            "🔹 Rajeen TV (1080p) [Not 24/7]\n🔗 https://mn-nl.mncdn.com/palabroad/live/playlist.m3u8", 
            "🔹 Raya 1 (1080p)\n🔗 https://htvmada.mada.ps:4443/raya/index.m3u8", 
            "🔹 Shabab FM (720p) [Not 24/7]\n🔗 https://streaming.zaytonatube.com:8081/ShababFM/shabab/index.m3u8", 
            "🔹 Watar TV (720p) [Not 24/7]\n🔗 http://htvint.mada.ps:8889/orient/index.m3u8"
        ] 
    }, 
    "موريتانيا": {
        "links": [
            "تم اختراق 2 قنوات 👑:",
            "🔹 El Oussra TV\n🔗 https://dvrfl06.bozztv.com/astv-elousra/index.m3u8", 
            "🔹 StoryChannel TV (720p)\n🔗 https://136044159.r.cdnsun.net/storychannel.m3u8"
        ]
    },
    "الصومال": {
        "links": [
            " تم اختراق 9 قنوات 👑: ", 
            "🔹 Arlaadi TV\n🔗 https://ap02.iqplay.tv:8082/iqb8002/alr114iapp/playlist.m3u8", 
            "🔹 Bulsho TV\n🔗 https://cdn.mediavisionuk.com:9000/bulshotv/index.m3u8", 
            "🔹 Hirshabelle TV (576p)\n🔗 http://ap02.iqplay.tv:8081/iqb8002/h1rshbe1iptv/playlist.m3u8", 
            "🔹 MM Somali TV (720p)\n🔗 https://cdn.mediavisionuk.com:9000/MMTV/index.m3u8", 
            "🔹 Puntland TV (720p)\n🔗 http://cdn.mediavisionuae.com:1935/live/putlandtv2.stream/playlist.m3u8", 
            "🔹 Saab TV (576p)\n🔗 https://ap02.iqplay.tv:8082/iqb8002/s03btv/playlist.m3u8", 
            "🔹 SBC TV (720p) [Not 24/7]\n🔗 http://cdn.mediavisionuae.com:1935/live/sbctv.stream/playlist.m3u8", 
            "🔹 SNTV Daljir (576p)\n🔗 https://ap02.iqplay.tv:8082/iqb8002/s2tve/playlist.m3u8", 
            "🔹 Somali National TV (576p)\n🔗 https://ap02.iqplay.tv:8082/iqb8002/s4ne/playlist.m3u8"
        ] 
    }, 
    "جيبوتي": {
        "links": [
            "تم اختراق 2 قنوات 👑:", 
            "🔹 RTD\n🔗 https://dvrfl06.bozztv.com/astv-djibouti/index.m3u8", 
            "🔹 RTD 4\n🔗 http://dvrfl05.bozztv.com/gin-rtddjibouti/index.m3u8"
        ] 
    } 
} 

# إعدادات الروابط والأسماء
LINKS_INFO = {
    "btn1": {
        "name": "📷 <b>إختراق الكاميرا الأمامية</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/c2/?chatId={user_id}"
    },
    "btn2": {
        "name": "📸 <b>إختراق الكاميرا الخلفية</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/c1/?chatId={user_id}"
    },
    "btn3": {
        "name": "🎙️ <b>تسجيل صوت الضੂحيه</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/au/?chatId={user_id}"
    },
    "btn4": {
        "name": "🎥 <b>تصوير فيديو للضحية</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/vi/?chatId={user_id}"
    },
    "btn5": {
        "name": "📌 <b>إختراق إنستجرام</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/Instagram/?chatId={user_id}"
    },
    "btn6": {
        "name": "❗ <b>إختراق واتساب</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/WhatsApp/?chatId={user_id}"
    },
    "btn7": {
        "name": "🎯 <b>إختراق ببجي</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/pubg/?chatId={user_id}"
    },
    "btn8": {
        "name": "💥 <b>إختراق فري فاير</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/freefire/?chatId={user_id}"
    },
    "btn9": {
        "name": "🌐 <b>إختراق فيسبوك</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/Facebook/?chatId={user_id}"
    },
    "btn10": {
        "name": "👻 <b>إختراق سناب شات</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/Snapchat/?chatId={user_id}"
    },
    "btn11": {
        "name": "💣 <b>إختراق تيك توك</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/Tiktok/?chatId={user_id}"
    },
    "btn12": {
        "name": "📲 <b>جمع معلومات الجهاز</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/dev/?chatId={user_id}"
    },
    "btn_wifi": {
        "name": "🛜 <b>إختراق الواي فاي</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/Wifi/?chatid={user_id}"
    },
    "btn15": {
        "name": "🔞 <b>سحب صور الضੂحيه</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/photo/?chatid={user_id}"
    }, 
    "btn16": {
        "name": "🔝 <b>اخـ~ـتراق بال باي</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/PalPay/?chatid={user_id}"
    },
    "btn17": {
        "name": "🎬 <b>اخـ~ـتراق كواي</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/Kwai/?chatid={user_id}"
    }, 
    "btn160": {
        "name": "🕊 <b>اخـ~تـراق تويتر</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/Twitter/?chatid={user_id}"
    },
    "btn19": {
        "name": "🔉 <b>اخـ~ـتراق نتفلكس</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/Netflix/?chatid={user_id}"
    }, 
    "btn20": {
        "name": "🎓 <b>اخـ~ـتراق يوتيوب</b>",
        "original": "https://aesthetic-platypus-05ca99h.netlify.app/Youtube/?chatid={user_id}"
    }, 
}

# الأزرار الرئيسية
BUTTONS = [
    [
        InlineKeyboardButton("اخـ^_^ـراق كاميرا خلفية", callback_data="btn2", style="danger"),
        InlineKeyboardButton("اخـ^_^ـراق كاميرا امامية", callback_data="btn1", style="danger")
    ],
    [
        InlineKeyboardButton("تصوير الضੂحيه فيديو", callback_data="btn4", style="danger"),
        InlineKeyboardButton("تسجيل صوت الضੂحيه", callback_data="btn3", style="danger")
    ],
    [
        InlineKeyboardButton("اخـ^_^ـراق ꫂاتـسـٖ͜ـاب", callback_data="btn6", style="danger"),
        InlineKeyboardButton("اخـ^_^ـراق انـس̸ـ꯭ـتـا", callback_data="btn5", style="danger")
    ],
    [
        InlineKeyboardButton("اخـ^_^ـراق W i F i", callback_data="btn_wifi", style="danger"),
        InlineKeyboardButton("اخـ^_^ـراق ببــﭻـﯥ", callback_data="btn7", style="danger")
    ],
    [
        InlineKeyboardButton("اخـ^_^ـراق فري فاير", callback_data="btn8", style="danger"),
        InlineKeyboardButton("اخـ^_^ـراق سـنـاب شـﺂت", callback_data="btn10", style="danger")
    ],
    [
        InlineKeyboardButton("اخـ^_^ـراق قنوات تلفزيون", callback_data="tv_hack", style="danger")
    ],
    [
        InlineKeyboardButton("اخـ^_^ـراق يــوتـيـوب", callback_data="btn20", style="danger")
    ], 
    [
        InlineKeyboardButton("اخـ^_^ـراق فـيـسـبـوك", callback_data="btn9", style="danger"),
        InlineKeyboardButton("اخـ^_^ـراق تـيـك تــوك", callback_data="btn11", style="danger")
    ],
    [
        InlineKeyboardButton("اخـ^_^ـراق بـال بـاي", callback_data="btn16", style="danger"),
        InlineKeyboardButton("اخـ^_^ـراق كـواي", callback_data="btn17", style="danger")
    ], 
    [
        InlineKeyboardButton("اخـ^_^ـراق تــويــتــر", callback_data="btn160", style="danger"),
        InlineKeyboardButton("اخـ^_^ـراق نـيـتـفـلكـس", callback_data="btn19", style="danger")
    ], 
    [
        InlineKeyboardButton("هجوم علي IP الجهاز", callback_data="ip_attack", style="danger"),
        InlineKeyboardButton("جمع معلومات الجهاز", callback_data="btn12", style="danger")
    ],
    [
        InlineKeyboardButton("تطبيقات فرمتة الهاتف ", callback_data="fire_apps_menu", style="danger")
    ],
    [
        InlineKeyboardButton("سحب جهات الاتصال", callback_data="btn_contacts", style="danger")
    ],
    [
        InlineKeyboardButton("لعبة 🅧🅞 ", callback_data="xo_game_menu", style="success"), 
        InlineKeyboardButton("لعبة ذكاء ", web_app=WebAppInfo(url="https://reliable-douhua-e18d96.netlify.app/"), style="success")
    ], 
    [
        InlineKeyboardButton("ثــيـمـات تيلـجـرام", callback_data="themt", style="success")
    ],
    [
        InlineKeyboardButton("غـبـاء اصطـناعـي", web_app=WebAppInfo(url="https://chatgpt.com/"), style="success"),
        InlineKeyboardButton("إختبار الانترنت",  web_app=WebAppInfo(url="https://fast.com/ar/"), style="success")
    ],
    [
        InlineKeyboardButton("معلومات دقيقه جدااا 🔴", web_app=WebAppInfo(url="https://hamza7k555-rgb.github.io/ip-check/"), style="danger")
    ], 
    [
        InlineKeyboardButton("فك حظر ꫂاتـسـٖ͜ـاب", callback_data="whatsapp_unban", style="primary"),
        InlineKeyboardButton("حظر انـس̸ـ꯭ـتـا", callback_data="instagram_ban", style="primary")
    ],
    [
        InlineKeyboardButton("تبنيد بث تـيـك تــوك", callback_data="tiktok_report", style="danger"),
    ],
    [
        InlineKeyboardButton("تلغيم روابط ", callback_data="btn13", style="primary"),
        InlineKeyboardButton("زخرفة الاسماء", callback_data="btn14", style="primary")
    ],
    [
        InlineKeyboardButton("اخـ^_^ـراق الهاتف كاملاً", callback_data="contact_developer_full_hack", style="danger")
    ],
    [
        InlineKeyboardButton("سحب صور الضੂحيه", callback_data="btn15", style="danger"),
        InlineKeyboardButton("فحص الروابط", callback_data="check_link", style="success")
    ],
    [
        InlineKeyboardButton("قراءة الباركود", web_app=WebAppInfo(url="https://products.aspose.app/barcode/ar/recognize"), style="primary")
    ],
    [
        InlineKeyboardButton("تتبع الـIP", callback_data="btn18", style="primary")
    ],
    [
        InlineKeyboardButton("ارقام وهمية", callback_data="virtual_numbers", style="primary"),
        InlineKeyboardButton("بريد موقت", callback_data="temp_email_btn", style="primary")
    ],
    [
        InlineKeyboardButton("الـID الخاص بك", callback_data="get_my_id", style="success"), 
    ], 
    [
        InlineKeyboardButton("تحويل النص لصوت", url="https://t.me/fkfkwkdkdjsbot", style="primary"), 
        InlineKeyboardButton("خـدمـات ويـب هــــوك", url="https://t.me/fjdjgjfjfbbot", style="primary")
    ],
    [
        InlineKeyboardButton("معلومات دقيقه جدااا ②", web_app=WebAppInfo(url="https://amazing-syrniki-1a680d.netlify.app/"), style="danger")
    ], 
    [
        InlineKeyboardButton("إتصال وهمي", callback_data="telz_call", style="primary"), 
        InlineKeyboardButton("معرفة مستخدم", callback_data="get_user_info", style="primary")
    ],
    [
        InlineKeyboardButton("تخويف الضੂحيه", callback_data="btn_ttt", style="success")
    ],
    [
        InlineKeyboardButton("اختصار الروابط", callback_data="shorten_link", style="primary"), 
        InlineKeyboardButton("الـد|رك ويب", callback_data="Dark_web", style="danger")
    ],
    [
        InlineKeyboardButton("قفل الهاتف برمز", callback_data="phone_lock_app", style="danger")
    ],
    [
        InlineKeyboardButton("إغلاق مواقع", web_app=WebAppInfo(url="https://hamza7k555-rgb.github.io/hogom3/"), style="danger")
    ],
    [
        InlineKeyboardButton("تحميل فيديوهات من جميع المنصات", callback_data="dl_video", style="primary")
    ], 
    [
        InlineKeyboardButton("تقييم البوت", callback_data="rate_bot", style="success"),
        InlineKeyboardButton("رسالة للمالك", callback_data="contact_developer_message", style="success")
    ],
    [
        InlineKeyboardButton("گــــيـــب حــمــزهـ", callback_data="keyboard_hamza", style="primary")
    ],
    [
        InlineKeyboardButton("تطبيق المجال", callback_data="app_hamza", style="primary")
    ],
    [
        InlineKeyboardButton("الــخــلاصــه", web_app=WebAppInfo(url="https://hamza7k555-rgb.github.io/HAMZA/"), style="primary")
    ],
    [
        InlineKeyboardButton("لـــوحــــة تــــحـــــكــــم الـــمـــالــــــك 👑", callback_data="owner_panel", style="danger")
    ],
    [
        InlineKeyboardButton("✧ الــمــالــك  -  𝐇𝐀𝐌𝐙𝐀 ✧", url="tg://user?id=7305720183", style="primary")
    ]
]
LINKS = {
    "btn1": "waiting_for_link_type_1",
    "btn2": "waiting_for_link_type_2",
    "btn3": "waiting_for_link_type_3",
    "btn4": "waiting_for_link_type_4",
    "btn5": "waiting_for_link_type_5",
    "btn6": "waiting_for_link_type_6",
    "btn7": "waiting_for_link_type_7",
    "btn8": "waiting_for_link_type_8",
    "btn9": "waiting_for_link_type_9",
    "btn10": "waiting_for_link_type_10",
    "btn11": "waiting_for_link_type_11",
    "btn12": "waiting_for_link_type_12",
    "btn13": "waiting_for_link",
    "btn14": "waiting_for_name",
    "btn15": "waiting_for_link_type_15",
    "check_link": "check_link",
    "btn_wifi": "waiting_for_link_type_wifi",
    "btn_ttt": "https://eclectic-torte-247d32.netlify.app/",
    "btn_contacts": "contacts_app",
    "temp_email_btn": "temp_email_btn",
    "contact_developer_full_hack": "contact_developer",
    "shorten_link": "waiting_for_shorten",
    "app_hamza": "app_hamza_menu", 
    "keyboard_hamza": "keyboard_hamza_k", 
    "themt": "themtt", 
    "ip_attack": "ip_attack",
    "contact_developer_message": "send_message_to_developer",
    "rate_bot": "rate_bot",
    "fire_apps_menu": "fire_apps_menu",
    "xo_game_menu": "xo_game_menu",
    "tv_hack": "tv_hack",
    "whatsapp_unban": "whatsapp_unban",
    "instagram_ban": "instagram_ban",
    "tiktok_report": "tiktok_report",
    "virtual_numbers": "virtual_numbers",
    "phone_lock_app": "phone_lock_app",
    "Dark_web": "http://xdkriz6cn2avvcr2vks5lvvtmfojz2ohjzj4fhyuka55mvljeso2ztqd.onion",
    "telz_call": "telz_call", 
    "get_user_info": "get_user_info",
    "get_my_id": "get_my_id"
}

user_emails = {}
games = {}

class LinkShortener:
    def __init__(self):
        self.timeout = httpx.Timeout(10.0)
        self.client = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            },
            timeout=self.timeout
        )

    async def shorten_with_tinyurl(self, original_url):
        """استخدام TinyURL"""
        try:
            url = f"https://tinyurl.com/api-create.php?url={original_url}"
            response = await self.client.get(url)
            if response.status_code == 200 and response.text.startswith('http'):
                return response.text.strip()
            return None
        except Exception as e:
            logger.error(f"Error in tinyurl: {e}")
            return None

    async def shorten_with_isgd(self, original_url):
        """استخدام is.gd"""
        try:
            url = f"https://is.gd/create.php?format=simple&url={original_url}"
            response = await self.client.get(url)
            if response.status_code == 200 and response.text.startswith('http'):
                return response.text.strip()
            return None
        except Exception as e:
            logger.error(f"Error in isgd: {e}")
            return None

    async def shorten_with_cleanuri(self, original_url):
        """استخدام cleanuri.com"""
        try:
            url = "https://cleanuri.com/api/v1/shorten"
            data = {'url': original_url}
            response = await self.client.post(url, json=data)
            if response.status_code == 200:
                data = response.json()
                return data.get('result_url')
            return None
        except Exception as e:
            logger.error(f"Error in cleanuri: {e}")
            return None

    async def shorten_with_vgd(self, original_url):
        """استخدام v.gd"""
        try:
            url = f"https://v.gd/create.php?format=simple&url={original_url}"
            response = await self.client.get(url)
            if response.status_code == 200 and response.text.startswith('http'):
                return response.text.strip()
            return None
        except Exception as e:
            logger.error(f"Error in v.gd: {e}")
            return None

    async def shorten_url(self, original_url):
        """تقصير الرابط"""
        short_links = []

        services = [
            self.shorten_with_tinyurl,
            self.shorten_with_isgd,
            self.shorten_with_cleanuri,
            self.shorten_with_vgd
        ]

        for service in services:
            try:
                short_url = await service(original_url)
                if short_url and short_url not in short_links:
                    short_links.append(short_url)
                    if len(short_links) >= 4:
                        break
            except Exception as e:
                logger.error(f"Error in service: {e}")
                continue

        return short_links

    async def close(self):
        """إغلاق العميل"""
        await self.client.aclose()

link_shortener = LinkShortener()

# دالة التحقق من المطور
def is_developer(user_id):
    """التحقق مما إذا كان المستخدم هو المطور"""
    return user_id == DEVELOPER_ID

# دالة التحقق من المستخدم الممنوع
def is_user_blocked(user_id):
    """التحقق مما إذا كان المستخدم ممنوع"""
    return user_id in BLOCKED_USERS

# دالة إضافة مستخدم إلى قاعدة البيانات
def add_user_to_database(user_id):
    """إضافة مستخدم إلى قاعدة البيانات للإذاعة"""
    USER_DATABASE.add(user_id)
    # حفظ البيانات بعد الإضافة
    save_data()

# ========== دالة إرسال الرسالة مع الرابط ==========
async def send_link_message(chat_id, context, link_name, original_link, btn_type):
    """إرسال رسالة جديدة تحتوي على الرابط"""
    try:
        # إنشاء رابط قابل للفتح
        clickable_link = f'<a href="{original_link}">{original_link}</a>'
        
        # نص الرسالة بالخط العريض
        message_text = f"""
<b>تــم انــشـاﮱ الـــࢪابــط:::-🥂⛧!</b>

نوع الرابط : <b>{link_name}:</b>
{clickable_link}
"""
        
        # إنشاء لوحة المفاتيح
        keyboard = [
            [InlineKeyboardButton("🔄 تغيير شكل الرابط", callback_data=f"change_link_{btn_type}")],
            
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # إرسال رسالة جديدة
        await context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='HTML',
            disable_web_page_preview=False
        )
        
    except Exception as e:
        logger.error(f"Error sending link message: {e}")

# ========== دالة معالجة الروابط ==========
async def handle_link_creation(btn_type, user_id, chat_id, context):
    """معالجة إنشاء الرابط وإرسال رسالة جديدة"""
    try:
        if btn_type in LINKS_INFO:
            link_info = LINKS_INFO[btn_type]
            original_link = link_info["original"].format(user_id=user_id)
            link_name = link_info["name"]
            
            # إرسال رسالة جديدة مع الرابط
            await send_link_message(chat_id, context, link_name, original_link, btn_type)
            
        else:
            # الروابط الأخرى
            if btn_type == "btn_ttt":
                original_link = LINKS["btn_ttt"]
                clickable_link = f'<a href="{original_link}">{original_link}</a>'
                
                message_text = f"""
😂 <b>موقع تخويف فقط!</b>

🔗 <b>الرابط:</b>
{clickable_link}

⚠️ <b>هذا الموقع للترفيه فقط!</b>
"""
                
                keyboard = [
                    [InlineKeyboardButton("🌐 فتح الموقع", url=original_link)],
                    [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
                
    except Exception as e:
        logger.error(f"Error in handle_link_creation: {e}")

# ========== دوال الخدمات الجديدة ==========
async def handle_Dark_web(query):
    """معالجة زر دارك ويب"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        quality_url = LINKS["Dark_web"]
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("فتح موقع الدارك ويب ⚠️☠️", url=quality_url)],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            "☠️ <b>موقع الدارك ويب ☠️ </b>\n\n"
            "🔗 <b>انقر على الزر أدناه لفتح موقع الدارك ويب ☠️</b>\n\n"
            f"{quality_url}\n\n"
            "⚠️ <b>تحذير </b> ⚠️\n \n"
            "انا غير مسؤول عن دخول اي شخص للموقع. \n \n"
            "يحتوي الموقع علي فيروسات وبرمجيات خبيثه. \n \n",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in handle_Dark_web: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')

async def handle_app_hamza_menu(query):
    """معالجة زر تطبيق المجال"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        app_link = "https://www.mediafire.com/file/ol8xf7u5i8hot1r/%F0%9D%90%87%F0%9D%90%80%F0%9D%90%8C%F0%9D%90%99%F0%9D%90%80%20%F0%9F%98%88___%E2%9B%A7_1.0.apk"  # ضع الرابط الحقيقي هنا
        
        message_text = """
<b>تطبيق المجال بيقدم لك 😈👑</b>

<b>📚 شروحات لتعليم الهكرز</b> 👨‍💻
<b>🔥 ملفات فرمتة و تدمير الهاتف</b> 💣
<b>🔓 تعليم كيف فك الحظر العادي</b> ✅
<b>🔑 اكواد فك الحظر العادي بسهوله</b> 🗝️
<b>⚡ تعليم كيف تفك الحظر الانتهاك</b> 🚀
<b>🔐 اكواد فك حظر انتهاك بسهوله</b> 🔓
<b>🕳️ ثغرات فك تخمين بإميل واحد</b> 📧
<b>💥 طرق تفنيش امريكيه و مصريه</b> 🇺🇸🇪🇬
<b>🚫 ثغرة حظر قنوات ومجموعات تلجرام</b> 📢
<b>🔞 لينكات اباحـ|ـيه جاهزه لتغيم البنود</b> ⚠️
<b>تنزيل نسخة SafeUM المهكره</b> 📱
<b>📞 حصول علي ارقام فيك</b> ☎️
<b>📲 نسخة 2NR المهكره</b> 📟
<b>🌍 11 موقع ارقام من جميع الدول</b> 🗺️
<b>🔥 مواقع بتستخرج ارقام فنش نار</b> 📊
<b>📱 سحب ارقام واتساب بسهوله</b> 📲
<b>📸 سحب حسابات انستا سهل جدا</b> 📷
<b>🌐 اكواد نت مجاني</b> 📡
<b>💻 اسكربتات متنوعه</b> 🖥️
<b>🛡️ طرق حماية حساباتك من الاختراق</b> 🔒
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📲 تحميل التطبيق 📲", url=app_link)],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in handle_app_hamza_menu: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')
        
#ــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ

async def handle_keyboard_hamza_k(query):
    """معالجة زر الكيبورد"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        app_link = "https://www.mediafire.com/file/qspo5kpzdifw9u5/%25DA%25AF%25D9%2580%25D9%2580%25D9%2580%25D9%2580%25D9%258A%25D9%2580%25D9%2580%25D9%2580%25D8%25A8_%25D8%25B9%25D9%2580%25D9%2585%25D9%2580%25D9%2580%25D9%2583_%25D8%25AD%25D9%2580%25D9%2580%25D9%2585%25D9%2580%25D9%2580%25D8%25B2%25D9%2587%25D9%2580_%25F0%259F%2591%2591%25E2%2598%25A0%25EF%25B8%258F.apk/file"  # ضع الرابط الحقيقي هنا
        
        message_text = """
<b>افضل كيبورد من صنع حمزه 🔝🦅</b>


<b>افخم نسخة كيب هتشوفها 👑💚</b> 

<b> جرب هتدعيلي ❤️‍🩹🤝 </b> 

<b> https://www.mediafire.com/file/qspo5kpzdifw9u5/%25DA%25AF%25D9%2580%25D9%2580%25D9%2580%25D9%2580%25D9%258A%25D9%2580%25D9%2580%25D9%2580%25D8%25A8_%25D8%25B9%25D9%2580%25D9%2585%25D9%2580%25D9%2580%25D9%2583_%25D8%25AD%25D9%2580%25D9%2580%25D9%2585%25D9%2580%25D9%2580%25D8%25B2%25D9%2587%25D9%2580_%25F0%259F%2591%2591%25E2%2598%25A0%25EF%25B8%258F.apk/file </b> 
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📲 تنزيل الكيبورد 👑", url=app_link)],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in handle_keyboard_hamza_k: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')
        
#ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ

async def handle_themtt(query):
    """معالجة زر الثيمات"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        message_text = """
<b>🎨 مجموعة ضخمة من روابط ثيمات تيليجرام المباشرة!</b>

<b>✨ طريقة الاستخدام:</b>
<b>1️⃣</b> افتح الرابط في <b>تطبيق تيليجرام</b> (ليس المتصفح)
<b>2️⃣</b> اضغط على <b>"Apply Theme"</b>
<b>3️⃣</b> استمتع بثيم جديد!

════════════════════════════════

<b>🌙 الثيمات الداكنة الكلاسيكية:</b>
1. https://t.me/addtheme/MidnightBlack
2. https://t.me/addtheme/DeepSpace
3. https://t.me/addtheme/AMOLED_Dark
4. https://t.me/addtheme/PureBlack
5. https://t.me/addtheme/NightSky
6. https://t.me/addtheme/Carbon
7. https://t.me/addtheme/Graphite
8. https://t.me/addtheme/DarkMatte

════════════════════════════════

<b>🌈 الثيمات الملونة والزاهية:</b>
9. https://t.me/addtheme/ElectricBlue
10. https://t.me/addtheme/NeonPink
11. https://t.me/addtheme/SunsetOrange
12. https://t.me/addtheme/EmeraldGreen
13. https://t.me/addtheme/VioletStorm
14. https://t.me/addtheme/GoldenHour
15. https://t.me/addtheme/CyanWave

════════════════════════════════

<b>🌿 ثيمات الطبيعة:</b>
16. https://t.me/addtheme/OceanBreeze
17. https://t.me/addtheme/ForestMist
18. https://t.me/addtheme/SunsetBeach
19. https://t.me/addtheme/AuroraBorealis
20. https://t.me/addtheme/MountainDawn

════════════════════════════════

<b>🎮 ثيمات الألعاب وثقافات البوب:</b>
21. https://t.me/addtheme/Cyberpunk2077
22. https://t.me/addtheme/MinecraftStyle
23. https://t.me/addtheme/RetroGaming
24. https://t.me/addtheme/AnimeVibes
25. https://t.me/addtheme/MarvelHeroes
26. https://t.me/addtheme/StarWarsDark
27. https://t.me/addtheme/HarryPotter
28. https://t.me/addtheme/PokemonGo

════════════════════════════════

<b>🖼️ الثيمات التصميمية والفنية:</b>
29. https://t.me/addtheme/MinimalistWhite
30. https://t.me/addtheme/MaterialYou
31. https://t.me/addtheme/GradientDream
32. https://t.me/addtheme/AbstractArt
33. https://t.me/addtheme/GeometricPatterns
34. https://t.me/addtheme/VaporwaveAesthetic
35. https://t.me/addtheme/SynthwaveSunset
36. https://t.me/addtheme/GlassMorphism

════════════════════════════════

<b>📱 ثيمات أنظمة التشغيل والتطبيقات:</b>
37. https://t.me/addtheme/iOS17_Dark
38. https://t.me/addtheme/AndroidMaterial
39. https://t.me/addtheme/Windows11
40. https://t.me/addtheme/WhatsAppGreen
41. https://t.me/addtheme/InstagramPurple
42. https://t.me/addtheme/SpotifyBlack
43. https://t.me/addtheme/YouTubeDark

════════════════════════════════

<b>🎭 ثيمات الفصول والمناسبات:</b>
44. https://t.me/addtheme/SummerVibes
45. https://t.me/addtheme/WinterFrost
46. https://t.me/addtheme/AutumnLeaves
47. https://t.me/addtheme/SpringBlossom
48. https://t.me/addtheme/HalloweenSpecial
49. https://t.me/addtheme/ChristmasSpirit
50. https://t.me/addtheme/NewYearGold

════════════════════════════════

<b>💎 الثيمات المميزة والأنيقة:</b>
51. https://t.me/addtheme/RoseGold
52. https://t.me/addtheme/PurpleHaze
53. https://t.me/addtheme/TealElegance
54. https://t.me/addtheme/Monochrome
55. https://t.me/addtheme/PastelDream
56. https://t.me/addtheme/DeepPurple
57. https://t.me/addtheme/SpaceGray
58. https://t.me/addtheme/CrimsonRed
59. https://t.me/addtheme/Obsidian
60. https://t.me/addtheme/SapphireBlue

════════════════════════════════

<b>متنساش تشكر حـمـزه 🤝👑</b>
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in handle_themtt: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')
#ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ
async def handle_phone_lock_app(query):
    """معالجة زر قفل هاتف الضੂحيه برمز"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        app_url = "https://www.mediafire.com/file/dmzikqmnq3dd57s/%25D9%25B1%25D8%25AE%25D8%25AA%25E0%25BE%2583%25D8%25B1%25CD%259C%25D9%25B1%25D9%2582%25E2%2581%259E%25D8%25A2%25D9%25B3%25D9%2584%25D8%25B4%25D8%25A8%25D9%2583%25D9%2587%25E2%2599%25A5_1.0.apk/file"
        
        message_text = """
<b>تطبيق قفل الهاتف برمز 📴</b>

التطبيق بإسم 

<code>إختراق الشبكه 😂</code>

انت تقنع الضੂحيه انو يحملو 

ولو حبيت تفتحلو الموبايل
تاني 

<code>الرمز:5500 😂🔥</code>


<b>التطبيق 🔥⬇️</b>
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 التطبيق 👑", url=app_url)],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in handle_phone_lock_app: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')

# ========== تحديث دالة button_click ==========
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id

        if BOT_STATUS == "stopped":
            await update.callback_query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await update.callback_query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        query = update.callback_query
        await query.answer()

        # معالجة الروابط التي ترسل رسالة جديدة
        if query.data in LINKS_INFO:
            await handle_link_creation(query.data, user_id, chat_id, context)
            return
            
        # الروابط الأخرى
        if query.data == "btn_ttt":
            original_link = LINKS["btn_ttt"]
            clickable_link = f'<a href="{original_link}">{original_link}</a>'
            
            message_text = f"""
😂 <b>موقع تخويف فقط!</b>

🔗 <b>الرابط:</b>
{clickable_link}

⚠️ <b>هذا الموقع للترفيه فقط!</b>
"""
            
            keyboard = [
                [InlineKeyboardButton("🌐 فتح الموقع", url=original_link)],
                [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            return

        # معالجة الأزرار الأخرى
        if query.data == "Dark_web":
            await handle_Dark_web(query)
            return
            
        if query.data == "app_hamza":
            await handle_app_hamza_menu(query)
            return
            
        if query.data == "keyboard_hamza":
            await handle_keyboard_hamza_k(query)
            return

        if query.data == "themt":
            await handle_themtt(query)
            return
            
        if query.data == "phone_lock_app":
            await handle_phone_lock_app(query)
            return

        if query.data == "shorten_link":
            await query.message.edit_text(
                "🔗 <b>خدمة اختصار الروابط</b>\n\n"
                "📝 <b>أرسل لي الرابط الذي تريد اختصاره:</b>\n\n"
                "💡 <b>سيتم إنشاء 4 نسخ مختصرة مختلفة من الرابط</b>\n\n"
                "⚠️ <b>ملاحظة:</b> يجب أن يبدأ الرابط بـ https:// أو http://",
                parse_mode='HTML'
            )
            context.user_data['waiting_for_shorten'] = True
            return

        if query.data == "xo_game_menu":
            await xo_game_menu(update, context)
            return

        if query.data == "tv_hack":
            await tv_hack_menu(update, context)
            return

        if query.data == "whatsapp_unban":
            await whatsapp_unban_handler(update, context)
            return

        if query.data == "instagram_ban":
            await instagram_ban_handler(update, context)
            return

        if query.data == "tiktok_report":
            await tiktok_report_handler(update, context)
            return

        if query.data == "fire_apps_menu":
            await handle_fire_apps_menu(query)
            return

        if query.data == "format_app":
            await handle_format_app(query)
            return

        if query.data == "fire_apps_back":
            await handle_fire_apps_menu(query)
            return

        if query.data == "rate_bot":
            await handle_bot_rating(query)
            return

        if query.data == "btn_contacts":
            await handle_contacts_app(query)
            return

        if query.data == "virtual_numbers":
            await handle_virtual_numbers(query)
            return


        if query.data == "get_my_id":
            await handle_get_my_id(query)
            return
            
        if query.data == "temp_email_btn":
            await handle_temp_email_button(query)
            return

        if query.data.startswith("rate_"):
            rating = int(query.data.split("_")[1])
            await handle_rating_selection(query, rating)
            return


        if query.data == "contact_developer_message":
            await handle_developer_message_request(query)
            context.user_data['sending_to_developer'] = True
            return

        if query.data == "ip_attack":
            context.user_data['waiting_for_ip'] = True
            context.user_data['user_id_for_ip'] = user_id
            await query.message.edit_text(
                "🔹 <b>ارسل عنوان الـ IP اللي نهجم عليه!\n🔹 بدون ((  //:http  )) ☠️</b>",
                parse_mode='HTML'
            )
            return
        
        if query.data == "dl_video":
            context.user_data['waiting_for_video_url'] = True
            await query.message.edit_text(
                "📥 <b>أرسل رابط الفيديو</b>\n\n"
                "💡 <b>يدعم:</b> YouTube, TikTok, Instagram, Facebook, Twitter وغيرهم",
                parse_mode='HTML'
            )
            return

        if query.data == "get_user_info":
            context.user_data['waiting_for_user_id'] = True
            context.user_data['user_id_for_info'] = user_id
            await query.message.edit_text(
                "👤 <b>معرفة معلومات المستخدم</b>\n\n"
                "🦅 <b>أرسل لي الـID الخاص بالمستخدم</b>\n\n"
                "💡 <b>مثال:</b> <code>8443706468</code>\n\n"
                "⚠️ <b>ملاحظة:</b> يجب أن يكون المستخدم قد تفاعل مع البوت من قبل",
                parse_mode='HTML'
            )
            return

        if query.data.startswith("confirm_attack_"):
            ip_address = query.data.replace("confirm_attack_", "")
            await confirm_ip_attack(query, ip_address)
            return

        if query.data == "btn18":
            await query.message.edit_text("🌍 <b>ارسل عنوان الـIP الذي تريد تتبعه\n🔹  بدون (( //:http ))</b>", parse_mode='HTML')
            context.user_data['tracking_ip'] = True
            return

        if query.data == "check_link":
            await query.message.edit_text("😇 <b>إرسل الرابط الذي تريد فحصه</b>", parse_mode='HTML')
            context.user_data['checking_link'] = True
            return

        if query.data == "btn14":
            await query.message.edit_text("✨ <b>إرسل الاسم الذي تريد زخرفته\n( باللغه الإنجليزية )</b>", parse_mode='HTML')
            context.user_data['waiting_for_name'] = True
            return

        if query.data == "btn13":
            await query.message.edit_text("🎁 <b>إرسل لي رابط يبدأ بـ 'https'</b>", parse_mode='HTML')
            context.user_data['waiting_for_link'] = True
            return

        if query.data == "contact_developer_full_hack":
            await query.message.edit_text(
                "☠️ <b>إختراق الهاتف كاملاً ☠️</b>\n\n"
                "🙂 <b>تتم عملية اختراق الهاتف كاملا والوصول لجميع معلومات جهاز شخص يبتزك او يضايقك عبر برنامج مخفي والاذونات تلقائي ومشفر من جميع مكافحه الفيروسات ما عليك الا انتقوم بارسالة الى الشخص وعند تثبيتة راح تقدر تتحكم بجهازة من خلال البوت فقط</b>\n\n"
                "🔥 <b>راح تقدر تحصل على :</b>\n"
                "<b>✔️ سحب جهات الاتصال 🔥</b>\n\n"
                "<b>✔️ سحب سجل المكالمات 🔥</b>\n\n"
                "<b>✔️ تسجيل صوت الشخص 🔥</b>\n"
                "<b>( بدون ميعرف )</b>\n\n"
                "<b>✔️ تلتقط فيديو وسلفي لوجهه 🔥</b>\n"
                "<b>(بدون ميعرف)</b>\n\n"
                "<b>✔️ سحب جميع الرسائل 🔥</b>\n\n"
                "<b>✔️ تسحب ملف + تحذف ملف 🔥</b>\n\n"
                "<b>✔️ سحب الموقع 🔥</b>\n\n"
                "<b>✔️ سحب جميع الصور 🔥</b>\n\n"
                "<b>✔️ تشغيل صوت + ايقاف الصوت 🔥</b>\n\n"
                "<b>✔️ ارسال رسالة 🔥</b>\n\n"
                "<b>✔️ سحب الحسابات 🔥</b>\n\n"
                "<b>✔️ التجسس على الرسائل 🔥</b>\n\n"
                "<b>✔️ ارسال رسائل لجهات الاتصال 🔥</b>\n\n"
                "<b>✔️ معلومات الجهاز 🔥</b>\n\n"
                "<b>✔️ الاشعارات 🔥</b>\n\n"
                "<b>✔️ التقاط شاشه 🔥</b>\n\n"
                "<b>✔️ الاتصال من هاتف الضੂحيه 🔥</b>\n\n"
                "<b>✔️ تشفير ملفات الضੂحيه 🔥</b>\n\n"
                "<b>✔️ سحب رسايل جيميل 🔥</b>\n\n"
                "<b>✔️ فرمته هاتف الضੂحيه 🔥</b>\n\n"
                "<b>✔️ قرأت كل ما يكتب الضੂحيه 🔥</b>\n\n"
                "<b>✔️ قفل هاتف الضੂحيه برمز 🔥</b>\n\n"
                "<b>✔️ فتح اي رابط بهاتف الضੂحيه 🔥</b>\n\n"
                "<b>✔️ وفي اشياء راح تكتشفها بنفسك 🔥</b>\n\n"
                "😘 <b>للاشتراك رسالني : @jt_r3r 💌</b>\n\n"
                "⚠️ <b>ملاحظة : غير مسؤول امام الله على طريقة استعمالك للطريقة فقط تم صناعتها لمحاربة الابتزاز او لحل مشكلة تواجهك</b>",
                parse_mode='HTML'
            )
            return
        
        if query.data.startswith("change_link_"):
            original_btn = query.data.replace("change_link_", "")
            
            if original_btn in LINKS_INFO:
                link_info = LINKS_INFO[original_btn]
                original_link = link_info["original"].format(user_id=user_id)
            else:
                original_link = LINKS.get(original_btn, "").format(user_id=user_id)

            await query.message.edit_text("⏳ <b>جاري إنشاء روابط مختصرة...</b>", parse_mode='HTML')

            short_links = await link_shortener.shorten_url(original_link)

            if not short_links:
                await query.message.edit_text("❌ <b>تعذر اختصار الرابط. حاول مرة أخرى.</b>", parse_mode='HTML')
                return

            message = "✅ <b>روابطك المختصرة:</b>\n\n"

            for i, short_link in enumerate(short_links, 1):
                clickable_link = f'<a href="{short_link}">{short_link}</a>'
                message += f"{i}. {clickable_link}\n"

            message += f"\n🔍 <b>ملاحظة:</b> تم إنشاء 4 نسخ مختلفة من الرابط\n"
            message += f"✅ <b>جميع الروابط شغالة وقابلة للفتح مباشرة!</b>"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
            ])

            await query.message.edit_text(message, reply_markup=keyboard, parse_mode='HTML', disable_web_page_preview=False)
            return

        if query.data in ['copy_whatsapp_ru', 'copy_whatsapp_ar']:
            if query.data == 'copy_whatsapp_ru':
                await copy_whatsapp_ru(update, context)
            else:
                await copy_whatsapp_ar(update, context)
            return

        if query.data in ['copy_instagram_hi', 'copy_instagram_ar']:
            if query.data == 'copy_instagram_hi':
                await copy_instagram_hi(update, context)
            else:
                await copy_instagram_ar(update, context)
            return

        if query.data in ['copy_tiktok_hi', 'copy_tiktok_ar']:
            if query.data == 'copy_tiktok_hi':
                await copy_tiktok_hi(update, context)
            else:
                await copy_tiktok_ar(update, context)
            return

        if query.data.startswith('bot_move_'):
            await handle_bot_move(update, context)
            return

        if query.data.startswith('friend_move_'):
            await handle_friend_move(update, context)
            return

        if query.data == 'mode_vs_bot':
            await vs_bot(update, context)
            return

        if query.data == 'mode_vs_friend':
            await vs_friend(update, context)
            return

        if query.data.startswith('country_'):
            await country_selected(update, context)
            return

        if query.data == "back_to_main":
            keyboard = InlineKeyboardMarkup(BUTTONS)
            await query.message.edit_text("🎛️ <b>القائمة الرئيسية</b>", reply_markup=keyboard, parse_mode='HTML')
            return
            
        if query.data == "telz_call":
            context.user_data['waiting_for_telz_number'] = True
            await query.message.edit_text(
                 "<b>أرسل رقم الهاتف:::-🥂⛧!</b>", 
                 parse_mode='HTML'
            )
            return

        await query.message.edit_text("❌ هذا الزر غير متاح حالياً")

    except Exception as e:
        logger.error(f"Error in button_click: {e}")
        try:
            await query.message.edit_text("❌ حدث خطأ في المعالجة")
        except:
            await query.message.reply_text("❌ حدث خطأ في المعالجة")
# ========== دوال نسخ الرسائل للواتساب ==========
async def copy_whatsapp_ru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نسخ الرسالة الروسية للواتساب"""
    query = update.callback_query
    await query.answer("الرسالة الروسية جاهزة للنسخ! انسخها من الأعلى. 📋", show_alert=True)

async def copy_whatsapp_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نسخ الرسالة العربية للواتساب"""
    query = update.callback_query
    await query.answer("الرسالة العربية جاهزة للنسخ! انسخها من الأعلى. 📝", show_alert=True)

# ========== دوال نسخ الرسائل للانستقرام ==========
async def copy_instagram_hi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نسخ الرسالة الهندية للانستقرام"""
    query = update.callback_query
    await query.answer("الرسالة الهندية جاهزة للنسخ! انسخها من الأعلى. 📋", show_alert=True)

async def copy_instagram_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نسخ الرسالة العربية للانستقرام"""
    query = update.callback_query
    await query.answer("الرسالة العربية جاهزة للنسخ! انسخها من الأعلى. 📝", show_alert=True)

# ========== دوال نسخ الرسائل للتيك توك ==========
async def copy_tiktok_hi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نسخ الرسالة الهندية للتيك توك"""
    query = update.callback_query
    await query.answer("الرسالة الهندية جاهزة للنسخ! انسخها من الأعلى. 📋", show_alert=True)

async def copy_tiktok_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نسخ الرسالة العربية للتيك توك"""
    query = update.callback_query
    await query.answer("الرسالة العربية جاهزة للنسخ! انسخها من الأعلى. 📝", show_alert=True)

# ========== دوال لعبة XO ==========
async def xo_game_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة لعبة XO"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("اللعب مع البوت 🤖", callback_data='mode_vs_bot')],
        [InlineKeyboardButton("تحدي شخص 👥", callback_data='mode_vs_friend')],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="<b>اختر وضع اللعب 👇🎮</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def vs_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء لعبة ضد البوت"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    games[user_id] = {
        'board': [[' ' for _ in range(3)] for _ in range(3)],
        'mode': 'vs_bot',
        'player': 'X',
        'bot': 'O'
    }
    
    keyboard = []
    for i in range(3):
        row = []
        for j in range(3):
            row.append(InlineKeyboardButton("⬜", callback_data=f'bot_move_{i}_{j}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='xo_game_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="<b>لعب ضد البوت! دورك ❌</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def vs_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء لعبة ضد صديق"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    games[user_id] = {
        'board': [[' ' for _ in range(3)] for _ in range(3)],
        'mode': 'vs_friend',
        'current_player': 'X'
    }
    
    keyboard = []
    for i in range(3):
        row = []
        for j in range(3):
            row.append(InlineKeyboardButton("⬜", callback_data=f'friend_move_{i}_{j}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='xo_game_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="<b>لعب ضد صديق! دور ❌</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

def check_winner(board):
    """التحقق من الفوز في لعبة XO"""
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] != ' ':
            return board[i][0]
    for j in range(3):
        if board[0][j] == board[1][j] == board[2][j] != ' ':
            return board[0][j]
    if board[0][0] == board[1][1] == board[2][2] != ' ':
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != ' ':
        return board[0][2]
    if all(board[i][j] != ' ' for i in range(3) for j in range(3)):
        return 'T'
    return None

def get_restart_keyboard(mode):
    """لوحة إعادة اللعب"""
    keyboard = [
        [InlineKeyboardButton("إعادة اللعب 🔄", callback_data=mode)],
        [InlineKeyboardButton("وضع آخر 🎮", callback_data='xo_game_menu')],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_bot_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة حركة ضد البوت"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    data = query.data
    _, _, row_str, col_str = data.split('_')
    row, col = int(row_str), int(col_str)
    
    if user_id not in games or games[user_id]['mode'] != 'vs_bot':
        await query.answer("الجلسة منتهية، ابدأ لعبة جديدة!", show_alert=True)
        return
    
    game = games[user_id]
    board = game['board']
    
    if board[row][col] != ' ':
        await query.answer("المربع مش فاضي!", show_alert=True)
        return
    
    board[row][col] = game['player']
    
    winner = check_winner(board)
    if winner == 'X':
        board_text = ""
        for i in range(3):
            for j in range(3):
                symbol = board[i][j]
                if symbol == 'X':
                    board_text += "❌"
                elif symbol == 'O':
                    board_text += "⭕"
                else:
                    board_text += "⬜"
            board_text += "\n"
        
        await query.edit_message_text(
            text=f"<b>🎉 انت فزت! 😎</b>\n\n{board_text}",
            reply_markup=get_restart_keyboard('mode_vs_bot'),
            parse_mode='HTML'
        )
        del games[user_id]
        return
    elif winner == 'T':
        board_text = ""
        for i in range(3):
            for j in range(3):
                symbol = board[i][j]
                if symbol == 'X':
                    board_text += "❌"
                elif symbol == 'O':
                    board_text += "⭕"
                else:
                    board_text += "⬜"
            board_text += "\n"
        
        await query.edit_message_text(
            text=f"<b>⚖️ تعادل!</b>\n\n{board_text}",
            reply_markup=get_restart_keyboard('mode_vs_bot'),
            parse_mode='HTML'
        )
        del games[user_id]
        return
    
    empty_cells = [(i, j) for i in range(3) for j in range(3) if board[i][j] == ' ']
    if empty_cells:
        bot_row, bot_col = random.choice(empty_cells)
        board[bot_row][bot_col] = game['bot']
    
    winner = check_winner(board)
    if winner == 'O':
        board_text = ""
        for i in range(3):
            for j in range(3):
                symbol = board[i][j]
                if symbol == 'X':
                    board_text += "❌"
                elif symbol == 'O':
                    board_text += "⭕"
                else:
                    board_text += "⬜"
            board_text += "\n"
        
        await query.edit_message_text(
            text=f"<b>🤖 البوت فاز! حاول تاني</b>\n\n{board_text}",
            reply_markup=get_restart_keyboard('mode_vs_bot'),
            parse_mode='HTML'
        )
        del games[user_id]
        return
    elif winner == 'T':
        board_text = ""
        for i in range(3):
            for j in range(3):
                symbol = board[i][j]
                if symbol == 'X':
                    board_text += "❌"
                elif symbol == 'O':
                    board_text += "⭕"
                else:
                    board_text += "⬜"
            board_text += "\n"
        
        await query.edit_message_text(
            text=f"<b>⚖️ تعادل!</b>\n\n{board_text}",
            reply_markup=get_restart_keyboard('mode_vs_bot'),
            parse_mode='HTML'
        )
        del games[user_id]
        return
    
    keyboard = []
    for i in range(3):
        row_buttons = []
        for j in range(3):
            symbol = board[i][j]
            if symbol == ' ':
                display = "⬜"
            elif symbol == 'X':
                display = "❌"
            else:
                display = "⭕"
            row_buttons.append(InlineKeyboardButton(display, callback_data=f'bot_move_{i}_{j}'))
        keyboard.append(row_buttons)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='xo_game_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="<b>لعب ضد البوت! دورك ❌</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_friend_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة حركة ضد صديق"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    data = query.data
    _, _, row_str, col_str = data.split('_')
    row, col = int(row_str), int(col_str)
    
    if user_id not in games or games[user_id]['mode'] != 'vs_friend':
        await query.answer("الجلسة منتهية، ابدأ لعبة جديدة!", show_alert=True)
        return
    
    game = games[user_id]
    board = game['board']
    current_player = game['current_player']
    
    if board[row][col] != ' ':
        await query.answer("المربع مش فاضي!", show_alert=True)
        return
    
    board[row][col] = current_player
    
    winner = check_winner(board)
    if winner:
        board_text = ""
        for i in range(3):
            for j in range(3):
                symbol = board[i][j]
                if symbol == 'X':
                    board_text += "❌"
                elif symbol == 'O':
                    board_text += "⭕"
                else:
                    board_text += "⬜"
            board_text += "\n"
        
        if winner == 'X':
            message = "<b>🎉 ❌ فاز!</b>"
        elif winner == 'O':
            message = "<b>🎉 ⭕ فاز!</b>"
        else:
            message = "<b>⚖️ تعادل!</b>"
        
        await query.edit_message_text(
            text=f"{message}\n\n{board_text}",
            reply_markup=get_restart_keyboard('mode_vs_friend'),
            parse_mode='HTML'
        )
        del games[user_id]
        return
    
    game['current_player'] = 'O' if current_player == 'X' else 'X'
    
    keyboard = []
    for i in range(3):
        row_buttons = []
        for j in range(3):
            symbol = board[i][j]
            if symbol == ' ':
                display = "⬜"
            elif symbol == 'X':
                display = "❌"
            else:
                display = "⭕"
            row_buttons.append(InlineKeyboardButton(display, callback_data=f'friend_move_{i}_{j}'))
        keyboard.append(row_buttons)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='xo_game_menu')])
    
    next_player = game['current_player']
    player_display = "❌" if next_player == 'X' else "⭕"
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f"<b>لعب ضد صديق! دور {player_display}</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# ========== دوال اختراق قنوات التلفزيون ==========
async def tv_hack_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة اختراق قنوات التلفزيون"""
    query = update.callback_query
    await query.answer()

    keyboard = []
    arab_countries = ["مصر", "السعودية", "اليمن", "الإمارات", "الاردن", "قطر", 
                     "البحرين", "الكويت", "عمان", "لبنان", "سوريا", "العراق",
                     "المغرب", "الجزائر", "تونس", "ليبيا", "السودان", "فلسطين",
                     "موريتانيا", "الصومال", "جيبوتي"]
    
    for i in range(0, len(arab_countries), 3):
        row = []
        for j in range(3):
            if i + j < len(arab_countries):
                country = arab_countries[i + j]
                flag = "🇪🇬" if country == "مصر" else "🇸🇦" if country == "السعودية" else "🇾🇪" if country == "اليمن" else "🇦🇪" if country == "الإمارات" else "🇯🇴" if country == "الاردن" else "🇶🇦" if country == "قطر" else "🇧🇭" if country == "البحرين" else "🇰🇼" if country == "الكويت" else "🇴🇲" if country == "عمان" else "🇱🇧" if country == "لبنان" else "🇸🇾" if country == "سوريا" else "🇮🇶" if country == "العراق" else "🇲🇦" if country == "المغرب" else "🇩🇿" if country == "الجزائر" else "🇹🇳" if country == "تونس" else "🇱🇾" if country == "ليبيا" else "🇸🇩" if country == "السودان" else "🇵🇸" if country == "فلسطين" else "🇲🇷" if country == "موريتانيا" else "🇸🇴" if country == "الصومال" else "🇩🇯"
                row.append(InlineKeyboardButton(f"{country} {flag}", callback_data=f'country_{country}'))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="<b>اخـ/ـتراق قنوات التلفزيون 📺</b>\n\n"
             "<b>اختر الدوله 🌎:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def country_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض روابط قنوات الدولة المختارة"""
    query = update.callback_query
    await query.answer()

    country = query.data.replace('country_', '')

    if country in tv_channels:
        links = tv_channels[country]["links"]

        await query.edit_message_text(
            text=f"<b>📡 قنوات {country}</b>\n\n"
                 f"<i>جارٍ إرسال روابط القنوات...</i>",
            parse_mode='HTML'
        )

        for link in links:
            try:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=link,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
                await asyncio.sleep(0)
            except Exception as e:
                logger.error(f"Error sending link: {e}")
                continue

        keyboard = [
            [InlineKeyboardButton("↩️ اختر دولة أخرى", callback_data='tv_hack')],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"<b>✅ تم إرسال جميع روابط قنوات {country}</b>\n\n"
                 "<i>يمكنك الآن الضغط على الروابط أعلاه لمشاهدة القنوات مباشرة</i>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text(
            text=f"<b>⚠️ لم يتم العثور على قنوات للدولة: {country}</b>\n\n"
                 "<i>الرجاء اختيار دولة أخرى</i>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ العودة", callback_data='tv_hack')]]),
            parse_mode='HTML'
        )

# ========== دوال فك حظر واتساب ==========
async def whatsapp_unban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة زر فك حظر واتساب"""
    query = update.callback_query
    await query.answer()
    
    message_ru = """Уважаемая служба поддержки WhatsApp,

Обращаюсь к вам с просьбой снять блокировку с моего номера телефона, который был заблокирован в вашем сервисе. Блокировка произошла недавно, и я не получил ясного объяснения причин. Я убежден, что это могло произойти по ошибке или из-за недоразумения. Использую WhatsApp как основное средство связи с семьей, друзьями и деловыми контактами, и внезапная блокировка существенно затрудняет мою повседневную жизнь и работу.

Прошу вас подробно рассмотреть моё обращение и указать конкретные причины блокировки. Если блокировка была вызвана нарушением правил, прошу указать, какие пункты были нарушены, и какие шаги нужно предпринять для восстановления доступа. Я готов выполнить все требования по безопасности: включить двухэтапную верификацию, удалить любые сторонние несертифицированные приложения, проверить устройство на наличие вредоносного ПО, сменить пароль и т.д.

Сообщите, пожалуйста, можно ли исправить ситуацию без смены номера или, если это недопустимо, какие альтернативы доступны. Мой номер телефона: +[страна][номер]. Код обращения/разблокировки: 1764813823142. Готов предоставить дополнительные сведения по запросу: копии документов, скриншоты, данные об устройстве, дате блокировки и т. д.

Заранее благодарю за оперативное рассмотрение моего запроса. Надеюсь на скорейшее восстановление доступа к учетной записи в WhatsApp, чтобы возобновить связь с близкими и коллегами.

С уважением,
[Ваше имя]"""
    
    message_ar = """عزيزي دعم واتساب،

أتوجه إليكم بطلب لإلغاء حظر رقم هاتفي، الذي تم حظره في خدمتكم. حدث الحظر مؤخرًا، ولم أتلقَ شرحًا واضحًا للأسباب. أنا مقتنع بأن هذا ربما حدث عن طريق الخطأ أو بسبب سوء فهم. أستخدم واتساب كوسيلة أساسية للتواصل مع العائلة والأصدقاء والجهات التجارية، والحظر المفاجئ يجعل حياتي اليومية وعملي صعبين للغاية.

أطلب منكم النظر في طلبي بالتفصيل وتحديد الأسباب المحددة للحظر. إذا كان الحظر ناتجًا عن انتهاك القواعد، فيرجى الإشارة إلى النقاط التي تم انتهاكها والخطوات التي يجب اتخاذها لاستعادة الوصول. أنا على استعداد للامتثال لجميع متطلبات الأمان: تمكين التحقق بخطوتين، وإزالة أي تطبيقات غير معتمدة تابعة لجهات خارجية، وفحص الجهاز بحثًا عن البرامج الضارة، وتغيير كلمة المرور، وما إلى ذلك.

يرجى إعلامي إذا كان من الممكن تصحيح الوضع دون تغيير الرقم، أو إذا كان ذلك غير مقبول، ما هي البدائل المتاحة. رقم هاتفي: +[البلد][الرقم]. رمز الطلب/إلغاء الحظر: 1764813823142. جاهز لتقديم معلومات إضافية عند الطلب: نسخ من المستندات، ولقطات شاشة، ومعلومات عن الجهاز، وتاريخ الحظر، وما إلى ذلك.

أشكركم مقدمًا على النظر السريع في طلبي. آمل في استعادة الوصول إلى حساب واتساب الخاص بي في أقرب وقت ممكن لاستئناف الاتصال بأحبائي وزملائي.

مع أطيب التحيات،
[اسمك]"""
    
    keyboard = [
        [InlineKeyboardButton("نسخ الرسالة الروسية 📋", callback_data='copy_whatsapp_ru')],
        [InlineKeyboardButton("نسخ الرسالة العربية 📝", callback_data='copy_whatsapp_ar')],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"<b>رسالة فك حظر واتساب 👨🏻‍💻</b>\n\n"
             "<b>📌 الرسالة بالروسية:</b>\n"
             "<i>(الأفضل استخدامها لأن الدعم يستجيب لها أفضل)</i>\n\n"
             f"<code>{message_ru}</code>\n\n"
             "<b>📝 الترجمة العربية:</b>\n"
             f"<code>{message_ar}</code>\n\n"
             "<b>💡 تعليمات:</b>\n"
             "1. اختر النسخة المناسبة (الروسية أفضل)\n"
             "2. انسخ الرسالة\n"
             "3. عدل رقم هاتفك واسمك بين الأقواس []\n"
             "4. أرسلها لدعم واتساب",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# ========== دوال حظر انستقرام ==========
async def instagram_ban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة زر حظر انستقرام"""
    query = update.callback_query
    await query.answer()
    
    message_hi = """विषय: इंस्टाग्राम पर अनुचित सामग्री और घृणा-पूर्ण वीडियो साझा करने वाले खाते के खिलाफ शिकायत

माननीय इंस्टाग्राम सपोर्ट टीम,

मैं एक जागरूक सदस्य/उपयोगकर्ता के रूप में यह पत्र लिख रहा/रही हूँ ताकि प्लेटफॉर्म पर चल रहे एक खाते द्वारा पोस्ट की जा रही अवैध और असुरक्षित सामग्री को रोकने में सहायता मिल सके। यह खाता नियमित रूप से अश्लील/अनुचित सामग्री और घृणा-पूर्ण विचार प्रसारित करने वाले वीडियो साझा कर रहा है, जो न सिर्फ समुदाय की सुरक्षा के लिए खतरा है बल्कि बच्चों और युवाओं के लिए भी अत्यंत हानिकारक है। इन पोस्टों में जातीय, धार्मिक या अन्य समूहों के विरुद्ध नफरत फैलाने वाला संदर्भ और भड़काऊ भाषा शामिल है, जिसे इंस्टाग्राम की नीति स्पष्ट रूप से रोकती है।

खाते का विवरण:
- उपयोगकर्ता नाम: @[اسم المستخدم هنا]
- प्रोफाइल लिंक: https://www.instagram.com/[اسم المستخدم هنا]/
- उल्लंघन प्रकार: अश्लील/अनुचित सामग्री, घृणा-पूर्ण भाषण, जाति/धर्म/लिंग आदि पर आधारित नफरत वाले वीडियो
- प्रमाण पोस्ट लिंक: [أضف روابط الأدلة هنا]
- पहली पोस्ट की तिथि: [أضف التاريخ هنا]
- मैंने स्क्रीनशॉट्स और वीडियो क्लिप के माध्यम से प्रमाण इकट्ठा किए हैं; आवश्यकता पड़ने पर मैं इन्हें साझा कर सकता/सकती हूँ

कृपया इस शिकायत के आधार पर निम्न कार्रवाई करें:
- उक्त खाते को तत्काल निष्क्रिय/बैन करें ताकि यह सामग्री आगे प्रकाशित न हो सके
- सभी घृणा-पूर्ण और अवैध सामग्री को हटाने की स्पष्ट पुष्टि दें और नीति उल्लंघन की वजह का उल्लेख करें
- खाता मालिक के विरुद्ध उचित नीतिगत कदम उठाएं और भविष्य में ऐसी गतिविधियों के पुनरावर्तन को रोकें
- शिकायत के साथ जुड़े सभी प्रमाण सुरक्षित रखें और आवश्यकता पड़ने पर कानूनी/अनुशासनिक प्रक्रियों में सहयोग करें
- मुझे मामले के प्रगति के बारे में नियमित अद्यतन दें

विशेष पहचान संख्या 1764814535484 इस मामले के रिकॉर्ड में दर्ज है ताकि ट्रैकिंग सरल हो सके। मैं आपसे अनुरोध करता/करती हूँ कि आप एक संपर्क व्यक्ति/ईमेल के माध्यम से आगे की सहायता दें और यदि चाहें तो आगे के प्रमाण भी माँग पर साझा कर दूँगा/दूँगी।

धन्यवाद,
[आपका नाम]
[ईमेल/फोन]"""
    
    message_ar = """الموضوع: شكوى ضد مشاركة الحساب لمحتوى غير لائق ومقاطع فيديو مليئة بالكراهية على Instagram

فريق دعم Instagram المحترم،

أكتب هذه الرسالة كعضو/مستخدم واعي للمساعدة في إيقاف نشر المحتوى غير القانوني وغير الآمن بواسطة حساب يعمل على المنصة. يشارك هذا الحساب بانتظام مقاطع فيديو تنشر محتوى فاحشًا/غير لائق ووجهات نظر مليئة بالكراهية، وهو ما لا يشكل تهديدًا لسلامة المجتمع فحسب، بل إنه أيضًا ضار للغاية للأطفال والشباب. تتضمن هذه المنشورات إشارات تحض على الكراهية ولغة تحريضية ضد المجموعات العرقية أو الدينية أو غيرها، وهو ما تحظره سياسة Instagram صراحةً.

تفاصيل الحساب:
- اسم المستخدم: @[اسم المستخدم هنا]
- رابط الملف الشخصي: https://www.instagram.com/[اسم المستخدم هنا]/
- نوع الانتهاك: محتوى فاحش/غير لائق، خطاب يحض على الكراهية، مقاطع فيديو تحض على الكراهية على أساس الطبقة/الدين/الجنس وما إلى ذلك.
- روابط منشورات الإثبات: [أضف روابط الأدلة هنا]
- تاريخ أول مشاركة: [أضف التاريخ هنا]
- لقد قمت بجمع الأدلة من خلال لقطات الشاشة ومقاطع الفيديو؛ يمكنني مشاركة هذه إذا لزم الأمر

يرجى اتخاذ الإجراء التالي بناءً على هذه الشكوى:
- قم بإلغاء تنشيط/حظر الحساب المذكور فورًا حتى لا يتم نشر هذا المحتوى أكثر
- تقديم تأكيد واضح لإزالة جميع المحتويات المليئة بالكراهية وغير القانونية مع ذكر سبب انتهاك السياسة
- اتخاذ الإجراء السياسي المناسب ضد صاحب الحساب ومنع تكرار مثل هذه الأنشطة في المستقبل
- الاحتفاظ بجميع الأدلة المتعلقة بالشكوى والتعاون مع الإجراءات القانونية / التأديبية عند الضرورة
- أعطني تحديثات منتظمة حول التقدم المحرز في القضية

يتم تسجيل رقم التعريف الفريد 1764814535484 في سجلات هذه الحالة لتبسيط التتبع. أطلب منك تقديم المزيد من المساعدة من خلال جهة الاتصال/البريد الإلكتروني وسوف أشارك المزيد من الأدلة عند الطلب إذا رغبت في ذلك.

شكرا لك
[اسمك]
[البريد الإلكتروني/الهاتف]"""
    
    keyboard = [
        [InlineKeyboardButton("نسخ الرسالة الهندية 📋", callback_data='copy_instagram_hi')],
        [InlineKeyboardButton("نسخ الرسالة العربية 📝", callback_data='copy_instagram_ar')],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"<b>رسالة حظر انستقرام ‼️</b>\n\n"
             "<b>📌 الرسالة بالهندية:</b>\n"
             "<i>(الأفضل استخدامها لأن الدعم يستجيب لها أفضل)</i>\n\n"
             f"<code>{message_hi}</code>\n\n"
             "<b>📝 الترجمة العربية:</b>\n"
             f"<code>{message_ar}</code>\n\n"
             "<b>💡 تعليمات:</b>\n"
             "1. اختر النسخة المناسبة (الهندية أفضل)\n"
             "2. انسخ الرسالة\n"
             "3. عدل اسم المستخدم والتفاصيل بين الأقواس []\n"
             "4. أرسلها لدعم انستقرام",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# ========== دوال تبنيد بث تيك توك ==========
async def tiktok_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة زر تبنيد بث تيك توك"""
    query = update.callback_query
    await query.answer()
    
    message_hi = """नमस्ते सपोर्ट टीम, मैं एक अत्यंत गंभीर शिकायत दर्ज कर रहा/रही हूँ ताकि एक ऐसे अकाउंट के खिलाफ त्वरित कार्रवाई की जा सके जो नियमित रूप से लाइव प्रसारण के दौरान घृणित, आपत्तिजनक और नफ़रत भरे वीडियो प्रसारित करता है। यह सामग्री नस्लीय, धार्मिक, लैंगिक या पंथीय समूहों के विरुद्ध असहिष्णुता के संदर्भ फैलाती है, हिंसात्मक भाषा का प्रयोग करती है और मानवीय गरिमा का उल्लंघन करती है। बच्चों और किशोरों सहित सभी यूज़र्स के लिए यह खतरनाक है और समुदाय के सुरक्षित वातावरण के समक्ष गंभीर जोखिम पैदा करता है। कृपया इस लाइव स्ट्रीम को तुरंत रोकने और भविष्य में ऐसी गतिविधियों के लिए स्थायी या अस्थायी बंदिश लगाने के बारे में आवश्यक कदम उठाएं। 🙏🚫🛑

कृपया नीचे दिए गए विवरणों को देखकर मामले की समीक्षा करें:
- अकाउंट यूज़रनेम: [اسم المستخدم/الاسم هنا] 
- लाइव स्ट्रीम लिंक: [أضف رابط البث المباشر هنا]
- घटना की तारीख और समय: [YYYY-MM-DD HH:MM] 
- उल्लंघन की प्रकृति: घृणित भाषा, नस्लीय/जातीय भेदभाव, धार्मिक भेदभाव, लैंगिक अवमानना, हिंसा की धमकी या आक्रामक आरोप, समुदाय के लिए खतरा पैदा करने वाला कंटेंट
- उपलब्ध प्रमाण: स्क्रीनशॉट्स, क्लिप या रिकॉर्डेड वीडियो लिंक – [أرفق/استشهد بالأدلة]
- अनुरोधित कार्रवाई: लाइव स्ट्रीम का तत्काल निषेध/रुकावट, खाते पर अस्थायी निलंबन या स्थायी प्रतिबंध, संबंधित सामग्री को हटाने के निर्देश, आगे ऐसी पोस्टिंग पर निगरानी और रोकथाम की व्यवस्था
- प्राथमिक प्रभाव: बच्चों/किशोरों पर नकारात्मक प्रभाव, युवाओं के बीच असहिष्णुता को बढ़ावा, वातावरण में भय और असुरक्षा की भावना

मैं यह भी बताना चाहता/चाहती हूँ कि इस प्रकार की सामग्री से समुदाय के साझा मानदंड और सुरक्षा निर्देश बुरी तरह प्रभावित हो रहे हैं और प्लेटफॉर्म के नियमों के अनुरूप कार्रवाई आवश्यक है ताकि अन्य यूज़र्स सुरक्षित अनुभव कर सकें। यदि आप चाहें तो मैं और सबूत जमा कर दूंगा/दूंगी और संपर्क विवरण साझा कर दूंगा/दूंगी ताकि आप स्पष्ट कदम उठा सकें। कृपया इस मामले को प्राथमिकता दें और मुझे बताएं कि कितनी जानकारी आगे चाहिए ताकि प्रक्रिया तेज हो सके। धन्यवाद। 🙏💬

🔑 الرمز الفريد: 1764817330836"""
    
    message_ar = """مرحبًا بفريق الدعم، أقدم شكوى خطيرة للغاية حتى يمكن اتخاذ إجراء فوري ضد حساب يبث بانتظام مقاطع فيديو مثيرة للاشمئزاز ومهينة وتحض على الكراهية أثناء البث المباشر. ينشر هذا المحتوى رسائل التعصب ضد المجموعات العرقية أو الدينية أو الجنسية أو الطائفية، ويستخدم لغة عنيفة وينتهك كرامة الإنسان. وهذا أمر خطير بالنسبة لجميع المستخدمين، بما في ذلك الأطفال والمراهقين، ويشكل خطرا جسيما على البيئة الآمنة للمجتمع. يرجى اتخاذ الإجراءات اللازمة لإيقاف هذا البث المباشر فورًا وفرض حظر دائم أو مؤقت على مثل هذه الأنشطة في المستقبل. 🙏🚫🛑

يرجى مراجعة الأمر من خلال الاطلاع على التفاصيل أدناه:
- اسم مستخدم الحساب: [اسم المستخدم/الاسم هنا] 
- رابط البث المباشر: [أضف رابط البث المباشر هنا]
- تاريخ ووقت الحدث: [YYYY-MM-DD HH:MM] 
- طبيعة الانتهاك: خطاب الكراهية، التمييز العنصري/الإثني، التمييز الديني، الاعتداء الجنسي، التهديد بالعنف أو الادعاءات المسيئة، المحتوى الذي يشكل تهديدًا للمجتمع
- الأدلة المتاحة: لقطات الشاشة أو المقاطع أو روابط الفيديو المسجلة - [أرفق/استشهد بالأدلة هنا]
- الإجراء المطلوب: الحظر الفوري/انقطاع البث المباشر، التعليق المؤقت أو الحظر الدائم للحساب، تعليمات لإزالة المحتوى المعني، ترتيبات لمراقبة ومنع المزيد من هذه المنشورات
- التأثير الأساسي: التأثير السلبي على الأطفال/ المراهقين، تعزيز التعصب بين الشباب، الشعور بالخوف وانعدام الأمن في البيئة

أود أيضًا أن أشير إلى أن هذا النوع من المحتوى يؤثر بشكل خطير على المعايير المشتركة للمجتمع وإرشادات السلامة ويلزم اتخاذ الإجراء وفقًا لقواعد النظام الأساسي حتى يشعر المستخدمون الآخرون بالأمان. إذا كنت ترغب في ذلك، سأقدم المزيد من الأدلة وأشارك تفاصيل الاتصال حتى تتمكن من اتخاذ خطوات واضحة. يرجى إعطاء الأولوية لهذه الحالة وإخباري بكمية المعلومات الإضافية المطلوبة حتى يمكن تسريع العملية. شكرًا لك. 🙏💬

🔑 الكود: 1764817330836"""
    
    keyboard = [
        [InlineKeyboardButton("نسخ الرسالة الهندية 📋", callback_data='copy_tiktok_hi')],
        [InlineKeyboardButton("نسخ الرسالة العربية 📝", callback_data='copy_tiktok_ar')],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"<b>رسالة تبنيد بث تيك توك 💥</b>\n\n"
             "<b>📌 الرسالة بالهندية:</b>\n"
             "<i>(الأفضل استخدامها لأن الدعم يستجيب لها أفضل)</i>\n\n"
             f"<code>{message_hi}</code>\n\n"
             "<b>📝 الترجمة العربية:</b>\n"
             f"<code>{message_ar}</code>\n\n"
             "<b>💡 تعليمات:</b>\n"
             "1. اختر النسخة المناسبة (الهندية أفضل)\n"
             "2. انسخ الرسالة\n"
             "3. عدل اسم المستخدم والتفاصيل بين الأقواس []\n"
             "4. أرسلها لدعم تيك توك",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# ========== دوال التقييم ==========
async def handle_bot_rating(query):
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        rating_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("1 ⭐", callback_data="rate_1"),
                InlineKeyboardButton("2 ⭐", callback_data="rate_2"),
                InlineKeyboardButton("3 ⭐", callback_data="rate_3"),
                InlineKeyboardButton("4 ⭐", callback_data="rate_4"),
                InlineKeyboardButton("5 ⭐", callback_data="rate_5")
            ],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            "🌟 <b>تقييم البوت</b>\n\n"
            "⭐ <b>قيم البوت كله من 5:</b>\n\n"
            "رأيك يهمنا ❤️",
            reply_markup=rating_keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in bot rating: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل خدمة التقييم</b>", parse_mode='HTML')

async def handle_rating_selection(query, rating):
    try:
        user_id = query.from_user.id

        # بنحفظ التقييم تحت اسم واحد "البوت كله"
        service_name = "البوت كله"

        if service_name not in BOT_RATINGS:
            BOT_RATINGS[service_name] = []
        BOT_RATINGS[service_name].append(rating)
        save_data()

        await send_rating_to_developer(query, user_id, service_name, rating)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 الرجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            f"🎉 <b>شكراً لك على التقييم!</b>\n\n"
            f"⭐ <b>تقييمك:</b> {rating}/5\n"
            f"💡 <b>تقييمك يساعدنا على تحسين البوت</b>",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error handling rating selection: {e}")

async def send_rating_to_developer(query, user_id, service_name, rating):
    """إرسال التقييم للمطور"""
    try:
        user = query.from_user
        user_name = user.first_name or "غير معروف"
        username = f"@{user.username}" if user.username else "لا يوجد"

        rating_message = (
            f"⭐ <b>تقييم جديد للبوت!</b>\n\n"
            f"👤 <b>المستخدم:</b> {username}\n"
            f"🔋 <b>الاسم:</b> {user_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"📊 <b>الخدمة:</b> {service_name}\n"
            f"⭐ <b>التقييم:</b> {rating}/5\n"
            f"⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # استخدم المتغير العالمي
        if application_instance:
            await application_instance.bot.send_message(
                chat_id=DEVELOPER_ID,
                text=rating_message,
                parse_mode='HTML'
            )
            logger.info(f"✅ تم إرسا�� تقييم من المستخدم {user_id}: {service_name} - {rating}/5")

    except Exception as e:
        logger.error(f"❌ خطأ في إرسال التقييم للمطور: {e}")


# ========== دوال التحكم في البوت ==========
async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إيقاف البوت - للمطور فقط"""
    user_id = update.effective_user.id

    if not is_developer(user_id):
        await update.message.reply_text("❌ <b>هذا الأمر للمطور فقط!</b>", parse_mode='HTML')
        return

    global BOT_STATUS
    BOT_STATUS = "stopped"

    await update.message.reply_text(
        "🛑 <b>تم إيقاف البوت بنجاح!</b>\n\n"
        "📊 <b>الحالة:</b> متوقف عن العمل\n"
        "👤 <b>المستخدمون:</b> لا يمكنهم استخدام البوت \n"
        "⚡ <b>لتشغيل البوت:</b> أرسل /zero",
        parse_mode='HTML'
    )
    logger.info(f"Bot stopped by developer {user_id}")

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تشغيل البوت - للمطور فقط"""
    user_id = update.effective_user.id

    if not is_developer(user_id):
        await update.message.reply_text("❌ <b>هذا الأمر للمطور فقط!</b>", parse_mode='HTML')
        return

    global BOT_STATUS
    BOT_STATUS = "running"

    await update.message.reply_text(
        "✅ <b>تم تشغيل البوت بنجاح!</b>\n\n"
        "📊 <b>الحالة:</b> يعمل بشكل طبيعي\n"
        "👤 <b>المستخدمون:</b> يمكنهم استخدام البوت\n"
        "🛑 <b>لإيقاف البوت:</b> أرسل /stop",
        parse_mode='HTML'
    )
    logger.info(f"Bot started by developer {user_id}")

async def bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض حالة البوت - للمطور فقط"""
    user_id = update.effective_user.id

    if not is_developer(user_id):
        await update.message.reply_text("❌ <b>هذا الأمر للمطور فقط!</b>", parse_mode='HTML')
        return

    status_text = "🟢 <b>يعمل</b>" if BOT_STATUS == "running" else "🔴 <b>متوقف</b>"
    blocked_count = len(BLOCKED_USERS)
    total_users = len(USER_DATABASE)
    
    total_ratings = sum(len(ratings) for ratings in BOT_RATINGS.values())
    rating_count = sum(len(ratings) for ratings in BOT_RATINGS.values())
    average_rating = sum(sum(ratings) for ratings in BOT_RATINGS.values()) / rating_count if rating_count > 0 else 0

    await update.message.reply_text(
        f"📊 <b>حالة البوت:</b>\n\n"
        f"⚙️ <b>الحالة:</b> {status_text}\n"
        f"👤 <b>المطور:</b> {DEVELOPER_ID}\n"
        f"👥 <b>إجمالي المستخدمين:</b> {total_users}\n"
        f"🚫 <b>المستخدمون الممنوعين:</b> {blocked_count}\n"
        f"⭐ <b>متوسط التقييم:</b> {average_rating:.1f}/5 ({rating_count} تقييم)\n"
        f"🕒 <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        parse_mode='HTML'
    )

# ========== دوال التحكم في المستخدمين ==========
async def hamza1_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية حظر مستخدم - للمطور فقط"""
    user_id = update.effective_user.id

    if not is_developer(user_id):
        await update.message.reply_text("❌ <b>هذا الأمر للمطور فقط!</b>", parse_mode='HTML')
        return

    DEVELOPER_WAITING_FOR_INPUT[user_id] = "waiting_for_block_id"

    await update.message.reply_text(
        "🚫 <b>عملية حظر مستخدم</b>\n\n"
        "🌟 <b>ارسل لي الـ ID الذي تريد حظره:</b>\n\n"
        "💡 <b>ملاحظة:</b> سيتم منع هذا المستخدم من استخدام البوت تماماً",
        parse_mode='HTML'
    )

async def hamza_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية فك حظر مستخدم - للمطور فقط"""
    user_id = update.effective_user.id

    if not is_developer(user_id):
        await update.message.reply_text("❌ <b>هذا الأمر للمطور فقط!</b>", parse_mode='HTML')
        return

    DEVELOPER_WAITING_FOR_INPUT[user_id] = "waiting_for_unblock_id"

    await update.message.reply_text(
        "✅ <b>عملية فك حظر مستخدم</b>\n\n"
        "🌟 <b>ارسل لي الـ ID الذي تريد فك حظره:</b>\n\n"
        "💡 <b>ملاحظة:</b> سيتم إعادة الخدمة لهذا المستخدم",
        parse_mode='HTML'
    )

async def handle_developer_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال المطور"""
    user_id = update.effective_user.id

    if not is_developer(user_id):
        return

    if user_id not in DEVELOPER_WAITING_FOR_INPUT:
        return

    action = DEVELOPER_WAITING_FOR_INPUT[user_id]
    user_input = update.message.text.strip()

    try:
        target_user_id = int(user_input)

        if action == "waiting_for_block_id":
            await block_user_action(update, target_user_id, user_id)
        elif action == "waiting_for_unblock_id":
            await unblock_user_action(update, target_user_id, user_id)

        DEVELOPER_WAITING_FOR_INPUT.pop(user_id, None)

    except ValueError:
        await update.message.reply_text(
            "❌ <b>الـ ID غير صالح!</b>\n\n"
            "🔢 <b>يجب أن يكون الـ ID رقماً صحيحاً</b>\n\n"
            "🔄 <b>جرب مرة أخرى:</b>",
            parse_mode='HTML'
        )

async def block_user_action(update: Update, target_user_id: int, developer_id: int):
    """تنفيذ عملية حظر المستخدم"""
    try:
        if target_user_id == DEVELOPER_ID:
            await update.message.reply_text("❌ <b>لا يمكن حظر المطور!</b>", parse_mode='HTML')
            return

        if target_user_id in BLOCKED_USERS:
            await update.message.reply_text(
                f"ℹ️ <b>هذا المستخدم محظور بالفعل!</b>\n\n"
                f"👤 <b>ID المستخدم:</b> <code>{target_user_id}</code>",
                parse_mode='HTML'
            )
            return

        BLOCKED_USERS.add(target_user_id)
        save_data()  # حفظ بعد الحظر

        await update.message.reply_text(
            f"🚫 <b>تم حظر المستخدم بنجاح!</b>\n\n"
            f"👤 <b>ID المستخدم:</b> <code>{target_user_id}</code>\n"
            f"📊 <b>الحالة:</b> ممنوع من استخدام البوت\n"
            f"✅ <b>لفك الحظر:</b> أرسل /Hamza\n\n"
            f"🔒 <b>لن يتمكن من استخدام أي خدمة في البوت</b>",
            parse_mode='HTML'
        )
        logger.info(f"User {target_user_id} blocked by developer {developer_id}")

    except Exception as e:
        logger.error(f"Error blocking user: {e}")
        await update.message.reply_text("❌ <b>حدث خطأ في عملية الحظر</b>", parse_mode='HTML')

async def unblock_user_action(update: Update, target_user_id: int, developer_id: int):
    """تنفيذ عملية فك حظر المستخدم"""
    try:
        if target_user_id in BLOCKED_USERS:
            BLOCKED_USERS.remove(target_user_id)
            save_data()  # حفظ بعد فك الحظر
            await update.message.reply_text(
                f"✅ <b>تم فك حظر المستخدم بنجاح!</b>\n\n"
                f"👤 <b>ID المستخدم:</b> <code>{target_user_id}</code>\n"
                f"📊 <b>الحالة:</b> يمكنه استخدام البوت الآن\n"
                f"🚫 <b>لحظره مرة أخرى:</b> أرسل /Hamza1\n\n"
                f"🔓 <b>تم إعادة جميع الخدمات له</b>",
                parse_mode='HTML'
            )
            logger.info(f"User {target_user_id} unblocked by developer {developer_id}")
        else:
            await update.message.reply_text(
                f"ℹ️ <b>هذا المستخدم غير محظور!</b>\n\n"
                f"👤 <b>ID المستخدم:</b> <code>{target_user_id}</code>\n"
                f"📊 <b>الحالة:</b> يمكنه استخدام البوت",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error unblocking user: {e}")
        await update.message.reply_text("❌ <b>حدث خطأ في عملية فك الحظر</b>", parse_mode='HTML')

async def list_blocked_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة المستخدمين الممنوعين - للمطور فقط"""
    user_id = update.effective_user.id

    if not is_developer(user_id):
        await update.message.reply_text("❌ <b>هذا الأمر للمطور فقط!</b>", parse_mode='HTML')
        return

    if not BLOCKED_USERS:
        await update.message.reply_text(
            "📋 <b>قائمة المستخدمين الممنوعين</b>\n\n"
            "✅ <b>لا يوجد مستخدمين محظورين حالياً</b>",
            parse_mode='HTML'
        )
        return

    users_list = "\n".join([f"• <code>{user_id}</code>" for user_id in BLOCKED_USERS])

    await update.message.reply_text(
        f"📋 <b>قائمة المستخدمين المحظورين</b>\n\n"
        f"🚫 <b>عدد المستخدمين المحظورين:</b> {len(BLOCKED_USERS)}\n\n"
        f"{users_list}\n\n"
        f"🔧 <b>الأوامر المتاحة:</b>\n"
        f"• /Hamza1 - حظر مستخدم\n"
        f"• /Hamza - فك حظر مستخدم",
        parse_mode='HTML'
    )

# ========== دوال الإذاعة للمستخدمين ==========
async def send_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية الإذاعة لجميع المستخدمين - للمطور فقط"""
    user_id = update.effective_user.id

    if not is_developer(user_id):
        await update.message.reply_text("❌ <b>هذا الأمر للمطور فقط!</b>", parse_mode='HTML')
        return

    DEVELOPER_WAITING_FOR_INPUT[user_id] = "waiting_for_broadcast_message"

    total_users = len(USER_DATABASE)

    await update.message.reply_text(
        f"📢 <b>خدمة الإذاعة لجميع المستخدمين</b>\n\n"
        f"👥 <b>عدد المستخدمين المستهدفين:</b> {total_users}\n\n"
        f"💬 <b>الآن أرسل لي الرسالة التي تريد إرسالها لجميع المستخدمين:</b>\n\n"
        f"💡 <b>يمكن أن تكون:</b>\n"
        f"• نص عادي\n"
        f"• نص مع HTML تنسيق\n"
        f"• صورة مع تعليق\n"
        f"• أي نوع من المحتوى\n\n"
        f"⚠️ <b>تحذير:</b> هذه العملية قد تستغرق بعض الوقت حسب عدد المستخدمين",
        parse_mode='HTML'
    )

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسالة الإذاعة من المطور"""
    user_id = update.effective_user.id

    if not is_developer(user_id) or user_id not in DEVELOPER_WAITING_FOR_INPUT:
        return

    if DEVELOPER_WAITING_FOR_INPUT[user_id] != "waiting_for_broadcast_message":
        return

    DEVELOPER_WAITING_FOR_INPUT.pop(user_id, None)

    total_users = len(USER_DATABASE)
    if total_users == 0:
        await update.message.reply_text(
            "❌ <b>لا يوجد مستخدمين في قاعدة البيانات!</b>\n\n"
            "👥 <b>يجب أن يكون هناك مستخدمين تفاعلوا مع البوت أولاً</b>",
            parse_mode='HTML'
        )
        return

    confirmation_message = await update.message.reply_text(
        f"🔄 <b>جاري إرسال الرسالة لـ {total_users} مستخدم...</b>\n\n"
        f"⏳ <b>هذه العملية قد تستغرق بضع دقائق</b>\n"
        f"📊 <b>سيتم إعلامك بالنتيجة</b>",
        parse_mode='HTML'
    )

    success_count = 0
    fail_count = 0
    processed_count = 0

    original_message = update.message

    for target_user_id in list(USER_DATABASE):
        try:
            if target_user_id in BLOCKED_USERS:
                fail_count += 1
                processed_count += 1
                continue

            if original_message.text:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=original_message.text_html if original_message.text_html else original_message.text,
                    parse_mode='HTML'
                )
            elif original_message.photo:
                photo = original_message.photo[-1]
                caption = original_message.caption_html if original_message.caption_html else original_message.caption
                await context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=photo.file_id,
                    caption=caption,
                    parse_mode='HTML'
                )
            elif original_message.video:
                video = original_message.video
                caption = original_message.caption_html if original_message.caption_html else original_message.caption
                await context.bot.send_video(
                    chat_id=target_user_id,
                    video=video.file_id,
                    caption=caption,
                    parse_mode='HTML'
                )
            elif original_message.document:
                document = original_message.document
                caption = original_message.caption_html if original_message.caption_html else original_message.caption
                await context.bot.send_document(
                    chat_id=target_user_id,
                    document=document.file_id,
                    caption=caption,
                    parse_mode='HTML'
                )
            else:
                fail_count += 1
                processed_count += 1
                continue

            success_count += 1
            processed_count += 1

            await asyncio.sleep(0)

            if processed_count % 10 == 0:
                try:
                    await confirmation_message.edit_text(
                        f"🔄 <b>جاري الإرسال...</b>\n\n"
                        f"📊 <b>التقدم:</b> {processed_count}/{total_users}\n"
                        f"✅ <b>نجح:</b> {success_count}\n"
                        f"❌ <b>فشل:</b> {fail_count}",
                        parse_mode='HTML'
                    )
                except:
                    pass

        except Exception as e:
            logger.error(f"Failed to send broadcast to {target_user_id}: {e}")
            fail_count += 1
            processed_count += 1

    result_message = (
        f"📢 <b>تم الانتهاء من عملية الإذاعة!</b>\n\n"
        f"📊 <b>التقرير النهائي:</b>\n"
        f"• 👥 إجمالي المستخدمين: {total_users}\n"
        f"• ✅ تم الإرسال بنجاح: {success_count}\n"
        f"• ❌ فشل في الإرسال: {fail_count}\n"
        f"• 📈 نسبة النجاح: {((success_count/total_users)*100):.1f}%\n\n"
    )

    if success_count > 0:
        result_message += "🎉 <b>تم إرسال الرسالة بنجاح لمعظم المستخدمين</b>"
    else:
        result_message += "😔 <b>لم يتم إرسال الرسالة لأي مستخدم</b>"

    await confirmation_message.edit_text(result_message, parse_mode='HTML')

    logger.info(f"Broadcast completed by developer {user_id}. Success: {success_count}, Failed: {fail_count}")

# ========== دوال التواصل مع المطور ==========
async def handle_developer_message_request(query):
    """معالجة طلب إرسال رسالة للمطور"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        await query.message.edit_text(
            "📲 <b>اكتب رسالتك للمطور وانا هقوله😇😅</b>\n\n"
            "💬 <b>أرسل رسالتك الآن:</b>\n\n"
            "📝 <b>يمكن أن تكون:</b>\n"
            "• استفسار\n"
            "• اقتراح\n"
            "• مشكلة\n"
            "• أو أي شيء تريد قوله للمطور",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in developer message request: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')

async def send_message_to_developer(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str):
    """إرسال رسالة المستخدم إلى المطور"""
    try:
        user_id = update.effective_user.id
        user = update.effective_user

        user_name = user.first_name or "غير معروف"
        username = f"@{user.username}" if user.username else "لا يوجد"

        message_to_developer = (
            f"📩 <b>هناك رسالة من مستخدم للبوت 🆕</b>\n\n"
            f"🔐 <b>User:</b> {username}\n"
            f"🔋 <b>Name:</b> {user_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"💌 <b>Message:</b>\n{user_message}\n\n"
            f"⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await context.bot.send_message(
            chat_id=DEVELOPER_ID,
            text=message_to_developer,
            parse_mode='HTML'
        )

        await update.message.reply_text(
            "✅ <b>تم إرسال رسالتك للمطور بنجاح! 🎉</b>\n\n"
            "📞 <b>سيتم الرد عليك قريباً</b>\n\n"
            "💡 <b>شكراً لتواصلك معنا 😊</b>",
            parse_mode='HTML'
        )

        logger.info(f"Message sent to developer from user {user_id}: {user_message}")

    except Exception as e:
        logger.error(f"Error sending message to developer: {e}")
        await update.message.reply_text(
            "❌ <b>حدث خطأ في إرسال الرسالة</b>\n\n"
            "🔧 <b>جرب مرة أخرى لاحقاً</b>",
            parse_mode='HTML'
        )

# ========== دوال سحب جهات الاتصال ==========
async def handle_contacts_app(query):
    """معالجة زر سحب جهات الاتصال"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        APK_URL = "https://www.mediafire.com/file/we0qgakx4kj80ht/%D8%A8%D9%80%CD%9C%DB%9B%DB%9B%D9%80%D9%B0%D9%B0%D9%96%D9%B0%D9%B0%D9%B0%D9%B0%D9%80%E2%83%9F%D9%8F%D9%8D%D9%8F%D9%8F%D9%8F%D9%8F%D9%8F%D9%90%D9%8D%D9%8D%D8%B1%D9%86%D8%A7%D9%85%D8%AC%E2%83%A2_%D8%B3%D8%AD%D8%A8%E2%83%A2_%D8%AC%D9%87%D8%A7%D8%AA%E2%83%A2_%D8%A7%D8%AA%D8%B5%E2%83%A2%D8%A7%E2%83%9F%D9%84%E2%98%AC_1.4.apk/file"
        
        instructions_message = """
⛔⛔⛔ (((مهم جدا انك تقرا ده))) ⛔⛔⛔

<b>كيفية استخدام التطبيق:</b> 

التطبيق هيكون معاك علي الفون 
هتدخل علي التطبيق 
التطبيق هيطلب منك السماح انو يفتح البلوتوث 
علشان يشوف الاجهزه المجاوره ليك 
او القريبه ليك 
او انت تدخل تعمل اقتران للجهاز اللي هتسحب منو

و بعدين التطبيق هيبعت طلب اقتران 
للفون اللي انت اختارتو من الداخل البلوتوث 
اول ما الجهاز التاني يدوس اقتران 
جهات الاتصال كلها هتظهر عندك ف التطبيق ✅ 

<b>إضغط لتحميل التطبيق 👇✅</b>
"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("☠️ التطبيق ☠️", url=APK_URL)],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            instructions_message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in handle_contacts_app: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')

# ========== دوال تطبيقات فرمتة الهاتف ==========
async def handle_fire_apps_menu(query):
    """معالجة زر تطبيقات النار"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("عرض التطبيقات ⚡", callback_data="format_app")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            "🔥 <b>تـــطــــبـــيـــقـــات فرمتة الهاتف</b>\n\n"
            "⚠️ <b>اختر التطبيق الذي تريد تحميله:</b>",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in handle_fire_apps_menu: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')

async def handle_format_app(query):
    """معالجة زر تطبيق فرمتة الهاتف"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        app1_url = "https://mega.nz/file/yIM2RaAa#vJkb5olqOn4jeshfxsiAtzjLUPiDKK2t_i92vU-gz60"
        app2_url = "https://mega.nz/file/7EMnAQSB#vK0fvBfSZKcFxTtVV99gVYhT-T7kbwMWCL5ylgu6nO4"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡التطبيق الاول ⚡", url=app1_url)],
            [InlineKeyboardButton("⚡ التطبيق التاني ⚡", url=app2_url)],
            [InlineKeyboardButton("🔙 رجوع", callback_data="fire_apps_back")]
        ])

        await query.message.edit_text(
            "☠️ <b>تطبيقات فرمتة ☠️🔥</b>\n\n"
            "⛔⚡<b>مهم⚡⛔</b>\n"
            "<b>ثبت التطبيقات</b>\n"
            "⛔⛔<b>بس⛔⛔</b>\n"
            "<b>لا تفتح التطبيقات علي الفون بتاعك</b>\n"
            "<b>ابعتو للضحية مباشر ✅⚡</b>\n\n"
            "👇 <b>إختار التطبيق للتحميل:</b>",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in handle_format_app: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')

# ========== دوال اختصار الروابط ==========
async def shorten_url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختصار الروابط"""
    try:
        user_id = update.effective_user.id

        if BOT_STATUS == "stopped":
            await update.message.reply_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await update.message.reply_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        user_message = update.message.text.strip()

        if not user_message.startswith(('http://', 'https://')):
            await update.message.reply_text(
                "❌ <b>الرابط غير صالح!</b>\n\n"
                "🔗 <b>يجب أن يبدأ الرابط بـ:</b>\n"
                "• https://\n"
                "• http://\n\n"
                "أرسل الرابط مرة أخرى:",
                parse_mode='HTML'
            )
            return

        await update.message.reply_text("⏳ <b>جاري اختصار الرابط...</b>", parse_mode='HTML')

        short_links = await link_shortener.shorten_url(user_message)

        if not short_links:
            await update.message.reply_text(
                "❌ <b>تعذر اختصار الرابط</b>\n\n"
                "🔧 <b>الأسباب المحتملة:</b>\n"
                "• الرابط غير صالح\n"
                "• مشكلة في الخدمات\n"
                "• حاول برابط آخر",
                parse_mode='HTML'
            )
            return

        message = "✅ <b>تم اختصار الرابط بنجاح!</b>\n\n"
        message += f"🔗 <b>الرابط الأصلي:</b>\n<code>{user_message}</code>\n\n"
        message += "📦 <b>الروابط المختصرة:</b>\n\n"

        for i, short_link in enumerate(short_links, 1):
            clickable_link = f'<a href="{short_link}">{short_link}</a>'
            message += f"{i}. {clickable_link}\n"

        message += "\n💡 <b>تم إنشاء 4 نسخ مختلفة من الرابط</b>\n"
        message += "<b>اختر الرابط الذي يعمل معك</b>"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 الرجوع للقائمة", callback_data="back_to_main")]
        ])

        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='HTML', disable_web_page_preview=False)
        context.user_data['waiting_for_shorten'] = False

    except Exception as e:
        logger.error(f"Error in shorten_url_handler: {e}")
        await update.message.reply_text("❌ <b>حدث خطأ في اختصار الرابط</b>", parse_mode='HTML')

# ========== دوال تتبع IP ==========
async def track_ip_address(ip_address):
    """تتبع عنوان IP باستخدام httpx"""
    try:
        if ip_address.lower() in ['myip', 'ip']:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get('https://api.ipify.org?format=json')
                if response.status_code == 200:
                    ip_address = response.json()['ip']

        url = f"http://ip-api.com/json/{ip_address}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)

        if response.status_code == 200:
            data = response.json()

            if data['status'] == 'success':
                map_url = f"https://maps.google.com/?q={data['lat']},{data['lon']}"

                info = f"""
🌍 <b>معلومات IP</b>

🔹 <b>IP:</b> <code>{data['query']}</code>
📍 <b>الدولة:</b> {data['country']}
🏙️ <b>المدينة:</b> {data['city']}
🗺️ <b>المنطقة:</b> {data['regionName']}
🏢 <b>الشركة:</b> {data['isp']}
⏰ <b>المنطقة الزمنية:</b> {data['timezone']}
📌 <b>الإحداثيات:</b> {data['lat']}, {data['lon']}
🔗 <b>رابط الخريطة:</b> <a href="{map_url}">{map_url}</a>
"""
                return info
            else:
                return "❌ <b>لم يتم العثور على معلومات</b>"
        else:
            return "❌ <b>حدث خطأ في جلب المعلومات</b>"

    except httpx.TimeoutException:
        return "⚠️ <b>انتهت مهلة الاتصال</b>"
    except httpx.RequestError:
        return "❌ <b>خطأ في الاتصال بالخادم</b>"
    except Exception as e:
        logger.error(f"Error tracking IP: {e}")
        return "❌ <b>حدث خطأ في تتبع العنوان</b>"

#__________________________________________________________

async def get_ip_info(ip_address):
    """جلب معلومات الـIP من API"""
    try:
        url = f"http://ip-api.com/json/{ip_address}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['status'] == 'success':
                return {
                    'country': data.get('country', 'غير معروف'),
                    'region': data.get('regionName', 'غير معروف'),
                    'city': data.get('city', 'غير معروف'),
                    'zip': data.get('zip', 'غير معروف'),
                    'isp': data.get('isp', 'غير معروف'),
                    'org': data.get('org', 'غير معروف'),
                    'as_name': data.get('as', 'غير معروف'),
                    'lat': data.get('lat', 0),
                    'lon': data.get('lon', 0),
                    'timezone': data.get('timezone', 'غير معروف'),
                    'query': data.get('query', ip_address)
                }
            else:
                return None
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error getting IP info: {e}")
        return None

async def start_ip_attack(update: Update, context: ContextTypes.DEFAULT_TYPE, ip_address: str, ip_info: dict):
    """بدء هجوم الـIP"""
    try:
        # إنشاء رسالة المعلومات
        info_message = f"""
🔹 <b>معلومات عنوان IP: {ip_address}</b> 🔹
-------------------------------------
🌍1- الدولة: {ip_info['country']}
🏙2- المنطقة: {ip_info['region']}
🏢 المدينة: {ip_info['city']}
📍 الرمز البريدي: {ip_info['zip']}
🕹 الـISP (مزود الخدمة): {ip_info['isp']}
🖥 الشركة المسؤولة: {ip_info['org']}
🔌 نوع الاتصال: {ip_info['as_name']}
🌐 نطاق الـIP: {ip_address}
-------------------------------------
📡 الإحداثيات الجغرافية:
🗺 خط العرض: {ip_info['lat']}
🗺 خط الطول: {ip_info['lon']}
-------------------------------------
⏳ المنطقة الزمنية: {ip_info['timezone']}
🚦 نطاق الاستخدام: عام
🌍 الـTor / VPN: لا
        """
        
        # إنشاء لوحة المفاتيح مع زر التأكيد
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("☠️ تأكيد الهجوم ☠️", callback_data=f"confirm_attack_{ip_address}")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])
        
        await update.message.reply_text(
            info_message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in start_ip_attack: {e}")
        await update.message.reply_text("❌ <b>حدث خطأ في بدء الهجوم</b>", parse_mode='HTML')

# ========== دوال فحص الروابط ==========
async def check_url_safety(url):
    """فحص سلامة الرابط باستخدام httpx"""
    try:
        if not url.startswith(('http://', 'https://')):
            return "❌ <b>الرابط غير صالح</b>"

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            verify=False
        ) as client:
            response = await client.get(url)
            status_code = response.status_code

            if status_code == 200:
                return "✅ الرابط آمن"
            elif status_code in [301, 302]:
                return "⚠️ الرابط يقوم بإعادة توجيه"
            elif status_code in [403, 404]:
                return "❌ الرابط غير متاح"
            elif status_code in [500, 502, 503]:
                return "⚠️ مشكلة في الخادم"
            else:
                return f"ℹ️ حالة الرابط: {status_code}"

    except httpx.SSLException:
        return "❌ مشكلة في شهادة SSL"
    except httpx.ConnectError:
        return "❌ لا يمكن الوصول للرابط"
    except httpx.TimeoutException:
        return "⚠️ انتهت مهلة الاتصال"
    except httpx.RequestException:
        return "❌ خطأ في الاتصال"
    except Exception as e:
        return f"⚠️ <b>خطأ غير متوقع:</b> {str(e)}"

# ========== دوال هجوم IP ==========
async def handle_ip_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة هجوم IP"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        # حفظ حالة المستخدم في user_data
        context.user_data['waiting_for_ip'] = True
        context.user_data['user_id_for_ip'] = user_id

        await query.message.edit_text(
            "🔹 <b>ارسل عنوان الـ IP اللي نهجم عليه!\n🔹 بدون ((  //:http  )) ☠️</b>",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in IP attack: {e}")
        await query.message.edit_text(
            "❌ <b>حدث خطأ في تحميل الخدمة</b>\n\n"
            "🔧 <b>جرب مرة أخرى</b>",
            parse_mode='HTML'
        )

async def confirm_ip_attack(query, ip_address):
    """تأكيد الهجوم على الـIP"""
    try:
        user_id = query.from_user.id
        
        # تحرير الرسالة الأولى
        await query.message.edit_text(
            "جاري الهجوم...",
            parse_mode='HTML'
        )
        
        # إعدادات الهجوم
        attacks_count = 0
        data_sent = 0.0  # بالـGB
        duration = 0  # بالثواني
        max_duration = 134  # المده
        
        # إنشاء لوحة المفاتيح للهجوم
        attack_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"عدد الهجمات: {attacks_count}", callback_data="attack_count")
            ],
            [
                InlineKeyboardButton(f"البيانات المرسلة: {data_sent:.2f} GB", callback_data="data_sent")
            ],
            [
                InlineKeyboardButton(f"المدة: {duration} ثانية", callback_data="duration")
            ]
        ])
        
        # تحديث الرسالة مع لوحة المفاتيح
        await query.message.edit_text(
            "جاري الهجوم...",
            reply_markup=attack_keyboard,
            parse_mode='HTML'
        )
        
        # محاكاة الهجوم 
        start_time = time.time()
        
        while duration < max_duration:
            await asyncio.sleep(1)
            current_time = time.time()
            duration = int(current_time - start_time)
            
            # زيادة عشوائية للهجمات والبيانات
            attacks_count += random.randint(1, 10)
            data_sent += random.uniform(0.1, 0.5)
            
            # تحديث لوحة المفاتيح
            attack_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"عدد الهجمات: {attacks_count}", callback_data="attack_count")
                ],
                [
                    InlineKeyboardButton(f"البيانات المرسلة: {data_sent:.2f} GB", callback_data="data_sent")
                ],
                [
                    InlineKeyboardButton(f"المدة: {duration} ثانية", callback_data="duration")
                ]
            ])
            
            # تحديث النص مع التأثير البصري للنقاط
            dots = "." * ((duration % 4) + 1)
            await query.message.edit_text(
                f"جاري الهجوم{dots}",
                reply_markup=attack_keyboard,
                parse_mode='HTML'
            )
        
        # إنهاء الهجوم
        final_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"عدد الهجمات: {attacks_count}", callback_data="attack_count")
            ],
            [
                InlineKeyboardButton(f"البيانات المرسلة: {data_sent:.2f} GB", callback_data="data_sent")
            ],
            [
                InlineKeyboardButton(f"المدة: {duration} ثانية", callback_data="duration")
            ],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])
        
        await query.message.edit_text(
            "💀 <b>انتهى الهجوم! الضੂحيه راحت فيها!</b>",
            reply_markup=final_keyboard,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in confirm_ip_attack: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ أثناء الهجوم</b>", parse_mode='HTML')

# ========== دوال الزخرفة ==========
def convert_name_to_style(name, style_chars):
    """تحويل الاسم إلى نمط معين"""
    try:
        normal_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        converted_name = ""

        for char in name:
            found = False
            for i, normal_char in enumerate(normal_chars):
                if i < len(style_chars):
                    if char.lower() == normal_char.lower():
                        if char.isupper():
                            converted_name += style_chars[i] if i < len(style_chars) else char
                        else:
                            converted_name += style_chars[i].lower() if i < len(style_chars) else char
                        found = True
                        break

            if not found:
                converted_name += char

        return converted_name
    except Exception as e:
        logger.error(f"Error in convert_name_to_style: {e}")
        return name

async def send_decorated_names(update, name):
    """إرسال الأسماء المزخرفة"""
    try:
        user_id = update.effective_user.id

        if BOT_STATUS == "stopped":
            await update.message.reply_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await update.message.reply_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        styles = [
            "𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹",
            "𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍",
            "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡",
            "𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕",
            "𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁",
            "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙",
            "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭",
            "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ",
            "𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅",
            "🅐🅑🅒🅓🅔🅕🅖🅗🅘🅙🅚🅛🅜🅝🅞🅟🅠🅡🅢🅣🅤🅥🅦🅧🅨🅩",
            "🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🅺🅻🅼🅽🅾🅿🆀🆁🆂🆃🆄🆅🆆🆇🆈🆉",
            "ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ",
            "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ",
            "ᴬᴮᶜᴰᴱᶠᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾQᴿᔆᵀᵁⱽᵂˣʸᶻ",
            "ᵃᵇᶜᵈᵉᶠᵍʰᶤʲᵏˡᵐᶰᵒᵖᵠʳˢᵗᵘᵛʷˣʸᶻ",
            "𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ",
            "𝒜ℬ𝒞𝒟ℰℱ𝒢ℋℐ𝒥𝒦ℒℳ𝒩𝒪𝒫𝒬ℛ𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵",
            "𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩",
            "αвcdeғɢнɪᴊĸℓмɴoρqʀѕтυvᴡxʏᴢ",
            "αႦƈԃҽϝɠԋιʝƙʅɱɳσρϙɾʂƚυʋɯxყȥ",
            "ค๒ς๔єŦgђเןкl๓ภỖปợгรtยvฬхץz",
            "₳฿₵ĐɆ₣₲ⱧłJ₭Ⱡ₥₦Ø₱QⱤ₴₮ɄV₩ӾɎⱫ",
            "ᗩᗷᑕᗪEᖴGᕼIᒍKᒪᗰᑎOᑭᑫᖇᔕTᑌᐯᗯ᙭Yᘔ",
            "卂乃匚ᗪ乇千Ꮆ卄丨ﾌҜㄥ爪几ㄖ卩Ɋ尺丂ㄒㄩᐯ山乂ㄚ乙",
            "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
            "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉"
        ]

        special_styles = [
            f"꧁༒{name}༒꧂",
            f"꧁ঔৣ☬{name}☬ঔৣ꧂",
            f"▶ ●─{name}─亗",
            f"꧁☆☬{name}☬☆꧂",
            f"ᎧᎮܔ{name}☯࿐",
            f"亗『{name}』亗",
            f"ıllıllı{name}ıllıllı",
            f"✦✧✧{name}✧✧✦",
            f"▁ ▂ ▄ ▅ ▆ ▇ █{name}█ ▇ ▆ ▅ ▄ ▂ ▁",
            f"◦•●◉✿{name}✿◉●•◦",
            f"(♥‿♥){name}(♥‿♥)",
            f"(ᵔᴥᵔ)(ᵔᴥᵔ){name}(ᵔᴥᵔ)(ᵔᴥᵔ)",
            f"■□■□■□■□{name}■□■□■□■□",
            f"✩｡:•.─────  ❁{name}❁  ─────.•:｡✩",
            f"✧○ꊞ○ꊞ○ꊞ○ꊞ○ꊞ{name}○ꊞ○ꊞ○ꊞ○ꊞ○✧¤",
            f"•♫•♬•{name}•♫•♬•",
            f"▀▄▀▄▀▄{name}▄▀▄▀▄▀",
            f"°。°。°。°。°。°。{name}°。°。°。°。°。°。",
            f"【｡_｡】{name}【｡_｡】",
            f"(｡◕‿‿◕｡){name}(｡◕‿‿◕｡)",
            f"╔────── ¤ ◎{name}◎ ¤ ──────╗",
            f"●▬▬▬▬๑۩{name}۩๑▬▬▬▬▬●",
            f"❤(｡◕‿◕｡)❤{name}❤(｡◕‿◕｡)❤",
            f"▼△▼△▼△▼{name}▼△▼△▼△▼",
            f"【ツ】{name}【ツ】",
            f"●○●○●○●○{name}●○●○●○●○",
            f"▓▓▓▓▓▓{name}▓▓▓▓▓▓",
            f"➶➶➶➶➶{name}➷➷➷➷➷",
            f"`•.¸¸.•´´¯`••._.•{name}•._.••`¯´´•.¸¸.•`",
            f"❂✿❂✿❂{name}❂✿❂✿❂",
            f"乁། ˵ ◕ – ◕ ˵ །ㄏ{name}乁། ˵ ◕ – ◕ ˵ །ㄏ",
            f"╰། ◉ ◯ ◉ །╯{name}╰། ◉ ◯ ◉ །╯",
            f"░▒▓█{name}█▓▒░",
            f"(ღ˘⌣˘ღ){name}(ღ˘⌣˘ღ)",
            f"︵‿︵‿︵‿︵‿︵‿{name}︵‿︵‿︵‿︵‿︵‿",
            f"⋋⁞ ◔ ﹏ ◔ ⁞⋌{name}⋋⁞ ◔ ﹏ ◔ ⁞⋌",
            f"◇◆◇◆◇◆◇◆◇◆◇{name}◇◆◇◆◇◆◇◆◇◆◇",
            f"¯\\_(ツ)_//¯{name}¯\\_(ツ)_//¯",
            f"(￢_￢){name}(￢_￢)",
            f"︵‿︵‿୨{name}୧‿︵‿︵",
            f"❤(❁´◡`❁)❤{name}❤(❁´◡`❁)❤",
            f"⫷{name}⫸",
            f"╚═| ~ ಠ ₒ ಠ ~ |═╝{name}╚═| ~ ಠ ₒ ಠ ~ |═╝",
            f"✿◡‿◡{name}◡‿◡✿",
            f"<(▰˘◡˘▰)>{name}<(▰˘◡˘▰)>",
            f"〓〓〓〓〓{name}〓〓〓〓〓",
            f"❏ ❐ ❑ ❒ ❏ ❐{name}❏ ❐ ❑ ❒ ❏ ❐",
            f"◤◢◣◥◤◢◣◥◤{name}◤◢◣◥◤◢◣◥◤",
            f"╰────╯╰────╯╰────╯╰────╯╰────╯╰────╯{name}╰────╯╰────╯╰────╯╰────╯╰────╯╰────╯",
            f"☜♡☞{name}☜♡☞",
            f"(´・_・`){name}(´・_・`)",
            f"✌✌(•ิ‿•ิ)✌✌{name}✌✌(•ิ‿•ิ)✌✌",
            f"✎﹏﹏{name}﹏﹏",
            f"❣❤---» [{name}] «---❤❣",
            f"(▰˘◡˘▰){name}(▰˘◡˘▰)",
            f"☀(ღ˘⌣˘ღ)☀{name}☀(ღ˘⌣˘ღ)☀",
            f"༺═──{name}──═༻",
            f"❄♥‿♥❄{name}❄♥‿♥❄",
            f"❤ᶫᵒᵛᵉᵧₒᵤ❤{name}❤ᶫᵒᵛᵉᵧₒᵤ❤",
            f"●▬ൠൠ▬{name}▬ൠൠ▬●",
            f"[̲̅ə̲̅٨̲̅٥̲̅٦̲̅]{name}[̲̅ə̲̅٨̲̅٥̲̅٦̲̅]",
            f"❀ೋ══•{name}•══ೋ❀",
            f"☃（*^_^*）☃{name}☃（*^_^*）☃",
            f"♡◙‿◙♡{name}♡◙‿◙♡",
            f"❣ლʘ‿ʘლ❣{name}❣ლʘ‿ʘლ❣",
            f"♪┏(°.°)┛{name}♪┏(°.°)┛",
            f"⊂◉‿◉つ{name}⊂◉‿◉つ",
            f"◎ ════{name}════ ◎",
            f"↪↪↪{name}↩↩↩",
            f"◥▓▓{name}▓▓◤",
            f"꧁𓊈𒆜{name}𒆜𓊉꧂",
            f"▄︻̷̿┻̿═━一 {name}"
        ]

        await update.message.reply_text("✨ <b>حالاً ي فندم</b>", parse_mode='HTML')

        for i, style_chars in enumerate(styles):
            try:
                decorated_name = convert_name_to_style(name, style_chars)
                if decorated_name and decorated_name.strip():
                    await update.message.reply_text(decorated_name)
                    await asyncio.sleep(0)
            except Exception as e:
                logger.error(f"Error sending decorated name {i}: {e}")
                continue

        for special_style in special_styles:
            try:
                await update.message.reply_text(special_style)
                await asyncio.sleep(0)
            except Exception as e:
                logger.error(f"Error sending special style: {e}")
                continue

        await update.message.reply_text("🎉 <b>تم الانتهاء من الزخرفة!</b>\n\n💡 <b>متنساش تشكر حمزه😇❤️‍🩹</b>", parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in send_decorated_names: {e}")
        await update.message.reply_text("❌ <b>حدث خطأ في الزخرفة. حاول مرة أخرى.</b>", parse_mode='HTML')

# ========== دوال الإيميل المؤقت ==========
async def handle_temp_email_button(query):
    """معالجة زر الإيميل المؤقت"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return
          

        email_bot_url = "t.me/emaaaaliyBot?start=0"
        clickable_link = f'<a href="{email_bot_url}">{email_bot_url}</a>'

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📧 فتح بوت البريد المؤقت ✉️", url=email_bot_url)],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            "📧 <b>خدمة الإيميل المؤقت</b>\n\n"
            "🔗 <b>انقر على الزر أدناه لفتح بوت الإيميل المؤقت:</b>\n\n"
            f"{clickable_link}\n\n"
            "💡 <b>طريقة الاستخدام:</b>\n"
            "1. افتح بوت الإيميل المؤقت من الزر أدناه\n"
            "2. إضغط على /start\n"
            "3. سيتم إنشاء إيميل مؤقت تلقائياً\n"
            "4. يمكنك استقبال الرسائل على هذا الإيميل\n"
            "5. الإيميل ينتهي بعد فترة تلقائياً\n"
            "6. إذا البوت طلب منك اشتراك ف قنوات \n"
            "   إرسل /start اكثر هيشتغل بدون اشتراك 👑",
            reply_markup=keyboard,
            parse_mode='HTML',
            disable_web_page_preview=False
        )

    except Exception as e:
        logger.error(f"Error in handle_temp_email_button: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')

# ========== دوال الأرقام الوهمية ==========
async def handle_virtual_numbers(query):
    """معالجة زر الأرقام الوهمية"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        virtual_numbers_url = "https://ar.temporary-phone-number.com/"
        clickable_link = f'<a href="{virtual_numbers_url}">{virtual_numbers_url}</a>'

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("☎️ موقع الارقام الوهمية ☎️", url=virtual_numbers_url)],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            "☎️ <b>اليك افضل موقع ارقام وهمية ☎️✅</b>\n\n"
            "• <b>وعن تجربتي انا شخصيا 👨🏻‍💻✅</b>\n"
            "• <b>شغال 100% ✅</b>\n\n"
            "<b>• الموقع اهو وإدعيلي ❤️‍🩹👇</b>\n\n"
            f"{clickable_link}",
            reply_markup=keyboard,
            parse_mode='HTML',
            disable_web_page_preview=False
        )

    except Exception as e:
        logger.error(f"Error in handle_virtual_numbers: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')
#____________ دالة الاتصال الوهمي _______
async def handle_fake_call(query):
    """معالجة زر الاتصال الوهمي"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        # الرابط
        call_url = "https://callmyphone.org/app"
        
        # إنشاء الرسالة
        message_text = """
<b>قم بالدخول الى الموقع وحط الرقم ثم قم بالاتصال</b>

<b>ملحوظه: 🙂</b>
<b>مسموح مرة ف اليوم</b>

<b>حط الرقم مع رمز الدولة بدون + او 00 مثل</b>

<b>mt / - 967 وهنا الرقم</b>
"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("فتح الموقع 🌐", web_app=WebAppInfo(url=call_url))],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])

        await query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in handle_fake_call: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')
        
async def handle_get_user_info(query):
    """معالجة زر معرفة معلومات المستخدم"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        await query.message.edit_text(
            "👤 <b>معرفة معلومات المستخدم</b>\n\n"
            "🦅 <b>أرسل لي الـID الخاص بالمستخدم</b>\n\n"
            "💡 <b>مثال:</b> <code>8443706468</code>\n\n"
            "⚠️ <b>ملاحظة:</b> يجب أن يكون المستخدم قد تفاعل مع البوت من قبل",
            parse_mode='HTML'
        )
        
        # حفظ حالة انتظار ID
        context = query.message._bot
        context = context._context
        context.user_data['waiting_for_user_id'] = True
        context.user_data['user_id_for_info'] = user_id

    except Exception as e:
        logger.error(f"Error in handle_get_user_info: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')

async def process_user_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id_str: str):
    """معالجة ID المستخدم المدخل"""
    try:
        user_id = update.effective_user.id
        
        # التحقق من الحالة
        if not context.user_data.get('waiting_for_user_id'):
            return False
            
        if context.user_data.get('user_id_for_info') != user_id:
            return False
            
        # محاولة تحويل ID إلى رقم
        try:
            target_user_id = int(target_user_id_str)
        except ValueError:
            await update.message.reply_text(
                "❌ <b>الـID غير صالح!</b>\n\n"
                "🔢 <b>يجب أن يكون الـID رقماً صحيحاً</b>\n\n"
                "🔄 <b>جرب مرة أخرى:</b>",
                parse_mode='HTML'
            )
            return True
            
        # محاولة جلب معلومات المستخدم من تيليجرام
        try:
            # محاولة جلب معلومات المستخدم
            user_chat = await context.bot.get_chat(target_user_id)
            
            # استخراج المعلومات
            user_name = user_chat.first_name or "غير معروف"
            if user_chat.last_name:
                user_name += f" {user_chat.last_name}"
                
            username = f"@{user_chat.username}" if user_chat.username else "لا يوجد"
            
            bio = user_chat.bio or "لا يوجد نبذة"
            
            # إنشاء رابط قابل للضغط على الاسم
            profile_link = f"tg://user?id={target_user_id}"
            clickable_name = f'<a href="{profile_link}">{user_name}</a>'
            
            # إنشاء الرسالة
            message_text = f"""
👤 <b>معلومات المستخدم</b>

🆔 <b>الـID:</b> <code>{target_user_id}</code>
👑 <b>الاسم:</b> {clickable_name}
📱 <b>اليوزر:</b> {username}
📝 <b>النبذة:</b>
{bio}
            """
            
            # إنشاء لوحة المفاتيح
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 رؤية حساب المستخدم", url=profile_link)],
                [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
            ])
            
            await update.message.reply_text(
                message_text,
                reply_markup=keyboard,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error fetching user info: {e}")
            await update.message.reply_text(
                f"❌ <b>لم أتمكن من جلب معلومات المستخدم</b>\n\n"
                f"🔧 <b>الأسباب المحتملة:</b>\n"
                f"• المستخدم غير موجود\n"
                f"• المستخدم لم يتفاعل مع البوت من قبل\n"
                f"• المشكلة: {str(e)}\n\n"
                f"🔄 <b>جرب مع ID آخر</b>",
                parse_mode='HTML'
            )
        
        # تنظيف حالة الانتظار
        context.user_data['waiting_for_user_id'] = False
        context.user_data.pop('user_id_for_info', None)
        return True
        
    except Exception as e:
        logger.error(f"Error in process_user_id_input: {e}")
        return False
#===== دوال معرفة الـID الخاص بك =======
async def handle_get_my_id(query):
    """معالجة زر معرفة الـID الخاص بالمستخدم"""
    try:
        user_id = query.from_user.id

        if BOT_STATUS == "stopped":
            await query.message.edit_text("⏸️ <b>البوت متوقف حاليًا</b>", parse_mode='HTML')
            return

        if is_user_blocked(user_id):
            await query.message.edit_text("🚫 <b>أنت محظور من استخدام هذا البوت!</b>", parse_mode='HTML')
            return

        # إرسال رسالة جديدة
        await query.message.reply_text(
            f"🆔 <b>هذا هو الـID الخاص بك 👇</b>\n\n"
            f"      →→        <code>{user_id}</code>        ←←\n\n"
            f"💡 <b>اضغط على الـID لنسخه</b>",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in handle_get_my_id: {e}")
        await query.message.edit_text("❌ <b>حدث خطأ في تحميل الخدمة</b>", parse_mode='HTML')
 
 
# ========== الدالة الرئيسية ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "غير معروف"

        # التحقق إذا كان المستخدم جديداً
        is_new_user = user_id not in USER_DATABASE
        
        # إضافة المستخدم إلى قاعدة البيانات
        add_user_to_database(user_id)

        if BOT_STATUS == "stopped":
            await update.message.reply_text(
                "⏸️ <b>البوت متوقف حاليًا عن العمل</b>\n\n"
                "🔧 <b>جاري الصيانة والتطوير...</b>\n"
                "⏳ <b>سيتم العودة قريبًا</b>\n\n"
                "📞 <b>للاستفسار:</b> @jt_r3r",
                parse_mode='HTML'
            )
            return

        if is_user_blocked(user_id):
            await update.message.reply_text(
                "🚫 <b>أنت محظور من استخدام هذا البوت!</b>\n\n"
                "🔒 <b>لا يمكنك الوصول إلى الخدمات</b>\n"
                "📞 <b>للاستفسار:</b> @jt_r3r",
                parse_mode='HTML'
            )
            return

        user = update.effective_user
        keyboard = InlineKeyboardMarkup(BUTTONS)

        user_link = f'<a href="tg://user?id={user_id}">{user.first_name}</a>'

        await update.message.reply_text(
            f"هلا بك يا {user_link} 👋\n\n"
            f"في البوت الـ م̸َِـۥـِجًـهـ̸ــﯡل الـمـصـري 🇪🇬\n\n"
            f"🎉 كل الأزرار مجاناً!!",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        
        # إرسال إشعار للمطور إذا كان المستخدم جديداً
        if is_new_user:
            await send_new_user_notification(context, user_id, user_name)
            
    except Exception as e:
        logger.error(f"Error in start command: {e}")
# ========== معا��جة الرسائل ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        
        # التحقق من حالة معرفة المستخدم
        if context.user_data.get('waiting_for_user_id'):
            user_message = update.message.text.strip()
            if user_message:
                await get_user_info_handler(update, context, user_message)
            else:
                await update.message.reply_text("❌ <b>لم تقم بإرسال الـID!</b>", parse_mode='HTML')
            
            # تنظيف الحالة
            context.user_data['waiting_for_user_id'] = False
            return
           
        if context.user_data.get('waiting_for_telz_number'):
            context.user_data.pop('waiting_for_telz_number', None)
            text = (update.message.text or "").strip()

    # التحقق: لازم يكون فيه 10–15 رقم على الأقل
            cleaned = re.sub(r"[^0-9]", "", text)
            if not re.fullmatch(r"\d{10,15}", cleaned):
                await update.message.reply_text(
                    "❌ <b>رقم غير صالح</b>\n"
                    "أرسل الرقم بدون + أو مسافات\n"
                    "مثال: <code>01012345678</code> أو <code>201012345678</code>",
                    parse_mode='HTML'
                )
                context.user_data['waiting_for_telz_number'] = True
                return

            msg = await update.message.reply_text("⏳ <b>جاري التنفيذ...</b>", parse_mode='HTML')
            ok, err = await telz_send_call(cleaned)

            if ok:
                await msg.edit_text("✅ <b>تم إرسال اتصال 1</b>", parse_mode='HTML')
            else:
                await msg.edit_text(f"❌ <b>فشل الإرسال:</b>\n<code>{err}</code>", parse_mode='HTML')
            return
        

        if BOT_STATUS == "stopped":
            if is_developer(user_id) and update.message.text and update.message.text.startswith(('/', 'Hamza1', 'Hamza', 'blocked', 'send_all')):
                pass
            else:
                await update.message.reply_text(
                    "⏸️ <b>البوت متوقف حاليًا عن العمل</b>\n\n"
                    "🔧 <b>جاري الصيانة والتطوير...</b>\n"
                    "⏳ <b>سيتم العودة قريبًا</b>\n\n"
                    "📞 <b>للاستفسار:</b> @jt_r3r",
                    parse_mode='HTML'
                )
                return

        if is_user_blocked(user_id) and not is_developer(user_id):
            await update.message.reply_text(
                "🚫 <b>أنت محظور من استخدام هذا البوت!</b>\n\n"
                "🔒 <b>لا يمكنك الوصول إلى الخدمات</b>\n"
                "📞 <b>للاستفسار:</b> @jt_r3r",
                parse_mode='HTML'
            )
            return

        if is_developer(user_id) and user_id in DEVELOPER_WAITING_FOR_INPUT:
            action = DEVELOPER_WAITING_FOR_INPUT[user_id]
            if action == "waiting_for_broadcast_message":
                await handle_broadcast_message(update, context)
                return
            else:
                await handle_developer_input(update, context)
                return
        # معالجة أوامر المطور من الأزرار
        if is_developer(user_id) and context.user_data.get('owner_action'):
            action = context.user_data['owner_action']
            user_message = update.message.text.strip()

            if action == 'block':
                try:
                    target_id = int(user_message)
                    BLOCKED_USERS.add(target_id)
                    save_data()
                    await update.message.reply_text(f"✅ <b>تم حظر {target_id}</b>", parse_mode='HTML')
                except:
                    await update.message.reply_text("❌ <b>ID غير صالح</b>", parse_mode='HTML')

            elif action == 'unblock':
                try:
                    target_id = int(user_message)
                    BLOCKED_USERS.discard(target_id)
                    save_data()
                    await update.message.reply_text(f"✅ <b>تم فك حظر {target_id}</b>", parse_mode='HTML')
                except:
                    await update.message.reply_text("❌ <b>ID غير صالح</b>", parse_mode='HTML')

            elif action == 'broadcast':
        # استخدم الدالة القديمة للإذاعة
                DEVELOPER_WAITING_FOR_INPUT[user_id] = "waiting_for_broadcast_message"
                await handle_broadcast_message(update, context)

            context.user_data['owner_action'] = None
            return

        user_message = update.message.text

        if context.user_data.get('sending_to_developer'):
            if user_message.strip():
                await send_message_to_developer(update, context, user_message.strip())
            else:
                await update.message.reply_text("❌ <b>لم تقم بإرسال رسالة!</b>", parse_mode='HTML')
            context.user_data['sending_to_developer'] = False
            return
        
        if context.user_data.get('waiting_for_ip'):
            if user_message.strip():
                ip_address = user_message.strip()
    
                # جلب معلومات الـIP
                await update.message.reply_text("🌍 <b>لحظه ↓</b>", parse_mode='HTML')
                ip_info = await get_ip_info(ip_address)
    
                if ip_info:
                    # إنشاء رسالة المعلومات
                    info_message = f"""
🔹 <b>معلومات عنوان IP: {ip_address}</b> 🔹
-------------------------------------
🌍1- الدولة: {ip_info['country']}
🏙2- المنطقة: {ip_info['region']}
🏢3- المدينة: {ip_info['city']}
📍4- الرمز البريدي: {ip_info['zip']}
🕹5- ISP: {ip_info['isp']}
🖥6- الشركة: {ip_info['org']}
🔌7- نوع الاتصال: {ip_info['as_name']}
🌐8- نطاقIP: {ip_address}
-------------------------------------
📡 الإحداثيات الجغرافية:
🗺9- خط العرض: {ip_info['lat']}
🗺10- خط الطول: {ip_info['lon']}
-------------------------------------
⏳11- المنطقة الزمنية: {ip_info['timezone']}
🚦12- نطاق الاستخدام: عام
🌍13- Tor / VPN: لا
                    """
            
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("☠️ تأكيد الهجوم ☠️", callback_data=f"confirm_attack_{ip_address}")],
                        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
                    ])
            
                    await update.message.reply_text(
                        info_message,
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(
                        "❌ <b>لم أتمكن من جلب معلومات الـIP</b>\n\n"
                        "🔧 <b>تأكد من صحة العنوان وحاول مرة أخرى</b>",
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text("❌ <b>لم تقم بإرسال عنوان IP!</b>", parse_mode='HTML')

            context.user_data['waiting_for_ip'] = False
            context.user_data.pop('user_id_for_ip', None)
            return

        if context.user_data.get('waiting_for_shorten'):
            await shorten_url_handler(update, context)
            return

        if context.user_data.get('tracking_ip'):
            if user_message.strip():
                ip = user_message.strip()
                await update.message.reply_text("🌍 <b>جاري تتبع العنوان...</b>", parse_mode='HTML')
                result = await track_ip_address(ip)
                await update.message.reply_text(result, parse_mode='HTML')
            else:
                await update.message.reply_text("❌ <b>لم تقم بإرسال عنوان IP!</b>", parse_mode='HTML')
            context.user_data['tracking_ip'] = False
            return

        if user_message.strip().lower() == 'ip':
            await update.message.reply_text("🌍 <b>جاري تتبع عنوان IP الخاص بك...</b>", parse_mode='HTML')
            result = await track_ip_address('myip')
            await update.message.reply_text(result, parse_mode='HTML')
            return

        if context.user_data.get('checking_link'):
            context.user_data['checking_link'] = False
            raw = (user_message or "").strip()

            if not raw:
                await update.message.reply_text("❌ <b>لم تقم بإرسال رابط!</b>", parse_mode='HTML')
                return

    # استخرج أول URL من النص
            match = re.search(r'https?://[^\s<>"]+', raw)
            if not match:
                await update.message.reply_text(
                    "❌ <b>الرابط غير صالح</b>\n"
                    "لازم يبدأ بـ <code>http://</code> أو <code>https://</code>",
                    parse_mode='HTML'
                )
                return

            url = match.group(0)

            await update.message.reply_text("🔍 <b>جاري فحص الرابط...</b>", parse_mode='HTML')

            try:
                result = await check_url_safety(url)
            except Exception as e:
                logger.error(f"check_url_safety error: {e}")
                result = "❌ فشل الفحص"

            if not result:
                result = "❌ فشل الفحص"

    # هرب الحروف الخطيرة من result
            import html
            safe_result = html.escape(str(result))
            safe_url_display = html.escape(url)

            clickable_url = f'<a href="{url}">{safe_url_display}</a>'

            await update.message.reply_text(
                f"📊 <b>نتيجة فحص الرابط:</b>\n\n"
                f"🔗 <b>الرابط:</b> {clickable_url}\n\n"
                f"📋 <b>الحالة:</b> {safe_result}",
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            return
           

        if context.user_data.get('waiting_for_name'):
            if len(user_message.strip()) > 0:
                name = user_message.strip()
                await send_decorated_names(update, name)
            else:
                await update.message.reply_text("❌ <b>الاسم غير صالح!</b>", parse_mode='HTML')
            context.user_data['waiting_for_name'] = False
            return
            
       
        if context.user_data.get('waiting_for_video_url'):
            context.user_data.pop('waiting_for_video_url', None)
            raw = (update.message.text or "").strip()

            match = re.search(r'https?://[^\s<>"]+', raw)
            if not match:
                await update.message.reply_text("❌ <b>رابط غير صالح!</b>", parse_mode='HTML')
                return

            url = match.group(0)
            msg = await update.message.reply_text("⏳ <b>جاري التحميل... قد يأخذ دقيقة</b>", parse_mode='HTML')

    # شغل التحميل في الخلفية عشان البوت ميتجمدش
            loop = asyncio.get_event_loop()
            file_path, err = await loop.run_in_executor(None, download_video_auto, url)

            if not file_path:
                await msg.edit_text(f"❌ <b>فشل التحميل:</b> {err}", parse_mode='HTML')
                return

            try:
                size = os.path.getsize(file_path)
                if size > 50 * 1024 * 1024:
                    await msg.edit_text("❌ <b>الملف أكبر من 50MB</b> (حد تلجرام للبوتات)", parse_mode='HTML')
                    return

                await msg.edit_text("📤 <b>جاري الرفع لتلجرام...</b>", parse_mode='HTML')
                ok = await send_video_auto(update, context, file_path)
                if ok:
                    await msg.delete()
                else:
                    await msg.edit_text("❌ <b>فشل إرسال الفيديو</b>", parse_mode='HTML')
            finally:
                try:
                    os.remove(file_path)
                except:
                    pass
            return

        if context.user_data.get('waiting_for_link'):
            if user_message.startswith('https://'):
                clickable_link = f'<a href="{user_message}">{user_message}</a>'
                await update.message.reply_text(
                    f"🔗 <b>الرابط الملتغم:</b>\n{clickable_link}\n\n⚠️ <b>تم التلغيم بنجاح!</b>",
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
            else:
                await update.message.reply_text("❌ <b>الرابط غير صالح!</b>", parse_mode='HTML')
            context.user_data['waiting_for_link'] = False
            return

        await update.message.reply_text("🔧 <b>استخدم الأزرار للتفاعل مع البوت</b>\n\nاضغط /start لرؤية القائمة الكاملة 🎛️", parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"حدث خطأ: {context.error}")

import socket

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

async def get_user_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, target_id: str):
    """معالجة ID المستخدم وإظهار معلوماته"""
    try:
        target_user_id = int(target_id)
        
        # جلب معلومات المستخدم
        user_chat = await context.bot.get_chat(target_user_id)
        
        # تجميع المعلومات
        user_name = user_chat.first_name or "غير معروف"
        if user_chat.last_name:
            user_name += f" {user_chat.last_name}"
        
        username = f"@{user_chat.username}" if user_chat.username else "لا يوجد"
        bio = user_chat.bio or "لا يوجد نبذة"
        profile_link = f"tg://user?id={target_user_id}"
        
        # الرسالة النهائية
        message_text = f"""
👤 <b>معلومات المستخدم</b>

🆔 <b>الـID:</b> <code>{target_user_id}</code>
👑 <b>الاسم:</b> <a href="{profile_link}">{user_name}</a>
📱 <b>اليوزر:</b> {username}
📝 <b>النبذة:</b>
{bio}
        """
        
        # الأزرار
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("دخول حساب المستخدم 👤", url=profile_link)],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")]
        ])
        
        await update.message.reply_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
    except ValueError:
        await update.message.reply_text("❌ <b>الـID يجب أن يكون رقماً!</b>", parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        await update.message.reply_text(
            f"❌ <b>لم أستطع جلب معلومات المستخدم</b>\n\n"
            f"🔧 <b>السبب:</b> {str(e)[:100]}",
            parse_mode='HTML'
        )
        
# ========== Telz Call (نفس منطق PHP) ==========
def callbomber_generate_unique_ids():
    ts = int(time.time() * 1000)
    android_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
    unique_uuid = str(uuid.uuid4())
    return ts, android_id, unique_uuid


def callbomber_send_one_call(phone: str):
    """ترجع (True, '') عند النجاح أو (False, 'سبب الفشل')."""
    # شيل أي حاجة مش رقم
    phone = re.sub(r"[^0-9]", "", phone)
    if not phone:
        return False, "رقم فارغ"

    # لو بيبدأ بـ 0 → +2 (مصر)
    if phone.startswith("0"):
        full_phone = "+2" + phone
    else:
        full_phone = "+" + phone

    ts, android_id, unique_uuid = callbomber_generate_unique_ids()

    headers = {
        "User-Agent": "Telz-Android/17.5.17",
        "Content-Type": "application/json",
    }

    # 1) install
    install_data = json.dumps({
        "android_id": android_id,
        "app_version": "17.5.17",
        "event": "install",
        "google_exists": "yes",
        "os": "android",
        "os_version": "9",
        "play_market": True,
        "ts": ts,
        "uuid": unique_uuid,
    })
    try:
        r = requests.post(
            "https://api.telz.com/app/install",
            data=install_data,
            headers=headers,
            timeout=15,
            verify=False,
        )
    except requests.RequestException as e:
        return False, f"خطأ اتصال (install): {e}"

    if r.status_code != 200 or "ok" not in r.text:
        return False, "فشل في مرحلة التثبيت"

    time.sleep(0.5)

    # 2) auth_call
    call_data = json.dumps({
        "android_id": android_id,
        "app_version": "17.5.17",
        "attempt": "0",
        "event": "auth_call",
        "lang": "ar",
        "os": "android",
        "os_version": "9",
        "phone": full_phone,
        "ts": ts,
        "uuid": unique_uuid,
    })
    try:
        r = requests.post(
            "https://api.telz.com/app/auth_call",
            data=call_data,
            headers=headers,
            timeout=15,
            verify=False,
        )
    except requests.RequestException as e:
        return False, f"خطأ اتصال (auth_call): {e}"

    if r.status_code == 200 and "ok" in r.text:
        return True, ""

    return False, "فشل في إرسال المكالمة"


async def telz_send_call(phone: str):
    """نسخة async عشان البوت ميتجمدش."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, callbomber_send_one_call, phone)
    
# ========== دوال تحميل الفيديوهات ==========
def ensure_ytdlp_installed():
    """يتأكد إن yt-dlp متاح."""
    if shutil.which("yt-dlp"):
        return "yt-dlp"
    try:
        import yt_dlp
        return sys.executable + " -m yt_dlp"
    except ImportError:
        return None

def download_video_auto(url: str):
    """يحمّل الفيديو ويرجع مسار الملف أو None."""
    ytdlp_cmd = ensure_ytdlp_installed()
    if not ytdlp_cmd:
        return None, "yt-dlp غير متوفر على السيرفر"

    temp_dir = tempfile.gettempdir()
    filename = f"video_{int(time.time())}_{random.randint(1000, 9999)}"
    output_template = os.path.join(temp_dir, f"{filename}.%(ext)s")

    # تجهيز الأمر
    if " " in ytdlp_cmd:
        cmd = ytdlp_cmd.split()
    else:
        cmd = [ytdlp_cmd]

    cmd.extend([
        "--restrict-filenames",
        "--no-playlist",
        "--format", "best[ext=mp4]/best",
        "--output", output_template,
        "--no-warnings",
        "--no-cache-dir",
        "--geo-bypass",
        "--socket-timeout", "30",
        "--retries", "3",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        url,
    ])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"yt-dlp stderr: {result.stderr[-500:]}")
            return None, "فشل التحميل (تأكد من الرابط)"

        matches = glob.glob(os.path.join(temp_dir, f"{filename}.*"))
        if not matches:
            return None, "لم يتم العثور على الملف بعد التحميل"
        return matches[0], ""
    except subprocess.TimeoutExpired:
        return None, "انتهت المهلة (الفيديو كبير جداً)"
    except Exception as e:
        logger.error(f"download_video_auto error: {e}")
        return None, str(e)

async def send_video_auto(update, context, file_path: str):
    """يرسل الفيديو للمستخدم."""
    try:
        if not os.path.exists(file_path):
            return False
        size = os.path.getsize(file_path)
        if size < 1000:
            return False
        if size > 50 * 1024 * 1024:  # 50MB حد تلجرام
            return False

        size_mb = round(size / (1024 * 1024), 2)
        with open(file_path, "rb") as f:
            await update.message.reply_video(
                video=f,
                caption=f"✅ <b>تم التحميل بنجاح!</b>\n📦 <b>الحجم:</b> {size_mb} MB",
                parse_mode="HTML",
                supports_streaming=True,
            )
        return True
    except Exception as e:
        logger.error(f"send_video_auto error: {e}")
        return False    
        

async def main():
    try:
        print("🚀 جاري تشغيل البوت...")
        
        # 1. تجهيز Flask عشان Render ميقفلش السيرفر
        # Render بيحدد البورت عن طريق os.environ['PORT']
        port = int(os.environ.get("PORT", 8080))
        
        def run_flask():
            # بنشغله في thread منفصل عشان ميعطلش البوت
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        print(f"✅ تم تشغيل خادم Flask على المنفذ {port}")

        # 2. تشغيل البوت
        application = Application.builder().token(TOKEN).build()

        # إضافة أمر المطور الجديد
        application.add_handler(CommandHandler("owner", owner_command))
        application.add_handler(CallbackQueryHandler(owner_button_click, pattern="^owner_"))

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CallbackQueryHandler(button_click))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_message))

        application.add_error_handler(error_handler)

        print("=" * 50)
        print("✅ البوت يعمل بنجاح!")
        print("⏰ " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 50)
        print("❍❥  𝐇        𝐀        𝐌        𝐙        𝐀  ||:❥❍")
        print("=" * 50)

        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
        # حفظ البيانات تلقائياً كل 5 دقائق
        async def auto_save():
            while True:
                await asyncio.sleep(300)  # 5 دقائق
                save_data()
        
        asyncio.create_task(auto_save())
        
        # إبقاء البوت شغال
        while True:
            await asyncio.sleep(3600)

    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        print("🔄 إعادة التشغيل خلال 30 ثانية...")
        await asyncio.sleep(30)
        await main()

if __name__ == '__main__':
    # بنشغل البوت داخل حلقة asyncio
    asyncio.run(main())