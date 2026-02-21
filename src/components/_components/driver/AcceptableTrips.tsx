"use client";
import React, { useState } from "react";
import { Locale } from "../../../../i18n.config";
import { useQuery } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import TripDetails from "./TripDetails";
import IsLoadig from "../ISloading";
import Pagination from "../Pagination";

export default function AcceptableTrips({
  token,
  locale,
  trans,
}: {
  token?: string;
  locale: Locale;
  trans: any;
}) {
  const [page, setPage] = useState(1);
  const { data: upcomingData, isLoading: upcomingLoading } = useQuery<any>({
    queryKey: ["accep", page],
    queryFn: () =>
      fetchData({
        endpoint: "/api/trips/list-trips/",
        token: token,
        queryParams: {
          locale: locale,
          trip_status: "accepted",
          page_size: "6",
          page: page.toString(),
        },
      }),
  });
  return (
    <div className="">
      <h1 className="text-2xl font-bold my-5">{trans.upcomingTrips.title}</h1>
      <div className=" ">
        {upcomingLoading ? (
          <IsLoadig />
        ) : (
          <div>
            <div className=" grid lg:grid-cols-2 grid-cols-1 gap-5">
              {upcomingData.trips.length > 0 ? (
                upcomingData.trips.map((item: any) => (
                  <div className="" key={item.id}>
                    <TripDetails
                      tripState="accpted"
                      detailsTrips={item}
                      trans={trans}
                      token={token}
                      locale={locale}
                    />
                  </div>
                ))
              ) : (
                <div className="flex items-center justify-center  flex-col h-[40vh]">
                  <h1 className="text-2xl font-bold">{trans.noTrips.title}</h1>
                  <p className="text-lg font-medium my-2">
                    {trans.noTrips.desc}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {!upcomingLoading && upcomingData.num_pages > 1 && (
        <Pagination
          currentPage={page}
          onPageChange={(pa) => setPage(pa)}
          locale={locale}
          totalPages={upcomingData.num_pages}
        />
      )}
    </div>
  );
}
