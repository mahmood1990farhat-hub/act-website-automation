"use client";

import React, { useState } from "react";
import { Locale } from "../../../../i18n.config";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import { postData } from "@/lib/api/postData";
import IsLoading from "../ISloading";
import Pagination from "../Pagination";
import { FaDownload, FaEdit, FaExclamationTriangle } from "react-icons/fa";
import GlobalModal from "../GlobalModal";
import { Button } from "@/components/ui/button";
import { HiOutlineEye, HiOutlineX, HiOutlineReply } from "react-icons/hi";
import { useForm } from "react-hook-form";
import { toast } from "react-toastify";
import { extract_error } from "@/lib/api/errorApi";

export default function Complaints({
  token,
  locale,
  trans,
}: {
  token?: string;
  locale: Locale;
  trans: any;
}) {
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  const [selectedComplaint, setSelectedComplaint] = useState<any>(null);
  const [showUpdateStatusModal, setShowUpdateStatusModal] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const queryClient = useQueryClient();

  const {
    data: complaintsData,
    isLoading: complaintsLoading,
  } = useQuery<any>({
    queryKey: ["admin-complaints", page, filterStatus, filterType],
    queryFn: () =>
      fetchData({
        endpoint: "/api/admin-panel/trip-complaints/",
        token,
        queryParams: {
          page: page.toString(),
          page_size: "10",
          ...(filterStatus && { status: filterStatus }),
          ...(filterType && { complaint_type: filterType }),
        },
      }),
  });

  // Support both { data: { ... } } and plain payload shapes
  const payload = complaintsData?.data || complaintsData || {};
  const complaints = payload.complaints || [];
  const stats = payload.stats || {};
  const pagination = payload.pagination || {};

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
        return "bg-yellow-50 text-yellow-700 border-yellow-200";
      case "under_review":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "resolved":
        return "bg-green-50 text-green-700 border-green-200";
      case "closed":
        return "bg-gray-100 text-gray-700 border-gray-200";
      default:
        return "bg-gray-100 text-gray-700 border-gray-200";
    }
  };

  const handleUpdateStatus = async (data: { admin_response: string; status: string }) => {
    if (!selectedComplaint) return;
    
    setActionLoading(true);
    try {
      await postData({
        endpoint: `/api/admin-panel/trip-complaints/${selectedComplaint.id}/respond/`,
        token,
        body: {
          admin_response: data.admin_response,
          status: data.status,
        },
        noToast: false, // Let API show toast
      });
      
      // Refresh complaints list
      queryClient.invalidateQueries({ queryKey: ["admin-complaints"] });
      setShowUpdateStatusModal(false);
      setSelectedComplaint(null);
    } catch (error: any) {
      // Error toast is handled by postData
      console.error("Error updating complaint status:", error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDownload = async (id: number) => {
    try {
      const base =
        process.env.NEXT_PUBLIC_API_BASE_URL || window.location.origin;
      const url = `${base}/api/admin-panel/trip-complaints/${id}/download-pdf/`;

      const response = await fetch(url, {
        method: "GET",
        headers: token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : undefined,
      });

      if (!response.ok) {
        throw new Error("Failed to download PDF");
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `complaint-report-${id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err: any) {
      console.error(err);
      const errorMessage = extract_error(err) || err?.message || "Failed to download PDF";
      toast.error(errorMessage);
    }
  };

  return (
    <div className="w-full">
      {/* Stats + Filters */}
      <div className="mb-6 space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {Object.entries(stats).map(([key, value]: [string, any]) => (
            <div
              key={key}
              className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm"
            >
              <p className="text-gray-500 text-xs mb-1">
                {trans.stats?.[key] ?? key}
              </p>
              <p className="text-gray-900 text-xl font-bold">{value}</p>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Status Filter */}
            <div>
              <label className="block mb-2 text-[16px] text-gray-800">
                {trans.complaint_list.filter.status_label}
              </label>
              <select
                value={filterStatus}
                onChange={(e) => {
                  setFilterStatus(e.target.value);
                  setPage(1);
                }}
                className="w-full p-3 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="">{trans.complaint_list.filter.all}</option>
                {Object.keys(trans.statuses).map((status) => (
                  <option key={status} value={status}>
                    {trans.statuses[status]}
                  </option>
                ))}
              </select>
            </div>

            {/* Type Filter */}
            <div>
              <label className="block mb-2 text-[16px] text-gray-800">
                {trans.complaint_list.filter.type_label}
              </label>
              <select
                value={filterType}
                onChange={(e) => {
                  setFilterType(e.target.value);
                  setPage(1);
                }}
                className="w-full p-3 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="">{trans.complaint_list.filter.all}</option>
                {Object.keys(trans.complaint_types).map((type) => (
                  <option key={type} value={type}>
                    {trans.complaint_types[type]}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Complaints List */}
      {complaintsLoading ? (
        <div className="flex items-center justify-center py-20">
          <IsLoading />
        </div>
      ) : complaints.length === 0 ? (
        <div className="bg-white rounded-xl p-12 border border-gray-200 text-center shadow-sm">
          <FaExclamationTriangle className="text-gray-400 text-5xl mx-auto mb-4" />
          <p className="text-gray-500 text-lg">
            {trans.complaint_list.empty}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {complaints.map((complaint: any) => (
            <div
              key={complaint.id}
              className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-200"
            >
              <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3 flex-wrap">
                    <span
                      className={`px-3 py-1 rounded-lg text-xs font-semibold border ${getStatusColor(
                        complaint.status
                      )}`}
                    >
                      {trans.statuses[complaint.status] ||
                        complaint.status_display}
                    </span>
                    <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-primary/10 text-primary border border-primary/30">
                      {trans.complaint_types[complaint.complaint_type] ||
                        complaint.complaint_type_display}
                    </span>
                    <span className="text-gray-500 text-sm">
                      {trans.complaint_card.complaint_id}: #{complaint.id}
                    </span>
                  </div>

                  <h3 className="text-gray-900 text-lg font-bold mb-2">
                    {complaint.title}
                  </h3>

                  <p className="text-gray-700 mb-3 line-clamp-2">
                    {complaint.description}
                  </p>

                  {/* Important Info */}
                  <div className="flex flex-wrap items-center gap-4 text-sm mb-3">
                    {complaint.complainant && (
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500 font-medium">
                          {trans.complaint_card.complainant || "Complainant"}:
                        </span>
                        <span className="text-gray-900 font-semibold">
                          {complaint.complainant.full_name}
                        </span>
                      </div>
                    )}
                    {complaint.trip_data?.passenger_info && (
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500 font-medium">
                          {trans.complaint_card.passenger || "Passenger"}:
                        </span>
                        <span className="text-gray-900 font-semibold">
                          {complaint.trip_data.passenger_info.first_name}{" "}
                          {complaint.trip_data.passenger_info.last_name}
                        </span>
                      </div>
                    )}
                    {complaint.trip_data?.driver_info && (
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500 font-medium">
                          {trans.complaint_card.driver || "Driver"}:
                        </span>
                        <span className="text-gray-900 font-semibold">
                          {complaint.trip_data.driver_info.first_name}{" "}
                          {complaint.trip_data.driver_info.last_name}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-sm">
                    {complaint.status === "resolved" ? (
                      <span className="text-green-600 font-semibold">
                        ✓ {trans.complaint_card.resolved}
                      </span>
                    ) : (
                      <span className="text-yellow-600 font-semibold">
                        ⏳ {trans.complaint_card.not_resolved}
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-sm text-gray-500 md:text-right min-w-[180px]">
                  {complaint.trip_data && (
                    <div className="mb-2">
                      <span className="block font-semibold text-gray-900 mb-1">
                        {trans.complaint_card.trip_date}
                      </span>
                      <span>{complaint.trip_data.trip_date}</span>
                    </div>
                  )}
                  <div>
                    <span className="block font-semibold text-gray-900 mb-1">
                      {trans.complaint_card.created_at}
                    </span>
                    <span>
                      {new Date(complaint.created_at).toLocaleDateString(
                        locale === "ar" ? "ar-EG" : "en-US"
                      )}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
                <Button
                  onClick={() => setSelectedComplaint(complaint)}
                  variant="outline"
                  className="w-full bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-foreground font-bold shadow-lg shadow-yellow-500/20"
                >
                  <HiOutlineEye className="w-4 h-4" />
                  <span>{trans.complaint_card.show_details || "Show Details"}</span>
                </Button>
                <Button
                  onClick={() => {
                    setSelectedComplaint(complaint);
                    setShowUpdateStatusModal(true);
                  }}
                  variant="secondary"
                  className="flex items-center gap-2"
                >
                  <FaEdit className="w-4 h-4" />
                  {trans.complaint_card.update_status || "Update Status"}
                </Button>
                <Button
                  onClick={() => handleDownload(complaint.id)}
                  className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-xs font-semibold transition-colors"
                >
                  <FaDownload />
                  <span>{trans.complaint_card.downloadPdf || "Download PDF"}</span>
                </Button>
              </div>

              {complaint.admin_response && (
                <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                  <p className="text-gray-500 text-sm mb-1">
                    {trans.complaint_card.admin_response}:
                  </p>
                  <p className="text-gray-900">{complaint.admin_response}</p>
                </div>
              )}

              {complaint.status === "resolved" && (
                <div className="mt-2 text-sm">
                  <span className="text-gray-500">
                    {trans.complaint_card.resolved_at}:{" "}
                  </span>
                  <span className="text-green-600">
                    {new Date(complaint.resolved_at).toLocaleDateString(
                      locale === "ar" ? "ar-EG" : "en-US"
                    )}
                  </span>
                </div>
              )}
            </div>
          ))}

          {/* Pagination */}
          {pagination.num_pages > 1 && (
            <div className="mt-6">
              <Pagination
                currentPage={page}
                totalPages={pagination.num_pages}
                onPageChange={setPage}
                locale={locale}
              />
            </div>
          )}
        </div>
      )}

      {/* Details Modal - Driver Onboarding Pattern */}
      {selectedComplaint && !showUpdateStatusModal && (
        <div
          onClick={() => setSelectedComplaint(null)}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-3 lg:p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-card rounded-2xl w-full max-w-4xl shadow-2xl max-h-[95vh] xl:max-h-[90vh] overflow-y-auto on-scrollbar border-2 border-border"
          >
            {/* Modal Header */}
            <div className="sticky top-0 bg-gradient-to-r from-card to-background px-4 xl:px-6 py-4 lg:py-5 border-b-2 border-border rounded-t-2xl z-10">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <h2 className="text-xl lg:text-2xl font-bold text-foreground">
                {trans.complaint_card.complaint_details || "Complaint Details"}
              </h2>
                <div className="flex items-center gap-3">
                  <span
                    className={`px-4 py-2 rounded-full text-xs xl:text-sm font-bold border ${getStatusColor(
                      selectedComplaint.status
                    )}`}
                  >
                    {trans.statuses[selectedComplaint.status] || selectedComplaint.status_display}
                  </span>
                  <button
                    onClick={() => setSelectedComplaint(null)}
                    className="p-2 hover:bg-muted rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                  >
                    <HiOutlineX className="w-6 h-6" />
                  </button>
                </div>
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-4 md:p-6 space-y-5 md:space-y-6">
              {/* Complaint Information */}
              <div className="bg-muted border-2 border-yellow-500/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-yellow-500 rounded-full"></span>
                  {trans.complaint_card.complaint_info || "Complaint Information"}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.complaint_card.complaint_id}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                      #{selectedComplaint.id}
                    </p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                    {trans.complaint_card.type}
                  </p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-words">
                      {trans.complaint_types[selectedComplaint.complaint_type] || selectedComplaint.complaint_type_display}
                  </p>
                </div>
                  <div className="bg-card p-3 rounded-lg border border-border sm:col-span-2">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                    {trans.complaint_card.created_at}
                  </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                      {new Date(selectedComplaint.created_at).toLocaleDateString(
                      locale === "ar" ? "ar-EG" : "en-US",
                      {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      }
                    )}
                  </p>
                  </div>
                </div>
              </div>

              {/* Title & Description */}
              <div className="bg-muted border-2 border-blue-400/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-blue-500 rounded-full"></span>
                  {trans.complaint_card.complaint_content || "Complaint Content"}
                </h3>
                <div className="space-y-4">
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-2">
                      {trans.complaint_card.title}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-words">
                      {selectedComplaint.title}
                    </p>
              </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-2">
                  {trans.complaint_card.description}
                    </p>
                    <p className="text-foreground text-sm md:text-base break-words whitespace-pre-wrap">
                  {selectedComplaint.description}
                </p>
                  </div>
                </div>
              </div>

              {/* Complainant Info */}
              {selectedComplaint.complainant && (
                <div className="bg-muted border-2 border-emerald-400/50 rounded-xl p-4 md:p-5">
                  <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-emerald-500 rounded-full"></span>
                    {trans.complaint_card.complainant_info || "Complainant Information"}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.complaint_card.full_name || "Full Name"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedComplaint.complainant.full_name}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.complaint_card.phone_number || "Phone Number"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedComplaint.complainant.phone_number}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.complaint_card.email || "Email"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-all">
                        {selectedComplaint.complainant.email}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.complaint_card.account_type || "Account Type"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base capitalize break-words">
                        {selectedComplaint.complainant.account_type}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Trip Data */}
              {selectedComplaint.trip_data && (
                <div className="bg-muted border-2 border-indigo-400/50 rounded-xl p-4 md:p-5">
                  <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-indigo-500 rounded-full"></span>
                    {trans.complaint_card.trip_info || "Trip Information"}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.complaint_card.trip_id || "Trip ID"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base">
                        #{selectedComplaint.trip_data.id}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.complaint_card.trip_date}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedComplaint.trip_data.trip_date}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.complaint_card.trip_time || "Trip Time"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedComplaint.trip_data.trip_time}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.complaint_card.distance || "Distance"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base">
                        {selectedComplaint.trip_data.distance_miles} miles
                      </p>
                    </div>
                    {selectedComplaint.trip_data.expected_trip_duration_minutes && (
                      <div className="bg-card p-3 rounded-lg border border-border sm:col-span-2">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.complaint_card.duration || "Expected Duration"}
                      </p>
                        <p className="font-semibold text-foreground text-sm md:text-base">
                          {selectedComplaint.trip_data.expected_trip_duration_minutes} minutes
                      </p>
                    </div>
                    )}
                  </div>

                  {/* Passenger Info */}
                  {selectedComplaint.trip_data.passenger_info && (
                    <div className="mt-4 pt-4 border-t border-indigo-500/30">
                      <h4 className="text-sm md:text-base font-bold text-foreground mb-3">
                        {trans.complaint_card.passenger_info || "Passenger Information"}
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="bg-card p-3 rounded-lg border border-border">
                          <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                            {trans.complaint_card.name || "Name"}
                          </p>
                          <p className="font-semibold text-foreground text-sm md:text-base break-words">
                            {selectedComplaint.trip_data.passenger_info.first_name}{" "}
                            {selectedComplaint.trip_data.passenger_info.last_name}
                          </p>
                        </div>
                        <div className="bg-card p-3 rounded-lg border border-border">
                          <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                            {trans.complaint_card.phone_number || "Phone"}
                          </p>
                          <p className="font-semibold text-foreground text-sm md:text-base break-words">
                            {selectedComplaint.trip_data.passenger_info.phone_number}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Driver Info */}
                  {selectedComplaint.trip_data.driver_info && (
                    <div className="mt-4 pt-4 border-t border-indigo-500/30">
                      <h4 className="text-sm md:text-base font-bold text-foreground mb-3">
                        {trans.complaint_card.driver_info || "Driver Information"}
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="bg-card p-3 rounded-lg border border-border">
                          <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                            {trans.complaint_card.name || "Name"}
                          </p>
                          <p className="font-semibold text-foreground text-sm md:text-base break-words">
                            {selectedComplaint.trip_data.driver_info.first_name}{" "}
                            {selectedComplaint.trip_data.driver_info.last_name}
                          </p>
                        </div>
                        <div className="bg-card p-3 rounded-lg border border-border">
                          <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                            {trans.complaint_card.phone_number || "Phone"}
                          </p>
                          <p className="font-semibold text-foreground text-sm md:text-base break-words">
                            {selectedComplaint.trip_data.driver_info.phone_number}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Admin Response */}
              {selectedComplaint.admin_response && (
                <div className="bg-muted border-2 border-orange-400/50 rounded-xl p-4 md:p-5">
                  <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-orange-500 rounded-full"></span>
                    {trans.complaint_card.admin_response}
                  </h3>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-foreground text-sm md:text-base break-words whitespace-pre-wrap">
                    {selectedComplaint.admin_response}
                  </p>
                  </div>
                </div>
              )}

              {/* Resolved At */}
              {selectedComplaint.resolved_at && (
                <div className="bg-muted border-2 border-green-400/50 rounded-xl p-4 md:p-5">
                  <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-green-500 rounded-full"></span>
                    {trans.complaint_card.resolution_info || "Resolution Information"}
                  </h3>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                    {trans.complaint_card.resolved_at}
                  </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                      {new Date(selectedComplaint.resolved_at).toLocaleDateString(
                      locale === "ar" ? "ar-EG" : "en-US",
                      {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      }
                    )}
                  </p>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="sticky bottom-0 bg-gradient-to-r from-card to-background px-4 xl:px-6 py-4 lg:py-5 border-t-2 border-border rounded-b-2xl flex flex-col sm:flex-row justify-end gap-3">
              <Button
                onClick={() => {
                  setShowUpdateStatusModal(true);
                }}
                className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-black font-semibold"
              >
                <FaEdit className="w-4 h-4" />
                {trans.complaint_card.update_status || "Update Status"}
              </Button>
              <Button
                onClick={() => setSelectedComplaint(null)}
                variant="outline"
                className="border-border text-foreground hover:bg-muted"
              >
                {trans.complaint_card.close || "Close"}
              </Button>
            </div>
            </div>
          </div>
        )}

      {/* Update Status Modal */}
      <UpdateStatusForm
        isOpen={showUpdateStatusModal}
        onClose={() => {
          setShowUpdateStatusModal(false);
          setSelectedComplaint(null);
        }}
        onSubmit={handleUpdateStatus}
        isLoading={actionLoading}
        trans={trans}
        locale={locale}
        currentStatus={selectedComplaint?.status}
      />
    </div>
  );
}

// Update Status Form Component
function UpdateStatusForm({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
  trans,
  locale,
  currentStatus,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { admin_response: string; status: string }) => void;
  isLoading: boolean;
  trans: any;
  locale: Locale;
  currentStatus?: string;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<{ admin_response: string; status: string }>({
    defaultValues: {
      status: currentStatus || "pending",
    },
  });

  const selectedStatus = watch("status");

  const handleFormSubmit = (data: { admin_response: string; status: string }) => {
    onSubmit(data);
    reset();
  };

  // Status options based on enum
  const statusOptions = [
    { value: "pending", label: trans.statuses.pending || "Pending" },
    { value: "under_review", label: trans.statuses.under_review || "Under Review" },
    { value: "resolved", label: trans.statuses.resolved || "Resolved" },
    { value: "closed", label: trans.statuses.closed || "Closed" },
  ];

  if (!isOpen) return null;

  return (
    <GlobalModal isOpen={isOpen} onClose={onClose}>
      <div className="bg-white rounded-xl p-6 max-w-lg w-full">
        <h1 className="font-bold text-lg mb-4 text-gray-900">
          {trans.complaint_card.update_status || "Update Complaint Status"}
        </h1>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4 text-[16px]">
          <div>
            <label className="block mb-2 text-start text-gray-700">
              {trans.complaint_card.status || "Status"}{" "}
              <span className="text-red-500">*</span>
            </label>
            <select
              {...register("status", { required: true })}
              className="p-2 w-full bg-white rounded-lg border border-gray-300 text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block mb-2 text-start text-gray-700">
              {trans.complaint_card.admin_response || "Admin Response"}{" "}
              <span className="text-red-500">*</span>
            </label>
            <textarea
              rows={4}
              {...register("admin_response", {
                required: trans.complaint_card.response_required ||
                  "Response is required",
              })}
              placeholder={
                selectedStatus === "resolved"
                  ? trans.complaint_card.resolution_placeholder ||
                    "Enter resolution details..."
                  : trans.complaint_card.response_placeholder ||
                    "Enter your response..."
              }
              className="p-2 w-full bg-white rounded-lg border border-gray-300 text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            {errors.admin_response && (
              <p className="text-red-500 text-sm mt-1">
                {errors.admin_response.message}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-300 rounded-md p-2 font-bold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {trans.complaint_card.cancel || "Cancel"}
            </button>
            <Button type="submit" className="flex-1" disabled={isLoading}>
              {isLoading
                ? trans.complaint_card.updating || "Updating..."
                : trans.complaint_card.update || "Update Status"}
            </Button>
          </div>
        </form>
      </div>
    </GlobalModal>
  );
}
