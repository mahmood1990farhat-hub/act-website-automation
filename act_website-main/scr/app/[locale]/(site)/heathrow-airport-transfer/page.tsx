import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, Clock3, Plane, ShieldCheck, Star, CarTaxiFront, MapPin } from "lucide-react";
import Link from "next/link";
import { Locale } from "../../../../../i18n.config";

export const metadata = {
  title: "Heathrow Airport Transfer London | Airport & City Transfer",
  description:
    "Reliable private Heathrow airport transfers across London with fixed pricing, professional drivers, executive vehicles, flight monitoring and 24/7 booking.",
};

type PageProps = {
  params: Promise<{ locale: Locale }>;
};

const vehicleTypes = [
  {
    name: "Saloon",
    details: "Ideal for solo travellers and couples with cabin luggage.",
    capacity: "Up to 3 passengers",
  },
  {
    name: "Executive",
    details: "Premium comfort for business travel and airport pickups.",
    capacity: "Up to 3 passengers",
  },
  {
    name: "MPV / 7 Seater",
    details: "Best for families and groups with multiple suitcases.",
    capacity: "Up to 7 passengers",
  },
  {
    name: "Minibus",
    details: "Great for larger group transfers and event transport.",
    capacity: "Up to 8 passengers",
  },
];

const popularRoutes = [
  "Heathrow Airport to Central London",
  "Heathrow Airport to Canary Wharf",
  "Heathrow Airport to Kings Cross / St Pancras",
  "Heathrow Airport to Paddington",
  "Heathrow Airport to Oxford Street",
  "Heathrow Airport to South London",
];

const faqs = [
  {
    q: "Do you monitor flight delays for Heathrow pickups?",
    a: "Yes. We track your flight status and adjust pickup timing to match your actual arrival time where possible.",
  },
  {
    q: "Are your Heathrow transfer prices fixed?",
    a: "Yes. You receive a transparent fare before confirming your booking, with no hidden surprises.",
  },
  {
    q: "Can I pre-book a return transfer to Heathrow?",
    a: "Absolutely. You can book both arrival and return airport journeys in advance.",
  },
  {
    q: "Is your Heathrow transfer service available 24/7?",
    a: "Yes. Our booking and transfer service operates day and night for early and late flights.",
  },
];

