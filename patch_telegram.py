import os
import sys

# البحث عن مسار مكتبة تلجرام باستخدام بايثون نفسه
try:
    import telegram
    telegram_dir = os.path.dirname(telegram.__file__)
except ImportError:
    print("❌ مكتبة telegram غير مثبتة!")
    sys.exit(1)

target_file = os.path.join(telegram_dir, "_inlinekeyboardbutton.py")

if not os.path.exists(target_file):
    print(f"❌ الملف غير موجود: {target_file}")
    sys.exit(1)

print(f"✅ تم العثور على الملف: {target_file}")

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

if "style: Optional[str] = None" in content:
    print("✅ المكتبة معدلة بالفعل.")
    sys.exit(0)

# 1. إضافة style في __init__
content = content.replace(
    "def __init__(\n        self,\n        text: str,",
    "def __init__(\n        self,\n        text: str,\n        style: Optional[str] = None,"
)

# 2. حفظ style كـ attribute
content = content.replace(
    "self.text = text",
    "self.text = text\n        self.style = style"
)

# 3. إضافته للـ payload اللي بيتبعت لتلجرام
content = content.replace(
    '"text": self.text,',
    '"text": self.text,\n            "style": self.style,'
)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)

# التحقق
with open(target_file, "r", encoding="utf-8") as f:
    if "style: Optional[str] = None" in f.read():
        print("✅ تم تعديل مكتبة تلجرام بنجاح!")
    else:
        print("❌ فشل التعديل — الكود مش مطابق للمتوقع")
        sys.exit(1)
