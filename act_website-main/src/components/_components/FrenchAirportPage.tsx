import Link from "next/link";
import copy from "@/dictionaries/fr/airports.json";
import { getPublicPageSeo } from "@/lib/seo";

export type FrenchAirportSlug = keyof typeof copy.pages;
export const frenchAirportMetadata = (slug: FrenchAirportSlug) => getPublicPageSeo("fr", slug, copy.pages[slug].metadata);

export default function FrenchAirportPage({ slug }: { slug: FrenchAirportSlug }) {
  const page = copy.pages[slug];
  const shared = copy.shared;
  const text = (value: string) => value.replaceAll("{airport}", page.airport);
  const paragraphs = "serviceParagraphs" in page ? page.serviceParagraphs : shared.serviceParagraphs;
  const faqs = shared.faqs.map((faq, i) => i === 2 && "vehicleFaq" in page ? page.vehicleFaq : faq);
  const url = `https://airportandcitytransfer.com/fr/${slug}`;
  const structuredData = { "@context": "https://schema.org", "@graph": [
    { "@type": "WebPage", "@id": url, url, name: page.metadata.title, description: page.metadata.description, inLanguage: "fr" },
    { "@type": "Service", "@id": url + "#service", url, name: page.heading, description: text(shared.intro), areaServed: [page.airport, "London"], provider: { "@type": "Organization", name: "Airport & City Transfer", url: "https://airportandcitytransfer.com" } },
    { "@type": "FAQPage", "@id": url + "#faq", inLanguage: "fr", mainEntity: faqs.map(faq => ({ "@type": "Question", name: text(faq.q), acceptedAnswer: { "@type": "Answer", text: text(faq.a) } })) }
  ] };
  const card = "rounded-2xl border border-yellow-500/30 bg-zinc-900 p-6";
  const section = "mx-auto max-w-6xl px-6 py-12 md:px-12";
  const book = <Link href="/fr#book-now" className="inline-block rounded-lg bg-yellow-500 px-5 py-3 font-semibold text-black">{shared.bookNow}</Link>;
  return <article className="bg-black text-white" lang="fr" dir="ltr">
    <script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(structuredData).replace(/</g, "\\u003c")}} />
    <section className={section + " md:py-20"}>
      <span className="rounded-full bg-yellow-500 px-3 py-1 text-sm text-black">{page.badge}</span>
      <h1 className="mt-7 max-w-4xl text-4xl font-bold leading-tight md:text-6xl">{page.heading}</h1>
      <p className="mt-6 max-w-3xl text-lg leading-relaxed text-gray-300">{text(shared.intro)}</p>
      <div className="mt-8 flex flex-wrap gap-4">{book}<Link href="/fr/about-us#contact-us" className="rounded-lg border border-yellow-500 px-5 py-3 text-yellow-500">{shared.contactUs}</Link></div>
    </section>
    <section className={section}><h2 className="text-3xl font-semibold">{shared.whyChoose}</h2><div className="mt-8 grid gap-4 md:grid-cols-3">{shared.benefits.map(value => <div key={value} className={card}>{value}</div>)}</div></section>
    <section className={section}><h2 className="text-3xl font-semibold">{shared.vehicleTypes}</h2><div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">{shared.vehicles.map(value => <div key={value} className={card}>{value}</div>)}</div></section>
    <section className={section}><h2 className="text-3xl font-semibold">{text(shared.popularRoutesTitle)}</h2><div className="mt-8 grid gap-4 md:grid-cols-2">{page.routes.map(value => <div key={value} className={card}>{value}</div>)}</div></section>
    <section className={section}><h2 className="text-3xl font-semibold">{text(shared.serviceTitle)}</h2><div className="mt-6 space-y-5 text-gray-300">{paragraphs.map(value => <p key={value}>{text(value)}</p>)}</div></section>
    <section className={section}><h2 className="text-3xl font-semibold">{shared.faqTitle}</h2><div className="mt-8 space-y-4">{faqs.map(faq => <div key={faq.q} className={card}><h3 className="font-semibold">{text(faq.q)}</h3><p className="mt-2 text-gray-300">{text(faq.a)}</p></div>)}</div></section>
    <section className={section}><div className={card + " text-center"}><h2 className="text-3xl font-bold">{text(shared.finalTitle)}</h2><p className="my-6 text-gray-300">{text(shared.finalDescription)}</p>{book}</div></section>
  </article>;
}
