import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const content = {
  "title": "توصيل من وإلى مطار هيثرو في لندن | ACT",
  "description": "احجز مسبقاً سيارة خاصة من وإلى مطار هيثرو مع ACT. خيارات تناسب العائلات ورحلات العمل، مع توضيح السعر قبل تأكيد الحجز وتحديد عدد الركاب والأمتعة.",
  "badge": "توصيل مطار هيثرو",
  "heading": "خدمة التوصيل من وإلى مطار هيثرو في لندن",
  "intro": "ابدأ رحلتك أو اختتمها براحة مع Airport & City Transfer. احجز مسبقاً سيارة خاصة بين مطار هيثرو ووجهتك في لندن، واختر الفئة المناسبة لعدد الركاب والأمتعة، مع الاطلاع على السعر قبل تأكيد الحجز.",
  "benefits": [
    "متابعة موعد الرحلة عند تزويدنا ببياناتها",
    "توضيح السعر قبل تأكيد الحجز",
    "سائقون محترفون",
    "خيارات سيارات لرحلات العمل والعائلات",
    "إمكانية طلب خدمة الاستقبال والترحيب بحسب التوفر",
    "حجز مسبق عبر الإنترنت"
  ],
  "vehicles": [
    "سيارة خاصة قياسية",
    "سيارة تنفيذية لرحلات العمل",
    "سيارة فاخرة",
    "سيارة تتسع حتى 7 ركاب، بحسب الأمتعة والفئة المتاحة",
    "فان فاخر"
  ],
  "vehicleNote": "اختر السيارة وفق عدد الركاب وحجم الأمتعة. تظهر الخيارات المتاحة لرحلتك أثناء الحجز.",
  "routes": [
    "من هيثرو إلى وسط لندن",
    "من هيثرو إلى كناري وارف",
    "من هيثرو إلى مايفير",
    "من هيثرو إلى فنادق لندن",
    "من هيثرو إلى مطار غاتويك",
    "من هيثرو إلى مناطق الأعمال في لندن"
  ],
  "paragraphs": [
    "توفّر Airport & City Transfer خدمة نقل خاصة بالحجز المسبق للمسافرين من وإلى مطار هيثرو. سواء كانت زيارتك للعمل أو لقضاء إجازة عائلية أو للإقامة في أحد فنادق لندن، يمكنك ترتيب رحلة تناسب موعد سفرك ووجهتك.",
    "أدخل موقع الانطلاق والوجهة والتاريخ والوقت، ثم حدّد عدد الركاب والأمتعة للاطلاع على الخيارات المناسبة. وإذا كانت رحلتك مرتبطة برحلة جوية، فأضف بياناتها لتسهيل تنسيق الاستقبال أو الوصول إلى المطار.",
    "نحرص على وضوح تفاصيل الرحلة والسعر قبل تأكيد الحجز. راجع تفاصيل السيارة وأي خدمات إضافية تختارها، وتواصل معنا إذا احتجت إلى مساعدة في ترتيب رحلتك."
  ],
  "faqs": [
    {
      "q": "هل توفّرون الاستقبال من مطار هيثرو والتوصيل إليه؟",
      "a": "نعم، يمكنك حجز سيارة خاصة مسبقاً من مطار هيثرو إلى وجهتك في لندن أو من لندن إلى المطار. حدّد الاتجاه الصحيح وموقع الانطلاق والوجهة عند الحجز."
    },
    {
      "q": "ماذا يحدث إذا تغيّر موعد وصول رحلتي الجوية؟",
      "a": "عند تزويدنا ببيانات الرحلة، نتابع موعدها للمساعدة في تنسيق الاستقبال. تواصل معنا إذا تغيّر رقم الرحلة أو كانت لديك مستجدات تؤثر في ترتيب رحلتك."
    },
    {
      "q": "هل يمكن حجز سيارة عائلية أو سيارة تتسع لسبعة ركاب؟",
      "a": "تتوفر خيارات للعائلات والمجموعات بحسب التوفر. أدخل عدد الركاب والأمتعة بدقة، لأن سعة الأمتعة تختلف بين فئات السيارات وقد تؤثر في الخيار المناسب لك."
    },
    {
      "q": "كيف أعرف سعر الرحلة؟",
      "a": "يظهر السعر أثناء الحجز بعد إدخال تفاصيل الرحلة واختيار السيارة. راجع المبلغ الإجمالي وأي خدمات إضافية قبل التأكيد، وتواصل معنا إذا احتجت إلى توضيح."
    },
    {
      "q": "هل يمكنني الحجز لرحلة خلال أقل من 24 ساعة؟",
      "a": "للحجز عبر الموقع، اختر موعداً يبعد 24 ساعة على الأقل. إذا كان موعد رحلتك أقرب من ذلك، اتصل بنا على ‎+44 208 153 0303 للاستفسار عن إمكانية ترتيبها."
    }
  ],
  "closing": "رتّب تنقّلك مسبقاً مع ACT واختر السيارة المناسبة لرحلتك. أدخل تفاصيل الانطلاق والوجهة للاطلاع على الخيارات والأسعار المتاحة."
};
export const arabicMetadata = { title: content.title, description: content.description };

