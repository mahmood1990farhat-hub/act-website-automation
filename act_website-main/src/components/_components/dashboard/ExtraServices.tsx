"use client";

import React, { useState } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Locale } from "../../../../i18n.config";
import { fetchData } from "@/lib/api/fetchData";
import { postData } from "@/lib/api/postData";
import { putData } from "@/lib/api/putApi";
import { deleteData } from "@/lib/api/deleteApi";
import { toast } from "react-toastify";
import { Button } from "@/components/ui/button";
import IsLoading from "../ISloading";
import GlobalModal from "../GlobalModal";
import Pagination from "../Pagination";
import { extract_error } from "@/lib/api/errorApi";
import { FaCheckCircle, FaEdit, FaPlus, FaTimesCircle, FaTrash } from "react-icons/fa";

type NestedName = {
  id: number;
  name_en: string;
  name_ar: string;
};

type ExtraServiceFee = {
  id: number;
  service_key: string;
  service_name_en: string;
  service_name_ar: string;
  airport: NestedName | null;
  vehicle_type: NestedName | null;
  direction: "pickup" | "dropoff" | "both";
  fee_amount: string;
  pricing_mode: "fixed_fee" | "per_item";
  priority: number;
  is_active: boolean;
  order: number;
};

type ExtraServicesResponse = {
  success: boolean;
  message: string;
  data: ExtraServiceFee[];
  pagination: {
    count: number;
    num_pages: number;
    current_page: number;
    page_size: number;
  };
};

type Airport = {
  id: number;
  name_en: string;
  name_ar: string;
};

type VehicleType = {
  id: number;
  name_en: string;
  name_ar: string;
};

type ExtraServiceFormData = {
  service_key: string;
  service_name_en: string;
  service_name_ar: string;
  airport_id: string;
  vehicle_type_id: string;
  direction: "pickup" | "dropoff" | "both";
  fee_amount: string;
  pricing_mode: "fixed_fee" | "per_item";
  priority: number;
  is_active: boolean;
  order: number;
};

type ExtraServicesProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

const serviceOptions = [
  { value: "meet_greet", label: "Meet & Greet Service", ar: "خدمة الاستقبال والمرافقة" },
  { value: "child_seat", label: "Child Seat", ar: "مقعد طفل" },
  { value: "infant_seat", label: "Infant Seat", ar: "مقعد رضيع" },
  { value: "booster_seat", label: "Booster Seat", ar: "مقعد معزز" },
  { value: "wheelchair_assistance", label: "Wheelchair Assistance", ar: "مساعدة كرسي متحرك" },
];

const defaultValues: ExtraServiceFormData = {
  service_key: "meet_greet",
  service_name_en: "Meet & Greet Service",
  service_name_ar: "خدمة الاستقبال والمرافقة",
  airport_id: "",
  vehicle_type_id: "",
  direction: "pickup",
  fee_amount: "0.00",
  pricing_mode: "fixed_fee",
  priority: 0,
  is_active: true,
  order: 0,
};

const directionLabels: Record<ExtraServiceFee["direction"], string> = {
  pickup: "Pickup",
  dropoff: "Drop-off",
  both: "Both",
};

