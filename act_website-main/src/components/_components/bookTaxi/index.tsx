"use client";
import { LANGUAGE_CHANGE_EVENT, saveLanguageDraft, takeLanguageDraft } from "@/lib/booking-language-draft";
import { languageSwitchText } from "@/lib/language-switch-text";
import { Button } from "@/components/ui/button";
import Image from "next/image";
import React, { useEffect, useState } from "react";
import { PlaceSuggestion } from "./LocationSelector";
import RoutePoints from "./RoutePoints";
import ChooseCar from "./ChooseCar";
import { Locale, directionFor, localizedVehicleValue } from "../../../../i18n.config";
import ConfirmFlightDetails from "./ConfirmFlightDetails";
import PaymentDsetails from "./PaymentDsetails";
import BookingConfirmation from "./BookingConfirmation";
import MapView from "./MapView";
import Auth from "../auth/Auth";
import Link from "next/link";
import PassengerDetails from "./PassengerDetails";
import ChildInfantTravelInfo from "./ChildInfantTravelInfo";
import FlightDetails from "./FlightDetails";
import AdditionalRequirements from "./AdditionalRequirements";


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
  cost_breakdown: string;
  transfer_fare: string;
  vat_20: string;
  airport_access_fee: string;
  meet_and_greet: string;
  included: string;
  total_price: string;
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

export type PassengerCounts = {
  adults: number;
  children: number;
  infants: number;
  numberOfPassengers: number;
};

export type PassengerDetailsForm = {
  fullName: string;
  email: string;
  countryCode: string;
  mobileNumber: string;
};

export type ChildInfantTravelForm = {
  infantSeatOption: string;
  childSeatOption: string;
};

export type FlightDetailsForm = {
  flightType: "" | "arrival" | "departure";
  flightNumber: string;
  airline: string;
  landingTime: string;
  departureTime: string;
  pickupSignName: string;
};

export type AdditionalRequirementsForm = {
  notesToDriver: string;
};

