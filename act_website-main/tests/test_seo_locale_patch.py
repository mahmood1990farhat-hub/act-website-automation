"""Focused source contracts; not a Next build, rendered DOM or HTTP test."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'src/app/[locale]/(site)'
AIRPORTS = ('heathrow', 'gatwick', 'stansted', 'luton', 'london-city')


class SeoLocalePatchTests(unittest.TestCase):
    def test_home_metadata_both_languages(self):
        source = (SITE / 'page.tsx').read_text()
        self.assertIn('getPublicPageSeo(locale, "", locale === "ar" ?', source)
        self.assertIn('London Airport Transfers | Airport & City Transfer', source)
        self.assertIn('خدمات النقل من وإلى مطارات لندن', source)
        self.assertEqual(source.count('description:'), 2)

    def test_existing_canonical_language_helper(self):
        source = (ROOT / 'src/lib/seo.ts').read_text()
        for value in ('canonical: buildLocalizedUrl(locale, path)',
                      'en: buildLocalizedUrl', 'ar: buildLocalizedUrl', '"x-default":'):
            self.assertIn(value, source)

    def test_contact_destination_exists(self):
        source = (SITE / 'about-us/page.tsx').read_text()
        self.assertIn('id="contact-us"', source)
        self.assertIn('<ContactUs ', source)

    def test_booking_destination_exists(self):
        source = (ROOT / 'src/components/_components/bookTaxi/index.tsx').read_text()
        self.assertIn('id="book-now"', source)


def check_links(airport):
    def test(self):
        source = (SITE / f'{airport}-airport-transfer/page.tsx').read_text()
        self.assertRegex(source, r'export default async function \w+\(')
        self.assertIn('const { locale } = await params;', source)
        self.assertIn('const bookingHref = `/${locale}#book-now`;', source)
        self.assertIn('const contactHref = `/${locale}/about-us#contact-us`;', source)
        self.assertEqual(source.count('href={bookingHref}'), 2)
        self.assertEqual(source.count('href={contactHref}'), 1)
        self.assertNotRegex(source, r'href="/en')
    return test


def check_schema(airport):
    def test(self):
        source = (SITE / f'{airport}-airport-transfer/page.tsx').read_text()
        self.assertIn(f'url: `https://airportandcitytransfer.com/${{locale}}/{airport}-airport-transfer`', source)
        self.assertIn(f'getPublicPageSeo(locale, "{airport}-airport-transfer", pageMetadata)', source)
    return test


for airport in AIRPORTS:
    setattr(SeoLocalePatchTests, 'test_links_' + airport.replace('-', '_'), check_links(airport))
    setattr(SeoLocalePatchTests, 'test_schema_' + airport.replace('-', '_'), check_schema(airport))

if __name__ == '__main__':
    unittest.main()
