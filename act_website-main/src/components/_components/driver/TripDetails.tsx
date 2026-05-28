"use client";
import { formatDate } from "@/lib/FormatDate";
import { Calendar, Clock, User } from "lucide-react";
import React, { useState } from "react";
import { Locale } from "../../../../i18n.config";
import { Button } from "@/components/ui/button";
import { postData } from "@/lib/api/postData";
import { useRouter } from "next/navigation";
import GlobalModalDriver from "../GlobalModalDriver";

type typeProps = {
  trans: any;
  locale: Locale;
  detailsTrips: any;
  token?: string;
  tripState?: string;
  variant?: "light" | "dashboard";
};

export default function TripDetails({
  trans,
  locale,
  detailsTrips,
  token,
  tripState,
  variant = "light",
}: typeProps) {
  const [modalbtuMoveToPickup, setModalbtuMoveToPickup] = useState(false);

  const [modalStraTrip, setModalStraTrip] = useState(false);
  const [modalEndTrip, setModalEndTrip] = useState(false);

  const router = useRouter();

  const AcceptTrip = async () => {
    try {
      const res = await postData({
        endpoint: `/api/trips/${detailsTrips.id}/accept/`,
        token: token,
      });
    } catch (err) {
      console.log(err);
    }
  };

  const DriverOnTheWay = async () => {
    try {
      const res = await postData({
        endpoint: `/api/trips/${detailsTrips.id}/driver-on-the-way/`,
        token: token,
      });
      router.push(`/${locale}/driver/upcoming-trips`);
    } catch (err) {
      console.log(err);
    }
  };
  const StartedTrip = async () => {
    try {
      const res = await postData({
        endpoint: `/api/trips/${detailsTrips.id}/start/`,
        token: token,
      });
      router.push(`/${locale}/driver/upcoming-trips`);
    } catch (err) {
      console.log(err);
    }
  };

  const EndTrip = async () => {
    try {
      const res = await postData({
        endpoint: `/api/trips/${detailsTrips.id}/complete/`,
        token: token,
      });
      router.push(`/${locale}/driver/upcoming-trips`);
    } catch (err) {
      console.log(err);
    }
  };

  return (
    <>
      <div className={`${variant === "dashboard" ? "bg-card border-2 border-border text-foreground" : "bg-white text-gray-900"} shadow-lg rounded-lg p-6 space-y-3 overflow-y-auto on-scrollbar`}>
        {tripState !== "newRequests" && tripState && detailsTrips?.passenger_info && (
          <div className="flex flex-col items-center">
            <div className="w-16 h-16 bg-gray-900 rounded-full flex items-center justify-center mb-3">
              <User className="w-8 h-8 text-yellow-400" />
            </div>
            <h2 className="text-lg font-medium text-gray-900">
              {detailsTrips.passenger_info.full_name ||
                detailsTrips.passenger_info.first_name}
            </h2>
          </div>
        )}

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {trans.tripDetails.id}: {detailsTrips.id}
            </h1>
            <p className="text-sm text-gray-500">
              {formatDate(new Date(detailsTrips.created_at), locale)}
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className={`flex justify-between items-center max-md:flex-col w-full border-b ${variant === "dashboard" ? "border-border" : "border-gray-200"}`}>
            <span className={`${variant === "dashboard" ? "text-muted-foreground" : "text-gray-500"} w-full`}>
              {trans.tripDetails.pickupLocation}
            </span>
            <b className={`${variant === "dashboard" ? "text-foreground" : "text-gray-900"} font-medium md:w-1/2 text-end`}>
              {detailsTrips.pickup_str || "-"}
            </b>
          </div>

          <div className={`flex justify-between items-center max-md:flex-col border-b ${variant === "dashboard" ? "border-border" : "border-gray-200"}`}>
            <span className={`${variant === "dashboard" ? "text-muted-foreground" : "text-gray-500"} w-full`}>
              {trans.tripDetails.dropoffLocation}
            </span>
            <b className={`${variant === "dashboard" ? "text-foreground" : "text-gray-900"} font-medium md:w-1/2   text-end`}>
              {detailsTrips.dropoff_str || "-"}
            </b>
          </div>

          <div className={`flex justify-between items-center border-b ${variant === "dashboard" ? "border-border" : "border-gray-200"}`}>
            <span className={`${variant === "dashboard" ? "text-muted-foreground" : "text-gray-500"}`}>
              {trans.tripDetails.passengerCount}
            </span>
            <b className={`${variant === "dashboard" ? "text-foreground" : "text-gray-900"} font-medium`}>
              {detailsTrips.passengers_count || "0"}
            </b>
          </div>

          <div className={`flex justify-between items-center border-b ${variant === "dashboard" ? "border-border" : "border-gray-200"}`}>
            <span className={`${variant === "dashboard" ? "text-muted-foreground" : "text-gray-500"}`}>
              {trans.tripDetails.largeBagsCount}
            </span>
            <b className={`${variant === "dashboard" ? "text-foreground" : "text-gray-900"} font-medium`}>
              {detailsTrips.large_suitcase || "0"}
            </b>
          </div>

          <div className={`flex justify-between items-center border-b ${variant === "dashboard" ? "border-border" : "border-gray-200"}`}>
            <span className={`${variant === "dashboard" ? "text-muted-foreground" : "text-gray-500"}`}>
              {trans.tripDetails.smallBagsCount}
            </span>
            <b className={`${variant === "dashboard" ? "text-foreground" : "text-gray-900"} font-medium`}>
              {detailsTrips.small_suitcase || "0"}
            </b>
          </div>

          <div className={`flex justify-between items-center border-b ${variant === "dashboard" ? "border-border" : "border-gray-200"}`}>
            <span className={`${variant === "dashboard" ? "text-muted-foreground" : "text-gray-500"}`}>{trans.tripDetails.carType}</span>
            <span className={`${variant === "dashboard" ? "text-yellow-500" : "text-primary"} font-medium`}>
              {detailsTrips.car_type || "0"}
            </span>
          </div>
        </div>

        <div className={`${variant === "dashboard" ? "bg-muted border-2 border-yellow-500/50" : "bg-gray-200"} p-3 rounded`}>
          <div className="flex items-center justify-between">
            <span className={`font-semibold ${variant === "dashboard" ? "text-foreground" : "text-gray-900"}`}>{trans.tripDetails.calendar}</span>
          </div>
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="flex items-center justify-between bg-card rounded-lg border border-border px-3 py-2">
              <div className="flex items-center gap-2">
                <Calendar className={`w-4 h-4 ${variant === "dashboard" ? "text-yellow-500" : ""}`} />
                <span className={`text-sm ${variant === "dashboard" ? "text-muted-foreground" : "text-gray-700"}`}>{trans.tripDetails.date}</span>
              </div>
              <div className={`${variant === "dashboard" ? "bg-background text-foreground" : "bg-foreground text-primary"} px-3 py-1 font-bold rounded text-sm`}>
                {formatDate(new Date(detailsTrips.trip_date), locale)}
              </div>
            </div>
            <div className="flex items-center justify-between bg-card rounded-lg border border-border px-3 py-2">
              <div className="flex items-center gap-2">
                <Clock className={`w-4 h-4 ${variant === "dashboard" ? "text-yellow-500" : ""}`} />
                <span className={`text-sm ${variant === "dashboard" ? "text-muted-foreground" : "text-gray-700"}`}>{trans.tripDetails.time}</span>
              </div>
              <div className={`${variant === "dashboard" ? "bg-background text-foreground" : "bg-foreground text-primary"} px-3 py-1 font-bold rounded text-sm`}>
                {detailsTrips.trip_time?.slice(0, 5)}
              </div>
            </div>
          </div>
        </div>

        <div>
          <p className={`${variant === "dashboard" ? "text-muted-foreground" : "text-gray-500"} mb-1`}>{trans.tripDetails.totalCost}</p>
          <p className={`text-3xl font-bold ${variant === "dashboard" ? "text-yellow-600" : "text-popover"}`}>
            £ {detailsTrips.cost}
          </p>
        </div>
        {tripState === "newRequests" && (
          <Button onClick={AcceptTrip} className="w-full text-lg">
            {trans.tripDetails.btuAccept}
          </Button>
        )}
        {tripState === "accpted" && (
          <Button
            onClick={() => setModalbtuMoveToPickup(true)}
            className="w-full text-lg"
          >
            {trans.tripDetails.btuMoveToPicku}
          </Button>
        )}
        {tripState === "upcoming" && (
          <div className="flex items-center gap-5">
            <div className="w-full text-lg">
              <button className="w-full text-lg text-white bg-foreground p-1 font-medium rounded-lg">
                {trans.tripDetails.btuContact}
              </button>
            </div>

            <div className="w-full text-lg">
              <Button
                className="w-full text-lg"
                onClick={() => setModalStraTrip(true)}
              >
                {trans.tripDetails.btuStartTrip}
              </Button>
            </div>
          </div>
        )}
        {tripState === "active" && (
          <div className="flex items-center gap-5">
            <div className="w-full text-lg">
              <button className="w-full text-lg text-white bg-foreground p-1 font-medium rounded-lg">
                {trans.tripDetails.btuContact}
              </button>
            </div>

            <div className="w-full text-lg">
              <Button
                className="w-full text-lg"
                onClick={() => setModalEndTrip(true)}
              >
                {trans.tripDetails.btuEndTrip}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* modal Move To Pickup */}

      <GlobalModalDriver
        isOpen={modalbtuMoveToPickup}
        onClose={() => setModalbtuMoveToPickup(false)}
      >
        <h1 className="font-bold text-lg">
          {" "}
          {trans.tripDetails.modal.moveToPickup.title}
        </h1>
        <p className="text-gray-500">
          {trans.tripDetails.modal.moveToPickup.decs_1}{" "}
          <span className="text-black font-bold">{detailsTrips.id}</span>
          {trans.tripDetails.modal.moveToPickup.decs_2}
        </p>
        <div className="flex items-center gap-5">
          <div className="w-full ">
            <button
              onClick={() => setModalbtuMoveToPickup(false)}
              className="w-full text-lg text-white bg-foreground p-1.5 font-medium rounded-lg"
            >
              {trans.tripDetails.modal.moveToPickup.btuCancel}
            </button>
          </div>
          <div className="w-full g">
            <Button className="w-full text-lg p-5" onClick={DriverOnTheWay}>
              {trans.tripDetails.modal.moveToPickup.btuStartTrip}
            </Button>
          </div>
        </div>
      </GlobalModalDriver>

      {/* modal started trip */}
      <GlobalModalDriver
        isOpen={modalStraTrip}
        onClose={() => setModalStraTrip(false)}
      >
        <h1 className="font-bold text-lg">
          {trans.tripDetails.modal.startTrip.title}
        </h1>
        <p className="text-gray-500">{trans.tripDetails.modal.startTrip.decs}</p>
        <div className="flex items-center gap-5">
          <div className="w-full ">
            <button
              onClick={() => setModalStraTrip(false)}
              className="w-full text-lg text-white bg-foreground p-1.5 font-medium rounded-lg"
            >
              {trans.tripDetails.modal.startTrip.btuCancel}
            </button>
          </div>
          <div className="w-full g">
            <Button className="w-full text-lg p-5" onClick={StartedTrip}>
              {trans.tripDetails.btuStartTrip}
            </Button>
          </div>
        </div>
      </GlobalModalDriver>

      {/* modal end trip */}
      <GlobalModalDriver
        isOpen={modalEndTrip}
        onClose={() => setModalEndTrip(false)}
      >
        <h1 className="font-bold text-lg">
          {trans.tripDetails.modal.endTrip.title}
        </h1>
        <p className="text-gray-500">{trans.tripDetails.modal.endTrip.desc}</p>
        <div className="flex items-center gap-5">
          <div className="w-full ">
            <button
              onClick={() => setModalEndTrip(false)}
              className="w-full text-lg text-white bg-foreground p-1.5 font-medium rounded-lg"
            >
              {trans.tripDetails.modal.endTrip.btuCancel}
            </button>
          </div>
          <div className="w-full g">
            <Button className="w-full text-lg p-5" onClick={EndTrip}>
              {trans.tripDetails.btuEndTrip}
            </Button>
          </div>
        </div>
      </GlobalModalDriver>
    </>
  );
}
