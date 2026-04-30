"use client";
import React, { useState } from "react";
import { Locale } from "../../../../i18n.config";
import TripComplaintsCard from "./TripsComplaintCard";
import { useQuery } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import IsLoadig from "../ISloading";
import Pagination from "../Pagination";

export default function TripComplaints({
  token,
  locale,
  trans,
}: {
  token?: string;
  locale: Locale;
  trans: any;
}) {
  const [page, setPage] = useState(1);

  const { data: tripsComplaints, isLoading: tripsComplaintsLodaing } =
    useQuery<any>({
      queryKey: ["Trips Complaints", page],
      queryFn: () =>
        fetchData({
          endpoint: "/api/admin-panel/trip-complaints/",
          token: token,
          queryParams: {
            locale: locale,
            page_size: "12",
            page: page.toString(),
          },
        }),
    });

  return (
    <div>
      {tripsComplaintsLodaing ? (
        <IsLoadig />
      ) : (
        <div className="grid grid-cols-3 gap-5">
          {tripsComplaints.complaints.map((complaint: any) => (
            <div>
              <TripComplaintsCard trans={trans} complaint={complaint} />
            </div>
          ))}
        </div>
      )}

            {!tripsComplaintsLodaing && (
              <div className="flex items-center justify-between px-6 border-t border-gray-200">
                <div className="text-sm mx-auto text-gray-500">
                  {trans.pagination.table} {page} {trans.pagination.of}{" "}
                  {tripsComplaints.num_pages} {trans.pagination.tables}
                </div>

                <Pagination
                  currentPage={page}
                  onPageChange={(pa) => setPage(pa)}
                  locale={locale}
                  totalPages={tripsComplaints.num_pages}
                />
              </div>
            )}
    </div>
  );
}
