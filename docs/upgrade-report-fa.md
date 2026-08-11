# گزارش ارتقای comic-translate (شاخهٔ `ai-upgrade`)

آخرین به‌روزرسانی: ۱۱ اوت ۲۰۲۶ — وضعیت: بخش‌های ۱ و ۲ تمام، بخش ۳ منتظر تأیید، بخش ۴ شروع نشده.

این فایل زندهٔ گزارش است و در پایان هر بخش تکمیل می‌شود.

## فهرست

- [بخش ۱ — پرامپت سیستمی سفارشی](#بخش-۱--پرامپت-سیستمی-سفارشی)
- [بخش ۲ — ورک‌فلوی batch چند تصویری](#بخش-۲--ورکفلوی-batch-چند-تصویری)
- [بخش ۳ — پیشنهادهای خودکارسازی (منتظر تأیید)](#بخش-۳--پیشنهادهای-خودکارسازی-منتظر-تأیید)
- [بخش ۴ — رجیستری مدل‌ها (شروع نشده)](#بخش-۴--رجیستری-مدلها-شروع-نشده)
- [کارهای باقی‌مانده و تصمیم‌های لازم](#کارهای-باقیمانده-و-تصمیمهای-لازم)

---

## بخش ۱ — پرامپت سیستمی سفارشی

بخش جداگانه‌ای در تنظیمات که به کاربر اجازه می‌دهد دستور سیستمی خودش را **به** پرامپت پایه اضافه کند (هرگز جای آن را نگیرد).

### فایل‌های تغییر‌یافته

| فایل | کار |
|---|---|
| `app/ui/settings/llms_page.py` | `MTextEdit` پرامپت سفارشی + چک‌باکس فعال‌سازی + متن توضیح؛ پریست‌های نام‌دار به‌صورت JSON در QSettings؛ خاکستری‌شدن کنترل‌ها در حالت اکانت میزبان |
| `app/ui/settings/settings_page.py` | `custom_system_instructions` و `custom_system_instructions_enabled` به `get_llm_settings()` اضافه شد؛ ذخیره/بازخوانی از QSettings با پیش‌فرض سالم و JSON مقاوم به خرابی |
| `app/ui/settings/settings_ui.py` | معرفی ویجت‌های جدید به لایهٔ UI |
| `modules/translation/llm/base.py` | `get_final_system_prompt()` که متن کاربر را با جداکنندهٔ روشن به پرامپت پایه **می‌چسباند** (جایگزین نمی‌کند)؛ خواندن تنظیمات در `initialize()` |
| `modules/translation/user.py` | `logger.warning` برای حالت اکانت میزبان که این فیلد را پشتیبانی نمی‌کند |

### کامیت‌ها

| کامیت | عنوان |
|---|---|
| `80ea44d` | Append user-defined instructions to LLM system prompt |
| `d4ab7ec` | Add custom system prompt settings with named presets |
| `fe43866` | Log when a custom system prompt cannot reach the hosted backend |

### راهنمای تست دستی

1. Settings → بخش LLM → متنی در «Custom System Instructions» بنویس و چک‌باکس فعال‌سازی را بزن.
2. یک پریست نام‌دار ذخیره کن، تنظیمات را ببند و باز کن؛ متن و پریست باید برگردند.
3. یک صفحه را ترجمه کن؛ دستور سفارشی باید **علاوه بر** پرامپت پایه اعمال شود.
4. با اکانت میزبان وارد شو؛ کنترل‌ها باید خاکستری و همراه هشدار باشند.

### محدودیت

- پرامپت پایه در `modules/translation/base.py` دست‌نخورده ماند (خواستهٔ صریح).
- در حالت اکانت میزبان (`UserTranslator`) بک‌اند ComicLabs فیلدی برای system instructions ندارد؛ UI خاکستری می‌شود، برچسب هشدار نشان داده می‌شود و در لاگ هم warning ثبت می‌شود.
- برای GPT / Claude / Gemini / Deepseek / Custom در حالت کلید مستقیم کار می‌کند.

---

## بخش ۲ — ورک‌فلوی batch چند تصویری

### ۱) فایل‌های تغییر‌یافته و اضافه‌شده

| فایل | نوع | کار |
|---|---|---|
| `app/ui/list_view.py` | تغییر | نقش‌های `PAGE_STATUS_ROLE` / `PAGE_PROGRESS_ROLE`، وضعیت‌های queued/processing/done/failed، رسم برچسب وضعیت و نوار پیشرفت ۳ پیکسلی در دلیگیت، سیگنال‌های `retry_imgs` / `export_imgs`، آیتم منوی «Retry this page» فقط برای ردیف Failed، «Export Selected...»، و ارسال مسیر کامل صفحه (نه فقط نام فایل) در همهٔ اکشن‌ها |
| `app/controllers/image.py` | تغییر | `page_status` و `_batch_order`؛ متدهای `set_page_status`, `mark_batch_queued`, `mark_batch_progress`, `mark_batch_failed`, `mark_batch_done`, `finalize_batch_statuses`, `get_failed_batch_paths`؛ اعمال دوبارهٔ بج‌ها بعد از هر بازسازی لیست؛ پاک‌کردن بج‌ها در `clear_state()` |
| `app/controllers/batch_settings.py` | **جدید** | `BatchSettingsSnapshot` (فریز تنظیمات یک اجرا)، `SettingsSnapshotProxy` (پاسخ‌دادن با مقادیر فریزشده و fallback به تنظیمات زنده)، `BatchSettingsOverride` (نصب/برداشتن snapshot) |
| `modules/utils/pipeline_config.py` | تغییر | `resolve_pipeline_settings(main_page)` به‌عنوان تنها نقطهٔ خواندن تنظیمات پایپ‌لاین |
| `pipeline/batch_processor.py`, `pipeline/inpainting.py`, `pipeline/block_detection.py`, `pipeline/translation_handler.py`, `pipeline/ocr_handler.py`, `pipeline/webtoon_batch/chunk.py`, `pipeline/webtoon_batch/render.py`, `modules/ocr/processor.py`, `modules/translation/processor.py` | تغییر | همهٔ `main_page.settings_page`ها با `resolve_pipeline_settings(...)` جایگزین شدند؛ دو مورد آخر پرامپت سفارشی سکشن ۱ را به `engine.initialize()` می‌رسانند |
| `app/controllers/projects.py` | تغییر | `_render_pages_to_directory()` (حلقهٔ رندر مشترک بین اکسپورت آرشیو و پوشه) و `export_pages_to_folder()` با دیالوگ اجباری انتخاب پوشه |
| `controller.py` | تغییر | `_resolve_page_paths`, `retry_batch_pages`, `export_selected_pages`, `load_image_folders`, `active_pipeline_settings`, `_release_batch_settings_override`؛ نصب/برداشتن override در `_run_batch_for_paths`، به‌روزرسانی بج‌ها در `update_progress`، و پایان‌دادن به وضعیت‌ها در `on_batch_process_finished` |
| `modules/utils/archives.py` | تغییر | `collect_images_in_folders()` — پیمایش بازگشتی پوشه‌ها با ترتیب طبیعی (page2 قبل از page10) و گروه‌مانده‌ی فصل‌ها |
| `app/ui/main_window/builders/nav.py` | تغییر | `folder_browser_button` (`MClickBrowserFolderToolButton`) + آیتم منوی «Image Folder» |
| `app/ui/dayu_widgets/browser.py` | تغییر | `MDragFileButton` حالا پوشهٔ drop‌شده را با `_expand_folder()` باز می‌کند (`set_dayu_accept_folders`) |
| `app/ui/main_window/builders/workspace.py` | تغییر | فعال‌کردن پذیرش پوشه روی ناحیهٔ drag&drop |

### ۲) کامیت‌ها روی `ai-upgrade` (قدیمی → جدید)

| کامیت | عنوان |
|---|---|
| `4514323` | Show per-page batch status in the page list |
| `3fb721f` | Export a selection of pages into a chosen folder |
| `5772fde` | Read pipeline settings through a single resolver |
| `40a6013` | Wire retry and folder export into the batch queue |
| `472b0b0` | Import a whole folder of pages |
| `b2a2976` | Clear per-page batch badges with the project |
| `10aba60` | Reuse the original batch settings for every retry |

### ۳) پاسخ چهار پرسش

**همزمانی.** صف از قبل پس‌زمینه‌ای است: `GenericWorker(QRunnable)` روی `QThreadPool` و کال‌بک‌ها به ترد GUI مارشال می‌شوند. `TaskRunnerController.run_threaded` یک صف **سریالی** است (هر لحظه یک پایپ‌لاین صفحه)، پس UI فریز نمی‌شود و می‌توان وسط صف صفحهٔ دیگری را باز و ویرایش کرد. تعارض state: خطای هر صفحه با `continue` رد می‌شود و صف نمی‌ایستد؛ و چون `run_threaded` سریالی است، اکسپورتی که وسط batch درخواست شود صف می‌شود نه اینکه با آن مسابقه بگذارد — این حالت با پیام «Export queued; it will start when the current batch finishes.» اعلام می‌شود.

**مقصد اکسپورت گروهی.** همیشه `QFileDialog.getExistingDirectory` باز می‌شود؛ هیچ‌گاه بی‌صدا از مسیر پیش‌فرض پروژه استفاده نمی‌شود.

**retry با تنظیمات اجرای اصلی.** `BatchSettingsSnapshot` این‌ها را فریز می‌کند: انتخاب ابزارها (translator/OCR/detector/inpainter)، `llm_settings` (شامل پرامپت سفارشی سکشن ۱)، `hd_strategy`، تنظیمات اکسپورت و رندر، و زبان مبدأ/مقصد هر صفحه. ویجت `settings_page` **جابه‌جا نمی‌شود** (یک QWidget واقعی است که پنجرهٔ اصلی در استک خود می‌گذارد و با `is` مقایسه می‌کند)؛ به‌جای آن پایپ‌لاین از `resolve_pipeline_settings()` می‌خواند که در طول retry به پروکسی اشاره می‌کند.

**تست دستی واقعی با ۳ صفحه.** با ۳ صفحهٔ تولیدشده انجام شد: صف‌شدن و پیشرفت و پایان وضعیت صفحات، باز کردن صفحهٔ وسط برای ویرایش و برگشت به گالری، ذخیره/بستن/بازکردن پروژه، و اکسپورت گروهی صفحات انتخابی به پوشهٔ دلخواه. یک نکتهٔ صریح: در این محیط کلید API و شبکه در دسترس نبود، پس **ترجمهٔ واقعی end-to-end اجرا نشد**؛ مسیر پایپ‌لاین با API وضعیت‌ها و snapshot تنظیمات تست شد، نه با فراخوانی واقعی مدل. اجرای گام‌های راهنمای زیر روی سیستم خودت با کلید فعال باقی می‌ماند.

### ۴) راهنمای تست دستی UI

1. اپ را اجرا کن: `python3 comic.py` (در این محیط `uv` نصب نیست).
2. از منوی ایمپورت گزینهٔ **Image Folder** را بزن و پوشه‌ای با ۳ صفحه بده — یا همان پوشه را روی ناحیهٔ drag&drop رها کن.
3. **Translate All** را بزن و در لیست صفحات بج‌های Queued / Processing (با نوار پیشرفت) / Done را ببین.
4. وسط اجرای صف روی صفحهٔ ۲ کلیک کن، متن یا باکس را دستی ویرایش کن و به گالری برگرد؛ صف باید بدون توقف ادامه دهد و پیشرفت صفحات دیگر از دست نرود.
5. اگر صفحه‌ای Failed شد: راست‌کلیک روی همان ردیف → **Retry this page**. (این آیتم فقط وقتی ظاهر می‌شود که ردیف انتخابی Failed باشد.)
6. دو صفحه را انتخاب کن → راست‌کلیک → **Export Selected...** → یک پوشهٔ دلخواه بده؛ باید دقیقاً همان صفحات نوشته شوند.
7. پروژه را ذخیره کن، اپ را ببند و باز کن؛ صفحات و زبان مبدأ/مقصد هر صفحه باید برگردند.

### ۵) تست‌های خودکار (هدلس)

دو اسکریپت بررسی در `/tmp` (کامیت نشده‌اند، چون تست موقتی توسعه‌اند و پروژه سوئیت pytest ندارد):

- `/tmp/section2_check.py` — ۴۹ بررسی: ایمپورت، بج‌های وضعیت، ویرایش دستی صفحهٔ وسط، فریز تنظیمات و بازگردانی‌شان، اکسپورت گروهی، همزمانی، و پایداری state بعد از restart. **۴۹/۴۹ پاس.**
- `/tmp/folder_import_check.py` — ۱۴ بررسی: پیمایش پوشه، ترتیب طبیعی، رد شدن فایل غیرتصویری، منوی ایمپورت، و باز شدن پوشهٔ drop‌شده. **۱۴/۱۴ پاس.**
- اجرای اپ به‌صورت offscreen برای ۶۰ ثانیه بدون کرش.

هر دو اسکریپت با `XDG_CONFIG_HOME` موقت اجرا می‌شوند تا QSettings واقعی کاربر نه خوانده و نه آلوده شود.

### ۶) انحرافات و محدودیت‌ها

- **کلید API و وضعیت GPU عمداً فریز نمی‌شوند.** اگر کاربر کلید منقضی را عوض کرده باشد باید کلید جدید استفاده شود، و سخت‌افزار هم ممکن است بین اجرا و retry تغییر کرده باشد.
- **snapshot در حافظه است، نه در فایل پروژه.** بعد از بستن و باز کردن اپ، retry با تنظیمات فعلی اجرا می‌شود و هشدار صریح «The original batch settings are no longer available…» نشان داده می‌شود. پایدارسازی‌اش پیشنهاد شمارهٔ ۳ بخش ۳ است.
- **حالت اکانت میزبان:** همان محدودیت سکشن ۱ (بدون فیلد system instructions در بک‌اند) پابرجاست؛ بقیهٔ قابلیت‌های بخش ۲ در هر دو حالت میزبان و کلید مستقیم کار می‌کنند.
- **صف سریالی است، موازی نیست.** این معماری موجود پروژه است و تغییرش نداده‌ام (موازی‌سازی هم ریسک rate-limit و هم ریسک تعارض state دارد). نتیجهٔ عملی: اکسپورت درخواستی وسط batch بعد از پایان صف اجرا می‌شود، که با پیام به کاربر اطلاع داده می‌شود.
- **بازسازی جزئی کد:** شرط نمایش «Retry this page» به متد `_selection_has_failed_page()` منتقل شد تا قابل تست باشد؛ رفتار منو تغییر نکرده.
- **بدون کلید API در این محیط:** هیچ فراخوانی واقعی مدل ترجمه/OCR ابری اجرا نشد. اکسپورت، رندر، ایمپورت، وضعیت‌ها و فریز تنظیمات کامل تست شدند؛ صحت خروجی ترجمه باید روی سیستم خودت با کلید فعال تأیید شود.

---

## بخش ۳ — پیشنهادهای خودکارسازی (منتظر تأیید)

هنوز هیچ کدی برای این بخش نوشته نشده. لطفاً شماره‌های مورد تأیید را اعلام کن.

| # | پیشنهاد | چه چیزی حل می‌کند | کار / ریسک |
|---|---|---|---|
| ۱ | تشخیص خودکار زبان مبدأ برای هر صفحه، وقتی زبان روی `Auto` است (بعد از OCR از متن تشخیص داده و در `image_states` ذخیره شود) | مجموعه‌های چندزبانه بدون تنظیم دستی هر صفحه | کم / کم — روی متن موجود OCR، به‌صورت opt-in |
| ۲ | واژه‌نامهٔ پروژه: جدول «اصطلاح → ترجمه» در `.ctpr` که به‌شکل extra-context به LLM تزریق می‌شود (پرامپت پایه دست‌نخورده) | یکدست ماندن نام شخصیت‌ها و اصطلاحات در کل جلد | متوسط / کم — باید بررسی شود مسیر میزبان هم `extra_context` را می‌فرستد؛ اگر نه، محدودیت در UI اعلام می‌شود |
| ۳ | ادامهٔ خودکار صف بعد از restart: ذخیرهٔ وضعیت صف + snapshot تنظیمات در فایل پروژه و پیشنهاد «Resume batch» در بازگشایی | کرش یا قطع برق وسط یک جلد بزرگ؛ و رفع محدودیت retry بعد از restart | متوسط / متوسط — schema پروژه با حفظ backward compatibility تغییر می‌کند |
| ۴ | retry و rate-limit هوشمند: backoff نمایی + jitter، احترام به `Retry-After` و کد ۴۲۹، سقف تلاش قابل تنظیم برای هر provider | شکست‌های گذرای شبکه و محدودیت نرخ که الان صفحه را Failed می‌کنند | متوسط / کم |
| ۵ | پروفایل‌های تنظیمات: پروفایل نام‌دار از کل ست (مدل، OCR، inpainter، زبان‌ها، رندر) با سوییچ سریع — از همان کد snapshot بخش ۲ استفاده می‌کند | جابه‌جایی بین «مانگا ژاپنی» و «وبتون کره‌ای» بدون تنظیم دوباره | متوسط / کم |
| ۶ | رد کردن صفحات تمام‌شده در اجرای گروهی: گزینهٔ «فقط صفحات ناتمام» در Translate All | ادامهٔ جلد نصف‌کاره بدون هزینهٔ دوبارهٔ API | کم / کم |
| ۷ | اکسپورت خودکار در پایان صف به پوشه/فرمت پیش‌تعیین‌شده (اختیاری) | حذف یک مرحلهٔ دستی در ورک‌فلوی تکراری | کم / کم |

---

## بخش ۴ — رجیستری مدل‌ها (شروع نشده)

طرح مورد توافق، برای اجرا بعد از بخش ۳:

- رجیستری قابل ویرایش مدل‌ها به‌صورت JSON در پوشهٔ کاربر (`get_user_data_dir()`) به‌جای `MODEL_MAP` هارد‌کد، با مقادیر فعلی به‌عنوان پیش‌فرض.
- UI مدیریت مدل: dropdown provider (OpenAI / Anthropic / Gemini / DeepSeek / Custom-compatible) و افزودن، ویرایش، حذف و تعیین پیش‌فرض.
- «Fetch Models from API» برای هر provider با پیام خطای روشن و امکان وارد کردن دستی model-id در صورت شکست.
- همگام‌سازی خودکار با `supported_translators`، `value_mappings`، `TranslationFactory._get_engine_class` و مصرف‌کننده‌های OCR.
- اعتبارسنجی کلید API با یک درخواست تست سبک.
- هر محدودیت مربوط به `UserTranslator` باید در UI و در همین گزارش صریح گفته شود، نه بی‌صدا نادیده گرفته شود.

---

## کارهای باقی‌مانده و تصمیم‌های لازم

1. **تصمیم کاربر:** انتخاب شماره‌های تأییدشده از جدول بخش ۳ (بدون آن، کدنویسی بخش ۳ شروع نمی‌شود).
2. **تصمیم کاربر:** آیا snapshot تنظیمات باید در فایل پروژه پایدار شود (پیشنهاد ۳)؟ این تنها راه رفع محدودیت retry بعد از restart است.
3. **باقی‌مانده:** بخش ۴ کامل.
4. **نکتهٔ محیط:** پروژه سوئیت pytest ندارد؛ اگر بخواهی، اسکریپت‌های بررسی `/tmp` را می‌توان به یک پوشهٔ `tests/` واقعی منتقل و به pytest تبدیل کرد.