export default function ArabicHeathrowPage() {
  const schema = {
    "@context": "https://schema.org", "@type": "Service",
    name: content.heading, serviceType: "نقل خاص من وإلى المطار",
    provider: { "@type": "LocalBusiness", name: "Airport & City Transfer", url: "https://airportandcitytransfer.com" },
    areaServed: ["London", "Heathrow Airport"],
    url: "https://airportandcitytransfer.com/ar/heathrow-airport-transfer",
    description: content.description,
  };
  return (
    <main lang="ar" dir="rtl" className="bg-black text-white" style={{ fontFamily: "Tahoma, Arial, sans-serif" }}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
      <section className="px-6 py-20 md:px-12 lg:px-20">
        <div className="mx-auto max-w-6xl">
          <Badge className="mb-6 bg-yellow-500 text-black">{content.badge}</Badge>
          <h1 className="max-w-4xl text-4xl font-bold leading-tight md:text-6xl">{content.heading}</h1>
          <p className="mt-6 max-w-3xl text-lg text-gray-300">{content.intro}</p>
          <div className="mt-8 flex flex-wrap gap-4">
            <Button asChild className="bg-yellow-500 text-black hover:bg-yellow-400"><Link href="/ar#book-now">احجز الآن</Link></Button>
            <Button asChild variant="outline" className="border-yellow-500 text-yellow-500"><Link href="/ar/about-us#contact-us">تواصل معنا</Link></Button>
          </div>
        </div>
      </section>
      <section className="px-6 py-14 md:px-12 lg:px-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-3xl font-semibold">لماذا تختار ACT؟</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">{content.benefits.map(item => (
            <Card key={item} className="border-yellow-500/30 bg-zinc-900 text-white"><CardContent className="p-6"><p className="font-medium">{item}</p></CardContent></Card>
          ))}</div>
        </div>
      </section>
      <section className="px-6 py-14 md:px-12 lg:px-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-3xl font-semibold">فئات السيارات</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-5">{content.vehicles.map(item => (
            <Card key={item} className="border-white/10 bg-zinc-900 text-white"><CardContent className="p-5 text-center"><p>{item}</p></CardContent></Card>
          ))}</div>
          <p className="mt-6 text-gray-300">{content.vehicleNote}</p>
        </div>
      </section>
      <section className="px-6 py-14 md:px-12 lg:px-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-3xl font-semibold">وجهات شائعة من مطار هيثرو</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-2">{content.routes.map(item => <div key={item} className="rounded-xl border border-white/10 bg-zinc-900 p-5">{item}</div>)}</div>
        </div>
      </section>
      <section className="px-6 py-14 md:px-12 lg:px-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-3xl font-semibold">تنقّل بسيارة خاصة من وإلى مطار هيثرو</h2>
          <div className="mt-6 space-y-5 text-gray-300">{content.paragraphs.map(item => <p key={item}>{item}</p>)}</div>
        </div>
      </section>
      <section className="px-6 py-14 md:px-12 lg:px-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-3xl font-semibold">الأسئلة الشائعة</h2>
          <div className="mt-8 space-y-4">{content.faqs.map(faq => (
            <Card key={faq.q} className="border-white/10 bg-zinc-900 text-white"><CardContent className="p-6">
              <h3 className="font-semibold">{faq.q}</h3>
              <p className="mt-2 text-gray-300">{faq.a.includes("+44 208 153 0303") ? <>{faq.a.split("+44 208 153 0303")[0]}<a dir="ltr" className="inline-block underline" href="tel:+442081530303">+44 208 153 0303</a>{faq.a.split("+44 208 153 0303")[1]}</> : faq.a}</p>
            </CardContent></Card>
          ))}</div>
        </div>
      </section>
      <section className="px-6 py-20 md:px-12 lg:px-20">
        <div className="mx-auto max-w-5xl rounded-3xl border border-yellow-500/30 bg-zinc-900 p-10 text-center">
          <h2 className="text-3xl font-bold">احجز رحلتك من وإلى مطار هيثرو</h2>
          <p className="mx-auto mt-4 max-w-2xl text-gray-300">{content.closing}</p>
          <Button asChild className="mt-8 bg-yellow-500 text-black hover:bg-yellow-400"><Link href="/ar#book-now">احجز الآن</Link></Button>
        </div>
      </section>
    </main>
  );
}
