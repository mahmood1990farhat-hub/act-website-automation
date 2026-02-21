"use client";
import React from "react";
import { Locale } from "../../../../i18n.config";
import { useQuery } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import IsLoadig from "../ISloading";
import MapView from "../bookTaxi/MapView";
import TripDetails from "./TripDetails";

export default function MonitorTrip({
  token,
  locale,
  trans,
  trip,
}: {
  token?: string;
  locale: Locale;
  trans: any;
  trip?: string;
}) {
  const { data: MonitorTripData, isLoading: MonitorTripLoading } =
    useQuery<any>({
      queryKey: ["MonitorTrip"],
      queryFn: () =>
        fetchData({
          endpoint: "/api/trips/list-trips/",
          token: token,
          queryParams: {
            locale: locale,
            trip_status: "active",
          },
        }),
    });

  return (
    <div className="">
      <h1 className="text-2xl font-bold my-5">{trans.monitorTrip.title}</h1>
      {MonitorTripLoading ? (
        <IsLoadig />
      ) : MonitorTripData.trips.length > 0 ? (
        <div className="grid grid-cols-2 gap-3">
          <div className="">
            <TripDetails
              tripState="active"
              detailsTrips={MonitorTripData.trips[0]}
              token={token}
              trans={trans}
              locale={locale}
            />
          </div>
          <MapView routePolyline={MonitorTripData.trips[0].route_polyline} />
        </div>
      ) : (
        <div className="flex items-center justify-center  flex-col h-[40vh]">
          <h1 className="text-2xl font-bold">{trans.noTrips.title}</h1>
          <p className="text-lg font-medium my-2">{trans.noTrips.desc}</p>
        </div>
      )}
    </div>
  );
}
