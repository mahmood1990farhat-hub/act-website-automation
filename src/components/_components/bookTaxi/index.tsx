"use client";
import { Button } from "@/components/ui/button";
import Image from "next/image";
import React, { useEffect, useState } from "react";
import { PlaceSuggestion } from "./LocationSelector";
import RoutePoints from "./RoutePoints";
import ChooseCar from "./ChooseCar";
import { Locale } from "../../../../i18n.config";
import ConfirmFlightDetails from "./ConfirmFlightDetails";
import PaymentDsetails from "./PaymentDsetails";
import BookingConfirmation from "./BookingConfirmation";
import MapView from "./MapView";
import Auth from "../auth/Auth";
import Link from "next/link";


export type book_Taxi = {
  title: string;
  subtitle: string;
  fromAirport: string;
  toAirport: string;
  form: {
    PickUp_location: string;
    stop_ponit: string;

    DropOff_location: string;
    error: string;
    date: string;
    time: string;
    is_required: string;
    button: string;
    smallSuitcase: string;
    largeSuitcase: string;
    NumberOfPassenger: string;
    error_message: string;
    error_button: string;
  };
};
export type Choose_car = {
  title: string;
  button: string;
};

export type Confir_flight_details = {
  title: string;
  Distance: string;
  Trip: string;
  Car_type: string;
  Cost: string;
  airport_vat: string;
  VAT: string;
  Edit: string;
  details: string;
  Total_Cost: string;
  button: string;
};
export type Payments_details = {
  title: string;
  form: {
    Card_Number: string;
    Expired_date: string;
    check: {
      Agree: string;
      privacy_policy: string;
      terms_of_use: string;
    };
    button: string;
  };
};

export type RoutePoint = {
  id: number;
  type: "pickup" | "stop" | "dropoff";
  point: PlaceSuggestion | any | null;
};

export type booking_Confirmation = {
  title: string;
  desc: {
    span_1: string;
    hour: string;
    hour_5: string;
    span_2: string;
  };
  button: string;
  button_Back_to_home: string;
};

export type home = {
  Book_Taxi: book_Taxi;
  Choose_car: Choose_car;
  Confir_flight_details: Confir_flight_details;
  Payments_details: Payments_details;
  Booking_Confirmation: booking_Confirmation;
};
export type VehicleType = {
  id: number;
  name_en: string;
  name_ar: string;
  desc_en: string;
  desc_ar: string;
  icon_url: string;
  max_passengers_count: number;
  airport_vat: number;
  base_trip_cost: number;
  regular_vat: number;
  total_cost: number;
};

export type calculatTripCost = {
  car_type: VehicleType[];
  distance_meters: number;
  distance_miles: number;
  route_polyline: string;
};

type typeProps = {
  home: home;
  locale: Locale;
  auth: any;
  policy_and_terms: any
};


export default function BookTaxi({ home, locale, auth, policy_and_terms }: typeProps) {
  const [routePoints, setRoutePoints] = useState<RoutePoint[]>([
    { id: 1, type: "pickup", point: null },
    { id: 2, type: "dropoff", point: null },
  ]);
  const [formDetails, setFormDetails] = useState({
    date: "",
    time: "",
    smallSuitcase: 0,
    largeSuitcase: 0,
    numberOfPassengers: 1,
  });
  const [SelectedCar, setSelectedCar] = useState<any | undefined>();
  const [rideOptions, setRideOptions] = useState<calculatTripCost | null>(null);
  const [clientSecret, setClientSecret] = useState<string>('')
  const [step, setStep] = useState<number>(1);
  useEffect(() => {
    const handleRouteChange = () => {
      window.scrollTo(0, 0);
    };
    handleRouteChange()

  }, [step]);

  
  const heroImage = locale === 'ar' ? `bg-[linear-gradient(rgba(0,0,0,0.85),rgba(0,0,0,0.85)),url('/images/act-hero-bg-skewed.jpg')]` : `bg-[linear-gradient(rgba(0,0,0,0.85),rgba(0,0,0,0.85)),url('/images/act-hero-bg.webp')]`;


  return (
    <div className={`${heroImage} bg-cover bg-no-repeat bg-center ${step !== 6 && 'py-16 lg:py-36'}`} id="book-now">
      {step !== 6 && (
        <div>
          <div
            className="flex items-center max-md:flex-col gap-5 py-5 w-full lg:px-24 px-5"
            dir={locale === "en" ? "ltr" : "rtl"}
          >
            <section
              className="flex-1 w-full"
              dir={locale === "en" ? "ltr" : "rtl"}
            >
              {step === 1 ? (
                <RoutePoints
                  locale={locale}
                  routePoints={routePoints}
                  setRoutePoints={setRoutePoints}
                  book_Taxi={home.Book_Taxi}
                  setValue={(d) => setFormDetails(d)}
                  formDetails={formDetails}
                  setTripData={(res) => setRideOptions(res)}
                  nextStep={() => setStep(2)}
                />
              ) : step === 2 ? (
                <ChooseCar
                  selectedCar={SelectedCar}
                  setSelectedCar={(data) => setSelectedCar(data)}
                  locale={locale}
                  Choose_car={home.Choose_car}
                  rideOptions={rideOptions}
                  nextStep={() => setStep(3)}
                  prevStep={() => setStep(1)}
                />
              ) : step === 3 ? (
                <ConfirmFlightDetails
                  trans={home}
                  rideOptions={rideOptions!}
                  locale={locale}
                  data={{
                    routePoints: routePoints,
                    time: formDetails.time,
                    date: formDetails.date,
                    distance: `   ${rideOptions?.distance_miles} miles / ${rideOptions && rideOptions?.distance_meters > 1000
                      ? rideOptions?.distance_meters / 1000 + " K.m"
                      : rideOptions?.distance_meters + " m"
                      }  `,
                    largeSuitcase: formDetails.largeSuitcase,
                    smallSuitcase: formDetails.smallSuitcase,
                    numberOfPassengers: formDetails.numberOfPassengers,
                    carName: SelectedCar
                      ? (SelectedCar[
                        `name_${locale}` as keyof VehicleType
                      ] as string)
                      : "",
                      carImage: SelectedCar ? SelectedCar.icon_url : "",
                    cartype: SelectedCar?.id,
                    cost: SelectedCar ? SelectedCar.base_trip_cost : undefined,
                    airport_vat: SelectedCar
                      ? SelectedCar.airport_vat
                      : undefined,
                    regular_vat: SelectedCar
                      ? SelectedCar.regular_vat
                      : undefined,
                    total_cost: SelectedCar
                      ? SelectedCar.total_cost
                      : undefined,
                      trip_duration_minutes: SelectedCar?.expected_trip_duration_minutes
                  }}
                  setStep={(e) => setStep(e)}
                  step={step}
                  setClientSecret={(Secret) => setClientSecret(Secret)}
                  editDatelis={() => setStep(1)}
                />
              ) : step === 4 ? (
                <>
                  <PaymentDsetails
                    policy_and_terms={policy_and_terms}
                    clientSecret={clientSecret}
                    trans={home.Payments_details}
                    nextStep={() => setStep(5)}
                    prevStep={() => setStep(3)}
                    locale={locale}
                  /></>
              ) : step === 5 ? (
                <div className="flex items-center justify-center ">
                  <BookingConfirmation trans={home.Booking_Confirmation} locale={locale} />
                </div>
              ) : null}
            </section>{" "}
          </div>
        </div>
      )}
      {step === 6 && (
        <Auth locale={locale} trans={auth} setStep={() => setStep(3)} isBookingFlow={true} />
      )}
    </div>
  );
}
