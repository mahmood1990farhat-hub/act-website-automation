"use client";
import React, { useState } from "react";
import { Locale } from "../../../../i18n.config";
import { useQuery } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import TripDetails from "./TripDetails";
import IsLoadig from "../ISloading";
import Pagination from "../Pagination";

export default function NewRequests({
  token,
  locale,
  trans,
}: {
  token?: string;
  locale: Locale;
  trans: any;
}) {
  const [page, setPage] = useState(1);
  const { data: newRequestsData, isLoading: newRequestsLoading } =
    useQuery<any>({
      queryKey: ["NewRequests", page],
      queryFn: () =>
        fetchData({
          endpoint: "/api/trips/new-trip-requests/",
          token: token,
          queryParams: {
            locale: locale,

            page_size: "6",
            page: page.toString(),
          },
        }),
    });

  return (
    <div className="">
      <h1 className="text-2xl font-bold">{trans.newRequests.title}</h1>
      <div className=" ">
        {newRequestsLoading ? (
          <IsLoadig />
        ) : (
          <div>
            <p className="flex items-center justify-between text-primary bg-foreground p-3 font-bold rounded-lg my-5">
              {trans.newRequests.TripsAwaitingApproval}{" "}
              <span className=" bg-primary text-foreground p-1 px-2.5   rounded-full ">
                {newRequestsData.count}
              </span>
            </p>
            {newRequestsData.trips.length>0 ?     <div className=" grid lg:grid-cols-2 grid-cols-1 gap-5">
              { newRequestsData.trips.map((item: any) => (
                <div className="">
                  <TripDetails
                    tripState="newRequests"
                    detailsTrips={item}
                    token={token}
                    trans={trans}
                    locale={locale}
                  />
                </div>
              ))}
            </div> :     <div className="flex items-center justify-center  flex-col h-[40vh]">
          <h1 className="text-2xl font-bold">{trans.noNewRequest.title}</h1>
          <p className="text-lg font-medium my-2">{trans.noNewRequest.desc}</p>
        </div>

            }
       
          </div>
        )}
      </div>

      {!newRequestsLoading && newRequestsData.trips.length > 0 && (
        <Pagination
          currentPage={page}
          onPageChange={(pa) => setPage(pa)}
          locale={locale}
          totalPages={newRequestsData.num_pages}
        />
      )}
    </div>
  );
}
