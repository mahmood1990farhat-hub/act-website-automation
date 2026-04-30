"use client";

import React, { useEffect, useState } from "react";
import MyTripsCard from "../MyTripsCard";
import { useQuery } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import { Locale } from "../../../../../i18n.config";
import IsLoading from "../../ISloading";
import Pagination from "../../Pagination";
import { FaList, FaClock } from "react-icons/fa";

type typeProps = {
  trans: any;
  token?: string;
  locale: Locale;
};
export default function TripsPassenger({ trans, token, locale }: typeProps) {
  const [typeTrips, setTypeTrips] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    window.scroll(0, 0);
  }, [page]);

  const { data: AllTrips, isLoading: AllTripsLodaing } = useQuery<any>({
    queryKey: ["myTrips", typeTrips, page],
    queryFn: () =>
      fetchData({
        endpoint: "/api/trips/list-trips/",
        token: token,
        queryParams: {
          page: page.toString(),
          page_size: "5",
          locale: locale,
          ...(typeTrips && { trip_status: typeTrips }),
        },
      }),
  });

  const { data: latest, isLoading: latestLodaing } = useQuery<[any]>({
    queryKey: ["Latest"],
    queryFn: () =>
      fetchData({
        endpoint: "/api/trips/latest-trips/",
        token: token,
        queryParams: {},
      }),
  });

  return (
    <div className="w-full">
      {/* Main Grid Container */}
      <div className="grid xl:grid-cols-[1fr_400px] lg:grid-cols-2 grid-cols-1 gap-6 lg:gap-8">
        
        {/* Left Section - All Trips */}
        <div className="w-full">
          {/* Section Header */}
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-primary/20 p-2.5 rounded-lg">
              <FaList className="text-primary text-lg" />
            </div>
            <h1 className="font-bold text-xl md:text-2xl text-white">
              {trans.section_1.title}
            </h1>
          </div>

          {/* Filter Tabs */}
          <div className="bg-foreground/50 backdrop-blur-sm rounded-xl p-2 mb-6 border border-muted/10">
            <div className="flex items-center justify-start gap-2 flex-wrap">
              {trans.section_1.tpes.map((it: { title: string; value: string }) => (
                <button
                  key={it.value}
                  onClick={() => {
                    setTypeTrips(it.value);
                    setPage(1);
                  }}
                  className={`
                    px-3 py-2 rounded-lg text-sm md:text-base font-semibold
                    transition-all duration-300 ease-in-out
                    ${
                      it.value === typeTrips
                        ? "bg-primary text-black shadow-lg shadow-primary/30 scale-105"
                        : "bg-transparent text-gray-300 hover:bg-muted/20 hover:text-white"
                    }
                  `}
                >
                  {it.title}
                </button>
              ))}
            </div>
          </div>

          {/* Content Area */}
          {AllTripsLodaing ? (
            <div className="flex items-center justify-center py-20">
              <IsLoading />
            </div>
          ) : (
            <div className="space-y-5">
              {/* Trips Count Badge */}
              <div className="flex items-center gap-3 bg-foreground/30 backdrop-blur-sm rounded-lg p-4 border border-muted/10">
                <span className="text-gray-300 text-sm md:text-base font-medium">
                  {trans.tripsCount}
                </span>
                <span className="bg-primary text-black font-bold text-sm md:text-base py-1.5 px-4 rounded-lg shadow-md">
                  {AllTrips?.count || 0}
                </span>
              </div>

              {/* Trips List */}
              {AllTrips?.trips && AllTrips.trips.length > 0 ? (
                <div className="space-y-4">
                  {AllTrips.trips.map((item: any) => (
                    <MyTripsCard
                      locale={locale}
                      key={item.id}
                      data={item}
                      token={token}
                      trans={trans.deleteTrip}
                      tripCardTrans={trans.tripCard}
                    />
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 px-4 bg-foreground/20 rounded-xl border border-muted/10">
                  <div className="bg-primary/10 p-6 rounded-full mb-4">
                    <FaList className="text-primary text-4xl" />
                  </div>
                  <p className="text-gray-200 text-center text-lg font-semibold">
                    {trans.noTrips?.title || "No trips found"}
                  </p>
                  <p className="text-gray-400 text-center text-sm mt-2">
                    {typeTrips 
                      ? (trans.noTrips?.tryDifferentFilter || "Try selecting a different filter")
                      : (trans.noTrips?.willAppearHere || "Your trips will appear here")}
                  </p>
                </div>
              )}

              {/* Pagination */}
              {AllTrips?.num_pages > 1 && (
                <div className="mt-8">
                  <Pagination
                    currentPage={page}
                    onPageChange={(pag) => setPage(pag)}
                    totalPages={AllTrips.num_pages}
                    locale={locale}
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Section - Latest Trips */}
        <div className="w-full">
          {/* Section Header */}
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-accent/20 p-2.5 rounded-lg">
              <FaClock className=" text-lg" />
            </div>
            <h1 className="font-bold text-xl md:text-2xl text-white">
              {trans.section_2.title}
            </h1>
          </div>

          {/* Description Card */}
          <div className="bg-gradient-to-br from-accent/10 to-accent/5 backdrop-blur-sm rounded-xl p-5 mb-6 border border-accent/20">
            <p className="text-gray-300 text-sm md:text-base leading-relaxed">
              {trans.section_2.desc}
            </p>
          </div>

          {/* Latest Trips Content */}
          {latestLodaing ? (
            <div className="flex items-center justify-center py-12">
              <IsLoading />
            </div>
          ) : (
            <div className="space-y-5">
              {/* Latest Count Badge */}
              <div className="flex items-center gap-3 bg-foreground/30 backdrop-blur-sm rounded-lg p-4 border border-muted/10">
                <span className="text-gray-300 text-sm md:text-base font-medium">
                  {trans.tripsCount}
                </span>
                <span className="bg-primary text-black font-bold text-sm md:text-base py-1.5 px-4 rounded-lg shadow-md">
                  {latest?.length || 0}
                </span>
              </div>

              {/* Latest Trips List */}
              {latest && latest.length > 0 ? (
                <div className="space-y-4">
                  {latest.map((item: any) => (
                    <MyTripsCard
                      locale={locale}
                      key={item.id}
                      data={item}
                      token={token}
                      trans={trans.deleteTrip}
                      tripCardTrans={trans.tripCard}
                    />
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 px-4 bg-foreground/20 rounded-xl border border-muted/10">
                  <div className="bg-accent/10 p-6 rounded-full mb-4">
                    <FaClock className=" text-4xl" />
                  </div>
                  <p className="text-gray-200 text-center text-lg font-semibold">
                    {trans.noRecentTrips?.title || "No recent trips"}
                  </p>
                  <p className="text-gray-400 text-center text-sm mt-2">
                    {trans.noRecentTrips?.desc || "Trips from the last 24 hours will appear here"}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
