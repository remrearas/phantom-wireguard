<!--
Phantom-WG
Copyright (C) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Phantom-WG Retro

[![Release Workflow](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/release-workflow.yml/badge.svg?branch=retro)](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/release-workflow.yml)

> [🇬🇧 English](README.md) | [🇹🇷 Türkçe](README_TR.md) | 🇸🇦 **العربية**

```bash
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
```

**خادمك. شبكتك. خصوصيتك.**

Phantom-WG هي أداة معيارية لإعداد وإدارة بنية WireGuard VPN التحتية
على خادمك الخاص. إلى جانب إدارة VPN الأساسية، توفر اتصالات مقاومة للرقابة،
تشفيرًا متعدد الطبقات، وسيناريوهات خصوصية متقدمة.

🌎 **https://retro.phantom.tc**

📰 **https://retro-docs.phantom.tc**

---

## البداية السريعة

### المتطلبات

**الخادم:**
- خادم متصل بالإنترنت بعنوان IPv4 عام (مطلوب) ونظام تشغيل مدعوم. عنوان IPv6 اختياري ومدعوم للاتصال ثنائي المكدس (dual-stack)
- صلاحيات Root

**نظام التشغيل:**
- Debian 12, 13
- Ubuntu 22.04, 24.04

> **استهلاك الموارد:** يعمل WireGuard كوحدة نواة (kernel module)، ويستهلك حدًا أدنى من موارد النظام.
> لمعلومات تفصيلية عن الأداء، راجع [WireGuard Performance](https://www.wireguard.com/performance/).

> **تبحث عن مزوّد؟** إذا لم تتمكّن من اختيار مزوّد الاستضافة، جرّب [Spin & Deploy](https://retro.phantom.tc/wheel/) — اختر عشوائيًا من مزوّدي VPS الموجّهين للخصوصية والداعمين للعملات الرقمية!

### التثبيت

```bash
curl -sSL https://install.phantom.tc | bash
```

![Installation](assets/recordings/installation-dark.gif#gh-dark-mode-only)
![Installation](assets/recordings/installation-light.gif#gh-light-mode-only)

> 📺 للاطلاع على شروحات الفيديو لجميع الميزات، راجع https://retro-docs.phantom.tc/feature-showcase/modules/core/add-client/.

> خدمة `install.phantom.tc` هي Cloudflare Worker تتم صيانتها بالكامل من مستودع GitHub هذا ويتم نشرها عبر GitHub Actions. لا تقوم بأي جمع بيانات أو قياس عن بُعد أو تسجيل. للتفاصيل، راجع [Privacy Notice](tools/phantom-install/PRIVACY.md).

### ما بعد التثبيت

عند اكتمال التثبيت بنجاح، سيظهر الخرج التالي:

```
========================================
   PHANTOM-WG INSTALLED!
========================================

Commands:
  phantom-wg - Interactive UI
  phantom-api       - API access

Quick Start:
  1. Run: phantom-wg
  2. Select 'Core Management'
  3. Add your first client

API Example:
  phantom-api core list_clients
```

---

## سيناريوهات الاستخدام

### Core - الإدارة المركزية

إدارة العملاء، توليد المفاتيح التشفيرية، تخصيص عناوين IP تلقائيًا، والتحكم
بالخدمات من واجهة مركزية واحدة.

![Core Flow](documentation/docs/assets/static/images/index/flow-diagrams/connection-flow-core.svg)

**الميزات الرئيسية:**
- إضافة/إزالة العملاء ومشاركة الإعدادات عبر رمز QR
- حالة الخادم وإحصاءات الاتصال
- إدارة جدار الحماية (Firewall)
- تغيير الشبكة الفرعية (Subnet) وإعادة تعيين عناوين IP

> **الاستخدام التفصيلي:** [Feature Showcase - Core Module](https://retro-docs.phantom.tc/feature-showcase/modules/core/add-client/)

---

### Multihop - طبقة VPN المزدوجة

وجّه حركة مرورك عبر خوادم WireGuard خارجية. أنشئ طبقة تشفير مزدوجة
باستخدام خوادمك الخاصة أو مزودي VPN التجاريين.

![Multihop Flow](documentation/docs/assets/static/images/index/flow-diagrams/connection-flow-multihop.svg)

**الميزات الرئيسية:**
- استيراد أي ملف إعدادات WireGuard
- قواعد توجيه تلقائية وإعداد NAT
- مراقبة الاتصال وإعادة الاتصال التلقائي
- اختبارات اتصال VPN

---

### Ghost - وضع التخفي

يُموَّه اتصال WireGuard الخاص بك ليبدو كحركة مرور HTTPS عادية. تجاوز أنظمة
الفحص العميق للحزم (DPI) وحجب جدران الحماية للحصول على اتصال مقاوم للرقابة.

![Ghost Flow](documentation/docs/assets/static/images/index/flow-diagrams/connection-flow-ghost.svg)

**الميزات الرئيسية:**
- نفق عبر WebSocket (عبر wstunnel)
- شهادات SSL تلقائية من Let's Encrypt
- تصدير إعدادات العميل عبر `phantom-casper`

---

### MultiGhost - أقصى درجات الخصوصية

ادمج وحدتي Ghost و Multihop للحصول على أعلى مستوى من الخصوصية ومقاومة
الرقابة. يُموَّه اتصالك كحركة HTTPS ويُوجَّه عبر طبقة VPN مزدوجة.

![MultiGhost Flow](documentation/docs/assets/static/images/index/flow-diagrams/connection-flow-multighost.svg)

**التفعيل:**
```bash
# 1. Ghost Mode تفعيل
phantom-api ghost enable domain="cdn.example.com"

# 2. VPN استيراد شبكة خارجية
phantom-api multihop import_vpn_config config_path="/path/to/vpn.conf"

# 3. Multihop تفعيل
phantom-api multihop enable_multihop exit_name="vpn-exit"
```

---

## طرق الوصول

| الطريقة                  | الأمر                           | الوصف                                |
|--------------------------|---------------------------------|--------------------------------------|
| **CLI التفاعلي**         | `phantom-wg`                    | واجهة مستخدم غنية قائمة على TUI      |
| **API**                  | `phantom-api <module> <action>` | وصول برمجي، خرج بصيغة JSON           |
| **Ghost Export**         | `phantom-casper <client>`       | إعدادات عميل Ghost Mode              |
| **Ghost Export for iOS** | `phantom-casper-ios <client>`   | إعدادات Ghost Mode بصيغة JSON لـ iOS |

---

## الوثائق

| الوثيقة                                                | الوصف                          |
|--------------------------------------------------------|--------------------------------|
| [API Documentation](https://retro-docs.phantom.tc/api) | مرجع تفصيلي لجميع إجراءات API  |
| [Module Architecture](phantom/modules/README.md)       | البنية التقنية ونماذج البيانات |

---

## إشعار العلامة التجارية

هذا المشروع هو تطبيق مستقل لإدارة VPN يستخدم بروتوكول [WireGuard](https://www.wireguard.com/).
لا توجد أي علاقة أو ارتباط أو تفويض أو مصادقة أو اتصال رسمي بأي شكل من الأشكال مع
Jason A. Donenfeld أو ZX2C4 أو Edge Security.

WireGuard® هي علامة تجارية مسجلة لـ Jason A. Donenfeld.

---

## الترخيص

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>

هذا البرنامج مرخص بموجب رخصة AGPL-3.0. للتفاصيل، راجع ملف [LICENSE](LICENSE).

لتراخيص الأطراف الثالثة، راجع [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES).

---

## 🎖️ شكر وتقدير

لم يكن هذا المشروع ممكنًا بدون المشاريع مفتوحة المصدر التالية:

- **[WireGuard](https://www.wireguard.com/)**
- **[wstunnel](https://github.com/erebe/wstunnel)**
- **[Let's Encrypt](https://letsencrypt.org/)**
- **[Rich](https://github.com/Textualize/rich)**
- **[TinyDB](https://github.com/msiemens/tinydb)**
- **[qrcode](https://github.com/lincolnloop/python-qrcode)**

---

## الدعم

Phantom-WG مشروع مفتوح المصدر. إذا كنت ترغب في دعم المشروع:

**Monero (XMR):**
```
84KzoZga5r7avaAqrWD4JhXaM6t69v3qe2gyCGNNxAaaJgFizt1NzAQXtYoBk1xJPXEHNi6GKV1SeDZWUX7rxzaAQeYyZwQ
```

**Bitcoin (BTC):**
```
bc1qnjjrsfdatnc2qtjpkzwpgxpmnj3v4tdduykz57
```

---

<!--suppress HtmlDeprecatedAttribute -->

<div align="center">

![Phantom Logo](documentation/docs/assets/static/images/phantom-horizontal-master-midnight-phantom.svg#gh-light-mode-only)
![Phantom Logo](documentation/docs/assets/static/images/phantom-horizontal-master-stellar-silver.svg#gh-dark-mode-only)

</div>