export default async function HeathrowAirportTransferPage({ params }: PageProps) {
  const locale = (await params).locale;
  const isRTL = locale === "ar";

  return (
    <div className={`min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 ${isRTL ? "rtl" : "ltr"}`}>
      <section className="bg-foreground text-white py-16 md:py-24">
        <div className="container mx-auto px-4 md:px-8">
          <div className="max-w-4xl space-y-6">
            <Badge variant="outline" className="text-primary border-primary/40 font-semibold">
              London Airport Transfers
            </Badge>
            <h1 className="text-3xl md:text-5xl font-bold leading-tight">
              Heathrow Airport Transfer in London
            </h1>
            <p className="text-base md:text-xl text-gray-300 leading-relaxed">
              Book dependable private Heathrow airport transfers with professional drivers, executive vehicles,
              flight monitoring, and fixed prices across London.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href={`/${locale}#book-now`}>
                <Button size="lg" className="cursor-pointer">Book Heathrow Transfer</Button>
              </Link>
              <Link href={`/${locale}/about-us`}>
                <Button size="lg" variant="outline" className="cursor-pointer text-black hover:text-white">
                  Learn About ACT
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="py-14 md:py-20">
        <div className="container mx-auto px-4 md:px-8">
          <div className="text-center mb-10">
            <h2 className="text-2xl md:text-4xl font-bold text-black">Why Choose ACT for Heathrow Transfers</h2>
          </div>
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {[
              { icon: ShieldCheck, title: "Licensed & Professional", text: "Experienced and vetted private hire drivers." },
              { icon: Clock3, title: "24/7 Availability", text: "Airport transfers for early departures and late arrivals." },
              { icon: Plane, title: "Flight Monitoring", text: "Pickup times aligned with real-time flight status." },
              { icon: Star, title: "Fixed Pricing", text: "Transparent fares confirmed before booking." },
            ].map((item) => (
              <Card key={item.title} className="border-0 shadow-md shadow-primary/20 h-full">
                <CardHeader>
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-3">
                    <item.icon className="w-6 h-6" />
                  </div>
                  <CardTitle className="text-lg">{item.title}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-gray-600">{item.text}</CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="py-14 md:py-20 bg-white">
        <div className="container mx-auto px-4 md:px-8">
          <h2 className="text-2xl md:text-4xl font-bold text-black text-center mb-10">Vehicle Types for Heathrow Airport Transfers</h2>
          <div className="grid gap-5 md:grid-cols-2">
            {vehicleTypes.map((vehicle) => (
              <Card key={vehicle.name} className="border border-primary/15 shadow-sm">
                <CardContent className="p-6">
                  <div className="flex items-start gap-3">
                    <CarTaxiFront className="text-primary mt-1" />
                    <div>
                      <h3 className="text-xl font-semibold text-black">{vehicle.name}</h3>
                      <p className="text-gray-600 mt-1">{vehicle.details}</p>
                      <p className="text-sm font-medium text-primary mt-2">{vehicle.capacity}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="py-14 md:py-20 bg-gray-50">
        <div className="container mx-auto px-4 md:px-8">
          <h2 className="text-2xl md:text-4xl font-bold text-black text-center mb-10">Popular Heathrow Routes</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {popularRoutes.map((route) => (
              <div key={route} className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm flex items-start gap-3">
                <MapPin className="text-primary mt-0.5" size={18} />
                <p className="text-gray-700 font-medium">{route}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-14 md:py-20 bg-white">
        <div className="container mx-auto px-4 md:px-8 max-w-4xl space-y-5">
          <h2 className="text-2xl md:text-4xl font-bold text-black">Heathrow Airport Transfer Service in London</h2>
          <p className="text-gray-700 leading-relaxed">
            Airport & City Transfer provides reliable Heathrow airport transportation for business travellers,
            families, and tourists across London. Whether you need a meet-and-greet pickup from arrivals or a
            timely drop-off for departure, our team focuses on punctuality, safety, and comfort.
          </p>
          <p className="text-gray-700 leading-relaxed">
            Our Heathrow transfer service includes fixed upfront fares, professional drivers, and a range of
            vehicle options to match your group size and luggage needs. With 24/7 availability and flight
            monitoring support, you can travel confidently at any hour.
          </p>
          <ul className="space-y-2">
            {[
              "Private Heathrow transfers across all London zones",
              "Executive and family-friendly vehicle options",
              "Fast online booking with instant journey confirmation",
              "Clean, comfortable vehicles and professional service",
            ].map((point) => (
              <li key={point} className="flex items-start gap-2 text-gray-700">
                <CheckCircle2 className="text-primary mt-0.5" size={18} />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="py-14 md:py-20 bg-gray-50">
        <div className="container mx-auto px-4 md:px-8 max-w-4xl">
          <h2 className="text-2xl md:text-4xl font-bold text-black mb-8 text-center">FAQs – Heathrow Transfer</h2>
          <div className="space-y-4">
            {faqs.map((faq) => (
              <Card key={faq.q} className="border border-gray-200">
                <CardContent className="p-5">
                  <h3 className="text-lg font-semibold text-black mb-2">{faq.q}</h3>
                  <p className="text-gray-700">{faq.a}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 md:py-24 bg-foreground text-white">
        <div className="container mx-auto px-4 md:px-8 text-center max-w-3xl">
          <h2 className="text-2xl md:text-4xl font-bold mb-4">Ready to Book Your Heathrow Airport Transfer?</h2>
          <p className="text-gray-300 mb-7">
            Secure your private transfer in minutes and travel across London with confidence.
          </p>
          <Link href={`/${locale}#book-now`}>
            <Button size="lg" className="cursor-pointer">Get a Fixed Price Now</Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