export type AdditionalInformation = {
  title: string;
  driverTitle: string;
  description: string;
  back: string;
  continue: string;
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
  Additional_Information: AdditionalInformation;
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
  airport_access_fee: number;
  base_trip_cost: number;
  transfer_fare: number;
  min_adjustment: number;
  regular_vat: number;
  total_cost: number;
  meet_and_greet_available?: boolean;
  meet_and_greet_fee?: number;
  meet_and_greet_total?: number;
  meet_and_greet_available_fee?: number;
  expected_trip_duration_minutes?: number;
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
    adults: 1,
    children: 0,
    infants: 0,
    numberOfPassengers: 1,
  });
  const [passengerDetails, setPassengerDetails] = useState<PassengerDetailsForm>({
    fullName: "",
    email: "",
    countryCode: "+44 United Kingdom",
    mobileNumber: "",
  });
  const [childInfantTravel, setChildInfantTravel] = useState<ChildInfantTravelForm>({
    infantSeatOption: "",
    childSeatOption: "",
  });
  const [flightDetails, setFlightDetails] = useState<FlightDetailsForm>({
    flightType: "",
    flightNumber: "",
    airline: "",
    landingTime: "",
    departureTime: "",
    pickupSignName: "",
  });
  const [additionalRequirements, setAdditionalRequirements] = useState<AdditionalRequirementsForm>({
    notesToDriver: "",
  });
  const [SelectedCar, setSelectedCar] = useState<any | undefined>();
  const [rideOptions, setRideOptions] = useState<calculatTripCost | null>(null);
  const [clientSecret, setClientSecret] = useState<string>('')
  const [paymentTotal, setPaymentTotal] = useState<number | null>(null);
  const [step, setStep] = useState<number>(1);
  const [restoredDraft, setRestoredDraft] = useState(false);
  useEffect(() => {
    try {
      const draft = takeLanguageDraft(window.sessionStorage, locale);
      if (!draft) return;
      setRoutePoints(draft.routePoints);
      setFormDetails(draft.formDetails);
      setPassengerDetails(draft.passengerDetails);
      setChildInfantTravel(draft.childInfantTravel);
      setFlightDetails(draft.flightDetails);
      setAdditionalRequirements(draft.additionalRequirements);
      setRestoredDraft(true);
      // Always recalculate the quote; payment/price/vehicle state is never restored.
      setStep(1);
    } catch { /* Storage unavailable: no handoff to restore. */ }
  }, [locale]);

  useEffect(() => {
    const transfer = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (clientSecret && step !== 9) {
        detail.reason = "payment";
        event.preventDefault();
        return;
      }
      if (step === 9) return;
      try {
        saveLanguageDraft(window.sessionStorage, { routePoints, formDetails, passengerDetails, childInfantTravel, flightDetails, additionalRequirements }, detail.locale);
      } catch {
        detail.reason = "failed";
        event.preventDefault();
      }
    };
    window.addEventListener(LANGUAGE_CHANGE_EVENT, transfer);
    return () => window.removeEventListener(LANGUAGE_CHANGE_EVENT, transfer);
  }, [routePoints, formDetails, passengerDetails, childInfantTravel, flightDetails, additionalRequirements, clientSecret, step]);


  useEffect(() => {
    const handleRouteChange = () => {
      window.scrollTo(0, 0);
    };
    handleRouteChange()

  }, [step]);

  
  const heroImage = locale === 'ar' ? `bg-[linear-gradient(rgba(0,0,0,0.85),rgba(0,0,0,0.85)),url('/images/act-hero-bg-skewed.jpg')]` : `bg-[linear-gradient(rgba(0,0,0,0.85),rgba(0,0,0,0.85)),url('/images/act-hero-bg.webp')]`;


  return (
    <div className={`${heroImage} bg-cover bg-no-repeat bg-center ${step !== 10 && 'py-16 lg:py-36'}`} id="book-now">
      {restoredDraft && <p role="status" className="mx-auto max-w-3xl p-4 text-white">{languageSwitchText(locale, "restored")}</p>}
      {step !== 10 && (
        <div>
          <div
            className="flex items-center max-md:flex-col gap-5 py-5 w-full lg:px-24 px-5"
            dir={directionFor(locale)}
          >
            <section
              className="flex-1 w-full"
              dir={directionFor(locale)}
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
                <PassengerDetails
                  locale={locale}
                  passengerDetails={passengerDetails}
                  setPassengerDetails={setPassengerDetails}
                  nextStep={() => setStep(formDetails.children > 0 || formDetails.infants > 0 ? 4 : 5)}
                  prevStep={() => setStep(2)}
                />
              ) : step === 4 ? (
                <ChildInfantTravelInfo
                  locale={locale}
                  passengerCounts={formDetails}
                  childInfantTravel={childInfantTravel}
                  setChildInfantTravel={setChildInfantTravel}
                  nextStep={() => setStep(5)}
                  prevStep={() => setStep(3)}
                />
              ) : step === 5 ? (
                <FlightDetails
                  locale={locale}
                  flightDetails={flightDetails}
                  setFlightDetails={setFlightDetails}
                  pickupTime={formDetails.time}
                  routePoints={routePoints}
                  changePickupTime={() => setStep(1)}
                  nextStep={() => setStep(6)}
                  prevStep={() => setStep(formDetails.children > 0 || formDetails.infants > 0 ? 4 : 3)}
                />
              ) : step === 6 ? (
                <AdditionalRequirements
                  locale={locale}
                  translations={home.Additional_Information}
                  additionalRequirements={additionalRequirements}
                  setAdditionalRequirements={setAdditionalRequirements}
                  nextStep={() => setStep(7)}
                  prevStep={() => setStep(5)}
                />
              ) : step === 7 ? (
                <ConfirmFlightDetails
                  trans={home}
                  rideOptions={rideOptions!}
                  locale={locale}
                  data={{
                    routePoints: routePoints,
                    time: formDetails.time,
                    date: formDetails.date,
                    distance: `${new Intl.NumberFormat(locale, {style: "unit", unit: "mile", unitDisplay: "short", maximumFractionDigits: 2}).format(rideOptions?.distance_miles ?? 0)} / ${new Intl.NumberFormat(locale, {style: "unit", unit: "kilometer", unitDisplay: "short", maximumFractionDigits: 2}).format((rideOptions?.distance_meters ?? 0) / 1000)}`,
                    largeSuitcase: formDetails.largeSuitcase,
                    smallSuitcase: formDetails.smallSuitcase,
                    adults: formDetails.adults,
                    children: formDetails.children,
                    infants: formDetails.infants,
                    numberOfPassengers: formDetails.numberOfPassengers,
                    passengerDetails,
                    childInfantTravel,
                    flightDetails,
                    additionalRequirements,
                    carName: SelectedCar
                      ? localizedVehicleValue(SelectedCar, "name", locale)
                      : "",
                      carImage: SelectedCar ? SelectedCar.icon_url : "",
                    cartype: SelectedCar?.id,
                    cost: SelectedCar ? SelectedCar.base_trip_cost : undefined,
                    transfer_fare: SelectedCar?.transfer_fare,
                    min_adjustment: SelectedCar?.min_adjustment,
                    airport_vat: SelectedCar
                      ? SelectedCar.airport_vat
                      : undefined,
                    airport_access_fee: SelectedCar?.airport_access_fee,
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
                  setPaymentTotal={setPaymentTotal}
                  editDatelis={() => setStep(1)}
                />
              ) : step === 8 ? (
                <>
                  <PaymentDsetails
                    policy_and_terms={policy_and_terms}
                    clientSecret={clientSecret}
                    bookingTotal={paymentTotal ?? SelectedCar?.total_cost ?? 0}
                    currency="GBP"
                    trans={home.Payments_details}
                    nextStep={() => setStep(9)}
                    prevStep={() => setStep(7)}
                    locale={locale}
                  /></>
              ) : step === 9 ? (
                <div className="flex items-center justify-center ">
                  <BookingConfirmation trans={home.Booking_Confirmation} locale={locale} />
                </div>
              ) : null}
            </section>{" "}
          </div>
        </div>
      )}
      {step === 10 && (
        <Auth locale={locale} trans={auth} setStep={() => setStep(7)} isBookingFlow={true} />
      )}
    </div>
  );
}

