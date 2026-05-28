"use client";

import { Button } from "@/components/ui/button";
import { fetchData } from "@/lib/api/fetchData";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Locale } from "../../../../i18n.config";
import IsLoadig from "../ISloading";

import { BsEyeFill } from "react-icons/bs";
import Pagination from "../Pagination";

import { FaClock} from "react-icons/fa";

import { MdDone } from "react-icons/md";
import { formatDate } from "@/lib/FormatDate";
import TripDetails from "./TripDetails";

import dynamic from "next/dynamic";
const MapView = dynamic(() => import("../bookTaxi/MapView"), { ssr: false });



function getStatusColor(status: string) {
  switch (status) {
    case "cancelled":
      return "text-accent  ";
    case "pending":
      return "text-primary ";
    case "driver_on_the_way":
      return "text-[#00BCD4] ";
    case "completed":
      return "text-[#9E9E9E] ";
    case "active":
      return "text-[#2196F3] ";
    case "accepted":
      return "text-[#4CAF50] ";
    default:
      return "text-[#22C822]  ";
  }
}

function getNotesColor(notes: string) {
  return notes === "Read" ? "text-yellow-600 bg-yellow-50" : "text-gray-500";
}

export default function TripsDriver({
  token,
  locale,
  trans,
}: {
  token?: string;
  locale: Locale;
  trans: any;
}) {
  const [detailsTrips, setDetailsTrips] = useState<any>();
  const [page, setPage] = useState(1);
  const [openDetails, setOpenDetails] = useState(false);


  const { data: AllTrips, isLoading: AllTripsLodaing } = useQuery<any>({
    queryKey: ["my Trips driver", page],
    queryFn: () =>
      fetchData({
        endpoint: "/api/trips/list-trips/",
        token: token,
        queryParams: {
          locale: locale,
          page_size: "6",
          page: page.toString(),
        },
      }),
  });
  const { data: statusTripe, isLoading: statusLoading } = useQuery<any>({
    queryKey: ["/api/drivers/trip-stats/"],
    queryFn: () =>
      fetchData({
        endpoint: "/api/drivers/trip-stats/",
        token: token,
        queryParams: {
          locale: locale,
        },
      }),
  });
console.log(statusTripe);

  return (
    <>
      <div>
        {!statusLoading && (
          <div className="grid lg:grid-cols-6 md:grid-cols-4 grid-cols-2 gap-4 ">
            <div className="bg-white rounded-lg shadow-lg p-4 space-y-3">
              <MdDone className="text-popover text-2xl" />
              <p>{trans.tripDetails.completedTrips}</p>
              <h3 className="text-2xl font-medium">{statusTripe.completed}</h3>
            </div>
            <div className="bg-white rounded-lg shadow-lg p-4 space-y-3">
              <FaClock className="text-primary text-2xl" />
              <p>{trans.tripDetails.pinnedTrips}</p>
              <h3 className="text-2xl font-medium">{statusTripe.pending}</h3>
            </div>
            <div className="bg-white rounded-lg shadow-lg p-4 space-y-3">
              <p className="text-accent text-2xl">X</p>
              <p>{trans.tripDetails.canceledTrips}</p>
              <h3 className="text-2xl font-medium">{statusTripe.cancelled}</h3>
            </div>
          </div>
        )}

        <div className="my-5">
          <div className="w-full bg-white rounded-lg shadow-sm border text-accent pt-5">
            {/* Desktop / tablet table */}
            <div className="hidden md:block">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 text-sm font-medium text-gray-300">
                      {trans.tableHeaders.map((trHeader: string) => (
                        <th key={trHeader} className="text-start py-4 px-4">
                          {trHeader}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {AllTripsLodaing ? (
                      <tr>
                        <td>
                          <IsLoadig />
                        </td>
                      </tr>
                    ) : (
                      AllTrips?.trips?.map((trip: any, index: any) => (
                        <tr
                          key={index}
                          className="border-b border-gray-100 hover:bg-gray-50 text-black"
                        >
                          <td className="py-4 px-4 font-medium">
                            {trip.passengerName || "-"}
                          </td>
                          <td className="py-4 px-4">{trip.id}</td>
                          <td className="py-4 px-4 text-wrap">
                            <div className="truncate">
                              {trip.pickup_str || "-"}
                            </div>
                            <div className="truncate">
                              {trip.dropoff_str || "-"}
                            </div>
                          </td>
                          <td className="py-4 px-4 text-sm">
                            <div>{formatDate(new Date(trip.trip_date), locale)}</div>
                            <div className="text-gray-500">
                              {trip.trip_time?.slice(0, 5)}
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            {(trip.distance_miles * 1.61).toFixed()} km
                          </td>
                          <td className="py-4 px-4 font-medium text-green-600">
                            £ {trip.cost}
                          </td>
                          <td className="py-4 px-4">
                            <span
                              className={`inline-flex items-center px-2.5  py-0.5 rounded-full font-bold  ${getStatusColor(
                                trip.status
                              )}`}
                            >
                              {
                                trans.status.find(
                                  (stat: { title: string; value: string }) =>
                                    trip.status === stat.value
                                )?.title
                              }
                            </span>
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex items-center space-x-2">
                              <Button
                                onClick={() => {
                                  setDetailsTrips(trip), setOpenDetails(true);
                                }}
                                variant="ghost"
                                className="p-0"
                              >
                                <BsEyeFill />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              {!AllTripsLodaing && (
                <div className="flex items-center justify-between px-6 border-t border-gray-200">
                  <div className="text-sm mx-auto text-gray-500">
                    {trans.tripDetails.table} {page} {trans.tripDetails.of}{" "}
                    {AllTrips?.num_pages} {trans.tripDetails.tables}
                  </div>

                  <Pagination
                    currentPage={page}
                    onPageChange={(pa) => setPage(pa)}
                    locale={locale}
                    totalPages={AllTrips?.num_pages}
                  />
                </div>
              )}
            </div>

            {/* Mobile cards */}
            <div className="md:hidden border-t border-gray-100 px-4 py-5 space-y-4">
              {AllTripsLodaing ? (
                <IsLoadig />
              ) : AllTrips?.trips?.length ? (
                AllTrips.trips.map((trip: any) => (
                  <div
                    key={trip.id}
                    className="rounded-2xl border border-gray-200 shadow-sm p-4 space-y-3"
                  >
                    <div className="flex items-start justify-between gap-3 border-b border-gray-100 pb-3">
                      <div>
                        <p className="text-xs text-gray-500 uppercase">
                          {trans.tableHeaders?.[1] || "Trip ID"}
                        </p>
                        <p className="text-lg font-semibold text-gray-900">#{trip.id}</p>
                      </div>
                      <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${getStatusColor(
                          trip.status
                        )}`}
                      >
                        {trans.status.find(
                          (stat: { title: string; value: string }) => trip.status === stat.value
                        )?.title || trip.status}
                      </span>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-gray-500">
                          {trans.tableHeaders?.[0]}
                        </span>
                        <span className="text-sm font-semibold text-gray-900 max-w-[60%] text-right">
                          {trip.passengerName || "-"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-gray-500">
                          {trans.tableHeaders?.[2]}
                        </span>
                        <span
                          className="text-sm font-semibold text-gray-900 max-w-[60%] text-right truncate"
                          title={trip.pickup_str}
                        >
                          {trip.pickup_str || "-"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-gray-500">
                          {trans.tripDetails?.dropoff || trans.tableHeaders?.[2]}
                        </span>
                        <span
                          className="text-sm font-semibold text-gray-900 max-w-[60%] text-right truncate"
                          title={trip.dropoff_str}
                        >
                          {trip.dropoff_str || "-"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-gray-500">
                          {trans.tableHeaders?.[3]}
                        </span>
                        <span className="text-sm font-semibold text-gray-900 text-right">
                          {formatDate(new Date(trip.trip_date), locale)}{" "}
                          {trip.trip_time?.slice(0, 5)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-gray-500">
                          {trans.tableHeaders?.[4]}
                        </span>
                        <span className="text-sm font-semibold text-gray-900">
                          {(trip.distance_miles * 1.61).toFixed()} km
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-gray-500">
                          {trans.tableHeaders?.[5]}
                        </span>
                        <span className="text-base font-bold text-green-600">
                          £ {trip.cost}
                        </span>
                      </div>
                    </div>

                    <Button
                      onClick={() => {
                        setDetailsTrips(trip);
                        setOpenDetails(true);
                      }}
                      className="w-full bg-yellow-500 hover:bg-yellow-600 text-black font-semibold"
                    >
                      <BsEyeFill className="mr-2" />
                      {trans.tripDetails?.viewDetails || trans.tripDetails?.tripDetails}
                    </Button>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 font-medium">
                  {trans.tripDetails?.noTrips || "No trips found"}
                </div>
              )}

              {!AllTripsLodaing && AllTrips?.trips?.length ? (
                <div className="pt-4 border-t border-gray-200">
                  <div className="text-center text-sm text-gray-500 mb-3">
                    {trans.tripDetails.table} {page} {trans.tripDetails.of}{" "}
                    {AllTrips?.num_pages} {trans.tripDetails.tables}
                  </div>
                  <Pagination
                    currentPage={page}
                    onPageChange={(pa) => setPage(pa)}
                    locale={locale}
                    totalPages={AllTrips?.num_pages}
                  />
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      {openDetails && (
        <div
          onClick={() => setOpenDetails(false)}
          className="fixed inset-0 bg-black/20 flex items-center justify-center z-50"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-foreground p-6 rounded-md w-full max-w-5xl shadow-xl max-h-screen overflow-y-auto on-scrollbar"
          >
            <h2 className="text-xl text-center font-bold mb-4 text-primary">
              {trans.tripDetails.tripDetails}
            </h2>

            <div className=" flex max-md:flex-col  gap-4 h-[630px]  max-h-[90vh] overflow-y-auto">
        
              <div className="md:w-1/2 overflow-y-auto on-scrollbar">
                <TripDetails detailsTrips={detailsTrips} trans={trans} locale={locale}/>
              </div>

              <div className="md:w-1/2 w-full min-h-[300px] max-md:max-h-[400px] rounded overflow-hidden">
                <MapView routePolyline={detailsTrips.route_polyline} />
              </div>
            </div>

            <div className="flex items-center justify-center gap-5 mt-5 w-full">
              <div className="w-full">
                <Button
                  variant={"secondary"}
                  className="w-full text-lg p-5"
                  onClick={() => setOpenDetails(false)}
                >
                  {trans.tripDetails.back}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      
    </>
  );
}