export default function ExtraServices({ trans, token, locale }: ExtraServicesProps) {
  const [page, setPage] = useState(1);
  const [showFormModal, setShowFormModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedFee, setSelectedFee] = useState<ExtraServiceFee | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<ExtraServiceFormData>({ defaultValues });

  const {
    data: feesData,
    isLoading,
    error,
  } = useQuery<ExtraServicesResponse>({
    queryKey: ["extra-services", page, token, locale],
    queryFn: async () =>
      fetchData({
        endpoint: "/api/pricing/extra-services/",
        token,
        queryParams: {
          locale,
          page: page.toString(),
          page_size: "10",
        },
      }),
    enabled: !!token,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const { data: airportsData = [] } = useQuery<Airport[]>({
    queryKey: ["airports", locale],
    queryFn: async () => {
      const response = await fetchData<Airport[] | { data: Airport[] }>({
        endpoint: "/api/trips/list-airports/",
        token,
        queryParams: { locale },
      });
      if (Array.isArray(response)) return response;
      if (response && typeof response === "object" && "data" in response) return response.data;
      return [];
    },
    enabled: !!token,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const { data: vehicleTypesData = [] } = useQuery<VehicleType[]>({
    queryKey: ["vehicle-types"],
    queryFn: async () =>
      fetchData<VehicleType[]>({ endpoint: "/api/vehicle/vehicle-types/" }),
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const createMutation = useMutation({
    mutationFn: (data: Record<string, any>) =>
      postData({
        endpoint: "/api/pricing/extra-services/",
        token,
        body: data,
        queryParams: { locale },
        noToast: false,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["extra-services"] });
      setShowFormModal(false);
      reset(defaultValues);
      setSelectedFee(null);
      setIsEditing(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, any> }) =>
      putData({
        endpoint: `/api/pricing/extra-services/${id}/`,
        token,
        body: data,
        queryParams: { locale },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["extra-services"] });
      toast.success("Extra service fee updated successfully");
      setShowFormModal(false);
      reset(defaultValues);
      setSelectedFee(null);
      setIsEditing(false);
    },
    onError: (err: any) => {
      toast.error(extract_error(err) || err?.message || "Failed to update extra service fee");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      deleteData({
        endpoint: `/api/pricing/extra-services/${id}`,
        token,
        queryParams: { locale },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["extra-services"] });
      toast.success("Extra service fee deleted successfully");
      setShowDeleteModal(false);
      setSelectedFee(null);
    },
    onError: (err: any) => {
      toast.error(extract_error(err) || err?.message || "Failed to delete extra service fee");
    },
  });

  const fees = feesData?.data || [];
  const pagination = feesData?.pagination || {
    count: 0,
    num_pages: 1,
    current_page: 1,
    page_size: 10,
  };

  const handleCreate = () => {
    setIsEditing(false);
    setSelectedFee(null);
    reset(defaultValues);
    setShowFormModal(true);
  };

  const handleEdit = (fee: ExtraServiceFee) => {
    setIsEditing(true);
    setSelectedFee(fee);
    reset({
      service_key: fee.service_key,
      service_name_en: fee.service_name_en,
      service_name_ar: fee.service_name_ar,
      airport_id: fee.airport?.id ? fee.airport.id.toString() : "",
      vehicle_type_id: fee.vehicle_type?.id ? fee.vehicle_type.id.toString() : "",
      direction: fee.direction,
      fee_amount: fee.fee_amount,
      pricing_mode: fee.pricing_mode,
      priority: fee.priority,
      is_active: fee.is_active,
      order: fee.order,
    });
    setShowFormModal(true);
  };

  const handleDelete = (fee: ExtraServiceFee) => {
    setSelectedFee(fee);
    setShowDeleteModal(true);
  };

  const buildPayload = (data: ExtraServiceFormData) => ({
    service_key: data.service_key,
    service_name_en: data.service_name_en,
    service_name_ar: data.service_name_ar,
    airport_id: data.airport_id ? Number(data.airport_id) : null,
    vehicle_type_id: data.vehicle_type_id ? Number(data.vehicle_type_id) : null,
    direction: data.direction,
    fee_amount: data.fee_amount,
    pricing_mode: data.pricing_mode,
    priority: data.priority,
    is_active: data.is_active,
    order: data.order,
  });

  const onSubmit: SubmitHandler<ExtraServiceFormData> = (data) => {
    const payload = buildPayload(data);
    if (isEditing && selectedFee) {
      updateMutation.mutate({ id: selectedFee.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <IsLoading />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card rounded-xl shadow-xl border-2 border-border p-6">
        <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
          <p className="text-red-700 font-medium">Failed to load extra service fees. Please try again.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <Button
          onClick={handleCreate}
          className="w-full sm:w-auto bg-primary hover:bg-primary/90 text-foreground font-semibold shadow-lg shadow-primary/30 text-sm md:text-base"
        >
          <FaPlus className="mr-2" />
          Add Extra Service Fee
        </Button>
      </div>

      {fees.length === 0 ? (
        <div className="bg-card rounded-xl shadow-xl border-2 border-border p-8 md:p-12 text-center">
          <p className="text-muted-foreground text-base md:text-lg">
            No extra service fees found
          </p>
        </div>
      ) : (
        <>
          <div className="hidden xl:block">
            <div className="bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[900px] text-xs md:text-sm">
                  <thead>
                    <tr className="border-b-2 border-border bg-gray-100 dark:bg-gray-800">
                      {["Service", "Airport", "Vehicle Type", "Direction", "Mode", "Fee", "Priority", "Status", "Actions"].map((label) => (
                        <th key={label} className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {fees.map((fee) => (
                      <tr key={fee.id} className="border-b border-border hover:bg-muted transition-colors">
                        <td className="py-3 px-4 font-bold text-foreground">
                          {locale === "ar" ? fee.service_name_ar : fee.service_name_en}
                        </td>
                        <td className="py-3 px-4 text-foreground">
                          {fee.airport ? (locale === "ar" ? fee.airport.name_ar : fee.airport.name_en) : "All airports"}
                        </td>
                        <td className="py-3 px-4 text-foreground">
                          {fee.vehicle_type ? (locale === "ar" ? fee.vehicle_type.name_ar : fee.vehicle_type.name_en) : "All vehicles"}
                        </td>
                        <td className="py-3 px-4 text-foreground">{directionLabels[fee.direction]}</td>
                        <td className="py-3 px-4 text-foreground">{fee.pricing_mode === "per_item" ? "Per item" : "Fixed fee"}</td>
                        <td className="py-3 px-4 text-foreground font-semibold">GBP {fee.fee_amount}</td>
                        <td className="py-3 px-4 text-foreground font-semibold">{fee.priority}</td>
                        <td className="py-3 px-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-bold ${fee.is_active ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"}`}>
                            {fee.is_active ? <FaCheckCircle className="mr-1" /> : <FaTimesCircle className="mr-1" />}
                            {fee.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center justify-center gap-2">
                            <Button onClick={() => handleEdit(fee)} variant="ghost" className="p-1.5 hover:bg-muted text-yellow-600 hover:text-yellow-700">
                              <FaEdit className="text-base" />
                            </Button>
                            <Button onClick={() => handleDelete(fee)} variant="ghost" className="p-1.5 hover:bg-muted text-red-600 hover:text-red-700">
                              <FaTrash className="text-base" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="xl:hidden space-y-4">
            {fees.map((fee) => (
              <div key={fee.id} className="bg-card rounded-xl shadow-lg border-2 border-border p-4">
                <div className="flex items-start justify-between mb-3 pb-3 border-b-2 border-border">
                  <div>
                    <h3 className="font-bold text-base md:text-lg text-foreground">
                      {locale === "ar" ? fee.service_name_ar : fee.service_name_en}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {fee.airport ? (locale === "ar" ? fee.airport.name_ar : fee.airport.name_en) : "All airports"} / {fee.vehicle_type ? (locale === "ar" ? fee.vehicle_type.name_ar : fee.vehicle_type.name_en) : "All vehicles"}
                    </p>
                  </div>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${fee.is_active ? "bg-green-50 text-green-700 border-green-200" : "bg-red-50 text-red-700 border-red-200"}`}>
                    {fee.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="bg-muted/50 p-2 rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Direction</p>
                    <p className="font-semibold text-sm text-foreground">{directionLabels[fee.direction]}</p>
                  </div>
                  <div className="bg-muted/50 p-2 rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Fee</p>
                    <p className="font-semibold text-sm text-foreground">GBP {fee.fee_amount}</p>
                  </div>
                  <div className="bg-muted/50 p-2 rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Priority</p>
                    <p className="font-semibold text-sm text-foreground">{fee.priority}</p>
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                  <Button onClick={() => handleEdit(fee)} variant="ghost" className="p-2 hover:bg-muted text-yellow-600 hover:text-yellow-700">
                    <FaEdit className="text-base" />
                  </Button>
                  <Button onClick={() => handleDelete(fee)} variant="ghost" className="p-2 hover:bg-muted text-red-600 hover:text-red-700">
                    <FaTrash className="text-base" />
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {pagination.num_pages > 1 && (
            <div className="flex flex-col items-center gap-3 pt-4">
              <div className="text-xs text-muted-foreground">
                Page {page} of {pagination.num_pages} pages
              </div>
              <Pagination
                currentPage={page}
                onPageChange={setPage}
                locale={locale}
                totalPages={pagination.num_pages}
              />
            </div>
          )}
        </>
      )}

      <GlobalModal
        isOpen={showFormModal}
        onClose={() => {
          if (!createMutation.isPending && !updateMutation.isPending) {
            setShowFormModal(false);
            reset(defaultValues);
            setSelectedFee(null);
            setIsEditing(false);
          }
        }}
      >
        <div className="p-4 md:p-6 w-full">
          <h2 className="text-lg md:text-xl font-bold text-foreground mb-4 md:mb-6">
            {isEditing ? "Edit Extra Service Fee" : "Create Extra Service Fee"}
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Service</label>
                <select
                  {...register("service_key", { required: true })}
                  onChange={(event) => {
                    const option = serviceOptions.find((item) => item.value === event.target.value);
                    setValue("service_key", event.target.value);
                    if (option) {
                      setValue("service_name_en", option.label);
                      setValue("service_name_ar", option.ar);
                    }
                  }}
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary"
                >
                  {serviceOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Direction</label>
                <select {...register("direction", { required: true })} className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary">
                  <option value="pickup">Pickup</option>
                  <option value="dropoff">Drop-off</option>
                  <option value="both">Both</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Service Name EN</label>
                <input {...register("service_name_en", { required: true })} className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary" />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Service Name AR</label>
                <input {...register("service_name_ar", { required: true })} className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary" />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Airport</label>
                <select {...register("airport_id")} className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary">
                  <option value="">All airports</option>
                  {airportsData.map((airport) => (
                    <option key={airport.id} value={airport.id}>{locale === "ar" ? airport.name_ar : airport.name_en}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Vehicle Type</label>
                <select {...register("vehicle_type_id")} className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary">
                  <option value="">All vehicles</option>
                  {vehicleTypesData.map((vehicle) => (
                    <option key={vehicle.id} value={vehicle.id}>{locale === "ar" ? vehicle.name_ar : vehicle.name_en}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Fee Amount — final customer price, including VAT
                </label>
                <input
                  type="text"
                  {...register("fee_amount", {
                    required: true,
                    pattern: /^\d+(\.\d{1,2})?$/,
                  })}
                  placeholder="15.00"
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary"
                />
                {errors.fee_amount && <p className="text-error text-sm mt-1">Invalid fee amount</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Pricing Mode</label>
                <select {...register("pricing_mode", { required: true })} className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary">
                  <option value="fixed_fee">Fixed fee</option>
                  <option value="per_item">Per item</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Order</label>
                <input
                  type="number"
                  {...register("order", { required: true, valueAsNumber: true, min: 0 })}
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Priority</label>
                <input
                  type="number"
                  {...register("priority", { required: true, valueAsNumber: true, min: 0 })}
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary"
                />
                {errors.priority && <p className="text-error text-sm mt-1">Priority must be 0 or higher</p>}
              </div>

              <div className="flex items-center pt-7">
                <label className="flex items-center cursor-pointer group">
                  <input
                    type="checkbox"
                    {...register("is_active")}
                    className="w-5 h-5 text-primary bg-background border-2 border-border rounded focus:ring-2 focus:ring-primary focus:ring-offset-2 cursor-pointer"
                  />
                  <span className="ml-3 text-sm font-medium text-foreground group-hover:text-primary">
                    Active
                  </span>
                </label>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-4 border-t-2 border-border">
              <Button type="button" variant="secondary" onClick={() => setShowFormModal(false)} className="w-full sm:flex-1 font-semibold">
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="w-full sm:flex-1 font-semibold bg-primary hover:bg-primary/90 text-foreground shadow-lg shadow-primary/30"
              >
                {createMutation.isPending || updateMutation.isPending ? "Saving..." : isEditing ? "Update" : "Create"}
              </Button>
            </div>
          </form>
        </div>
      </GlobalModal>

      <GlobalModal
        isOpen={showDeleteModal}
        onClose={() => {
          if (!deleteMutation.isPending) {
            setShowDeleteModal(false);
            setSelectedFee(null);
          }
        }}
      >
        <div className="p-4 md:p-6 w-full">
          <h2 className="text-lg md:text-xl font-bold text-foreground mb-4">Delete Extra Service Fee</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Are you sure you want to delete this extra service fee? This action cannot be undone.
          </p>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mt-4">
            <Button type="button" variant="secondary" onClick={() => setShowDeleteModal(false)} className="w-full sm:flex-1 font-semibold">
              Cancel
            </Button>
            <Button
              type="button"
              onClick={() => selectedFee && deleteMutation.mutate(selectedFee.id)}
              disabled={deleteMutation.isPending}
              className="w-full sm:flex-1 font-semibold bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30 disabled:opacity-60"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </div>
        </div>
      </GlobalModal>
    </div>
  );
}
