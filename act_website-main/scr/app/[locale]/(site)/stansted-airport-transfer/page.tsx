import Link from "next/link";
import { Metadata } from "next";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Stansted Airport Transfer London | Airport & City Transfer",
  description:
    "Reliable private Stansted airport transfers across London with fixed pricing, professional drivers, executive vehicles, flight monitoring and 24/7 booking.",
};

const benefits = [
  "Flight monitoring",
  "Fixed pricing",
  "Professional drivers",
  "Executive vehicles",
  "Meet & greet service",
  "24/7 online booking",
];

const vehicles = [
  "Standard PHV",
  "Executive",
  "Luxury",
  "7 Seater",
  "Luxury Van",
];

const routes = [
  "Stansted to Central London",
  "Stansted to Canary Wharf",
  "Stansted to Mayfair",
  "Stansted to London hotels",
  "Stansted to Heathrow Airport",
  "Stansted to business districts",
];

const faqs = [
  {
    q: "Do you provide Stansted airport pickup?",
    a: "Yes. Airport & City Transfer provides private Stansted airport pickup and drop-off services across London.",
  },
  {
    q: "Do you monitor delayed flights?",
    a: "Yes. We monitor flight times where flight details are provided, helping your driver prepare for delays or early arrivals.",
  },
  {
    q: "Can I book a 7 seater from Stansted?",
    a: "Yes. You can book a 7 seater airport transfer for families, groups, luggage, and business travel.",
  },
  {
    q: "Is the price fixed?",
    a: "ACT aims to provide clear pricing before booking, so customers can confirm their trip with confidence.",
  },
];

export default function StanstedAirportTransferPage() {
  return (
    <main className="bg-black text-white">
      <section className="px-6 py-20 md:px-12 lg:px-20">
        <div className="mx-auto max-w-6xl">
          <Badge className="mb-6 bg-yellow-500 text-black">
            Stansted Airport Transfer
          </Badge>

          <h1 className="max-w-4xl text-4xl font-bold leading-tight md:text-6xl">
            Stansted Airport Transfer London
          </h1>

          <p className="mt-6 max-w-3xl text-lg text-gray-300">
            Book a reliable private Stansted airport transfer across London with
            fixed pricing, professional drivers, executive vehicles, flight
            monitoring, and 24/7 online booking.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <Button asChild className="bg-yellow-500 text-black hover:bg-yellow-400">
              <Link href="/en#book-now">Book Now</Link>
            </Button>

            <Button asChild variant="outline" className="border-yellow-500 text-yellow-500">
              <Link href="/en/contact-us">Contact Us</Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="px-6 py-14 md:px-12 lg:px-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-3xl font-semibold">Why Choose ACT?</h2>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {benefits.map((item) => (
              <Card key={item} className="border-yellow-500/30 bg-zinc-900 text-white">
                <CardContent className="p-6">
                  <p className="font-medium">{item}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-14 md:px-12 lg:px-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-3xl font-semibold">Vehicle Types</h2>

          <div className="mt-8 grid gap-4 md:grid-cols-5">
            {vehicles.map((vehicle) => (
              <Card key={vehicle} className="border-white/10 bg-zinc-900 text-white">
                <CardContent className="p-5 text-center">
                  <p>{vehicle}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-14 md:px-12 lg:px-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-3xl font-semibold">Popular Stansted Routes</h2>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {routes.map((route) => (
              <div key={route} className="rounded-xl border border-white/10 bg-zinc-900 p-5">
                {route}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-14 md:px-12 lg:px-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-3xl font-semibold">
            Private Stansted Airport Transfer Service
          </h2>

          <div className="mt-6 space-y-5 text-gray-300">
            <p>
              Airport & City Transfer provides private Stansted airport transfer
              services for passengers travelling to and from London. Whether you
              are arriving for business, a family trip, a hotel stay, or an
              executive journey, ACT helps you pre-book a comfortable and reliable
              transfer.
            </p>

            <p>
              Our Stansted transfer service is designed for convenience. You can
              choose from standard private hire vehicles, executive cars, luxury
              vehicles, 7 seaters, and luxury vans depending on your journey,
              luggage, and passenger requirements.
            </p>

            <p>
              ACT focuses on clear communication, professional service, fixed
              pricing, and a smooth booking experience from airport pickup to
              final destination.
            </p>
          </div>
        </div>
      </section>

      <section className="px-6 py-14 md:px-12 lg:px-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-3xl font-semibold">FAQs</h2>

          <div className="mt-8 space-y-4">
            {faqs.map((faq) => (
              <Card key={faq.q} className="border-white/10 bg-zinc-900 text-white">
                <CardContent className="p-6">
                  <h3 className="font-semibold">{faq.q}</h3>
                  <p className="mt-2 text-gray-300">{faq.a}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-20 md:px-12 lg:px-20">
        <div className="mx-auto max-w-5xl rounded-3xl border border-yellow-500/30 bg-zinc-900 p-10 text-center">
          <h2 className="text-3xl font-bold">
            Book Your Stansted Airport Transfer Today
          </h2>

          <p className="mx-auto mt-4 max-w-2xl text-gray-300">
            Pre-book your Stansted airport transfer with Airport & City Transfer
            and travel across London with confidence.
          </p>

          <Button asChild className="mt-8 bg-yellow-500 text-black hover:bg-yellow-400">
            <Link href="/en#book-now">Book Now</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
