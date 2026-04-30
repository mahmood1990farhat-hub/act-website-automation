"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import { Locale } from "../../../../i18n.config";
import IsLoading from "../ISloading";
import Pagination from "../Pagination";
import { FaExclamationTriangle, FaPlus, FaList, FaStar } from "react-icons/fa";
import { toast } from "react-toastify";
import { extract_error } from "@/lib/api/errorApi";

type ComplaintsProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

export default function Complaints({ trans, token, locale }: ComplaintsProps) {
  const [activeTab, setActiveTab] = useState<"list" | "submit">("list");
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  
  const queryClient = useQueryClient();

  // Fetch complaints
  const { data: complaintsData, isLoading: complaintsLoading } = useQuery<any>({
    queryKey: ["complaints", page, filterStatus, filterType],
    queryFn: () =>
      fetchData({
        endpoint: "/api/complaints/passenger/complaints/",
        token: token,
        queryParams: {
          page: page.toString(),
          page_size: "10",
          ...(filterStatus && { status: filterStatus }),
          ...(filterType && { complaint_type: filterType }),
        },
      }),
    enabled: activeTab === "list",
  });

  // Fetch user's completed trips for the dropdown (only completed trips can be complained about)
  const { data: tripsData } = useQuery<any>({
    queryKey: ["trips-for-complaints"],
    queryFn: () =>
      fetchData({
        endpoint: "/api/trips/list-trips/",
        token: token,
        queryParams: {
          page_size: "100",
          trip_status: "completed",
          locale: locale,
        },
      }),
    enabled: activeTab === "submit",
  });

  const complaints = complaintsData?.data?.complaints || [];
  const stats = complaintsData?.data?.stats || {};
  const pagination = complaintsData?.data?.pagination || {};
  const trips = tripsData?.trips || [];

  // Submit complaint mutation
  const submitMutation = useMutation({
    mutationFn: async (formData: any) => {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/complaints/passenger/complaints/submit/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(formData),
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to submit complaint");
      }
      
      return response.json();
    },
    onSuccess: () => {
      toast.success(trans.submit_form.success_message);
      queryClient.invalidateQueries({ queryKey: ["complaints"] });
      setActiveTab("list");
      setFormData({
        trip: "",
        complaint_type: "",
        title: "",
        description: "",
      });
    },
    onError: (error: any) => {
      const errorMessage = extract_error(error) || error?.message || trans.submit_form.error_message;
      toast.error(errorMessage);
    },
  });

  const [formData, setFormData] = useState({
    trip: "",
    complaint_type: "",
    title: "",
    description: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!formData.trip) {
      toast.error(trans.submit_form.validation.trip_required);
      return;
    }
    if (!formData.complaint_type) {
      toast.error(trans.submit_form.validation.type_required);
      return;
    }
    if (!formData.title || formData.title.length < 5) {
      toast.error(trans.submit_form.validation.title_min);
      return;
    }
    if (!formData.description || formData.description.length < 20) {
      toast.error(trans.submit_form.validation.description_min);
      return;
    }

    submitMutation.mutate({
      trip: parseInt(formData.trip),
      complaint_type: formData.complaint_type,
      title: formData.title,
      description: formData.description,
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
      case "under_review":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      case "resolved":
        return "bg-green-500/20 text-green-400 border-green-500/30";
      case "closed":
        return "bg-gray-500/20 text-gray-400 border-gray-500/30";
      default:
        return "bg-gray-500/20 text-gray-400 border-gray-500/30";
    }
  };

  return (
    <div className="w-full">
      {/* Header with Stats */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-primary/20 p-3 rounded-lg">
            <FaExclamationTriangle className="text-primary text-2xl" />
          </div>
          <div>
            <h1 className="font-bold text-2xl md:text-3xl text-white">
              {trans.title}
            </h1>
            <p className="text-gray-400 text-sm mt-1">{trans.subtitle}</p>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
          {Object.entries(stats).map(([key, value]: [string, any]) => (
            <div
              key={key}
              className="bg-foreground/50 backdrop-blur-sm rounded-lg p-4 border border-muted/10"
            >
              <p className="text-gray-400 text-xs mb-1">{trans.stats[key]}</p>
              <p className="text-white text-xl font-bold">{value}</p>
            </div>
          ))}
        </div>

        {/* Tab Buttons */}
        <div className="bg-foreground/50 backdrop-blur-sm rounded-xl p-2 border border-muted/10">
          <div className="flex items-center justify-start gap-2">
            <button
              onClick={() => setActiveTab("list")}
              className={`
                px-4 py-2.5 rounded-lg text-sm md:text-base font-semibold
                transition-all duration-300 ease-in-out flex items-center gap-2
                ${
                  activeTab === "list"
                    ? "bg-primary text-black shadow-lg shadow-primary/30"
                    : "bg-transparent text-gray-300 hover:bg-muted/20 hover:text-white"
                }
              `}
            >
              <FaList />
              {trans.tabs.my_complaints}
            </button>
            <button
              onClick={() => setActiveTab("submit")}
              className={`
                px-4 py-2.5 rounded-lg text-sm md:text-base font-semibold
                transition-all duration-300 ease-in-out flex items-center gap-2
                ${
                  activeTab === "submit"
                    ? "bg-primary text-black shadow-lg shadow-primary/30"
                    : "bg-transparent text-gray-300 hover:bg-muted/20 hover:text-white"
                }
              `}
            >
              <FaPlus />
              {trans.tabs.submit_complaint}
            </button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      {activeTab === "list" ? (
        <div>
          {/* Filters */}
          <div className="bg-foreground/50 backdrop-blur-sm rounded-xl p-4 mb-6 border border-muted/10">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Status Filter */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.complaint_list.filter.status_label}
                </label>
                <select
                  value={filterStatus}
                  onChange={(e) => {
                    setFilterStatus(e.target.value);
                    setPage(1);
                  }}
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary"
                >
                  <option value="" className="bg-foreground text-gray-400">{trans.complaint_list.filter.all}</option>
                  {Object.keys(trans.statuses).map((status) => (
                    <option key={status} value={status} className="bg-foreground text-white">
                      {trans.statuses[status]}
                    </option>
                  ))}
                </select>
              </div>

              {/* Type Filter */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.complaint_list.filter.type_label}
                </label>
                <select
                  value={filterType}
                  onChange={(e) => {
                    setFilterType(e.target.value);
                    setPage(1);
                  }}
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary"
                >
                  <option value="" className="bg-foreground text-gray-400">{trans.complaint_list.filter.all}</option>
                  {Object.keys(trans.complaint_types).map((type) => (
                    <option key={type} value={type} className="bg-foreground text-white">
                      {trans.complaint_types[type]}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Complaints List */}
          {complaintsLoading ? (
            <div className="flex items-center justify-center py-20">
              <IsLoading />
            </div>
          ) : complaints.length === 0 ? (
            <div className="bg-foreground/30 backdrop-blur-sm rounded-xl p-12 border border-muted/10 text-center">
              <FaExclamationTriangle className="text-gray-500 text-5xl mx-auto mb-4" />
              <p className="text-gray-400 text-lg">{trans.complaint_list.empty}</p>
            </div>
          ) : (
            <div className="space-y-4">
              {complaints.map((complaint: any) => (
                <div
                  key={complaint.id}
                  className="bg-foreground/50 backdrop-blur-sm rounded-xl p-6 border border-muted/10 hover:border-primary/30 transition-all duration-300"
                >
                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3 flex-wrap">
                        <span
                          className={`px-3 py-1 rounded-lg text-xs font-semibold border ${getStatusColor(
                            complaint.status
                          )}`}
                        >
                          {trans.statuses[complaint.status] || complaint.status_display}
                        </span>
                        <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-primary/20 text-primary border border-primary/30">
                          {trans.complaint_types[complaint.complaint_type] || complaint.complaint_type_display}
                        </span>
                        <span className="text-gray-400 text-sm">
                          {trans.complaint_card.complaint_id}: #{complaint.id}
                        </span>
                      </div>
                      
                      <h3 className="text-white text-lg font-bold mb-2">
                        {complaint.title}
                      </h3>
                      
                      <p className="text-gray-300 mb-3">{complaint.description}</p>
                      
                      <div className="flex items-center gap-4 text-sm flex-wrap">
                        {complaint.status === "resolved" ? (
                          <>
                            <span className="text-green-400 font-semibold">
                              ✓ {trans.complaint_card.resolved}
                            </span>
                            {/* Google Review Button - Always Visible */}
                            <a
                              href={process.env.NEXT_PUBLIC_GOOGLE_REVIEW_URL || "https://play.google.com/store/apps/details?id=YOUR_APP_ID"}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-2 bg-primary hover:bg-primary/90 text-black font-bold py-2 px-4 rounded-lg shadow-lg transition-all duration-300 hover:shadow-xl hover:scale-105"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <FaStar className="text-yellow-400" />
                              {trans.complaint_card.leave_review || "Leave a Review"}
                            </a>
                          </>
                        ) : (
                          <span className="text-yellow-400 font-semibold">
                            ⏳ {trans.complaint_card.not_resolved}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-sm text-gray-400 md:text-right">
                      {complaint.trip_data && (
                        <div className="mb-2">
                          <span className="block font-semibold text-white mb-1">
                            {trans.complaint_card.trip_date}
                          </span>
                          <span>{complaint.trip_data.trip_date}</span>
                        </div>
                      )}
                      <div>
                        <span className="block font-semibold text-white mb-1">
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

                  {complaint.admin_response && (
                    <div className="mt-4 p-4 bg-primary/10 border border-primary/20 rounded-lg">
                      <p className="text-gray-400 text-sm mb-1">
                        {trans.complaint_card.admin_response}:
                      </p>
                      <p className="text-white">{complaint.admin_response}</p>
                    </div>
                  )}

                  {complaint.resolved_at && (
                    <div className="mt-2 text-sm">
                      <span className="text-gray-400">
                        {trans.complaint_card.resolved_at}:{" "}
                      </span>
                      <span className="text-green-400">
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
        </div>
      ) : (
        /* Submit Form */
        <div className="bg-foreground/50 backdrop-blur-sm rounded-xl p-6 md:p-8 border border-muted/10">
          <h2 className="text-white text-xl font-bold mb-2">
            {trans.submit_form.title}
          </h2>
          <p className="text-gray-400 mb-6">{trans.submit_form.subtitle}</p>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Two Column Layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Trip Selection */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.submit_form.fields.trip} <span className="text-primary">*</span>
                </label>
                <select
                  value={formData.trip}
                  onChange={(e) => setFormData({ ...formData, trip: e.target.value })}
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary"
                  required
                >
                  <option value="" className="bg-foreground text-gray-400">
                    {trans.submit_form.fields.trip_placeholder}
                  </option>
                  {trips.map((trip: any) => (
                    <option key={trip.id} value={trip.id} className="bg-foreground text-white">
                      Trip #{trip.id} - {trip.trip_date} {trip.trip_time}
                    </option>
                  ))}
                </select>
              </div>

              {/* Complaint Type */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.submit_form.fields.complaint_type} <span className="text-primary">*</span>
                </label>
                <select
                  value={formData.complaint_type}
                  onChange={(e) =>
                    setFormData({ ...formData, complaint_type: e.target.value })
                  }
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary"
                  required
                >
                  <option value="" className="bg-foreground text-gray-400">
                    {trans.submit_form.fields.complaint_type_placeholder}
                  </option>
                  {Object.keys(trans.complaint_types).map((type) => (
                    <option key={type} value={type} className="bg-foreground text-white">
                      {trans.complaint_types[type]}
                    </option>
                  ))}
                </select>
              </div>

              {/* Title */}
              <div className="md:col-span-2">
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.submit_form.fields.title} <span className="text-primary">*</span>
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) =>
                    setFormData({ ...formData, title: e.target.value })
                  }
                  placeholder={trans.submit_form.fields.title_placeholder}
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary placeholder:text-gray-400"
                  required
                />
              </div>
            </div>

            {/* Description - Full Width */}
            <div>
              <label className="block mb-2 text-[16px] text-gray-300">
                {trans.submit_form.fields.description} <span className="text-primary">*</span>
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder={trans.submit_form.fields.description_placeholder}
                className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary min-h-[150px] placeholder:text-gray-400"
                required
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitMutation.isPending}
              className="w-full bg-primary hover:bg-primary/90 text-black font-bold py-3 px-6 rounded-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitMutation.isPending
                ? trans.submit_form.button_loading
                : trans.submit_form.button}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

