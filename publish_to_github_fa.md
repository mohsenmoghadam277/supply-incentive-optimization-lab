# راهنمای انتشار پروژه در GitHub

این پوشه برای تبدیل‌شدن به یک مخزن GitHub آماده شده است. فایل‌های کد و مستندات در ریشه‌ی پروژه قرار دارند؛ فایل ZIP را به‌عنوان یک فایل واحد در مخزن آپلود نکنید.

## روش پیشنهادی: GitHub Desktop

1. فایل ZIP نهایی را دانلود و در یک مسیر مشخص Extract کنید.
2. در GitHub یک مخزن جدید با نامی مثل `supply-incentive-optimization-lab` بسازید. چون فایل‌های README و License از قبل در این بسته وجود دارند، مخزن را در GitHub با README یا License جدید مقداردهی اولیه نکنید.
3. با GitHub Desktop پوشه‌ی Extractشده را به‌عنوان مخزن محلی اضافه کنید یا در همان پوشه یک مخزن محلی جدید بسازید.
4. فایل‌ها را بررسی کنید؛ سپس یک commit مانند `Initial portfolio release` ثبت و مخزن را روی GitHub منتشر کنید.
5. در صورت استفاده برای رزومه، توضیح مخزن را وارد کنید:

   `End-to-end Data Science portfolio project for supply incentive experimentation, uplift modeling, campaign economics, FastAPI, SQL, and an interactive dashboard. Synthetic data only.`

## روش خط فرمان

پس از نصب Git و ساختن یک مخزن خالی در GitHub، PowerShell را در ریشه‌ی پوشه‌ی پروژه باز کنید. مقدار `YOUR_USERNAME` را با نام کاربری GitHub خود جایگزین کنید:

```powershell
git init
git add .
git status
git commit -m "Initial portfolio release"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/supply-incentive-optimization-lab.git
git push -u origin main
```

قبل از `git commit` خروجی `git status` را بررسی کنید و مطمئن شوید فایل محلی محرمانه‌ای اضافه نشده باشد. `.gitignore` محیط‌های مجازی، cacheها و فایل‌های محلی حساس متداول را حذف می‌کند؛ بااین‌حال، هیچ `.env`، credential، داده واقعی یا فایل محرمانه‌ای را به مخزن اضافه نکنید.

## پس از انتشار

- تب **Actions** را باز کنید و بررسی کنید workflow تست‌های Python با موفقیت تمام شود.
- صفحه‌ی اصلی مخزن را باز کنید و مطمئن شوید README انگلیسی نمایش داده می‌شود؛ README فارسی هم از پیوند ابتدای آن قابل دسترسی است.
- برای مشاهده‌ی داشبورد، فایل HTML را دانلود کنید و در مرورگر باز کنید، یا در ریشه‌ی پروژه `python -m http.server 8080` را اجرا کنید و آدرس `http://127.0.0.1:8080/snapp_incentive_dashboard_v3.html` را باز کنید.

**یادآوری:** داده‌ها، نتایج آزمایش، برآورد ROI و امتیازهای مدل کاملاً مصنوعی‌اند. پروژه مستقل است، به اسنپ وابستگی یا اتصال ندارد و نتایج آن را نباید به‌عنوان عملکرد واقعی یک شرکت معرفی کرد.
