# گزارش ارتقای comic-translate (شاخهٔ `ai-upgrade`)

آخرین به‌روزرسانی: ۱۱ اوت ۲۰۲۶ — وضعیت: بخش‌های ۱، ۲، ۳ و ۴ **تمام**؛ گزارش نهایی همین فایل است.

این فایل زندهٔ گزارش است و در پایان هر بخش تکمیل می‌شود.

## فهرست

- [بخش ۱ — پرامپت سیستمی سفارشی](#بخش-۱--پرامپت-سیستمی-سفارشی)
- [بخش ۲ — ورک‌فلوی batch چند تصویری](#بخش-۲--ورکفلوی-batch-چند-تصویری)
- [بخش ۳ — پیشنهادهای خودکارسازی](#بخش-۳--پیشنهادهای-خودکارسازی)
- [بخش ۴ — رجیستری مدل‌ها](#بخش-۴--رجیستری-مدلها)
- [گزارش نهایی تلفیقی (بخش‌های ۳ و ۴)](#گزارش-نهایی-تلفیقی-بخشهای-۳-و-۴)

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

## بخش ۳ — پیشنهادهای خودکارسازی

مطابق تأیید شما، از جدول ۷ پیشنهاد، شماره‌های **۱، ۲، ۳، ۴ و ۶** پیاده شد؛ پیشنهادهای **۵ (پروفایل‌های تنظیمات)** و **۷ (اکسپورت خودکار)** رد شدند. جزئیات هر بند در «گزارش نهایی تلفیقی» پایین است.

| # | پیشنهاد | وضعیت |
|---|---|---|
| ۱ | تشخیص خودکار زبان مبدأ هر صفحه (opt-in) | ✅ پیاده‌شده — کامیت `35f7e8d` |
| ۲ | واژه‌نامهٔ پروژه («اصطلاح → ترجمه» در `.ctpr`) | ✅ پیاده‌شده — کامیت‌های `e89afa5`، `7c78e6e` |
| ۳ | ادامهٔ خودکار صف بعد از restart (صف + snapshot در فایل پروژه) | ✅ پیاده‌شده — کامیت `00cf4f6` |
| ۴ | retry و rate-limit هوشمند (backoff نمایی + احترام به `Retry-After`) | ✅ پیاده‌شده — کامیت `77f35d4` |
| ۵ | پروفایل‌های تنظیمات | ❌ رد شد (طبق تأیید شما) |
| ۶ | رد کردن صفحات تمام‌شده در اجرای گروهی | ✅ پیاده‌شده — کامیت `97d84d7` |
| ۷ | اکسپورت خودکار در پایان صف | ❌ رد شد (طبق تأیید شما) |

---

## بخش ۴ — رجیستری مدل‌ها

مطابق طرح توافق‌شده و کامل پیاده شد — جزئیات در «گزارش نهایی تلفیقی» پایین:

- رجیستری قابل ویرایش JSON در `<user data dir>/models/models.json` به‌جای `MODEL_MAP` هارد‌کد، با مقادیر فعلی به‌عنوان پیش‌فرض همیشه‌برگشتنی.
- UI مدیریت در تب Tools با دو جدول (LLM / OCR)، افزودن/حذف/بازگردانی، «Fetch Models from API» و «Test Key».
- اعتبارسنجی کلید با درخواست سبک لیست مدل (بدون ترجمه و بدون هزینه).
- همگام‌سازی با `supported_translators`، `value_mappings`، `TranslationFactory._get_engine_class`، `OCRFactory` و مصرف‌کننده‌های OCR.
- محدودیت حالت اکانت میزبان (`UserTranslator`) در UI دیالوگ و همین گزارش صریح اعلام شده.

---

## گزارش نهایی تلفیقی (بخش‌های ۳ و ۴)

### ۱) فایل‌های تغییر‌یافته/اضافه‌شده (بخش‌های ۳ و ۴)

**بخش ۳ — بند ۱ (تشخیص خودکار زبان مبدأ هر صفحه)** — کامیت `35f7e8d`

| فایل | کار |
|---|---|
| `modules/utils/language_utils.py` | تابع تشخیص اسکریپت از متن OCR (لاتین/سیریلیک/کانجی/هانگول/چینی) |
| `pipeline/translation_handler.py` | نوشتن زبان تشخیص‌داده‌شده به `image_states` هر صفحه هنگام اجرای batch |
| `app/ui/settings/tools_page.py` | چک‌باکس opt-in «Detect the source language of each page» (پیش‌فرض خاموش) |
| `app/ui/settings/settings_page.py` | ذخیره/بازخوانی چک‌باکس در QSettings با پیش‌فرض False |
| `controller.py` | سیگنال `page_language_detected` و نوشتن زبان تشخیص‌داده‌شده روی صفحهٔ جاری |

**بخش ۳ — بند ۲ (واژه‌نامهٔ پروژه)** — کامیت‌های `e89afa5`، `7c78e6e`

| فایل | کار |
|---|---|
| `app/controllers/glossary.py` | **جدید** — `GlossaryStore` (ذخیره در blob پروژه)، `format_glossary_for_prompt`، `merge_extra_context` |
| `app/ui/glossary_dialog.py` | **جدید** — دیالوگ جدول «اصطلاح → ترجمه» با افزودن/حذف/بارگذاری/ذخیره/پاک‌کردن |
| `modules/utils/pipeline_config.py` | `resolve_extra_context()` — ادغام واژه‌نامه در extra-context همهٔ مسیرهای ترجمه |
| `app/projects/project_state_v2.py` | سریال/دسریال‌کردن واژه‌نامه در فایل `.ctpr` (کلید غایب = واژه‌نامه خالی، backward compatible) |
| `app/ui/main_window/window.py` / `controller.py` | اکشن منوی «Project Glossary» و باز کردن دیالوگ |
| `app/ui/glossary_dialog.py` | اصلاح ایمپورت نسبی خراب (`..dayu_widgets` → `.dayu_widgets`) که با بازکردن دیالوگ کرش می‌کرد |

**بخش ۳ — بند ۳ (ادامهٔ صف بعد از restart)** — کامیت `00cf4f6`

| فایل | کار |
|---|---|
| `app/controllers/batch_settings.py` | `BatchSettingsSnapshot.to_dict()/from_dict()` (فیلد `render_settings` عمداً حذف)؛ `note_language_detected()` که snapshot را هم به‌روز می‌کند |
| `app/controllers/image.py` | `get_batch_queue_state()` (فقط QUEUED/PROCESSING/FAILED)، `restore_batch_queue_state()`، `clear_batch_queue_state()`، `is_page_finished()` |
| `app/projects/project_state_v2.py` | `_serialize_batch_queue()`/`_restore_batch_queue()` با remap مسیرها از `original_to_temp`؛ کلید `batch_queue` در manifest |
| `app/controllers/projects.py` | `_prompt_resume_saved_batch()` بعد از بازکردن پروژه |
| `controller.py` | `resume_saved_batch()` — بازگرداندن صف و snapshot به `_run_batch_for_paths(..., reuse_last_settings=True)`؛ پاک‌کردن صف در پایان هر batch |

**بخش ۳ — بند ۴ (retry هوشمند)** — کامیت‌های `77f35d4`، `915a540`

| فایل | کار |
|---|---|
| `modules/utils/retry.py` | **جدید** — `with_retry()`، `status_code_of()`، `retry_after_of()`، `backoff_delay()` (نمایی + full jitter)، `is_retryable()`، `read_retry_settings()`؛ هرگز `InsufficientCreditsException`/`ContentFlaggedException` را retry نمی‌کند |
| `modules/translation/llm/base.py` | پوشاندن `_perform_translation` با `with_retry` (همهٔ انجین‌های LLM از اینجا سود می‌برند) |
| `modules/translation/user.py` | پوشاندن POST وب‌API با `with_retry`؛ استخراج `_map_response_errors()` |
| `modules/translation/microsoft.py`, `yandex.py`, `deepl.py` | پوشاندن درخواست‌هایشان با `with_retry` |
| `modules/translation/llm/gpt.py`, `claude.py`, `gemini.py` | پوشاندن درخواست‌ها + استخراج `_post_*` |
| `app/ui/settings/llms_page.py` | بخش «Retry on Temporary Errors»: چک‌باکس + ۳ اسپین (max attempts / base delay / max delay) |
| `app/ui/settings/settings_ui.py`, `settings_page.py` | پروکسی ویجت‌ها و ذخیره/بازخوانی به‌صورت JSON بلاب `llm/retry_settings` |
| `app/ui/list_view_image_loader.py` | خاموش‌کردن قطعی ترد بارگذاری تصاویر (پیش‌تر با `quit()` مسابقه داشت) |

**بخش ۳ — بند ۶ (رد کردن صفحات تمام‌شده)** — کامیت `97d84d7`

| فایل | کار |
|---|---|
| `app/ui/main_window/builders/workspace.py` | چک‌باکس «Skip translated pages» کنار دکمهٔ Translate All (پیش‌فرض خاموش) |
| `controller.py` | فیلترکردن صفحات `is_page_finished` در `start_batch_process` وقتی چک‌باکس روشن است + پیام اطلاع‌رسانی |
| `app/controllers/projects.py` | ذخیره/بازخوانی چک‌باکس در `main_page/skip_finished_pages` (پیش‌فرض False) |

**بخش ۴ (رجیستری مدل‌ها)** — کامیت‌های `1d792f6`، `ec393a3`

| فایل | کار |
|---|---|
| `modules/utils/model_registry.py` | **جدید** — بارگذاری/ذخیره/نقص‌امن رجیستری؛ پیش‌فرض‌های درون‌کد همیشه‌برگشتنی؛ فایل فقط با ویرایش کاربر ساخته می‌شود |
| `modules/utils/translator_utils.py` | `MODEL_MAP` → پروکسی زندهٔ `_live_model_map()` (قرارداد ایمپورت مصرف‌کننده‌ها دست‌نخورده) |
| `modules/translation/llm/{gpt,claude,gemini,deepseek}.py` | نقشهٔ مدل از رجیستری خوانده می‌شود (کش ماژولی lazy) |
| `modules/ocr/{gpt_ocr,gemini_ocr}.py` | نقشهٔ OCR از رجیستری خوانده می‌شود |
| `modules/translation/factory.py` | انتخاب انجین با substring شناسه — نام‌های رجیسترشدهٔ جدید با همان شناسه به انجین درست می‌رسند |
| `modules/ocr/factory.py` | مسیریابی OCR رجیسترشده حاوی «gpt»/«gemini» به انجین LLM-OCR متناظر |
| `app/controllers/model_registry_ctrl.py` | **جدید** — `test_api_key()` و `fetch_models()` (درخواست‌های سبک لیست مدل) + `friendly_llm_key()` و چرخهٔ دیالوگ |
| `app/ui/model_registry_dialog.py` | **جدید** — دیالوگ دو تب (LLM/OCR) با جدول قابل ویرایش، Fetch/Test، Restore Defaults |
| `app/ui/settings/tools_page.py` | دکمهٔ «Model Registry...» |
| `app/ui/settings/settings_ui.py` | پروکسی دکمه + `refresh_registry_combos()` برای ظاهرشدن فوری مدل‌های جدید در کامبوها |
| `app/ui/settings/settings_page.py` | فراخوانی `refresh_registry_combos()` در آغاز `load_settings()` تا مدل رجیسترشده بعد از restart از بین نرود |
| `controller.py` | `ModelRegistryController` + اتصال دکمه |

### ۲) کامیت‌های جدید روی `ai-upgrade` (قدیمی → جدید)

| کامیت | عنوان |
|---|---|
| `35f7e8d` | Detect the source language of each page during a batch run |
| `e89afa5` | Inject a project glossary into the translation context |
| `00cf4f6` | Resume an unfinished batch from a saved project's settings |
| `77f35d4` | Retry transient translation failures with exponential backoff |
| `7c78e6e` | Fix relative imports in the glossary dialog |
| `915a540` | Make the page-list image loader shutdown deterministic |
| `97d84d7` | Skip already-translated pages when re-running a batch |
| `1d792f6` | Add an editable model registry for LLM and OCR model IDs |
| `ec393a3` | Add a model registry editor with fetch-models and key validation |

### ۳) راهنمای تست دستی گام‌به‌گام

**بند ۳-۱ (تشخیص زبان صفحه):**
1. Settings → Tools → «Detect the source language of each page» را روشن کن (فقط وقتی زبان مبدأ `Auto` است کار می‌کند).
2. صفحه‌ای با متن ژاپنی/کره‌ای/روسی ایمپورت و Translate کن؛ زبان تشخیص‌داده‌شده باید در کامبوی زبان مبدأ همان صفحه بنشیند و برای صفحات بعدی حفظ شود.
3. چک‌باکس خاموش = رفتار قبلی (همه روی Auto می‌مانند).

**بند ۳-۲ (واژه‌نامهٔ پروژه):**
1. منوی «Project Glossary» را باز کن (در منوی اصلی پروژه).
2. چند اصطلاح مثل «Nen = Nen» و «HxH = Hunter x Hunter» اضافه کن؛ روی Add بزن.
3. پروژه را ذخیره، ببند و باز کن؛ واژه‌نامه باید برگردد.
4. یک صفحه را ترجمه کن؛ نام‌ها باید طبق واژه‌نامه پایدار بمانند (در extra-context هر درخواست تزریق می‌شود).

**بند ۳-۳ (ادامهٔ صف):**
1. یک پروژهٔ چندصفحه‌ای Translate All بزن و وسط صف اپ را ببند.
2. پروژه را دوباره باز کن؛ باید پیام «Resume» برای ادامهٔ صفحات ناتمام بیاید.
3. Resume بزن؛ فقط صفحات QUEUED/PROCESSING/FAILED دوباره اجرا می‌شوند، صفحات Done نه.
4. snapshot تنظیمات همان اجرای اول اعمال می‌شود (نه تنظیمات فعلی).

**بند ۳-۴ (retry هوشمند):**
1. Settings → LLMs → «Retry on Temporary Errors»؛ سه مقدار پیش‌فرض (۳ تلاش، تأخیر پایه ۲ ثانیه، سقف ۶۰ ثانیه) را ببین.
2. با کلید واقعی یک ترجمه را با اینترنت قطع/وصل کن؛ خطای گذرا باید با backoff تکرار شود نه اینکه فوراً Failed شود.
3. خطای ۴۰۱ (کلید نادرست) و «Insufficient credits» هرگز retry نمی‌شوند — فوراً خطا می‌دهند.

**بند ۳-۶ (رد کردن صفحات تمام‌شده):**
1. یک جلد را نصفه ترجمه کن (چند صفحه Done شوند).
2. چک‌باکس «Skip translated pages» را کنار Translate All روشن کن و Translate All بزن؛ فقط صفحات ناتمام اجرا شوند و پیام «N page(s) already have a finished translation» بیاید.
3. چک‌باکس خاموش = کل پروژه دوباره اجرا می‌شود (رفتار قبلی).
4. وضعیت چک‌باکس بعد از restart حفظ می‌شود.

**بخش ۴ (رجیستری مدل‌ها):**
1. Settings → Tools → «Model Registry...»؛ دو تب Translator (LLM) و OCR با سطرهای پیش‌فرض ببین.
2. مقدار API model ID یک سطر را عوض کن و Save بزن؛ در Translator/OCR dropdown همان لحظه سطرها به‌روز می‌شوند. (اعمال در انجین‌ها بعد از restart — در دیالوگ هم گفته شده.)
3. «Add Row» → نام دلخواه مثل `Claude-5-Opus` + شناسهٔ API → Save؛ در dropdown مترجم ظاهر می‌شود و با substring «Claude» به انجین درست می‌رود.
4. «Test Key»: provider را OpenAI-compatible بگذار و کلید را بده — یک درخواست `/models` سبک (بدون ترجمه و بدون هزینه) می‌زند؛ ۴۰۱/۴۰۳/زمان‌دار را با پیام روشن می‌گوید.
5. «Fetch Models»: لیست مدل‌های provider را می‌گیرد و مدل‌های تازه را به جدول اضافه می‌کند (با نام دوستانهٔ `GPT-…`/`Gemini-…`).
6. «Restore Defaults» هر سکشن را به پیش‌فرض برمی‌گرداند.
7. با اکانت ComicLabs وارد شو؛ در دیالوگ یادآوری می‌شود که در حالت میزبان رجیستری محلی اعمال نمی‌شود (سرور مدل را انتخاب می‌کند).

### ۳-الف) تست‌های خودکار (هدلس)

اسکریپت‌های بررسی موقت در `/tmp` (کامیت نشده‌اند، چون تست توسعه‌اند و پروژه سوئیت pytest ندارد — تبدیل به `tests/` در بخش ۵ پیشنهاد شده):

- `/tmp/section3_item6_check.py` — ۱۱ بررسی برای بند ۶ (پیش‌فرض چک‌باکس، فیلترکردن صفحات تمام‌شده، اجرا نرفتن وقتی همه تمام‌اند، پایداری تنظیم، پیش‌فرض سالم وقتی کلید غایب است). **۱۱/۱۱ پاس** (دو بار اجرا).
- `/tmp/section4_model_registry_check.py` — ۴۱ بررسی برای بخش ۴ (ماژول رجیستری و تحمل خرابی فایل، سیم‌کشی انجین‌ها، helpers شبکه با mock، دیالوگ و همگام‌سازی کامبوها، بازگردانی مدل رجیسترشده بعد از restart). **۴۱/۴۱ پاس**.
- همه با `XDG_CONFIG_HOME` موقت اجرا می‌شوند تا QSettings واقعی کاربر نه خوانده و نه آلوده شود؛ `UpdateChecker` برای آفلاین بودن patch شده.

### ۴) انحرافات و محدودیت‌ها (با توجیه فنی)

- **بندهای ۵ و ۷ بخش ۳ رد شدند** (پروفایل‌های تنظیمات و اکسپورت خودکار) — طبق تأیید صریح شما.
- **بازگشت به پیش‌فرض در رجیستری:** حذف یک کلید پیش‌فرض، آن را برمی‌گرداند (نه پاکش می‌کند) تا `value_mappings`/کامبوها هرگز به سطر مرده اشاره نکنند. پاک‌کردن واقعی فقط با «Restore Defaults» ممکن است که باز همان پیش‌فرض‌ها را می‌نشاند.
- **نام مدل ناشناخته در فکتوری:** اگر مدل رجیسترشده‌ای هیچ شناسهٔ انجین (GPT/Claude/Gemini/Deepseek/Custom) نداشته باشد، `TranslationFactory._get_engine_class` طبق رفتار قبلی به `GPTTranslation` می‌افتد. این رفتار قدیمی است و عمداً تغییر نکرده؛ `friendly_llm_key` در Fetch با پیشوند `GPT-` همین را تضمین می‌کند.
- **اعمال رجیستری بعد از restart:** انجین‌های LLM نقشه را در اولین استفاده به‌صورت ماژولی کش می‌کنند؛ ویرایش رجیستری در یک نشست فعال، انجین‌هایی که ساخته شده‌اند را تغییر نمی‌دهد (منطقی است: cache انجین در `TranslationFactory` هم وجود دارد). در UI دیالوگ نوشته شده: «Changes apply to the next translation run.»
- **حالت اکانت میزبان (`UserTranslator`) دست‌نخورده:** در حالت ورود، ترجمه و OCR روی سرور ComicLabs اجرا می‌شوند و رجیستری محلی اعمال نمی‌شود؛ دیالوگ رجیستری این را صریح نشان می‌دهد. `UserOCR.LLM_OCR_KEYS`/`FULL_PAGE_OCR_KEYS` همان دو کلید سخت‌کد قبلی هستند — مدل OCR رجیسترشدهٔ جدید در حالت میزبان به انجین محلی می‌رود (نه پروکسی)، چون سرور آن را نمی‌شناسد؛ این هم یک محدودیت صریح است، نه بی‌صدا.
- **Fetch/Test به اینترنت و کلید نیاز دارند:** در این محیط sandbox هیچ فراخوانی شبکه‌ای واقعی اجرا نشد؛ همهٔ مسیرها با mock تست شدند. «Test Key» فقط لیست مدل می‌گیرد (بدون ترجمه، بدون هزینه) — به همین دلیل سبک و امن است.
- **همچنان بدون کلید API در این محیط:** هیچ ترجمهٔ واقعی end-to-end اجرا نشد (همان محدودیت بخش‌های ۱ و ۲). صحت خروجی ترجمه و رفتار retry با سرویس واقعی باید روی سیستم خودت با کلید فعال تأیید شود.
- **Exit code فرایند تست‌ها:** یک abort نادر (~۱ در ۵ اجرا، `QThread: Destroyed while thread is still running`) هنگام خروج مترجم بعد از پایان تست‌ها دیده می‌شود؛ همهٔ ۴۹+ بررسی‌ها پیش از آن پاس شده‌اند. ردیابی نشان داد همهٔ تردهای loader پیش از خروج تمیز می‌ایستند و این abort مربوط به GC یک QThread در زمان خاموش‌شدن interpreter است — پیش از بخش ۴ هم وجود داشت و خارج از محدودهٔ این کار است.
- **تنظیمات retry در snapshot فریز نمی‌شود:** `BatchSettingsSnapshot` پروکسیِ `get_retry_settings` را به تنظیمات زنده واگذار می‌کند، پس کاربر می‌تواند وسط صف سقف تلاش را پایین بیاورد؛ تصمیم کوچکی که عمداً گرفته شد.
- **اسکریپت‌های تست در `/tmp` کامیت نشده‌اند:** پروژه سوئیت pytest ندارد؛ این‌ها ابزار بررسی موقت‌اند. اگر بخواهی به پوشهٔ `tests/` واقعی منتقل و به pytest تبدیل می‌شوند.

### ۵) کارهای باقی‌مانده / نیازمند تصمیم شما

- **تنها مورد واقعاً مانده:** اجرای **تست دستی end-to-end با کلید API فعال روی سیستم خودت** (ترجمهٔ واقعی، retry واقعی، fetch مدل واقعی). هیچ کدام از این‌ها در محیط بدون اینترنت قابل اجرا نبود؛ راهنمای گام‌به‌گام در بخش ۳ همین گزارش.
- پیشنهاد اختیاری: تبدیل اسکریپت‌های بررسی `/tmp` به یک سوئیت pytest واقعی در `tests/` (اگر بخواهی انجام می‌دهم).
- یادآوری صریح: کلیدهای API فقط در حالت «Save Keys» ذخیره می‌شوند (همان رفتار قبلی credentials_page)؛ هیچ‌کجا مقدار کلید در لاگ یا گزارش نمی‌آید و «Test Key» هم کلید را به‌صورت password-field می‌گیرد و فقط با درخواست لیست مدل بررسی‌اش می‌کند.
