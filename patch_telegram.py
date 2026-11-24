import os
import glob
import sys

# البحث عن مسار مكتبة تلجرام أوتوماتيك
site_packages = [p for p in sys.path if 'site-packages' in p]
if not site_packages:
    print("❌ لم يتم العثور على مجلد site-packages")
    sys.exit(1)

target_file = os.path.join(site_packages[0], "telegram", "_inlinekeyboardbutton.py")

if not os.path.exists(target_file):
    print(f"❌ الملف غير موجود: {target_file}")
    sys.exit(1)

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# تعديل دالة الـ init عشان تقبل style
if "style: Optional[str] = None" not in content:
    content = content.replace(
        "def __init__(\n        self,",
        "def __init__(\n        self,\n        style: Optional[str] = None,"
    )
    # إضافة السطر جوه الدالة
    content = content.replace(
        "self.url = url",
        "self.url = url\n        self.style = style"
    )
    # إضافة style للـ JSON اللي بيتبعت لتلجرام
    content = content.replace(
        '"url": url',
        '"url": url,\n            "style": style'
    )
    
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ تم تعديل مكتبة تلجرام بنجاح!")
else:
    print("✅ المكتبة معدلة بالفعل.")
